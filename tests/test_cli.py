"""Tests for ropa_agent.cli. The reviewer is replaced by fakes."""

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from ropa_agent.cli import main
from ropa_agent.errors import RunStopError
from ropa_agent.reviewer import ReviewOutcome
from tests.helpers import make_output, write_csv

ENV = {"ANTHROPIC_AUTH_TOKEN": "test"}
ROW = ["2025-01-01", "Ann Lee"] + ["Customer emails kept for 2 years"] * 11


async def fake_review(payload, settings):  # pylint: disable=unused-argument
    """row-3 crashes; every other row is 'Not ready to submit'."""
    if payload["submission_id"] == "row-3":
        raise ValueError("bad row")
    return ReviewOutcome(
        make_output({"markets": "incomplete"}, payload["submission_id"]))


async def stopping_review(payload, settings):  # pylint: disable=unused-argument
    """Simulates a rejected API key."""
    raise RunStopError("key rejected")


class TestMain(unittest.TestCase):
    """End-to-end runs without the model."""

    def setUp(self):
        # Closed in tearDown, so a 'with' block is not possible here.
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.source = Path(self.tmp.name) / "form.csv"
        self.target = Path(self.tmp.name) / "form_reviewed.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, review):
        """Run main() with a test key; return (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict("os.environ", ENV, clear=True), \
                redirect_stdout(out), redirect_stderr(err):
            code = main([str(self.source)], review=review)
        return code, out.getvalue(), err.getvalue()

    def test_writes_reviewed_file(self):
        write_csv(self.source, [ROW, ROW])
        code, out, _ = self.run_main(fake_review)
        self.assertEqual(code, 0)
        self.assertIn("row-2: Not ready to submit", out)
        with self.target.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[1][1], "Ann Lee")
        self.assertEqual(rows[2][-6:-4], ["Escalate", "technical_error"])
        self.assertIn("ValueError: bad row", rows[2][-4])

    def test_missing_file_writes_nothing(self):
        code, _, err = self.run_main(fake_review)
        self.assertEqual(code, 1)
        self.assertIn("Input file not found", err)
        self.assertFalse(self.target.exists())

    def test_run_stop_during_review_writes_nothing(self):
        write_csv(self.source, [ROW])
        code, _, err = self.run_main(stopping_review)
        self.assertEqual(code, 1)
        self.assertIn("key rejected", err)
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
