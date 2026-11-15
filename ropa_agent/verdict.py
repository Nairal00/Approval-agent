"""Turn the per-question statuses into the final verdict (PRD section 7)."""

READY = "Ready to Submit"
NOT_READY = "Not ready to submit"
ESCALATE = "Escalate"

MODEL_UNSURE = "model_unsure"
QUOTE_CHECK_FAILED = "quote_check_failed"
TECHNICAL_ERROR = "technical_error"


def compute_verdict(statuses):
    """Return (verdict, escalation_cause) for a list of question statuses.

    statuses: list of "complete", "incomplete" or "unsure", one per question.
    escalation_cause is "" unless the verdict is ESCALATE.

    Only called when checks 2 and 3 passed, so the list always has 11
    valid statuses. Quote and technical failures are handled elsewhere.
    """
    # Check "unsure" first: a mix of unsure and incomplete must escalate.
    if "unsure" in statuses:
        return ESCALATE, MODEL_UNSURE
    if "incomplete" in statuses:
        return NOT_READY, ""
    return READY, ""
