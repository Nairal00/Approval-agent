"""Tests for ropa_agent.config."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ropa_agent.config import (
    DEFAULT_MODEL,
    QUESTION_IDS,
    REQUIRED_COLUMNS,
    load_settings,
)
from ropa_agent.errors import RunStopError


class TestQuestions(unittest.TestCase):
    """The question table matches the PRD."""

    def test_eleven_unique_ids(self):
        self.assertEqual(len(QUESTION_IDS), 11)
        self.assertEqual(len(set(QUESTION_IDS)), 11)

    def test_name_and_timestamp_required(self):
        self.assertIn("1. Name", REQUIRED_COLUMNS)
        self.assertIn("Timestamp", REQUIRED_COLUMNS)
        self.assertEqual(len(REQUIRED_COLUMNS), 13)


class TestLoadSettings(unittest.TestCase):
    """Settings come from environment variables."""

    def test_missing_key_stops_run(self):
        with self.assertRaises(RunStopError):
            load_settings({})

    def test_default_model(self):
        settings = load_settings({"ANTHROPIC_AUTH_TOKEN": "x"})
        self.assertEqual(settings.model, DEFAULT_MODEL)

    def test_model_from_environment(self):
        settings = load_settings(
            {"ANTHROPIC_API_KEY": "x", "ROPA_MODEL": "deepseek-reasoner"})
        self.assertEqual(settings.model, "deepseek-reasoner")

    def test_loads_dotenv_when_environment_is_not_provided(self):
        with TemporaryDirectory() as directory:
            Path(directory, ".env").write_text(
                "ANTHROPIC_AUTH_TOKEN=from-dotenv\n"
                "ROPA_MODEL=dotenv-model\n",
                encoding="utf-8",
            )
            with patch("ropa_agent.config.PROJECT_ROOT", Path(directory)):
                with patch.dict("os.environ", {}, clear=True):
                    settings = load_settings()
                    self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"],
                                     "from-dotenv")
        self.assertEqual(settings.model, "dotenv-model")


if __name__ == "__main__":
    unittest.main()
