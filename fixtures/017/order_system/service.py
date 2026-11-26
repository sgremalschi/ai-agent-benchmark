"""Order processing orchestration."""

from .events import EventStore
from .inventory import Inventory
from .models import Order


class OrderService:
    def __init__(self, inventory: Inventory, event_store: EventStore):
        raise NotImplementedError

    def place_order(self, order_id: str, sku: str, quantity: int) -> Order:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> Order:
        raise NotImplementedError

    def get_order(self, order_id: str) -> Order | None:
        raise NotImplementedError
