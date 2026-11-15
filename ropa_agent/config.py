"""Question mapping and runtime settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from ropa_agent.errors import RunStopError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "ropa-review"
MAX_REDOS = 3
MAX_TURNS = 10
DEFAULT_MODEL = "claude-sonnet-4-5"

# (question_id, CSV column name, question text shown on the form)
QUESTIONS = [
    ("business_department", "2. Business Department",
     "Business Department"),
    ("purpose_of_processing", "3. Purpose of processing",
     "Purpose of processing"),
    ("reason_for_using_personal_data", "4. Why do you use personal data?",
     "Why do you use personal data?"),
    ("markets", "5. Markets to launch this project",
     "Markets to launch this project"),
    ("data_subjects", "6. Who do you hold information about?",
     "Who do you hold information about?"),
    ("data_categories",
     "7. What specific information do you hold about individuals?",
     "What specific information do you hold about individuals?"),
    ("data_sources", "8. Where do you get the data?",
     "Where do you get the data?"),
    ("data_recipients", "9. Who do you share the data with?",
     "Who do you share the data with?"),
    ("sharing_reason",
     "10.Why do you need to share this data with this recipient?",
     "Why do you need to share this data with this recipient?"),
    ("retention_period",
     "11. How long will personal information will be retained?",
     "How long will personal information will be retained?"),
    ("security_measures", "12. How do you keep it safe?",
     "How do you keep it safe?"),
]

QUESTION_IDS = [qid for qid, _, _ in QUESTIONS]
QUESTION_COLUMNS = {qid: column for qid, column, _ in QUESTIONS}
QUESTION_TEXTS = {qid: text for qid, _, text in QUESTIONS}

# Columns kept in the output but never sent to the model.
PRIVATE_COLUMNS = ["Timestamp", "1. Name"]
REQUIRED_COLUMNS = PRIVATE_COLUMNS + [column for _, column, _ in QUESTIONS]

KEY_VARIABLES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


@dataclass(frozen=True)
class Settings:
    """Model settings read from environment variables."""

    model: str


def _read_dotenv(path):
    """Read simple KEY=VALUE entries from a dotenv file."""
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name.startswith("export "):
            name = name[7:].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value
    return values


def load_settings(environ=None):
    """Read settings from the environment.

    The API key itself is not stored here: the SDK passes the environment
    to the model process. We only check that a key is present.
    """
    if environ is None:
        for name, value in _read_dotenv(PROJECT_ROOT / ".env").items():
            os.environ.setdefault(name, value)
        environ = os.environ
    if not any(environ.get(name) for name in KEY_VARIABLES):
        raise RunStopError(
            "No API key found. Set ANTHROPIC_AUTH_TOKEN (or ANTHROPIC_API_KEY) "
            "and ANTHROPIC_BASE_URL. See .env.example."
        )
    return Settings(model=environ.get("ROPA_MODEL") or DEFAULT_MODEL)
