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
        if order_id in self._orders:
            raise ValueError(f"Order {order_id!r} already exists")

        order = Order(order_id, sku, quantity, "PENDING")
        self._inventory.reserve(sku, quantity)
        try:
            self._event_store.publish(Event("OrderPlaced", order_id, sku, quantity))
        except Exception:
            self._inventory.release(sku, quantity)
            raise
        self._orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self._orders[order_id]
        if order.status == "CANCELLED":
            return order

        cancelled = Order(order.order_id, order.sku, order.quantity, "CANCELLED")
        # Publish before changing stock or the order so publication failure is harmless.
        self._event_store.publish(
            Event("OrderCancelled", order.order_id, order.sku, order.quantity)
        )
        self._inventory.release(order.sku, order.quantity)
        self._orders[order_id] = cancelled
        return cancelled

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)
