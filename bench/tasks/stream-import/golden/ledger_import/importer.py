"""Validate the rows of a statement and hand the valid ones to a sink."""

import csv
import itertools
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from ledger_import.errors import ImportAbortedError, InvalidValueError
from ledger_import.models import Fingerprint, ImportReport, Transaction
from ledger_import.parsing import (
    Columns,
    field,
    parse_amount,
    parse_currency,
    parse_date,
    parse_debit_credit,
    parse_description,
    resolve_columns,
)
from ledger_import.sinks import TransactionSink

BYTE_ORDER_MARK: str = "﻿"
DUPLICATE_MESSAGE: str = "duplicate of an earlier row"
DEFAULT_BATCH_SIZE: int = 500
READ_CHUNK_SIZE: int = 1 << 16


@dataclass(frozen=True, slots=True)
class ImportOptions:
    account: str
    delimiter: str = ","
    default_currency: str = "EUR"
    max_errors: int = 50
    batch_size: int = DEFAULT_BATCH_SIZE

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if not self.account.strip():
            raise ValueError("account must not be empty")
        if len(self.delimiter) != 1:
            raise ValueError("delimiter must be one character")
        if self.max_errors < 0:
            raise ValueError("max_errors must not be negative")


def import_file(path: Path, sink: TransactionSink, options: ImportOptions) -> ImportReport:
    with path.open(encoding="utf-8", newline="") as stream:
        return import_csv(stream, sink, options)


def import_csv(stream: TextIO, sink: TransactionSink, options: ImportOptions) -> ImportReport:
    """Import every valid row, or nothing when the import is aborted or fails."""
    reader: csv.DictReader[str] = csv.DictReader(_lines(stream), delimiter=options.delimiter)
    columns: Columns = resolve_columns(reader.fieldnames)
    sink.begin()
    try:
        report: ImportReport = _import_rows(reader, columns, sink, options)
        sink.commit()
    except BaseException:
        sink.rollback()
        raise
    return report


def _lines(stream: TextIO) -> Iterator[str]:
    """Yield lines ending in "\\n" only, so a lone "\\r" stays inside its line; drop the BOM."""
    chunks: Iterator[str] = iter(lambda: stream.read(READ_CHUNK_SIZE), "")
    first_chunk: str = next(chunks, "").removeprefix(BYTE_ORDER_MARK)
    pending: str = ""
    for chunk in itertools.chain([first_chunk], chunks):
        *complete, pending = (pending + chunk).split("\n")
        for line in complete:
            yield line + "\n"
    if pending:
        yield pending


def _import_rows(
    reader: csv.DictReader[str], columns: Columns, sink: TransactionSink, options: ImportOptions
) -> ImportReport:
    report: ImportReport = ImportReport()
    batch: list[Transaction] = []
    seen: set[Fingerprint] = set()
    for row in reader:
        transaction: Transaction | None = _validated(row, reader.line_num, columns, options, report)
        if transaction is None:
            continue
        if transaction.fingerprint in seen:
            _reject(report, reader.line_num, DUPLICATE_MESSAGE, options)
            continue
        seen.add(transaction.fingerprint)
        batch.append(transaction)
        report.accept(transaction)
        if len(batch) == options.batch_size:
            sink.write_batch(batch)
            batch = []
    if batch:
        sink.write_batch(batch)
    return report


def _validated(
    row: Mapping[str, str | None],
    line: int,
    columns: Columns,
    options: ImportOptions,
    report: ImportReport,
) -> Transaction | None:
    try:
        return parse_row(row, columns, options)
    except InvalidValueError as error:
        _reject(report, line, str(error), options)
        return None


def parse_row(
    row: Mapping[str, str | None], columns: Columns, options: ImportOptions
) -> Transaction:
    if columns.amount is not None:
        amount_text: str = field(row, columns.amount)
        if not amount_text.strip():
            raise InvalidValueError("missing amount")
        amount = parse_amount(amount_text)
    else:
        amount = parse_debit_credit(field(row, columns.debit), field(row, columns.credit))
    return Transaction(
        account=options.account,
        booked_on=parse_date(field(row, columns.date)),
        amount=amount,
        currency=parse_currency(field(row, columns.currency), options.default_currency),
        description=parse_description(field(row, columns.description)),
    )


def _reject(report: ImportReport, line: int, message: str, options: ImportOptions) -> None:
    report.reject(line, message)
    if len(report.errors) > options.max_errors:
        raise ImportAbortedError(report)
