"""Independent acceptance tests for Experiment 017."""

import pytest

from problems.order_system import (
    Event,
    EventStore,
    Inventory,
    OrderService,
)


def make_system(stock=None):
    inventory = Inventory({"A": 10, "B": 5} if stock is None else stock)
    store = EventStore()
    service = OrderService(inventory, store)
    return service, inventory, store


def test_unknown_sku_has_zero_stock():
    _, inventory, _ = make_system()
    assert inventory.available("missing") == 0


def test_initial_stock():
    _, inventory, _ = make_system()
    assert inventory.available("A") == 10
    assert inventory.available("B") == 5


@pytest.mark.parametrize("quantity", [-1, -10, 1.5, True])
def test_invalid_initial_stock(quantity):
    with pytest.raises(ValueError):
        Inventory({"A": quantity})


def test_negative_and_zero_initial_stock():
    inventory = Inventory({"A": 0})
    assert inventory.available("A") == 0


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, False])
def test_invalid_order_quantity(quantity):
    service, inventory, store = make_system()
    with pytest.raises(ValueError):
        service.place_order("o1", "A", quantity)
    assert inventory.available("A") == 10
    assert service.get_order("o1") is None
    assert store.events() == []


def test_successful_placement():
    service, inventory, store = make_system()
    order = service.place_order("o1", "A", 3)
    assert order.order_id == "o1"
    assert order.sku == "A"
    assert order.quantity == 3
    assert order.status == "PENDING"
    assert inventory.available("A") == 7
    assert store.events() == [Event("OrderPlaced", "o1", "A", 3)]


def test_exact_stock_reservation():
    service, inventory, _ = make_system({"A": 3})
    service.place_order("o1", "A", 3)
    assert inventory.available("A") == 0


def test_insufficient_stock_is_atomic():
    service, inventory, store = make_system({"A": 2})
    with pytest.raises(ValueError):
        service.place_order("o1", "A", 3)
    assert inventory.available("A") == 2
    assert service.get_order("o1") is None
    assert store.events() == []


def test_unknown_sku_order_rejected():
    service, inventory, store = make_system()
    with pytest.raises(ValueError):
        service.place_order("o1", "missing", 1)
    assert inventory.available("missing") == 0
    assert store.events() == []


def test_duplicate_order_id_is_atomic():
    service, inventory, store = make_system()
    service.place_order("o1", "A", 3)
    with pytest.raises(ValueError):
        service.place_order("o1", "B", 2)
    assert inventory.available("A") == 7
    assert inventory.available("B") == 5
    assert len(store.events()) == 1


def test_cancellation_restores_stock():
    service, inventory, store = make_system()
    service.place_order("o1", "A", 3)
    order = service.cancel_order("o1")
    assert order.status == "CANCELLED"
    assert inventory.available("A") == 10
    assert store.events()[-1] == Event("OrderCancelled", "o1", "A", 3)


def test_repeated_cancellation_is_idempotent():
    service, inventory, store = make_system()
    service.place_order("o1", "A", 3)
    service.cancel_order("o1")
    events_before = store.events()
    assert service.cancel_order("o1").status == "CANCELLED"
    assert inventory.available("A") == 10
    assert store.events() == events_before


def test_cancel_unknown_order():
    service, _, _ = make_system()
    with pytest.raises(KeyError):
        service.cancel_order("missing")


def test_get_unknown_order():
    service, _, _ = make_system()
    assert service.get_order("missing") is None


def test_event_order():
    service, _, store = make_system()
    service.place_order("o1", "A", 2)
    service.place_order("o2", "B", 1)
    service.cancel_order("o1")
    assert [event.event_type for event in store.events()] == [
        "OrderPlaced",
        "OrderPlaced",
        "OrderCancelled",
    ]
    assert [event.order_id for event in store.events()] == [
        "o1",
        "o2",
        "o1",
    ]


def test_event_list_is_defensive_copy():
    service, _, store = make_system()
    service.place_order("o1", "A", 1)
    returned = store.events()
    returned.clear()
    assert len(store.events()) == 1


def test_sku_isolation():
    service, inventory, _ = make_system()
    service.place_order("o1", "A", 3)
    assert inventory.available("B") == 5
    service.cancel_order("o1")
    assert inventory.available("B") == 5


class FailingEventStore(EventStore):
    def __init__(self):
        super().__init__()
        self.fail = False

    def publish(self, event):
        if self.fail:
            raise RuntimeError("simulated event publication failure")
        super().publish(event)


def test_placement_publish_failure_rolls_back():
    inventory = Inventory({"A": 10})
    store = FailingEventStore()
    service = OrderService(inventory, store)
    store.fail = True

    with pytest.raises(RuntimeError):
        service.place_order("o1", "A", 3)

    assert inventory.available("A") == 10
    assert service.get_order("o1") is None
    assert store.events() == []

    store.fail = False
    assert service.place_order("o1", "A", 3).status == "PENDING"


def test_cancellation_publish_failure_rolls_back():
    inventory = Inventory({"A": 10})
    store = FailingEventStore()
    service = OrderService(inventory, store)

    service.place_order("o1", "A", 3)
    store.fail = True

    with pytest.raises(RuntimeError):
        service.cancel_order("o1")

    assert inventory.available("A") == 7
    assert service.get_order("o1").status == "PENDING"
    assert len(store.events()) == 1

    store.fail = False
    assert service.cancel_order("o1").status == "CANCELLED"
    assert inventory.available("A") == 10


def test_multiple_orders_accounting():
    service, inventory, store = make_system()
    service.place_order("o1", "A", 3)
    service.place_order("o2", "A", 4)
    assert inventory.available("A") == 3

    service.cancel_order("o1")
    assert inventory.available("A") == 6
    assert len(store.events()) == 3
