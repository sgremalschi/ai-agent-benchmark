"""Behavioral tests for the synchronous order processing system."""

from dataclasses import FrozenInstanceError

import pytest

from problems.order_system import Event, EventStore, Inventory, Order, OrderService


@pytest.fixture
def system():
    inventory = Inventory({"widget": 10, "gadget": 4})
    events = EventStore()
    return OrderService(inventory, events), inventory, events


def test_placement_reserves_stock_and_returns_pending_order(system):
    service, inventory, _ = system
    order = service.place_order("one", "widget", 3)
    assert order == Order("one", "widget", 3, "PENDING")
    assert inventory.available("widget") == 7
    assert service.get_order("one") == order


def test_placement_emits_exactly_one_complete_event(system):
    service, _, events = system
    service.place_order("one", "widget", 3)
    assert events.events() == [Event("OrderPlaced", "one", "widget", 3)]


def test_placement_can_exhaust_stock(system):
    service, inventory, _ = system
    service.place_order("one", "widget", 10)
    assert inventory.available("widget") == 0


def test_duplicate_id_preserves_order_inventory_and_events(system):
    service, inventory, events = system
    original = service.place_order("one", "widget", 3)
    before = events.events()
    with pytest.raises(ValueError):
        service.place_order("one", "gadget", 2)
    assert service.get_order("one") == original
    assert inventory.available("widget") == 7
    assert inventory.available("gadget") == 4
    assert events.events() == before


@pytest.mark.parametrize("quantity", [0, -1, True, False, 1.0, "2", None])
def test_invalid_order_quantities_leave_state_unchanged(system, quantity):
    service, inventory, events = system
    with pytest.raises(ValueError):
        service.place_order("one", "widget", quantity)
    assert service.get_order("one") is None
    assert inventory.available("widget") == 10
    assert events.events() == []


@pytest.mark.parametrize("quantity", [-1, True, False, 1.5, "2", None])
def test_invalid_initial_stock_is_rejected(quantity):
    with pytest.raises(ValueError):
        Inventory({"valid": 3, "invalid": quantity})


def test_zero_initial_stock_is_valid():
    assert Inventory({"widget": 0}).available("widget") == 0


def test_initial_stock_is_copied():
    stock = {"widget": 10}
    inventory = Inventory(stock)
    stock["widget"] = 999
    assert inventory.available("widget") == 10


def test_unknown_sku_has_zero_stock():
    assert Inventory({}).available("unknown") == 0


@pytest.mark.parametrize("sku, quantity", [("widget", 11), ("unknown", 1)])
def test_insufficient_stock_leaves_state_unchanged(system, sku, quantity):
    service, inventory, events = system
    with pytest.raises(ValueError):
        service.place_order("one", sku, quantity)
    assert service.get_order("one") is None
    assert inventory.available("widget") == 10
    assert inventory.available("unknown") == 0
    assert events.events() == []


def test_cancellation_restores_stock_and_changes_status(system):
    service, inventory, _ = system
    service.place_order("one", "widget", 3)
    cancelled = service.cancel_order("one")
    assert cancelled == Order("one", "widget", 3, "CANCELLED")
    assert service.get_order("one") == cancelled
    assert inventory.available("widget") == 10


def test_cancellation_emits_exactly_one_complete_event(system):
    service, _, events = system
    service.place_order("one", "widget", 3)
    service.cancel_order("one")
    assert events.events() == [
        Event("OrderPlaced", "one", "widget", 3),
        Event("OrderCancelled", "one", "widget", 3),
    ]


def test_repeated_cancellation_is_idempotent(system):
    service, inventory, events = system
    service.place_order("one", "widget", 3)
    cancelled = service.cancel_order("one")
    before = events.events()
    assert service.cancel_order("one") == cancelled
    assert service.cancel_order("one") == cancelled
    assert inventory.available("widget") == 10
    assert events.events() == before


def test_cancelled_order_id_cannot_be_reused(system):
    service, inventory, events = system
    service.place_order("one", "widget", 3)
    service.cancel_order("one")
    with pytest.raises(ValueError):
        service.place_order("one", "widget", 2)
    assert service.get_order("one").status == "CANCELLED"
    assert inventory.available("widget") == 10
    assert len(events.events()) == 2


