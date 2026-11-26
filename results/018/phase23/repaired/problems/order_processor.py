"""Legacy order processing implementation.

Behavior is intentionally quirky. Refactoring must preserve it.
"""

from decimal import Decimal, ROUND_HALF_UP


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

        subtotal = subtotal + amount

        lines.append({
            "sku": sku,
            "quantity": quantity,
            "amount": str(amount.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )),
        })

    region = order.get("region", "default")

    if region in tax_rates:
        rate = Decimal(str(tax_rates[region]))
    else:
        rate = Decimal("0")

    tax = subtotal * rate / Decimal("100")

    if order.get("priority") == "express":
        shipping = Decimal("15")
    elif subtotal >= Decimal("100"):
        shipping = Decimal("0")
    else:
        shipping = Decimal("7.50")

    total = subtotal + tax + shipping

    return {
        "customer": customer,
        "lines": lines,
        "subtotal": str(subtotal.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )),
        "tax": str(tax.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )),
        "shipping": str(shipping.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )),
        "total": str(total.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )),
    }
