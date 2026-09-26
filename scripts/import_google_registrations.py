#!/usr/bin/env python3
"""Import explicitly enrolled Google Form responses into Student records.

Examples:

    python scripts/import_google_registrations.py --csv registrations.csv
    python scripts/import_google_registrations.py --sheet-url "<Google Sheet URL>"

Both commands default to dry-run. Add --write only after reviewing the
READY/ERROR/SKIPPED output.

The Sheet should contain an extra manual column named "Enrollment Status".
Only APPROVED, ENROLLED, or ACTIVE rows are written by default.

This script does not create or alter database tables.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse

from exam_platform.registration_pipeline import (
    DEFAULT_ENROLLMENT_STATUSES,
    fetch_google_sheet_csv,
    import_enrolled_rows,
    read_csv_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", help="Path to a Google Sheet CSV export.")
    source.add_argument("--sheet-url", help="Google Sheet URL whose CSV export is accessible.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist eligible rows to the existing Student database.",
    )
    parser.add_argument(
        "--status",
        nargs="+",
        default=sorted(DEFAULT_ENROLLMENT_STATUSES),
        help="Enrollment Status values that are allowed to write.",
    )
    parser.add_argument(
        "--output",
        default="registration_import_results.csv",
        help="CSV file for the import audit results.",
    )
    args = parser.parse_args()

    if args.csv:
        csv_text = Path(args.csv).read_text(encoding="utf-8-sig")
    else:
        csv_text = fetch_google_sheet_csv(args.sheet_url)

    rows = read_csv_rows(csv_text)
    results = import_enrolled_rows(
        rows,
        enrollment_statuses={value.upper() for value in args.status},
        dry_run=not args.write,
    )

    with Path(args.output).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["row_number", "status", "student_id", "message"],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "row_number": result.row_number,
                    "status": result.status,
                    "student_id": result.student_id or "",
                    "message": result.message,
                }
            )

    for result in results:
        print(
            f"row={result.row_number} status={result.status} "
            f"student_id={result.student_id or '-'} message={result.message}"
        )

    errors = sum(result.status == "ERROR" for result in results)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
