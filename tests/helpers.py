"""Shared test data."""

import csv

from ropa_agent.config import QUESTION_IDS, REQUIRED_COLUMNS

ANSWER = "Customer emails kept for 2 years"


def make_payload(answers=None, submission_id="row-2"):
    """Payload with every answer set to ANSWER unless overridden."""
    answers = answers or {}
    return {
        "submission_id": submission_id,
        "answers": [
            {
                "question_id": qid,
                "question_text": qid,
                "answer": answers.get(qid, ANSWER),
            }
            for qid in QUESTION_IDS
        ],
    }


def make_item(qid, status="complete", **fields):
    """One question entry as the model would return it."""
    item = {
        "question_id": qid,
        "status": status,
        "quoted_answer": "customer emails",
        "missing_detail": "",
        "priority": "",
        "unsure_reason": "",
    }
    if status == "incomplete":
        item["missing_detail"] = "Please say how long."
        item["priority"] = "High"
    if status == "unsure":
        item["unsure_reason"] = "The answer contradicts question 7."
    item.update(fields)
    return item


def make_output(statuses=None, submission_id="row-2"):
    """A valid model output; statuses maps question_id -> status."""
    statuses = statuses or {}
    return {
        "submission_id": submission_id,
        "summary": "Short summary.",
        "questions": [
            make_item(qid, statuses.get(qid, "complete"))
            for qid in QUESTION_IDS
        ],
    }


def write_csv(path, rows, header=None):
    """Write a CSV with the required header plus the given rows."""
    header = REQUIRED_COLUMNS if header is None else header
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
