from concurrent.futures import ThreadPoolExecutor

import pytest

from problems.inventory import Inventory


def test_unknown_sku_has_zero_stock():
    assert Inventory().available("missing") == 0


def test_add_stock_replaces_existing_quantity():
    inventory = Inventory()
    inventory.add_stock("A", 8)
    inventory.add_stock("A", 3)
    assert inventory.available("A") == 3


def test_zero_stock_is_valid():
    inventory = Inventory()
    inventory.add_stock("A", 0)
    assert inventory.available("A") == 0


def test_reserve_deducts_stock_once():
    inventory = Inventory()
    inventory.add_stock("A", 5)
    assert inventory.reserve("r1", "A", 2)
    assert inventory.available("A") == 3


def test_reserve_exact_available_quantity():
    inventory = Inventory()
    inventory.add_stock("A", 4)
    assert inventory.reserve("r1", "A", 4)
    assert inventory.available("A") == 0


def test_insufficient_stock_fails_without_state_change():
    inventory = Inventory()
    inventory.add_stock("A", 2)
    assert not inventory.reserve("r1", "A", 3)
    assert inventory.available("A") == 2
    assert inventory.reserve("r1", "A", 2)


def test_reservation_lifecycle_release_restores_stock():
    inventory = Inventory()
    inventory.add_stock("A", 6)
    assert inventory.reserve("r1", "A", 4)
    assert inventory.release("r1")
    assert inventory.available("A") == 6


def test_repeated_release_returns_false_and_does_not_restore_twice():
    inventory = Inventory()
    inventory.add_stock("A", 6)
    inventory.reserve("r1", "A", 4)
    assert inventory.release("r1")
    assert not inventory.release("r1")
    assert inventory.available("A") == 6


def test_fulfill_consumes_stock_without_restoring_it():
    inventory = Inventory()
    inventory.add_stock("A", 6)
    assert inventory.reserve("r1", "A", 4)
    assert inventory.fulfill("r1")
    assert inventory.available("A") == 2


def test_repeated_fulfill_returns_false():
    inventory = Inventory()
    inventory.add_stock("A", 2)
    inventory.reserve("r1", "A", 1)
    assert inventory.fulfill("r1")
    assert not inventory.fulfill("r1")


def test_reservation_id_reuse_after_release():
    inventory = Inventory()
    inventory.add_stock("A", 3)
    assert inventory.reserve("r1", "A", 1)
    assert inventory.release("r1")
    assert inventory.reserve("r1", "A", 1)


def test_reservation_id_reuse_after_fulfillment():
    inventory = Inventory()
    inventory.add_stock("A", 3)
    assert inventory.reserve("r1", "A", 1)
    assert inventory.fulfill("r1")
    assert inventory.reserve("r1", "A", 1)


def test_duplicate_active_id_raises_without_changing_state():
    inventory = Inventory()
    inventory.add_stock("A", 5)
    assert inventory.reserve("r1", "A", 2)
    with pytest.raises(ValueError):
        inventory.reserve("r1", "A", 1)
    assert inventory.available("A") == 3
    assert inventory.release("r1")
    assert inventory.available("A") == 5


def test_reservation_for_unknown_sku_fails():
    inventory = Inventory()
    assert not inventory.reserve("r1", "missing", 1)
    assert inventory.available("missing") == 0


def test_sku_stock_and_reservations_are_isolated():
    inventory = Inventory()
    inventory.add_stock("A", 5)
    inventory.add_stock("B", 7)
    assert inventory.reserve("r1", "A", 3)
    assert inventory.available("A") == 2
    assert inventory.available("B") == 7
    assert inventory.release("r1")
    assert inventory.available("A") == 5
    assert inventory.available("B") == 7


@pytest.mark.parametrize("quantity", [-1, -5])
def test_negative_stock_quantity_raises_without_mutation(quantity):
    inventory = Inventory()
    inventory.add_stock("A", 4)
    with pytest.raises(ValueError):
        inventory.add_stock("A", quantity)
    assert inventory.available("A") == 4


@pytest.mark.parametrize("quantity", [0, -1, -3])
def test_nonpositive_reservation_quantity_raises_without_mutation(quantity):
    inventory = Inventory()
    inventory.add_stock("A", 4)
    with pytest.raises(ValueError):
        inventory.reserve("r1", "A", quantity)
    assert inventory.available("A") == 4
    assert inventory.reserve("r1", "A", 4)


@pytest.mark.parametrize("quantity", [1.5, "2", True])
def test_non_integer_stock_quantity_raises_without_mutation(quantity):
    inventory = Inventory()
    inventory.add_stock("A", 4)
    with pytest.raises(ValueError):
        inventory.add_stock("A", quantity)
    assert inventory.available("A") == 4


@pytest.mark.parametrize("quantity", [1.5, "2", True])
def test_non_integer_reservation_quantity_raises_without_mutation(quantity):
    inventory = Inventory()
    inventory.add_stock("A", 4)
    with pytest.raises(ValueError):
        inventory.reserve("r1", "A", quantity)
    assert inventory.available("A") == 4


def test_concurrent_reservations_never_oversell():
    inventory = Inventory()
    inventory.add_stock("A", 17)

    def reserve(index):
        return inventory.reserve(f"r{index}", "A", 1)

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(reserve, range(100)))

    assert sum(results) == 17
    assert inventory.available("A") == 0
    assert sum(inventory.fulfill(f"r{index}") for index in range(100)) == 17
