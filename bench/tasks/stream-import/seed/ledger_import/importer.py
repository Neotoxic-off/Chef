"""Validate the rows of a statement and hand the valid ones to a sink."""

import csv
import io
from collections.abc import Mapping
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


@dataclass(frozen=True, slots=True)
class ImportOptions:
    account: str
    delimiter: str = ","
    default_currency: str = "EUR"
    max_errors: int = 50

    def __post_init__(self) -> None:
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
    text: str = stream.read().removeprefix(BYTE_ORDER_MARK)
    reader: csv.DictReader[str] = csv.DictReader(io.StringIO(text), delimiter=options.delimiter)
    columns: Columns = resolve_columns(reader.fieldnames)
    report: ImportReport = ImportReport()
    accepted: list[Transaction] = []
    seen: set[Fingerprint] = set()
    for row in reader:
        transaction: Transaction | None = _validated(row, reader.line_num, columns, options, report)
        if transaction is None:
            continue
        if transaction.fingerprint in seen:
            _reject(report, reader.line_num, DUPLICATE_MESSAGE, options)
            continue
        seen.add(transaction.fingerprint)
        accepted.append(transaction)
        report.accept(transaction)
    _write(sink, accepted)
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


def _write(sink: TransactionSink, transactions: list[Transaction]) -> None:
    sink.begin()
    try:
        if transactions:
            sink.write_batch(transactions)
    except BaseException:
        sink.rollback()
        raise
    sink.commit()