def test_cancelling_unknown_order_raises_without_changes(system):
    service, inventory, events = system
    with pytest.raises(KeyError):
        service.cancel_order("unknown")
    assert inventory.available("widget") == 10
    assert events.events() == []


def test_get_unknown_order_returns_none(system):
    service, _, _ = system
    assert service.get_order("unknown") is None


def test_events_follow_successful_operation_order(system):
    service, _, events = system
    service.place_order("one", "widget", 2)
    with pytest.raises(ValueError):
        service.place_order("bad", "widget", 100)
    service.place_order("two", "gadget", 1)
    service.cancel_order("one")
    service.cancel_order("one")
    service.cancel_order("two")
    assert events.events() == [
        Event("OrderPlaced", "one", "widget", 2),
        Event("OrderPlaced", "two", "gadget", 1),
        Event("OrderCancelled", "one", "widget", 2),
        Event("OrderCancelled", "two", "gadget", 1),
    ]


def test_events_returns_independent_lists(system):
    service, _, events = system
    snapshot = events.events()
    service.place_order("one", "widget", 2)
    assert snapshot == []
    snapshot = events.events()
    snapshot.clear()
    snapshot.append(Event("Fake", "fake", "widget", 99))
    assert events.events() == [Event("OrderPlaced", "one", "widget", 2)]


def test_orders_cannot_be_mutated_by_callers(system):
    service, inventory, _ = system
    order = service.place_order("one", "widget", 2)
    with pytest.raises(FrozenInstanceError):
        order.quantity = 100
    service.cancel_order("one")
    assert inventory.available("widget") == 10


def test_stored_events_cannot_be_mutated_by_callers(system):
    service, _, events = system
    service.place_order("one", "widget", 2)
    with pytest.raises(FrozenInstanceError):
        events.events()[0].quantity = 100
    assert events.events()[0].quantity == 2


class FailingEventStore(EventStore):
    def __init__(self):
        super().__init__()
        self.fail = True

    def publish(self, event):
        if self.fail:
            raise RuntimeError("Publication failed")
        super().publish(event)


def test_failed_placement_rolls_back_and_can_be_retried():
    inventory = Inventory({"widget": 10})
    events = FailingEventStore()
    service = OrderService(inventory, events)
    with pytest.raises(RuntimeError, match="Publication failed"):
        service.place_order("one", "widget", 3)
    assert inventory.available("widget") == 10
    assert service.get_order("one") is None
    assert events.events() == []
    events.fail = False
    assert service.place_order("one", "widget", 3).status == "PENDING"
    assert inventory.available("widget") == 7
    assert events.events() == [Event("OrderPlaced", "one", "widget", 3)]


def test_failed_cancellation_preserves_pending_order_and_can_be_retried():
    inventory = Inventory({"widget": 10})
    events = FailingEventStore()
    events.fail = False
    service = OrderService(inventory, events)
    original = service.place_order("one", "widget", 3)
    events.fail = True
    with pytest.raises(RuntimeError, match="Publication failed"):
        service.cancel_order("one")
    assert inventory.available("widget") == 7
    assert service.get_order("one") == original
    assert events.events() == [Event("OrderPlaced", "one", "widget", 3)]
    events.fail = False
    assert service.cancel_order("one").status == "CANCELLED"
    assert inventory.available("widget") == 10
    assert events.events()[-1] == Event("OrderCancelled", "one", "widget", 3)
    assert len(events.events()) == 2


def test_idempotent_cancellation_does_not_attempt_publication():
    inventory = Inventory({"widget": 10})
    events = FailingEventStore()
    events.fail = False
    service = OrderService(inventory, events)
    service.place_order("one", "widget", 3)
    service.cancel_order("one")
    events.fail = True
    assert service.cancel_order("one").status == "CANCELLED"
    assert inventory.available("widget") == 10
    assert len(events.events()) == 2


def test_orders_share_available_inventory_and_cancel_independently(system):
    service, inventory, _ = system
    service.place_order("one", "widget", 6)
    service.place_order("two", "widget", 4)
    with pytest.raises(ValueError):
        service.place_order("three", "widget", 1)
    service.cancel_order("one")
    assert inventory.available("widget") == 6
    assert service.get_order("two").status == "PENDING"
    service.place_order("three", "widget", 6)
    assert inventory.available("widget") == 0
