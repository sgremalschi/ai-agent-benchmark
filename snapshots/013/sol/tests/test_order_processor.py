from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext

import pytest

from problems.order_processor import process_order


@pytest.fixture
def catalog():
    return {"A": {"price": "10"}, "B": {"price": "0.335"}}


def make_order(**overrides):
    return {"customer": "Ada", "items": [{"sku": "A", "quantity": 1}], **overrides}


def test_complete_result_and_value_types(catalog):
    customer = {"name": "Ada"}
    order = make_order(
        customer=customer,
        items=[{"sku": "A", "quantity": 2, "discount": 10}, {"sku": "B", "quantity": 3}],
        region="NY",
    )

    result = process_order(order, catalog, {"NY": "8.25"})

    assert result == {
        "customer": customer,
        "lines": [
            {"sku": "A", "quantity": 2, "amount": "18.00"},
            {"sku": "B", "quantity": 3, "amount": "1.01"},
        ],
        "subtotal": "19.01",
        "tax": "1.57",
        "shipping": "7.50",
        "total": "28.07",
    }
    assert list(result) == ["customer", "lines", "subtotal", "tax", "shipping", "total"]
    assert result["customer"] is customer
    assert type(result["lines"]) is list
    assert type(result["lines"][0]["quantity"]) is int
    assert all(type(result[key]) is str for key in ("subtotal", "tax", "shipping", "total"))


@pytest.mark.parametrize(
    ("order", "error", "message"),
    [
        (None, TypeError, "order must be a dict"),
        ([], TypeError, "order must be a dict"),
        ({}, ValueError, "missing customer"),
        ({"items": None}, ValueError, "missing customer"),
        ({"customer": None}, ValueError, "missing items"),
        (make_order(items=()), TypeError, "items must be a list"),
        (make_order(items=[]), ValueError, "empty order"),
    ],
)
def test_order_validation_order_and_messages(order, error, message):
    with pytest.raises(error) as caught:
        process_order(order, None, None)
    assert type(caught.value) is error
    assert str(caught.value) == message


@pytest.mark.parametrize(
    ("item", "message"),
    [
        ({}, "missing sku"),
        ({"quantity": 0}, "missing sku"),
        ({"sku": "unknown"}, "missing quantity"),
        ({"sku": "unknown", "quantity": 0}, "unknown sku: unknown"),
        ({"sku": 42, "quantity": 1}, "unknown sku: 42"),
        ({"sku": "A", "quantity": 0}, "invalid quantity"),
        ({"sku": "A", "quantity": -1}, "invalid quantity"),
        ({"sku": "A", "quantity": 1.0}, "invalid quantity"),
        ({"sku": "A", "quantity": "1"}, "invalid quantity"),
        ({"sku": "A", "quantity": False}, "invalid quantity"),
    ],
)
def test_item_validation_order_and_messages(catalog, item, message):
    with pytest.raises(ValueError) as caught:
        process_order(make_order(items=[item]), catalog, None)
    assert type(caught.value) is ValueError
    assert str(caught.value) == message


def test_true_quantity_is_preserved(catalog):
    result = process_order(make_order(items=[{"sku": "A", "quantity": True}]), catalog, {})
    assert result["lines"] == [{"sku": "A", "quantity": True, "amount": "10.00"}]
    assert result["lines"][0]["quantity"] is True


@pytest.mark.parametrize(
    ("discount", "amount"),
    [("-10", "11.00"), ("100", "0.00"), ("150", "-5.00"), ("0.5", "9.95")],
)
def test_unrestricted_discounts(catalog, discount, amount):
    result = process_order(
        make_order(items=[{"sku": "A", "quantity": 1, "discount": discount}]), catalog, {}
    )
    assert result["lines"][0]["amount"] == amount
    assert result["subtotal"] == amount
    assert result["shipping"] == "7.50"


@pytest.mark.parametrize(
    ("price", "priority", "shipping", "total"),
    [
        ("99.999", None, "7.50", "107.50"),
        ("100", None, "0.00", "100.00"),
        ("101", "express", "15.00", "116.00"),
        ("10", "express", "15.00", "25.00"),
        ("10", "Express", "7.50", "17.50"),
        ("10", True, "7.50", "17.50"),
    ],
)
def test_shipping_uses_unrounded_subtotal_and_exact_priority(price, priority, shipping, total):
    result = process_order(make_order(priority=priority), {"A": {"price": price}}, {})
    assert result["shipping"] == shipping
    assert result["total"] == total


