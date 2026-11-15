"""Tests for ropa_agent.validators."""

import unittest

from ropa_agent.validators import check_completeness, check_quotes, normalize
from tests.helpers import make_item, make_output, make_payload


class TestCompleteness(unittest.TestCase):
    """Check 2."""

    def setUp(self):
        self.payload = make_payload()

    def test_valid_output_passes(self):
        output = make_output({"markets": "incomplete", "data_sources": "unsure"})
        self.assertEqual(check_completeness(self.payload, output), [])

    def test_not_an_object(self):
        self.assertEqual(len(check_completeness(self.payload, "oops")), 1)
        self.assertEqual(len(check_completeness(self.payload, {})), 1)

    def test_wrong_submission_id(self):
        output = make_output(submission_id="row-3")
        problems = check_completeness(self.payload, output)
        self.assertEqual(problems, ["submission_id must be 'row-2'."])

    def test_missing_and_duplicate_questions(self):
        output = make_output()
        output["questions"][1] = make_item("business_department")
        problems = check_completeness(self.payload, output)
        self.assertIn("Question 'purpose_of_processing' is missing.", problems)
        self.assertIn("Question 'business_department' appears 2 times.",
                      problems)

    def test_incomplete_needs_detail_and_priority(self):
        output = make_output()
        output["questions"][0] = make_item(
            "business_department", "incomplete",
            missing_detail=" ", priority="")
        self.assertEqual(len(check_completeness(self.payload, output)), 2)

    def test_unsure_needs_reason(self):
        output = make_output()
        output["questions"][0] = make_item(
            "business_department", "unsure", unsure_reason="")
        self.assertEqual(len(check_completeness(self.payload, output)), 1)


class TestQuotes(unittest.TestCase):
    """Check 3."""

    def test_normalize(self):
        self.assertEqual(normalize("  Two\nYEARS "), "twoyears")

    def test_quote_found_ignoring_spacing_and_case(self):
        payload = make_payload()
        output = make_output()
        output["questions"][0]["quoted_answer"] = "CUSTOMER\n  emails kept"
        self.assertEqual(check_quotes(payload, output), [])

    def test_invented_quote_fails(self):
        output = make_output()
        output["questions"][0]["quoted_answer"] = "kept forever"
        self.assertEqual(len(check_quotes(make_payload(), output)), 1)

    def test_blank_answer_needs_blank_quote(self):
        payload = make_payload({"markets": ""})
        output = make_output()
        problems = check_quotes(payload, output)
        self.assertEqual(len(problems), 1)
        self.assertIn("'markets' was left blank", problems[0])
        output["questions"][3]["quoted_answer"] = ""
        self.assertEqual(check_quotes(payload, output), [])

    def test_empty_quote_for_real_answer_fails(self):
        output = make_output()
        output["questions"][0]["quoted_answer"] = ""
        self.assertEqual(len(check_quotes(make_payload(), output)), 1)

    def test_unknown_ids_and_bad_shapes_skipped(self):
        output = make_output()
        output["questions"].append({"question_id": "other"})
        output["questions"].append("not a dict")
        self.assertEqual(check_quotes(make_payload(), output), [])
        self.assertEqual(check_quotes(make_payload(), None), [])


if __name__ == "__main__":
    unittest.main()
