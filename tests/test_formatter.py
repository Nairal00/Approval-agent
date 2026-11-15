"""Tests for ropa_agent.formatter."""

import unittest

from ropa_agent.formatter import (
    format_complete,
    format_missing_details,
    format_unsure,
    to_columns,
)
from ropa_agent.reviewer import ReviewOutcome
from tests.helpers import make_item, make_output


class TestFormatParts(unittest.TestCase):
    """Text for each column."""

    def test_missing_details_sorted_by_priority(self):
        items = [
            make_item("markets", "incomplete", priority="Low"),
            make_item("retention_period", "incomplete", priority="High",
                      quoted_answer="as long as needed"),
            make_item("data_sources", "incomplete", priority="Medium",
                      quoted_answer=""),
        ]
        lines = format_missing_details(items).split("\n")
        self.assertTrue(lines[0].startswith("[High] 11. How long"))
        self.assertIn('You wrote: "as long as needed".', lines[0])
        self.assertIn("You left this blank.", lines[1])
        self.assertTrue(lines[2].startswith("[Low] 5. Markets"))

    def test_unsure_and_complete(self):
        items = [make_item("markets", "unsure"), make_item("data_sources")]
        self.assertEqual(
            format_unsure(items),
            "5. Markets to launch this project - "
            "The answer contradicts question 7.")
        self.assertEqual(format_complete(items), "8. Where do you get the data?")


class TestToColumns(unittest.TestCase):
    """Whole-row result."""

    def test_escalated_row_keeps_model_text(self):
        outcome = ReviewOutcome(make_output({"markets": "incomplete"}),
                                "quote_check_failed", "quote not found")
        columns = to_columns(outcome)
        self.assertEqual(columns["verdict"], "Escalate")
        self.assertEqual(columns["escalation_cause"], "quote_check_failed")
        self.assertIn("Short summary.", columns["summary"])
        self.assertIn("quote not found", columns["summary"])
        self.assertIn("5. Markets", columns["missing_details"])

    def test_technical_error_without_output(self):
        columns = to_columns(ReviewOutcome(None, "technical_error", "timeout"))
        self.assertEqual(columns["verdict"], "Escalate")
        self.assertEqual(columns["summary"],
                         "Automatic review problem: timeout")
        self.assertEqual(columns["complete_questions"], "")

    def test_malformed_entries_ignored(self):
        output = make_output()
        output["questions"] += ["junk", {"question_id": "other"}]
        columns = to_columns(ReviewOutcome(output, "technical_error", "x"))
        self.assertEqual(len(columns["complete_questions"].split("\n")), 11)

    def test_passed_checks_use_compute_verdict(self):
        columns = to_columns(ReviewOutcome(make_output({"markets": "incomplete"})))
        self.assertEqual(columns["verdict"], "Not ready to submit")
        self.assertEqual(columns["escalation_cause"], "")
        self.assertEqual(columns["summary"], "Short summary.")


if __name__ == "__main__":
    unittest.main()
