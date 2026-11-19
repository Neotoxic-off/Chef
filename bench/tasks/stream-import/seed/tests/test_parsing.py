from datetime import date
from decimal import Decimal

import pytest

from ledger_import.errors import ImportFormatError, InvalidValueError
from ledger_import.parsing import (
    parse_amount,
    parse_currency,
    parse_date,
    parse_debit_credit,
    parse_description,
    resolve_columns,
)


@pytest.mark.parametrize("text", ["2026-03-01", "01/03/2026", "01.03.2026", " 2026-03-01 "])
def test_parse_date_accepts_bank_formats(text: str) -> None:
    assert parse_date(text) == date(2026, 3, 1)


@pytest.mark.parametrize("text", ["", "2026-13-01", "March 1st", "31/02/2026"])
def test_parse_date_rejects_invalid_dates(text: str) -> None:
    with pytest.raises(InvalidValueError):
        parse_date(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.50", Decimal("12.50")),
        ("-12.50", Decimal("-12.50")),
        ("(12.50)", Decimal("-12.50")),
        ("1,234.56", Decimal("1234.56")),
        ("1 234.56", Decimal("1234.56")),
        ("1'234", Decimal("1234")),
    ],
)
def test_parse_amount(text: str, expected: Decimal) -> None:
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["abc", "12.345", "NaN", "Infinity", ""])
def test_parse_amount_rejects_invalid_amounts(text: str) -> None:
    with pytest.raises(InvalidValueError):
        parse_amount(text)


def test_parse_debit_credit_signs_debits_negative() -> None:
    assert parse_debit_credit("40.00", "") == Decimal("-40.00")
    assert parse_debit_credit("", "40.00") == Decimal("40.00")


@pytest.mark.parametrize(("debit", "credit"), [("1.00", "2.00"), ("", " ")])
def test_parse_debit_credit_needs_exactly_one_side(debit: str, credit: str) -> None:
    with pytest.raises(InvalidValueError):
        parse_debit_credit(debit, credit)


def test_parse_currency_defaults_and_normalizes() -> None:
    assert parse_currency("", "EUR") == "EUR"
    assert parse_currency(" usd ", "EUR") == "USD"


@pytest.mark.parametrize("text", ["EURO", "E1R", "$"])
def test_parse_currency_rejects_invalid_codes(text: str) -> None:
    with pytest.raises(InvalidValueError):
        parse_currency(text, "EUR")


def test_parse_description_collapses_whitespace_and_truncates() -> None:
    assert parse_description("  Coffee \n shop ") == "Coffee shop"
    assert len(parse_description("x" * 500)) == 200


def test_parse_description_rejects_blank() -> None:
    with pytest.raises(InvalidValueError):
        parse_description("   ")


def test_resolve_columns_uses_aliases_case_insensitively() -> None:
    columns = resolve_columns(["Booking Date", "Details", "Debit", "Credit"])
    assert (columns.date, columns.description) == ("Booking Date", "Details")
    assert (columns.amount, columns.debit, columns.credit) == (None, "Debit", "Credit")
    assert columns.currency is None


@pytest.mark.parametrize("header", [None, [], ["date", "amount"], ["date", "memo", "debit"]])
def test_resolve_columns_rejects_incomplete_headers(header: list[str] | None) -> None:
    with pytest.raises(ImportFormatError):
        resolve_columns(header)
