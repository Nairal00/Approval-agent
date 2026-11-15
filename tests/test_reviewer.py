"""Tests for ropa_agent.reviewer. The SDK is replaced by fake query functions."""

import asyncio
import unittest

from claude_agent_sdk import CLIConnectionError, ResultError, ResultMessage

from ropa_agent.config import MAX_REDOS, Settings
from ropa_agent.errors import RunStopError
from ropa_agent.reviewer import build_options, review_row
from tests.helpers import make_output, make_payload

SETTINGS = Settings(model="test-model")


def result_message(output=None, is_error=False, status=None, session="s1"):
    """A ResultMessage like the SDK yields at the end of a call."""
    return ResultMessage(
        subtype="error_during_execution" if is_error else "success",
        duration_ms=0, duration_api_ms=0, is_error=is_error, num_turns=1,
        session_id=session, structured_output=output,
        api_error_status=status)


class FakeQuery:  # pylint: disable=too-few-public-methods
    """Yields one scripted reply per call and records the calls."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def __call__(self, *, prompt, options):
        self.calls.append((prompt, options))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        yield "some other message"
        yield reply


def run(payload, fake):
    """Run review_row with the fake query."""
    return asyncio.run(review_row(payload, SETTINGS, run_query=fake))


class TestBuildOptions(unittest.TestCase):
    """Agent configuration."""

    def test_options(self):
        options = build_options(SETTINGS, "abc")
        self.assertEqual(options.tools, ["Skill"])
        self.assertEqual(options.skills, ["ropa-review"])
        self.assertEqual(options.setting_sources, ["project"])
        self.assertEqual(options.resume, "abc")
        self.assertEqual(options.model, "test-model")
        self.assertEqual(options.output_format["type"], "json_schema")


class TestReviewRow(unittest.TestCase):
    """The redo loop and error handling."""

    def setUp(self):
        self.payload = make_payload()

    def test_pass_first_time(self):
        fake = FakeQuery(result_message(make_output()))
        outcome = run(self.payload, fake)
        self.assertEqual(outcome.cause, "")
        self.assertEqual(len(fake.calls), 1)
        self.assertIsNone(fake.calls[0][1].resume)

    def test_redo_resumes_same_session(self):
        bad = make_output(submission_id="row-9")
        fake = FakeQuery(result_message(bad, session="first"),
                         result_message(make_output()))
        outcome = run(self.payload, fake)
        self.assertEqual(outcome.cause, "")
        self.assertEqual(fake.calls[1][1].resume, "first")
        self.assertIn("submission_id must be 'row-2'", fake.calls[1][0])

    def test_quote_failure_after_max_redos(self):
        bad = make_output()
        bad["questions"][0]["quoted_answer"] = "made up"
        fake = FakeQuery(*[result_message(bad)] * (MAX_REDOS + 1))
        outcome = run(self.payload, fake)
        self.assertEqual(outcome.cause, "quote_check_failed")
        self.assertEqual(len(fake.calls), MAX_REDOS + 1)
        self.assertIs(outcome.output, bad)

    def test_completeness_failure_after_max_redos(self):
        bad = make_output(submission_id="row-9")
        fake = FakeQuery(*[result_message(bad)] * (MAX_REDOS + 1))
        self.assertEqual(run(self.payload, fake).cause, "technical_error")

    def test_error_result_is_technical_error(self):
        fake = FakeQuery(result_message(None, is_error=True))
        outcome = run(self.payload, fake)
        self.assertEqual(outcome.cause, "technical_error")
        self.assertIn("error_during_execution", outcome.detail)

    def test_sdk_exception_is_technical_error(self):
        fake = FakeQuery(CLIConnectionError("boom"))
        outcome = run(self.payload, fake)
        self.assertEqual(outcome.cause, "technical_error")
        self.assertIn("boom", outcome.detail)

    def test_no_result_message(self):
        async def empty(*, prompt, options):  # pylint: disable=unused-argument
            return
            yield  # pylint: disable=unreachable

        outcome = asyncio.run(review_row(self.payload, SETTINGS, empty))
        self.assertEqual(outcome.detail, "No structured result (no result).")

    def test_bad_key_stops_run(self):
        error = ResultError("api", data={"api_error_status": 401})
        with self.assertRaises(RunStopError):
            run(self.payload, FakeQuery(error))

    def test_other_api_error_is_row_level(self):
        error = ResultError("api", data={"api_error_status": 529})
        self.assertEqual(run(self.payload, FakeQuery(error)).cause,
                         "technical_error")

    def test_no_balance_in_result_stops_run(self):
        fake = FakeQuery(result_message(None, is_error=True, status=402))
        with self.assertRaises(RunStopError):
            run(self.payload, fake)


if __name__ == "__main__":
    unittest.main()
