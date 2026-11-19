"""Where imported transactions go. The importer writes inside one transaction per file."""

import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from ledger_import.models import Transaction

SCHEMA: str = """
CREATE TABLE IF NOT EXISTS ledger_transaction (
    id INTEGER PRIMARY KEY,
    account TEXT NOT NULL,
    booked_on TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    description TEXT NOT NULL
)
"""
INSERT: str = (
    "INSERT INTO ledger_transaction (account, booked_on, amount, currency, description)"
    " VALUES (?, ?, ?, ?, ?)"
)


class TransactionSink(Protocol):
    def begin(self) -> None: ...

    def write_batch(self, transactions: Sequence[Transaction]) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class InMemorySink:
    """Keeps committed transactions in a list. Used by tests and by the dry-run mode."""

    def __init__(self) -> None:
        self.committed: list[Transaction] = []
        self._pending: list[Transaction] | None = None

    def begin(self) -> None:
        if self._pending is not None:
            raise RuntimeError("a transaction is already open")
        self._pending = []

    def write_batch(self, transactions: Sequence[Transaction]) -> None:
        if self._pending is None:
            raise RuntimeError("write_batch called outside a transaction")
        self._pending.extend(transactions)

    def commit(self) -> None:
        if self._pending is None:
            raise RuntimeError("commit called outside a transaction")
        self.committed.extend(self._pending)
        self._pending = None

    def rollback(self) -> None:
        self._pending = None


class SqliteSink:
    def __init__(self, database: Path) -> None:
        self._connection: sqlite3.Connection = sqlite3.connect(database, autocommit=True)
        self._connection.execute(SCHEMA)

    def begin(self) -> None:
        self._connection.execute("BEGIN")

    def write_batch(self, transactions: Sequence[Transaction]) -> None:
        self._connection.executemany(
            INSERT,
            [
                (
                    transaction.account,
                    transaction.booked_on.isoformat(),
                    str(transaction.amount),
                    transaction.currency,
                    transaction.description,
                )
                for transaction in transactions
            ],
        )

    def commit(self) -> None:
        self._connection.execute("COMMIT")

    def rollback(self) -> None:
        if self._connection.in_transaction:
            self._connection.execute("ROLLBACK")

    def count(self) -> int:
        row: tuple[int] = self._connection.execute(
            "SELECT COUNT(*) FROM ledger_transaction"
        ).fetchone()
        return row[0]

    def close(self) -> None:
        self._connection.close()
