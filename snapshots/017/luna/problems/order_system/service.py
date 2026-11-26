"""Order processing orchestration."""

from .events import EventStore
from .inventory import Inventory
from .models import Event, Order


class OrderService:
    def __init__(self, inventory: Inventory, event_store: EventStore):
        self._inventory = inventory
        self._event_store = event_store
        self._orders: dict[str, Order] = {}

    def place_order(self, order_id: str, sku: str, quantity: int) -> Order:
        _validate_quantity(quantity)
        if order_id in self._orders:
            raise ValueError(f"Order {order_id!r} already exists")
        if self._inventory.available(sku) < quantity:
            raise ValueError(f"Insufficient stock for SKU {sku!r}")

        order = Order(order_id, sku, quantity, "PENDING")
        self._event_store.publish(Event("OrderPlaced", order_id, sku, quantity))
        self._inventory._reserve(sku, quantity)
        self._orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> Order:
        try:
            order = self._orders[order_id]
        except KeyError:
            raise KeyError(order_id) from None
        if order.status == "CANCELLED":
            return order

        cancelled = Order(order.order_id, order.sku, order.quantity, "CANCELLED")
        self._event_store.publish(
            Event("OrderCancelled", order.order_id, order.sku, order.quantity)
        )
        self._inventory._restore(order.sku, order.quantity)
        self._orders[order_id] = cancelled
        return cancelled

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)


def _validate_quantity(quantity: int) -> None:
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Quantity must be a positive integer")
