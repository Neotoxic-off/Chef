"""Values the importer produces."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

type Fingerprint = tuple[date, Decimal, str]


@dataclass(frozen=True, slots=True)
class Transaction:
    account: str
    booked_on: date
    amount: Decimal
    currency: str
    description: str

    @property
    def fingerprint(self) -> Fingerprint:
        """Rows of one file with the same fingerprint are one bank movement exported twice."""
        return (self.booked_on, self.amount, " ".join(self.description.casefold().split()))


@dataclass(frozen=True, slots=True)
class RowError:
    line: int
    message: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.message}"


@dataclass(slots=True)
class ImportReport:
    imported: int = 0
    errors: list[RowError] = field(default_factory=list[RowError])
    totals: dict[str, Decimal] = field(default_factory=dict[str, Decimal])

    def accept(self, transaction: Transaction) -> None:
        self.imported += 1
        self.totals[transaction.currency] = (
            self.totals.get(transaction.currency, Decimal(0)) + transaction.amount
        )

    def reject(self, line: int, message: str) -> None:
        self.errors.append(RowError(line, message))
