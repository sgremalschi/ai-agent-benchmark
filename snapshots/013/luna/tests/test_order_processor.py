from decimal import Decimal

import pytest

from problems.order_processor import process_order

CATALOG = {"book": {"price": "12.345"}}


def order(items, **extra):
    return {"customer": "Ada", "items": items, **extra}


def test_basic_order_returns_expected_structure_and_string_amounts():
    result = process_order(order([{"sku": "book", "quantity": 2}]), CATALOG, {})

    assert result == {
        "customer": "Ada",
        "lines": [{"sku": "book", "quantity": 2, "amount": "24.69"}],
        "subtotal": "24.69",
        "tax": "0.00",
        "shipping": "7.50",
        "total": "32.19",
    }
    assert isinstance(result["customer"], str)
    assert isinstance(result["lines"], list)
    assert all(isinstance(result[key], str) for key in ("subtotal", "tax", "shipping", "total"))


def test_missing_customer_precedes_missing_items():
    with pytest.raises(ValueError, match="^missing customer$"):
        process_order({}, CATALOG, {})


def test_non_dict_order_has_exact_type_error():
    with pytest.raises(TypeError, match="^order must be a dict$"):
        process_order([], CATALOG, {})


def test_missing_items_has_exact_message():
    with pytest.raises(ValueError, match="^missing items$"):
        process_order({"customer": "Ada"}, CATALOG, {})


def test_items_must_be_a_list():
    with pytest.raises(TypeError, match="^items must be a list$"):
        process_order(order(({"sku": "book", "quantity": 1},)), CATALOG, {})


def test_empty_list_is_rejected():
    with pytest.raises(ValueError, match="^empty order$"):
        process_order(order([]), CATALOG, {})


def test_missing_sku_is_checked_before_missing_quantity():
    with pytest.raises(ValueError, match="^missing sku$"):
        process_order(order([{}]), CATALOG, {})


def test_missing_quantity_has_exact_message():
    with pytest.raises(ValueError, match="^missing quantity$"):
        process_order(order([{"sku": "book"}]), CATALOG, {})


def test_unknown_sku_precedes_invalid_quantity():
    with pytest.raises(ValueError, match="^unknown sku: absent$"):
        process_order(order([{"sku": "absent", "quantity": 0}]), CATALOG, {})


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2", None])
def test_invalid_quantity_is_rejected(quantity):
    with pytest.raises(ValueError, match="^invalid quantity$"):
        process_order(order([{"sku": "book", "quantity": quantity}]), CATALOG, {})


def test_boolean_quantity_retains_python_integer_behavior():
    result = process_order(order([{"sku": "book", "quantity": True}]), CATALOG, {})

    assert result["lines"][0]["quantity"] is True
    assert result["subtotal"] == "12.35"


def test_discount_is_applied_before_line_rounding():
    result = process_order(
        order([{"sku": "book", "quantity": 1, "discount": "10"}]), CATALOG, {}
    )

    assert result["lines"][0]["amount"] == "11.11"
    assert result["subtotal"] == "11.11"


def test_line_amount_rounding_does_not_change_subtotal_intermediate_precision():
    catalog = {"fraction": {"price": "0.005"}}
    result = process_order(order([{"sku": "fraction", "quantity": 1}] * 2), catalog, {})

    assert [line["amount"] for line in result["lines"]] == ["0.01", "0.01"]
    assert result["subtotal"] == "0.01"


def test_region_tax_uses_decimal_conversion_and_half_up_rounding():
    result = process_order(
        order([{"sku": "book", "quantity": 1}], region="east"),
        CATALOG,
        {"east": "8.25"},
    )

    assert result["tax"] == "1.02"


def test_unknown_region_has_zero_tax():
    result = process_order(
        order([{"sku": "book", "quantity": 1}], region="missing"), CATALOG, {}
    )

    assert result["tax"] == "0.00"


def test_regular_shipping_is_free_at_subtotal_threshold():
    catalog = {"item": {"price": "100"}}
    result = process_order(order([{"sku": "item", "quantity": 1}]), catalog, {})

    assert result["shipping"] == "0.00"


def test_express_shipping_overrides_free_shipping_threshold():
    catalog = {"item": {"price": "100"}}
    result = process_order(
        order([{"sku": "item", "quantity": 1}], priority="express"), catalog, {}
    )

    assert result["shipping"] == "15.00"


def test_non_express_priority_uses_regular_shipping():
    result = process_order(
        order([{"sku": "book", "quantity": 1}], priority="overnight"), CATALOG, {}
    )

    assert result["shipping"] == "7.50"


def test_customer_and_sku_values_are_returned_without_coercion():
    customer = {"id": 7}
    sku = 42
    result = process_order(
        order([{"sku": sku, "quantity": 1}], customer=customer),
        {sku: {"price": Decimal("1.00")}},
        {},
    )

    assert result["customer"] is customer
    assert result["lines"][0]["sku"] == sku
