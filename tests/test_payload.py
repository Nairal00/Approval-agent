"""Tests for ropa_agent.payload."""

import json
import unittest

from ropa_agent.config import QUESTION_IDS, REQUIRED_COLUMNS
from ropa_agent.payload import (
    OUTPUT_SCHEMA,
    build_payload,
    build_prompt,
    build_redo_prompt,
)


class TestBuildPayload(unittest.TestCase):
    """One CSV row becomes the input JSON."""

    def setUp(self):
        self.column_index = {col: i for i, col in enumerate(REQUIRED_COLUMNS)}
        self.row = ["2025-01-01", "Ann Lee"] + [f"answer {i}" for i in range(11)]

    def test_shape(self):
        payload = build_payload(2, self.row, self.column_index)
        self.assertEqual(payload["submission_id"], "row-2")
        self.assertEqual([a["question_id"] for a in payload["answers"]],
                         QUESTION_IDS)
        self.assertEqual(payload["answers"][0]["answer"], "answer 0")

    def test_name_and_timestamp_not_sent(self):
        text = json.dumps(build_payload(2, self.row, self.column_index))
        self.assertNotIn("Ann Lee", text)
        self.assertNotIn("2025-01-01", text)


class TestPrompts(unittest.TestCase):
    """Messages sent to the agent."""

    def test_prompt_contains_payload(self):
        prompt = build_prompt({"submission_id": "row-9", "answers": []})
        self.assertIn('"row-9"', prompt)
        self.assertIn("ropa-review", prompt)

    def test_redo_prompt_lists_problems(self):
        prompt = build_redo_prompt(["problem A", "problem B"])
        self.assertIn("- problem A", prompt)
        self.assertIn("- problem B", prompt)

    def test_schema_enum_matches_ids(self):
        item = OUTPUT_SCHEMA["properties"]["questions"]["items"]
        self.assertEqual(item["properties"]["question_id"]["enum"],
                         QUESTION_IDS)


if __name__ == "__main__":
    unittest.main()
