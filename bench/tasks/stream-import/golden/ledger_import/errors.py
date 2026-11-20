"""Errors raised by the importer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ledger_import.models import ImportReport


class LedgerImportError(Exception):
    """Base class of every error the importer raises on purpose."""


class ImportFormatError(LedgerImportError):
    """The file is not a statement we can read: no header, or a required column is missing."""


class InvalidValueError(LedgerImportError):
    """One field of one row cannot be parsed. The row is rejected, the import goes on."""


class ImportAbortedError(LedgerImportError):
    """Too many rows were rejected: the file is probably not what the user meant to import."""

    def __init__(self, report: ImportReport) -> None:
        super().__init__(f"import aborted after {len(report.errors)} rejected rows")
        self.report: ImportReport = report