@pytest.mark.parametrize(
    ("overrides", "rates", "tax"),
    [
        ({}, {"default": "12.5"}, "1.25"),
        ({"region": "unknown"}, {"default": "12.5"}, "0.00"),
        ({"region": None}, {None: "-5"}, "-0.50"),
        ({"region": "NY"}, {"NY": "2.55"}, "0.26"),
    ],
)
def test_tax_region_defaults_and_rounding(catalog, overrides, rates, tax):
    assert process_order(make_order(**overrides), catalog, rates)["tax"] == tax


def test_line_rounding_does_not_affect_subtotal_or_total():
    order = make_order(items=[{"sku": "A", "quantity": 1}] * 2)
    result = process_order(order, {"A": {"price": "0.005"}}, {"default": "50"})
    assert [line["amount"] for line in result["lines"]] == ["0.01", "0.01"]
    assert result["subtotal"] == "0.01"
    assert result["tax"] == "0.01"
    assert result["total"] == "7.52"


def test_negative_half_cent_rounds_away_from_zero():
    result = process_order(make_order(), {"A": {"price": "-0.005"}}, {})
    assert result["lines"][0]["amount"] == "-0.01"
    assert result["subtotal"] == "-0.01"
    assert result["tax"] == "-0.00"
    assert result["total"] == "7.50"


def test_intermediate_arithmetic_respects_decimal_context():
    with localcontext() as context:
        context.prec = 6
        result = process_order(
            make_order(items=[{"sku": "A", "quantity": 3, "discount": "7.5"}]),
            {"A": {"price": "12.345"}},
            {"default": "8.25"},
        )
    assert result["subtotal"] == "34.26"
    assert result["tax"] == "2.83"
    assert result["total"] == "44.58"


def test_numeric_values_are_converted_through_strings():
    result = process_order(
        make_order(items=[{"sku": "A", "quantity": 1, "discount": Decimal("0")}]),
        {"A": {"price": 2.675}},
        {"default": 10.0},
    )
    assert result["subtotal"] == "2.68"
    assert result["tax"] == "0.27"
    assert result["total"] == "10.44"


def test_inputs_are_not_mutated(catalog):
    order = make_order(items=[{"sku": "A", "quantity": 2, "discount": "5"}])
    rates = {"default": "5"}
    before = deepcopy((order, catalog, rates))
    process_order(order, catalog, rates)
    assert (order, catalog, rates) == before


def test_first_line_failure_precedes_later_item_validation(catalog):
    with pytest.raises(InvalidOperation):
        process_order(
            make_order(items=[{"sku": "A", "quantity": 1, "discount": None}, {}]),
            catalog,
            None,
        )


def test_invalid_quantity_precedes_missing_price():
    with pytest.raises(ValueError, match="^invalid quantity$"):
        process_order(make_order(items=[{"sku": "A", "quantity": 0}]), {"A": {}}, None)


def test_missing_price_is_not_wrapped():
    with pytest.raises(KeyError) as caught:
        process_order(make_order(), {"A": {}}, None)
    assert caught.value.args == ("price",)


def test_non_mapping_item_retains_native_error(catalog):
    item = None
    with pytest.raises(TypeError) as native:
        "sku" in item
    with pytest.raises(TypeError) as caught:
        process_order(make_order(items=[item]), catalog, None)
    assert caught.value.args == native.value.args


def test_unhashable_sku_retains_native_error(catalog):
    with pytest.raises(TypeError) as native:
        [] in catalog
    with pytest.raises(TypeError) as caught:
        process_order(make_order(items=[{"sku": [], "quantity": 0}]), catalog, None)
    assert caught.value.args == native.value.args


def test_invalid_tax_precedes_shipping_lookup(catalog):
    class Order(dict):
        def get(self, key, default=None):
            assert key != "priority", "shipping was evaluated before tax"
            return super().get(key, default)

    with pytest.raises(InvalidOperation):
        process_order(Order(make_order()), catalog, {"default": "invalid"})


def test_nan_subtotal_fails_shipping_comparison():
    with pytest.raises(InvalidOperation):
        process_order(make_order(), {"A": {"price": "NaN"}}, {})


def test_express_priority_bypasses_nan_shipping_comparison():
    result = process_order(make_order(priority="express"), {"A": {"price": "NaN"}}, {})
    assert result["lines"][0]["amount"] == "NaN"
    assert result["subtotal"] == result["tax"] == result["total"] == "NaN"
    assert result["shipping"] == "15.00"
