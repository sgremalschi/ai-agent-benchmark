"""Independent acceptance tests for Experiment 016."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from problems.inventory import Inventory


def test_unknown_sku():
    assert Inventory().available("missing") == 0


def test_add_stock():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    assert inventory.available("A") == 10


def test_add_stock_replaces_quantity():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    inventory.add_stock("A", 4)
    assert inventory.available("A") == 4


def test_zero_stock_allowed():
    inventory = Inventory()
    inventory.add_stock("A", 0)
    assert inventory.available("A") == 0


@pytest.mark.parametrize("quantity", [-1, -10])
def test_negative_stock_rejected(quantity):
    inventory = Inventory()
    with pytest.raises(ValueError):
        inventory.add_stock("A", quantity)
    assert inventory.available("A") == 0


@pytest.mark.parametrize("quantity", [0, -1, -10])
def test_nonpositive_reservation_rejected(quantity):
    inventory = Inventory()
    inventory.add_stock("A", 10)
    with pytest.raises(ValueError):
        inventory.reserve("r1", "A", quantity)
    assert inventory.available("A") == 10


def test_successful_reservation():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    assert inventory.reserve("r1", "A", 4)
    assert inventory.available("A") == 6


def test_insufficient_stock():
    inventory = Inventory()
    inventory.add_stock("A", 3)
    assert inventory.reserve("r1", "A", 4) is False
    assert inventory.available("A") == 3
    assert inventory.release("r1") is False


def test_unknown_sku_reservation():
    inventory = Inventory()
    assert inventory.reserve("r1", "missing", 1) is False
    assert inventory.available("missing") == 0


def test_duplicate_active_reservation_id():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    assert inventory.reserve("r1", "A", 3)
    with pytest.raises(ValueError):
        inventory.reserve("r1", "A", 2)
    assert inventory.available("A") == 7
    assert inventory.release("r1")
    assert inventory.available("A") == 10


def test_duplicate_id_across_skus():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    inventory.add_stock("B", 10)
    assert inventory.reserve("r1", "A", 3)
    with pytest.raises(ValueError):
        inventory.reserve("r1", "B", 4)
    assert inventory.available("A") == 7
    assert inventory.available("B") == 10


def test_release_restores_stock():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    inventory.reserve("r1", "A", 4)
    assert inventory.release("r1")
    assert inventory.available("A") == 10


def test_release_only_once():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    inventory.reserve("r1", "A", 4)
    assert inventory.release("r1")
    assert inventory.release("r1") is False
    assert inventory.available("A") == 10


def test_fulfill_consumes_reservation():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    inventory.reserve("r1", "A", 4)
    assert inventory.fulfill("r1")
    assert inventory.available("A") == 6
    assert inventory.fulfill("r1") is False
    assert inventory.release("r1") is False


@pytest.mark.parametrize("operation", ["release", "fulfill"])
def test_reservation_id_reusable(operation):
    inventory = Inventory()
    inventory.add_stock("A", 10)
    assert inventory.reserve("r1", "A", 3)
    assert getattr(inventory, operation)("r1")
    assert inventory.reserve("r1", "A", 2)


def test_sku_isolation():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    inventory.add_stock("B", 7)
    inventory.reserve("r1", "A", 4)
    assert inventory.available("B") == 7
    inventory.release("r1")
    assert inventory.available("B") == 7


def test_concurrent_reservations_never_oversell():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    barrier = Barrier(20)

    def reserve(i):
        barrier.wait()
        return inventory.reserve(f"r{i}", "A", 1)

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(reserve, range(20)))

    assert sum(results) == 10
    assert inventory.available("A") == 0


def test_concurrent_release_only_once():
    inventory = Inventory()
    inventory.add_stock("A", 10)
    inventory.reserve("r1", "A", 4)
    barrier = Barrier(10)

    def release(_):
        barrier.wait()
        return inventory.release("r1")

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(release, range(10)))

    assert sum(results) == 1
    assert inventory.available("A") == 10


@pytest.mark.parametrize("quantity", [0.5, 1.5, True, False])
@pytest.mark.parametrize("operation", ["add_stock", "reserve"])
def test_quantity_type_rejection_preserves_state(quantity, operation):
    inventory = Inventory()
    inventory.add_stock("A", 10)
    assert inventory.reserve("existing", "A", 3)
    with pytest.raises(ValueError):
        if operation == "add_stock":
            inventory.add_stock("A", quantity)
        else:
            inventory.reserve("new", "A", quantity)
    assert inventory.available("A") == 7
    assert inventory.release("new") is False
    assert inventory.reserve("new", "A", 2)
    assert inventory.release("new")
    assert inventory.release("existing")
    assert inventory.available("A") == 10
