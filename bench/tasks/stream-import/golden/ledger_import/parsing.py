"""Parse the fields of one statement row. Every parser raises InvalidValueError on bad input."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from ledger_import.errors import ImportFormatError, InvalidValueError

DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y")
THOUSANDS_SEPARATORS: tuple[str, ...] = (",", " ", "'", "\u00a0")
MAX_DECIMAL_PLACES: int = 2
CURRENCY_CODE_LENGTH: int = 3
MAX_DESCRIPTION_LENGTH: int = 200

HEADER_ALIASES: dict[str, str] = {
    "date": "date",
    "booking date": "date",
    "value date": "date",
    "amount": "amount",
    "debit": "debit",
    "credit": "credit",
    "currency": "currency",
    "description": "description",
    "details": "description",
    "memo": "description",
}


@dataclass(frozen=True, slots=True)
class Columns:
    """Where each field we need lives in this file's header."""

    date: str
    description: str
    amount: str | None
    debit: str | None
    credit: str | None
    currency: str | None


def resolve_columns(fieldnames: Sequence[str] | None) -> Columns:
    if not fieldnames:
        raise ImportFormatError("the file has no header row")
    found: dict[str, str] = {}
    for name in fieldnames:
        canonical: str | None = HEADER_ALIASES.get(" ".join(name.casefold().split()))
        if canonical is not None and canonical not in found:
            found[canonical] = name
    missing: list[str] = [column for column in ("date", "description") if column not in found]
    if "amount" not in found and not {"debit", "credit"} <= found.keys():
        missing.append("amount (or debit and credit)")
    if missing:
        raise ImportFormatError(f"missing column: {', '.join(missing)}")
    return Columns(
        date=found["date"],
        description=found["description"],
        amount=found.get("amount"),
        debit=found.get("debit"),
        credit=found.get("credit"),
        currency=found.get("currency"),
    )


def parse_date(text: str) -> date:
    cleaned: str = text.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    raise InvalidValueError(f"invalid date {text!r}")


def parse_amount(text: str) -> Decimal:
    cleaned: str = text.strip()
    negative: bool = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    for separator in THOUSANDS_SEPARATORS:
        cleaned = cleaned.replace(separator, "")
    try:
        amount: Decimal = Decimal(cleaned)
    except InvalidOperation:
        raise InvalidValueError(f"invalid amount {text!r}") from None
    exponent: int | str = amount.as_tuple().exponent
    if not amount.is_finite() or (isinstance(exponent, int) and -exponent > MAX_DECIMAL_PLACES):
        raise InvalidValueError(f"invalid amount {text!r}")
    return -amount if negative else amount


def parse_debit_credit(debit: str, credit: str) -> Decimal:
    if debit.strip() and credit.strip():
        raise InvalidValueError("both debit and credit are filled")
    if not debit.strip() and not credit.strip():
        raise InvalidValueError("missing amount")
    return -parse_amount(debit) if debit.strip() else parse_amount(credit)


def parse_currency(text: str, default: str) -> str:
    code: str = text.strip().upper() or default
    if len(code) != CURRENCY_CODE_LENGTH or not code.isalpha():
        raise InvalidValueError(f"invalid currency {text!r}")
    return code


def parse_description(text: str) -> str:
    description: str = " ".join(text.split())
    if not description:
        raise InvalidValueError("missing description")
    return description[:MAX_DESCRIPTION_LENGTH]


def field(row: Mapping[str, str | None], column: str | None) -> str:
    """A short row leaves its last fields as None: read them as empty."""
    if column is None:
        return ""
    return row.get(column) or ""
