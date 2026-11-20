from typing import Any

import pytest

from invoice import build_invoice, render_invoice, summarize


def test_simple_french_order() -> None:
    inv = build_invoice(
        {"number": "A1", "items": [{"sku": "PEN", "qty": 2, "price": 3.5}], "date": "2024-03-10"}
    )
    assert inv["subtotal"] == 7.0
    assert inv["shipping"] == 4.9
    assert inv["total"] == 14.28
    assert inv["due"] == "2024-04-09"


def test_member_gets_discount() -> None:
    inv = build_invoice({"customer": {"type": "member"}, "items": [{"sku": "BAG", "price": 100}]})
    assert inv["discount"] == 5.0


def test_empty_order_is_rejected() -> None:
    try:
        build_invoice({"items": []})
    except ValueError:
        return
    raise AssertionError("an empty order must be rejected")


def test_render_has_total() -> None:
    inv = build_invoice({"number": "A2", "items": [{"sku": "PEN", "qty": 1, "price": 2}]})
    assert "TOTAL" in render_invoice(inv)


def test_summarize_counts_errors() -> None:
    result = summarize(
        [{"number": "A3", "items": [{"sku": "PEN", "price": 2}]}, {"number": "A4", "items": []}]
    )
    assert result["count"] == 1
    assert result["errors"] == ["A4: order has no items"]


def _order(**fields: Any) -> dict[str, Any]:
    return {"items": [{"sku": "BAG", "price": 100}], **fields}


def test_bulk_discounts_apply_per_line() -> None:
    inv = build_invoice(
        {"items": [{"sku": "A", "qty": 20, "price": 10}, {"sku": "B", "qty": 50, "price": 10}]}
    )
    assert [line["total"] for line in inv["lines"]] == [190.0, 460.0]


def test_wholesale_discount_and_payment_terms() -> None:
    small = build_invoice(_order(customer={"type": "wholesale"}, date="2024-01-01"))
    big = build_invoice({"customer": {"type": "wholesale"}, "items": [{"sku": "A", "price": 1000}]})
    assert small["discount"] == 7.0
    assert big["discount"] == 120.0
    assert small["due"] == "2024-03-01"


def test_coupon_only_applies_to_regular_customers() -> None:
    assert build_invoice(_order(coupon="WELCOME10"))["discount"] == 10.0
    assert build_invoice(_order(coupon="WELCOME10", customer={"type": "member"}))["discount"] == 5.0


def test_shipping_tiers_and_free_threshold() -> None:
    heavy = {"items": [{"sku": "A", "price": 1, "weight": 14}]}
    assert build_invoice({**heavy, "country": "FR"})["shipping"] == 11.9
    assert build_invoice({**heavy, "country": "DE"})["shipping"] == 18.1
    assert build_invoice({**heavy, "country": "US"})["shipping"] == 40.9
    assert build_invoice(_order(country="DE"))["shipping"] == 7.9
    assert build_invoice({"items": [{"sku": "A", "price": 300}], "country": "US"})["shipping"] == 0


def test_vat_rates_and_vat_number_exemption() -> None:
    assert build_invoice(_order(country="DE"))["vat"] == 20.5
    assert build_invoice(_order(country="US"))["vat"] == 0
    assert build_invoice(_order(country="IT", customer={"vat_number": "X"}))["vat"] == 0
    assert build_invoice(_order(customer={"vat_number": "X"}))["vat"] == 20.0


def test_invalid_orders_raise_value_errors() -> None:
    cases = [
        ({"items": [{"sku": "A", "qty": 0, "price": 1}]}, "bad quantity for A"),
        ({"items": [{"sku": "A", "price": -1}]}, "bad price for A"),
        (_order(customer={"type": "vip"}), "unknown customer type: vip"),
        (_order(country="GB"), "unsupported country: GB"),
    ]
    for order, message in cases:
        with pytest.raises(ValueError, match=message):
            build_invoice(order)


def test_bad_date_raises_value_error() -> None:
    with pytest.raises(ValueError):
        build_invoice(_order(date="10/03/2024"))


def test_render_full_invoice_exact_text() -> None:
    inv = build_invoice(
        {
            "number": "A9",
            "customer": {"name": "Ann", "type": "member"},
            "items": [{"sku": "PEN", "qty": 2, "price": 3.5}],
            "date": "2024-03-10",
        }
    )
    assert render_invoice(inv) == (
        "INVOICE A9\nCustomer: Ann (FR)\nIssued: 2024-03-10  Due: 2024-04-09\n"
        + "-" * 44
        + "\n"
        + "PEN              2        3.50          7.00\n"
        + "-" * 44
        + "\n"
        + "Subtotal                                7.00\n"
        + "Discount                               -0.35\n"
        + "Shipping                                4.90\n"
        + "VAT                                     2.31\n"
        + "TOTAL                                  13.86\n"
    )


def test_render_free_shipping_and_no_vat_omits_lines() -> None:
    text = render_invoice(build_invoice({"items": [{"sku": "A", "price": 400}], "country": "US"}))
    assert "Shipping                                free\n" in text
    assert "VAT" not in text
    assert "Discount" not in text


def test_summarize_totals_by_country_and_biggest() -> None:
    result = summarize(
        [
            {"number": "X1", "items": [{"sku": "A", "price": 10}]},
            {"number": "X2", "items": [{"sku": "A", "price": 500}], "country": "US"},
            {"number": "X3", "items": [{"sku": "A", "price": 10}]},
        ]
    )
    assert result["by_country"] == {"FR": 35.76, "US": 500}
    assert result["biggest"] == "X2"
    assert result["average"] == 178.59


def test_summarize_without_orders() -> None:
    assert summarize([]) == {
        "count": 0,
        "revenue": 0,
        "vat": 0,
        "average": 0,
        "by_country": {},
        "biggest": None,
        "errors": [],
    }
