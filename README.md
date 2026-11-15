# ROPA pre-review agent

Checks each Google Form ROPA response and decides whether it has enough
information for privacy review. See `PRD.md` for the full requirements.

## Setup

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set the model variables in your shell (see `.env.example`):

```bash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=your-deepseek-api-key
export ROPA_MODEL=claude-sonnet-4-5
```

## Run

```bash
python -m ropa_agent.cli responses.csv
```

This writes `responses_reviewed.csv` next to the input. The input file is
never changed. Six columns are added: `verdict`, `escalation_cause`,
`summary`, `missing_details`, `unsure_questions`, `complete_questions`.

## Criteria

The review criteria live in `.claude/skills/ropa-review/SKILL.md`.
Change that file to change how answers are judged; no code change needed.

## Tests

```bash
python -m pytest --cov=ropa_agent --cov-fail-under=95
pylint ropa_agent tests
```
