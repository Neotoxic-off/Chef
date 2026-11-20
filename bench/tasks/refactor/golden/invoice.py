import datetime
from typing import Any, NamedTuple

# Orders and invoices are plain JSON-like dicts shared with other services.
Order = dict[str, Any]
Invoice = dict[str, Any]

DEFAULT_COUNTRY = "FR"
DEFAULT_CUSTOMER_TYPE = "regular"
DEFAULT_ORDER_NUMBER = "DRAFT"
DEFAULT_ISSUE_DATE = datetime.date(2024, 1, 1)
DEFAULT_ITEM_WEIGHT = 0.5
DATE_FORMAT = "%Y-%m-%d"

BULK_DISCOUNTS = ((50, 0.08), (20, 0.05))  # (minimum quantity, rate), largest first
MEMBER_DISCOUNT_RATE = 0.05
WHOLESALE_BIG_ORDER = 1000
WHOLESALE_BIG_ORDER_RATE = 0.12
WHOLESALE_RATE = 0.07
COUPON_CODE = "WELCOME10"
COUPON_RATE = 0.1

PAYMENT_DAYS = {"wholesale": 60}
DEFAULT_PAYMENT_DAYS = 30

LIGHT_PARCEL_MAX_WEIGHT = 2
MEDIUM_PARCEL_MAX_WEIGHT = 10


class ShippingZone(NamedTuple):
    light_price: float
    medium_price: float
    price_per_extra_weight: float
    free_from_net: int


SHIPPING_ZONES = {
    "FR": ShippingZone(4.9, 9.9, 0.5, 100),
    "DE": ShippingZone(7.9, 14.9, 0.8, 150),
    "BE": ShippingZone(7.9, 14.9, 0.8, 150),
    "ES": ShippingZone(7.9, 14.9, 0.8, 150),
    "IT": ShippingZone(7.9, 14.9, 0.8, 150),
    "US": ShippingZone(19.9, 34.9, 1.5, 300),
}

VAT_RATES = {"FR": 0.2, "DE": 0.19, "BE": 0.21, "ES": 0.21, "IT": 0.22}
NO_VAT_RATE = 0
VAT_EXEMPT_WITH_VAT_NUMBER_EXCLUDED = ("FR", "US")

RECEIPT_WIDTH = 44
SKU_WIDTH = 12
QTY_WIDTH = 6
PRICE_WIDTH = 12
LINE_TOTAL_WIDTH = 14
LABEL_WIDTH = 30
AMOUNT_WIDTH = 14


def _build_line(item: Order) -> Invoice:
    qty = item.get("qty", 1)
    if qty <= 0:
        raise ValueError("bad quantity for " + item["sku"])
    price = item["price"]
    if price < 0:
        raise ValueError("bad price for " + item["sku"])
    total = round(qty * price, 2)
    for minimum_qty, rate in BULK_DISCOUNTS:
        if qty >= minimum_qty:
            total = round(total - total * rate, 2)
            break
    return {"sku": item["sku"], "qty": qty, "price": price, "total": total}


def _customer_discount(customer_type: str, subtotal: float) -> float:
    if customer_type == "member":
        return round(subtotal * MEMBER_DISCOUNT_RATE, 2)
    if customer_type == "wholesale":
        rate = WHOLESALE_BIG_ORDER_RATE if subtotal >= WHOLESALE_BIG_ORDER else WHOLESALE_RATE
        return round(subtotal * rate, 2)
    if customer_type == "regular":
        return 0
    raise ValueError("unknown customer type: " + customer_type)


def _shipping_cost(country: str, weight: float, net: float) -> float:
    zone = SHIPPING_ZONES.get(country)
    if zone is None:
        raise ValueError("unsupported country: " + country)
    if weight <= LIGHT_PARCEL_MAX_WEIGHT:
        shipping = zone.light_price
    elif weight <= MEDIUM_PARCEL_MAX_WEIGHT:
        shipping = zone.medium_price
    else:
        shipping = zone.medium_price + (weight - MEDIUM_PARCEL_MAX_WEIGHT) * zone.price_per_extra_weight
    if net >= zone.free_from_net:
        shipping = 0
    return round(shipping, 2)


def _vat_rate(country: str, customer: Order) -> float:
    if customer.get("vat_number") and country not in VAT_EXEMPT_WITH_VAT_NUMBER_EXCLUDED:
        return NO_VAT_RATE
    return VAT_RATES.get(country, NO_VAT_RATE)


