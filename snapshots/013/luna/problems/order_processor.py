"""Legacy order processing implementation.

Behavior is intentionally quirky. Refactoring must preserve it.
"""

from decimal import ROUND_HALF_UP, Decimal


def _format_money(amount):
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _price_line(item, catalog):
    if "sku" not in item:
        raise ValueError("missing sku")
    if "quantity" not in item:
        raise ValueError("missing quantity")

    sku = item["sku"]
    quantity = item["quantity"]

    if sku not in catalog:
        raise ValueError("unknown sku: " + str(sku))

    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("invalid quantity")

    price = Decimal(str(catalog[sku]["price"]))
    amount = price * quantity

    if "discount" in item:
        discount = Decimal(str(item["discount"]))
        amount = amount - amount * discount / Decimal("100")

    line = {
        "sku": sku,
        "quantity": quantity,
        "amount": _format_money(amount),
    }
    return amount, line


def _get_tax_rate(region, tax_rates):
    if region in tax_rates:
        return Decimal(str(tax_rates[region]))
    return Decimal("0")


def _get_shipping(order, subtotal):
    if order.get("priority") == "express":
        return Decimal("15")
    if subtotal >= Decimal("100"):
        return Decimal("0")
    return Decimal("7.50")


def process_order(order, catalog, tax_rates):
    if not isinstance(order, dict):
        raise TypeError("order must be a dict")

    if "customer" not in order:
        raise ValueError("missing customer")

    if "items" not in order:
        raise ValueError("missing items")

    customer = order["customer"]
    items = order["items"]

    if not isinstance(items, list):
        raise TypeError("items must be a list")

    if not items:
        raise ValueError("empty order")

    subtotal = Decimal("0")
    lines = []

    for item in items:
        amount, line = _price_line(item, catalog)
        subtotal = subtotal + amount
        lines.append(line)

    region = order.get("region", "default")
    rate = _get_tax_rate(region, tax_rates)
    tax = subtotal * rate / Decimal("100")
    shipping = _get_shipping(order, subtotal)
    total = subtotal + tax + shipping

    return {
        "customer": customer,
        "lines": lines,
        "subtotal": _format_money(subtotal),
        "tax": _format_money(tax),
        "shipping": _format_money(shipping),
        "total": _format_money(total),
    }
