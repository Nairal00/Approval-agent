"""Command-line entry point: python -m ropa_agent.cli input.csv"""

import argparse
import asyncio
import sys

from ropa_agent.config import load_settings
from ropa_agent.csv_io import output_path_for, read_table, write_table
from ropa_agent.errors import RunStopError
from ropa_agent.formatter import to_columns
from ropa_agent.payload import build_payload
from ropa_agent.reviewer import ReviewOutcome, review_row
from ropa_agent.verdict import TECHNICAL_ERROR


async def review_table(table, settings, review=review_row):
    """Review every row in order. One bad row never stops the others."""
    results = []
    for offset, row in enumerate(table.rows):
        row_number = offset + 2  # row 1 is the header
        try:
            payload = build_payload(row_number, row, table.column_index)
            outcome = await review(payload, settings)
            columns = to_columns(outcome)
        except RunStopError:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # PRD: any error while handling a row escalates only that row.
            columns = to_columns(ReviewOutcome(
                None, TECHNICAL_ERROR, f"{type(exc).__name__}: {exc}"))
        print(f"row-{row_number}: {columns['verdict']}", flush=True)
        results.append(columns)
    return results


def main(argv=None, review=review_row):
    """Run the review. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Pre-review ROPA form responses before privacy review.")
    parser.add_argument("csv_path", help="CSV exported from the Google Form")
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
        table = read_table(args.csv_path)
        results = asyncio.run(review_table(table, settings, review))
    except RunStopError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    target = output_path_for(args.csv_path)
    write_table(target, table, results)
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
