"""Tests for ropa_agent.csv_io."""

import csv
import tempfile
import unittest
from pathlib import Path

from ropa_agent.config import REQUIRED_COLUMNS
from ropa_agent.csv_io import (
    RESULT_COLUMNS,
    output_path_for,
    read_table,
    write_table,
)
from ropa_agent.errors import RunStopError
from tests.helpers import write_csv


class TestReadTable(unittest.TestCase):
    """Reading and validating the input CSV."""

    def setUp(self):
        # Closed in tearDown, so a 'with' block is not possible here.
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_stops_run(self):
        with self.assertRaises(RunStopError):
            read_table(self.dir / "nope.csv")

    def test_missing_column_stops_run(self):
        path = self.dir / "in.csv"
        write_csv(path, [], header=REQUIRED_COLUMNS[:-1])
        with self.assertRaises(RunStopError) as ctx:
            read_table(path)
        self.assertIn(REQUIRED_COLUMNS[-1], str(ctx.exception))

    def test_reads_rows_and_pads_short_rows(self):
        path = self.dir / "in.csv"
        write_csv(path, [["2025-01-01", "Ann"]])
        table = read_table(path)
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(len(table.rows[0]), len(REQUIRED_COLUMNS))
        self.assertEqual(table.column_index["1. Name"], 1)

    def test_tolerates_spacing_and_case(self):
        header = [col.upper().replace(". ", ".  ") for col in REQUIRED_COLUMNS]
        path = self.dir / "in.csv"
        write_csv(path, [], header=header)
        table = read_table(path)
        self.assertEqual(len(table.column_index), len(REQUIRED_COLUMNS))


class TestWriteTable(unittest.TestCase):
    """Writing the reviewed copy."""

    def test_output_path(self):
        self.assertEqual(output_path_for("/a/form.csv"),
                         Path("/a/form_reviewed.csv"))

    def test_appends_result_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "in.csv"
            write_csv(source, [["t", "Ann"] + ["x"] * 11])
            original = source.read_text(encoding="utf-8")
            table = read_table(source)
            result = {name: name + "-value" for name in RESULT_COLUMNS}
            target = output_path_for(source)
            write_table(target, table, [result])

            with target.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0], REQUIRED_COLUMNS + RESULT_COLUMNS)
            self.assertEqual(rows[1][1], "Ann")
            self.assertEqual(rows[1][-1], "complete_questions-value")
            self.assertEqual(source.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
