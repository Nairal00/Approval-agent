"""Read the Google Form CSV and write the reviewed copy."""

import csv
from dataclasses import dataclass
from pathlib import Path

from ropa_agent.config import REQUIRED_COLUMNS
from ropa_agent.errors import RunStopError

RESULT_COLUMNS = [
    "verdict",
    "escalation_cause",
    "summary",
    "missing_details",
    "unsure_questions",
    "complete_questions",
]


@dataclass
class Table:
    """The CSV content plus where each required column sits."""

    header: list
    rows: list
    column_index: dict


def normalize_column(name):
    """Make column matching tolerant of spacing and case differences."""
    return "".join(name.split()).lower()


def read_table(path):
    """Read the CSV and check that every required column is present."""
    path = Path(path)
    if not path.is_file():
        raise RunStopError(f"Input file not found: {path}")
    # utf-8-sig drops the BOM that Google Sheets exports may start with.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        rows = [row + [""] * (len(header) - len(row)) for row in reader]

    positions = {normalize_column(name): i for i, name in enumerate(header)}
    column_index = {}
    missing = []
    for column in REQUIRED_COLUMNS:
        position = positions.get(normalize_column(column))
        if position is None:
            missing.append(column)
        else:
            column_index[column] = position
    if missing:
        raise RunStopError("Missing columns in CSV: " + ", ".join(missing))
    return Table(header=header, rows=rows, column_index=column_index)


def output_path_for(input_path):
    """input.csv -> input_reviewed.csv in the same folder."""
    input_path = Path(input_path)
    return input_path.with_name(f"{input_path.stem}_reviewed.csv")


def write_table(path, table, results):
    """Write the original columns plus the result columns to a new file."""
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(table.header + RESULT_COLUMNS)
        for row, result in zip(table.rows, results):
            writer.writerow(row + [result[name] for name in RESULT_COLUMNS])