def _issue_date(order: Order) -> datetime.date:
    if order.get("date"):
        return datetime.datetime.strptime(order["date"], DATE_FORMAT).date()
    return DEFAULT_ISSUE_DATE


def build_invoice(order: Order) -> Invoice:
    if not order.get("items"):
        raise ValueError("order has no items")
    customer = order.get("customer", {})
    customer_type = customer.get("type", DEFAULT_CUSTOMER_TYPE)
    country = order.get("country", DEFAULT_COUNTRY)
    lines = [_build_line(item) for item in order["items"]]
    weight = 0
    for item in order["items"]:
        weight = weight + item.get("weight", DEFAULT_ITEM_WEIGHT) * item.get("qty", 1)
    subtotal = 0
    for line in lines:
        subtotal = subtotal + line["total"]
    subtotal = round(subtotal, 2)

    discount = _customer_discount(customer_type, subtotal)
    if order.get("coupon") == COUPON_CODE and customer_type == "regular":
        discount = round(discount + subtotal * COUPON_RATE, 2)
    net = round(subtotal - discount, 2)

    shipping = _shipping_cost(country, weight, net)
    vat = round((net + shipping) * _vat_rate(country, customer), 2)
    issued = _issue_date(order)
    due = issued + datetime.timedelta(days=PAYMENT_DAYS.get(customer_type, DEFAULT_PAYMENT_DAYS))
    return {
        "number": order.get("number", DEFAULT_ORDER_NUMBER),
        "customer": customer.get("name", "Unknown"),
        "country": country,
        "lines": lines,
        "subtotal": subtotal,
        "discount": discount,
        "shipping": shipping,
        "vat": vat,
        "total": round(net + shipping + vat, 2),
        "issued": issued.isoformat(),
        "due": due.isoformat(),
    }


def _money(amount: float) -> str:
    return format(amount, ".2f")


def _summary_row(label: str, value: str) -> str:
    return label.ljust(LABEL_WIDTH) + value.rjust(AMOUNT_WIDTH) + "\n"


def _render_line(line: Invoice) -> str:
    sku: str = line["sku"]
    return (
        sku.ljust(SKU_WIDTH)
        + str(line["qty"]).rjust(QTY_WIDTH)
        + _money(line["price"]).rjust(PRICE_WIDTH)
        + _money(line["total"]).rjust(LINE_TOTAL_WIDTH)
        + "\n"
    )


def render_invoice(inv: Invoice) -> str:
    separator = "-" * RECEIPT_WIDTH + "\n"
    out: str = "INVOICE " + inv["number"] + "\n"
    out += "Customer: " + inv["customer"] + " (" + inv["country"] + ")\n"
    out += "Issued: " + inv["issued"] + "  Due: " + inv["due"] + "\n"
    out += separator
    out += "".join(_render_line(line) for line in inv["lines"])
    out += separator
    out += _summary_row("Subtotal", _money(inv["subtotal"]))
    if inv["discount"] > 0:
        out += _summary_row("Discount", "-" + _money(inv["discount"]))
    out += _summary_row("Shipping", _money(inv["shipping"]) if inv["shipping"] > 0 else "free")
    if inv["vat"] > 0:
        out += _summary_row("VAT", _money(inv["vat"]))
    out += _summary_row("TOTAL", _money(inv["total"]))
    return out


def summarize(orders: list[Order]) -> Invoice:
    count = 0
    revenue = 0
    vat = 0
    by_country: dict[str, float] = {}
    errors = []
    biggest = None
    for order in orders:
        try:
            inv = build_invoice(order)
        except ValueError as error:
            errors.append(str(order.get("number", DEFAULT_ORDER_NUMBER)) + ": " + str(error))
            continue
        count += 1
        revenue = round(revenue + inv["total"], 2)
        vat = round(vat + inv["vat"], 2)
        by_country[inv["country"]] = round(by_country.get(inv["country"], 0) + inv["total"], 2)
        if biggest is None or inv["total"] > biggest["total"]:
            biggest = inv
    return {
        "count": count,
        "revenue": revenue,
        "vat": vat,
        "average": round(revenue / count, 2) if count > 0 else 0,
        "by_country": by_country,
        "biggest": biggest["number"] if biggest else None,
        "errors": errors,
    }
