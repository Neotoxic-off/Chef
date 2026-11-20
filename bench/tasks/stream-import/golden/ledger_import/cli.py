"""Command line entry point: ledger-import <file.csv> --db <ledger.sqlite3> --account <id>."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ledger_import.errors import ImportAbortedError, ImportFormatError
from ledger_import.importer import DEFAULT_BATCH_SIZE, ImportOptions, import_file
from ledger_import.models import ImportReport
from ledger_import.sinks import SqliteSink

EXIT_OK: int = 0
EXIT_ROWS_REJECTED: int = 1
EXIT_ABORTED: int = 3
EXIT_UNREADABLE_FILE: int = 4


def non_negative_int(text: str) -> int:
    try:
        value: int = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError(f"must not be negative: {value}")
    return value


def positive_int(text: str) -> int:
    value: int = non_negative_int(text)
    if value == 0:
        raise argparse.ArgumentTypeError("must be positive: 0")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="ledger-import", description="Import a bank statement CSV export into the ledger."
    )
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--db", type=Path, required=True, help="SQLite ledger database")
    parser.add_argument("--account", required=True, help="ledger account the rows belong to")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--currency", default="EUR", help="currency of rows that have none")
    parser.add_argument(
        "--max-errors", type=non_negative_int, default=50, help="abort after this many bad rows"
    )
    parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=DEFAULT_BATCH_SIZE,
        help="rows written to the ledger per batch",
    )
    return parser


def print_report(report: ImportReport) -> None:
    print(f"imported {report.imported} transactions, rejected {len(report.errors)} rows")
    for currency, total in sorted(report.totals.items()):
        print(f"  {currency} {total:+.2f}")
    for error in report.errors:
        print(f"  {error}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    args: argparse.Namespace = build_parser().parse_args(argv)
    options: ImportOptions = ImportOptions(
        account=args.account,
        delimiter=args.delimiter,
        default_currency=args.currency,
        max_errors=args.max_errors,
        batch_size=args.batch_size,
    )
    sink: SqliteSink = SqliteSink(args.db)
    try:
        report: ImportReport = import_file(args.csv_file, sink, options)
    except ImportAbortedError as aborted:
        print(f"ledger-import: {aborted}, nothing was imported", file=sys.stderr)
        print_report(aborted.report)
        return EXIT_ABORTED
    except (ImportFormatError, OSError, UnicodeDecodeError) as error:
        print(f"ledger-import: cannot read {args.csv_file}: {error}", file=sys.stderr)
        return EXIT_UNREADABLE_FILE
    finally:
        sink.close()
    print_report(report)
    return EXIT_ROWS_REJECTED if report.errors else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
