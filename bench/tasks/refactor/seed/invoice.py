import datetime


def build_invoice(order):
    if not order.get("items"):
        raise ValueError("order has no items")
    customer = order.get("customer", {})
    kind = customer.get("type", "regular")
    country = order.get("country", "FR")
    lines = []
    subtotal = 0
    weight = 0
    for item in order["items"]:
        qty = item.get("qty", 1)
        if qty <= 0:
            raise ValueError("bad quantity for " + item["sku"])
        price = item["price"]
        if price < 0:
            raise ValueError("bad price for " + item["sku"])
        total = round(qty * price, 2)
        # big quantities get a line discount
        if qty >= 50:
            total = round(total - total * 0.08, 2)
        elif qty >= 20:
            total = round(total - total * 0.05, 2)
        lines.append({"sku": item["sku"], "qty": qty, "price": price, "total": total})
        subtotal = subtotal + total
        weight = weight + item.get("weight", 0.5) * qty
    subtotal = round(subtotal, 2)
    discount = 0
    if kind == "member":
        discount = round(subtotal * 0.05, 2)
    elif kind == "wholesale":
        if subtotal >= 1000:
            discount = round(subtotal * 0.12, 2)
        else:
            discount = round(subtotal * 0.07, 2)
    elif kind == "regular":
        discount = 0
    else:
        raise ValueError("unknown customer type: " + kind)
    if order.get("coupon") == "WELCOME10" and kind == "regular":
        discount = round(discount + subtotal * 0.1, 2)
    net = round(subtotal - discount, 2)
    if country == "FR":
        if weight <= 2:
            shipping = 4.9
        elif weight <= 10:
            shipping = 9.9
        else:
            shipping = 9.9 + (weight - 10) * 0.5
        if net >= 100:
            shipping = 0
    elif country == "DE" or country == "BE" or country == "ES" or country == "IT":
        if weight <= 2:
            shipping = 7.9
        elif weight <= 10:
            shipping = 14.9
        else:
            shipping = 14.9 + (weight - 10) * 0.8
        if net >= 150:
            shipping = 0
    elif country == "US":
        if weight <= 2:
            shipping = 19.9
        elif weight <= 10:
            shipping = 34.9
        else:
            shipping = 34.9 + (weight - 10) * 1.5
        if net >= 300:
            shipping = 0
    else:
        raise ValueError("unsupported country: " + country)
    shipping = round(shipping, 2)
    if country == "FR":
        vat_rate = 0.2
    elif country == "DE":
        vat_rate = 0.19
    elif country == "BE" or country == "ES":
        vat_rate = 0.21
    elif country == "IT":
        vat_rate = 0.22
    else:
        vat_rate = 0
    if customer.get("vat_number") and country != "FR" and country != "US":
        vat_rate = 0
    vat = round((net + shipping) * vat_rate, 2)
    total = round(net + shipping + vat, 2)
    if order.get("date"):
        issued = datetime.datetime.strptime(order["date"], "%Y-%m-%d").date()
    else:
        issued = datetime.date(2024, 1, 1)
    if kind == "wholesale":
        due = issued + datetime.timedelta(days=60)
    else:
        due = issued + datetime.timedelta(days=30)
    return {
        "number": order.get("number", "DRAFT"),
        "customer": customer.get("name", "Unknown"),
        "country": country,
        "lines": lines,
        "subtotal": subtotal,
        "discount": discount,
        "shipping": shipping,
        "vat": vat,
        "total": total,
        "issued": issued.isoformat(),
        "due": due.isoformat(),
    }


def render_invoice(inv):
    out = ""
    out = out + "INVOICE " + inv["number"] + "\n"
    out = out + "Customer: " + inv["customer"] + " (" + inv["country"] + ")\n"
    out = out + "Issued: " + inv["issued"] + "  Due: " + inv["due"] + "\n"
    out = out + "-" * 44 + "\n"
    for line in inv["lines"]:
        out = out + line["sku"].ljust(12) + str(line["qty"]).rjust(6) + format(line["price"], ".2f").rjust(12)
        out = out + format(line["total"], ".2f").rjust(14) + "\n"
    out = out + "-" * 44 + "\n"
    out = out + "Subtotal".ljust(30) + format(inv["subtotal"], ".2f").rjust(14) + "\n"
    if inv["discount"] > 0:
        out = out + "Discount".ljust(30) + ("-" + format(inv["discount"], ".2f")).rjust(14) + "\n"
    if inv["shipping"] > 0:
        out = out + "Shipping".ljust(30) + format(inv["shipping"], ".2f").rjust(14) + "\n"
    else:
        out = out + "Shipping".ljust(30) + "free".rjust(14) + "\n"
    if inv["vat"] > 0:
        out = out + "VAT".ljust(30) + format(inv["vat"], ".2f").rjust(14) + "\n"
    out = out + "TOTAL".ljust(30) + format(inv["total"], ".2f").rjust(14) + "\n"
    return out


def summarize(orders):
    count = 0
    revenue = 0
    vat = 0
    by_country = {}
    errors = []
    biggest = None
    for o in orders:
        try:
            inv = build_invoice(o)
        except ValueError as e:
            errors.append(str(o.get("number", "DRAFT")) + ": " + str(e))
            continue
        count = count + 1
        revenue = round(revenue + inv["total"], 2)
        vat = round(vat + inv["vat"], 2)
        if inv["country"] in by_country:
            by_country[inv["country"]] = round(by_country[inv["country"]] + inv["total"], 2)
        else:
            by_country[inv["country"]] = inv["total"]
        if biggest is None or inv["total"] > biggest["total"]:
            biggest = inv
    if count > 0:
        average = round(revenue / count, 2)
    else:
        average = 0
    return {
        "count": count,
        "revenue": revenue,
        "vat": vat,
        "average": average,
        "by_country": by_country,
        "biggest": biggest["number"] if biggest else None,
        "errors": errors,
    }
