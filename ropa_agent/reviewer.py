"""Call the agent for one row and redo up to MAX_REDOS times."""

from dataclasses import dataclass

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    ResultError,
    ResultMessage,
    query,
)

from ropa_agent.config import MAX_REDOS, MAX_TURNS, PROJECT_ROOT, SKILL_NAME
from ropa_agent.errors import RunStopError
from ropa_agent.payload import (
    OUTPUT_SCHEMA,
    SYSTEM_PROMPT,
    build_prompt,
    build_redo_prompt,
)
from ropa_agent.validators import check_completeness, check_quotes
from ropa_agent.verdict import QUOTE_CHECK_FAILED, TECHNICAL_ERROR

# HTTP statuses that mean every later row would fail the same way.
_FATAL_STATUSES = {
    401: "The API key was rejected (401). Check ANTHROPIC_AUTH_TOKEN.",
    402: "The API account has no balance left (402).",
}


@dataclass
class ReviewOutcome:
    """What happened to one row.

    output: the model's structured result, or None if there is none.
    cause: "" if all checks passed, otherwise an escalation_cause.
    detail: short explanation for the privacy team when cause is set.
    """

    output: dict | None
    cause: str = ""
    detail: str = ""


def build_options(settings, session_id=None):
    """Agent options: project skill only, no file or shell tools."""
    return ClaudeAgentOptions(
        cwd=str(PROJECT_ROOT),
        # Only the Skill tool exists; skills= limits it to our one skill.
        tools=["Skill"],
        skills=[SKILL_NAME],
        setting_sources=["project"],
        system_prompt=SYSTEM_PROMPT,
        output_format={"type": "json_schema", "schema": OUTPUT_SCHEMA},
        model=settings.model,
        max_turns=MAX_TURNS,
        resume=session_id,
    )


def _stop_if_fatal(status):
    if status in _FATAL_STATUSES:
        raise RunStopError(_FATAL_STATUSES[status])


async def _ask(prompt, options, run_query):
    """Send one message and return the final ResultMessage (or None)."""
    result = None
    try:
        async for message in run_query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result = message
    except ResultError as exc:
        _stop_if_fatal(exc.api_error_status)
        raise
    if result is not None:
        _stop_if_fatal(result.api_error_status)
    return result


async def review_row(payload, settings, run_query=query):
    """Review one submission. Raises RunStopError only for run-level errors."""
    prompt = build_prompt(payload)
    session_id = None
    for attempt in range(MAX_REDOS + 1):
        try:
            result = await _ask(prompt, build_options(settings, session_id),
                                run_query)
        except ClaudeSDKError as exc:
            return ReviewOutcome(None, TECHNICAL_ERROR,
                                 f"Model call failed: {exc}")

        if result is None or result.is_error or result.structured_output is None:
            reason = result.subtype if result is not None else "no result"
            return ReviewOutcome(None, TECHNICAL_ERROR,
                                 f"No structured result ({reason}).")

        output = result.structured_output
        incomplete = check_completeness(payload, output)
        bad_quotes = check_quotes(payload, output)
        if not incomplete and not bad_quotes:
            return ReviewOutcome(output)
        if attempt == MAX_REDOS:
            cause = QUOTE_CHECK_FAILED if bad_quotes else TECHNICAL_ERROR
            return ReviewOutcome(output, cause,
                                 " ".join(incomplete + bad_quotes))

        # Continue the same conversation so the agent sees its last answer.
        session_id = result.session_id
        prompt = build_redo_prompt(incomplete + bad_quotes)
    raise AssertionError("unreachable")  # pragma: no cover
