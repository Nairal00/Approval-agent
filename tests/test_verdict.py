"""Tests for ropa_agent.verdict (PRD section 7)."""

import unittest

from ropa_agent.verdict import (
    ESCALATE,
    MODEL_UNSURE,
    NOT_READY,
    READY,
    compute_verdict,
)

ALL_COMPLETE = ["complete"] * 11


class TestComputeVerdict(unittest.TestCase):
    """Verdict rules."""

    def test_all_complete_is_ready(self):
        self.assertEqual(compute_verdict(ALL_COMPLETE), (READY, ""))

    def test_one_incomplete_is_not_ready(self):
        statuses = ALL_COMPLETE[:-1] + ["incomplete"]
        self.assertEqual(compute_verdict(statuses), (NOT_READY, ""))

    def test_one_unsure_escalates(self):
        statuses = ALL_COMPLETE[:-1] + ["unsure"]
        self.assertEqual(compute_verdict(statuses), (ESCALATE, MODEL_UNSURE))

    def test_unsure_wins_over_incomplete(self):
        statuses = ["incomplete"] * 5 + ["unsure"] + ["complete"] * 5
        self.assertEqual(compute_verdict(statuses), (ESCALATE, MODEL_UNSURE))


if __name__ == "__main__":
    unittest.main()
