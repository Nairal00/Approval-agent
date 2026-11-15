"""Turn a review outcome into the text of the result columns."""

from ropa_agent.config import QUESTION_COLUMNS, QUESTION_IDS
from ropa_agent.verdict import ESCALATE, compute_verdict

_PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def _by_question(output):
    """question_id -> entry, in form order, skipping malformed entries."""
    entries = {}
    for item in (output or {}).get("questions") or []:
        if isinstance(item, dict) and item.get("question_id") in QUESTION_COLUMNS:
            entries.setdefault(item["question_id"], item)
    return [entries[qid] for qid in QUESTION_IDS if qid in entries]


def _label(item):
    """The question as the submitter saw it, e.g. '7. Where do you get the data?'."""
    return QUESTION_COLUMNS[item["question_id"]]


def format_missing_details(items):
    """Incomplete questions, highest priority first."""
    incomplete = [item for item in items if item.get("status") == "incomplete"]
    incomplete.sort(key=lambda item: _PRIORITY_ORDER.get(item.get("priority"), 3))
    lines = []
    for item in incomplete:
        quote = item.get("quoted_answer", "")
        said = f'You wrote: "{quote}".' if quote else "You left this blank."
        lines.append(f"[{item.get('priority')}] {_label(item)} - {said} "
                     f"{item.get('missing_detail', '')}")
    return "\n".join(lines)


def format_unsure(items):
    """Questions the model could not judge, with its reason."""
    return "\n".join(f"{_label(item)} - {item.get('unsure_reason', '')}"
                     for item in items if item.get("status") == "unsure")


def format_complete(items):
    """Questions that were answered well enough."""
    return "\n".join(_label(item)
                     for item in items if item.get("status") == "complete")


def to_columns(outcome):
    """Build the six result columns for one row.

    outcome.cause is "" when all checks passed; then the verdict is computed
    from the statuses. Otherwise the row is escalated with that cause.
    """
    items = _by_question(outcome.output)
    if outcome.cause:
        verdict, cause = ESCALATE, outcome.cause
    else:
        verdict, cause = compute_verdict([item["status"] for item in items])

    summary = (outcome.output or {}).get("summary", "")
    if outcome.detail:
        note = f"Automatic review problem: {outcome.detail}"
        summary = f"{summary}\n{note}" if summary else note

    return {
        "verdict": verdict,
        "escalation_cause": cause,
        "summary": summary,
        "missing_details": format_missing_details(items),
        "unsure_questions": format_unsure(items),
        "complete_questions": format_complete(items),
    }
