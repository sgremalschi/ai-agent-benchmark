"""Tests for the in-memory order processing system."""

import pytest

from problems.order_system import EventStore, Inventory, OrderService


def setup_service(stock=None):
    inventory = Inventory(stock or {})
    events = EventStore()
    return OrderService(inventory, events), inventory, events


def test_successful_placement_reserves_stock_and_creates_pending_order():
    service, inventory, _ = setup_service({"book": 5})
    order = service.place_order("o1", "book", 2)
    assert (order.order_id, order.sku, order.quantity, order.status) == (
        "o1",
        "book",
        2,
        "PENDING",
    )
    assert inventory.available("book") == 3
    assert service.get_order("o1") == order


def test_placement_emits_one_order_placed_event():
    service, _, events = setup_service({"book": 2})
    service.place_order("o1", "book", 1)
    assert [(event.event_type, event.order_id) for event in events.events()] == [
        ("OrderPlaced", "o1")
    ]


def test_unknown_sku_has_zero_stock():
    _, inventory, _ = setup_service()
    assert inventory.available("missing") == 0


def test_initial_stock_is_copied():
    stock = {"book": 4}
    inventory = Inventory(stock)
    stock["book"] = 0
    assert inventory.available("book") == 4


@pytest.mark.parametrize("quantity", [0, -1, True, 1.5, "2", None])
def test_invalid_order_quantities_are_rejected(quantity):
    service, inventory, events = setup_service({"book": 4})
    with pytest.raises(ValueError):
        service.place_order("o1", "book", quantity)
    assert inventory.available("book") == 4
    assert service.get_order("o1") is None
    assert events.events() == []


@pytest.mark.parametrize("quantity", [-1, True, 1.5, "2"])
def test_invalid_initial_stock_is_rejected(quantity):
    with pytest.raises(ValueError):
        Inventory({"book": quantity})


def test_insufficient_stock_does_not_change_state():
    service, inventory, events = setup_service({"book": 1})
    with pytest.raises(ValueError):
        service.place_order("o1", "book", 2)
    assert inventory.available("book") == 1
    assert service.get_order("o1") is None
    assert events.events() == []


def test_duplicate_order_id_does_not_change_state():
    service, inventory, events = setup_service({"book": 5})
    service.place_order("o1", "book", 1)
    before_events = events.events()
    with pytest.raises(ValueError):
        service.place_order("o1", "book", 2)
    assert inventory.available("book") == 4
    assert service.get_order("o1").quantity == 1
    assert events.events() == before_events


def test_cancellation_restores_stock_and_changes_status():
    service, inventory, events = setup_service({"book": 5})
    service.place_order("o1", "book", 2)
    order = service.cancel_order("o1")
    assert order.status == "CANCELLED"
    assert service.get_order("o1").status == "CANCELLED"
    assert inventory.available("book") == 5
    assert events.events()[-1].event_type == "OrderCancelled"


def test_cancellation_emits_exactly_one_event():
    service, _, events = setup_service({"book": 5})
    service.place_order("o1", "book", 1)
    service.cancel_order("o1")
    assert [event.event_type for event in events.events()] == [
        "OrderPlaced",
        "OrderCancelled",
    ]


def test_repeated_cancellation_is_idempotent():
    service, inventory, events = setup_service({"book": 5})
    service.place_order("o1", "book", 2)
    first = service.cancel_order("o1")
    before_events = events.events()
    second = service.cancel_order("o1")
    assert second == first
    assert inventory.available("book") == 5
    assert events.events() == before_events


def test_cancelling_unknown_order_raises_key_error():
    service, _, _ = setup_service()
    with pytest.raises(KeyError):
        service.cancel_order("missing")


def test_get_unknown_order_returns_none():
    service, _, _ = setup_service()
    assert service.get_order("missing") is None


def test_event_order_matches_successful_operations():
    service, _, events = setup_service({"book": 5})
    service.place_order("first", "book", 1)
    service.place_order("second", "book", 1)
    service.cancel_order("first")
    assert [(event.event_type, event.order_id) for event in events.events()] == [
        ("OrderPlaced", "first"),
        ("OrderPlaced", "second"),
        ("OrderCancelled", "first"),
    ]


def test_events_returns_a_defensive_list_copy():
    service, _, events = setup_service({"book": 2})
    service.place_order("o1", "book", 1)
    snapshot = events.events()
    snapshot.clear()
    assert len(events.events()) == 1


@pytest.mark.parametrize("operation", ["place", "cancel"])
def test_publication_failure_does_not_commit_order_or_inventory(operation):
    class FailingEventStore(EventStore):
        def publish(self, event):
            raise RuntimeError("publication failed")

    inventory = Inventory({"book": 5})
    service = OrderService(inventory, FailingEventStore())
    if operation == "cancel":
        # Use a working store for placement, then fail the cancellation publish.
        working_store = EventStore()
        service = OrderService(inventory, working_store)
        service.place_order("o1", "book", 2)
        service._event_store = FailingEventStore()

    with pytest.raises(RuntimeError, match="publication failed"):
        if operation == "place":
            service.place_order("o1", "book", 2)
        else:
            service.cancel_order("o1")

    if operation == "place":
        assert inventory.available("book") == 5
        assert service.get_order("o1") is None
    else:
        assert inventory.available("book") == 3
        assert service.get_order("o1").status == "PENDING"
