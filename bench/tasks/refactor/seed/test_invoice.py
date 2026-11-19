from invoice import build_invoice, render_invoice, summarize


def test_simple_french_order():
    inv = build_invoice({"number": "A1", "items": [{"sku": "PEN", "qty": 2, "price": 3.5}], "date": "2024-03-10"})
    assert inv["subtotal"] == 7.0
    assert inv["shipping"] == 4.9
    assert inv["total"] == 14.28
    assert inv["due"] == "2024-04-09"


def test_member_gets_discount():
    inv = build_invoice({"customer": {"type": "member"}, "items": [{"sku": "BAG", "price": 100}]})
    assert inv["discount"] == 5.0


def test_empty_order_is_rejected():
    try:
        build_invoice({"items": []})
    except ValueError:
        return
    raise AssertionError("an empty order must be rejected")


def test_render_has_total():
    inv = build_invoice({"number": "A2", "items": [{"sku": "PEN", "qty": 1, "price": 2}]})
    assert "TOTAL" in render_invoice(inv)


def test_summarize_counts_errors():
    result = summarize([{"number": "A3", "items": [{"sku": "PEN", "price": 2}]}, {"number": "A4", "items": []}])
    assert result["count"] == 1
    assert result["errors"] == ["A4: order has no items"]
