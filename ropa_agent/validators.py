"""Check 2 (completeness) and check 3 (quote truth) on the model output.

Each function returns a list of problems in plain English. An empty list
means the check passed. The problems are sent back to the agent as-is.
"""

from collections import Counter

from ropa_agent.config import QUESTION_IDS
from ropa_agent.payload import PRIORITIES


def normalize(text):
    """Ignore whitespace, line breaks and case when comparing quotes."""
    return "".join(text.split()).lower()


def _items(output):
    """The question entries that are well-formed enough to inspect."""
    questions = output.get("questions") if isinstance(output, dict) else None
    if not isinstance(questions, list):
        return []
    return [item for item in questions if isinstance(item, dict)]


def check_completeness(payload, output):
    """Check 2: every question answered once, required fields filled."""
    if not isinstance(output, dict) or not isinstance(
            output.get("questions"), list):
        return ["The result must be an object with a 'questions' list."]

    problems = []
    expected_id = payload["submission_id"]
    if output.get("submission_id") != expected_id:
        problems.append(f"submission_id must be '{expected_id}'.")

    counts = Counter(item.get("question_id") for item in _items(output))
    for qid in QUESTION_IDS:
        if counts[qid] == 0:
            problems.append(f"Question '{qid}' is missing.")
        elif counts[qid] > 1:
            problems.append(f"Question '{qid}' appears {counts[qid]} times.")

    for item in _items(output):
        qid = item.get("question_id")
        status = item.get("status")
        if status == "incomplete":
            if not str(item.get("missing_detail", "")).strip():
                problems.append(
                    f"Question '{qid}' is incomplete but missing_detail is empty.")
            if item.get("priority") not in PRIORITIES:
                problems.append(
                    f"Question '{qid}' is incomplete but has no priority "
                    "(High, Medium or Low).")
        elif status == "unsure":
            if not str(item.get("unsure_reason", "")).strip():
                problems.append(
                    f"Question '{qid}' is unsure but unsure_reason is empty.")
    return problems


def check_quotes(payload, output):
    """Check 3: every quoted_answer really appears in the original answer."""
    originals = {a["question_id"]: a["answer"] for a in payload["answers"]}
    problems = []
    for item in _items(output):
        qid = item.get("question_id")
        if qid not in originals:
            continue  # unknown ids are reported by check_completeness
        original = normalize(originals[qid])
        quote = normalize(str(item.get("quoted_answer", "")))
        if not original:
            if quote:
                problems.append(
                    f"Question '{qid}' was left blank, so quoted_answer "
                    "must be empty.")
        elif not quote:
            problems.append(
                f"Question '{qid}' has an answer, but quoted_answer is empty. "
                "Copy the relevant words from the answer.")
        elif quote not in original:
            problems.append(
                f"The quoted_answer for '{qid}' is not in the submitter's "
                "answer. Copy the words exactly.")
    return problems
