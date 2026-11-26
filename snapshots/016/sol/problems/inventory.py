"""Simple inventory reservation service."""

from threading import Lock


class Inventory:
    def __init__(self):
        self.stock = {}
        self.reservations = {}
        self._lock = Lock()

    def add_stock(self, sku: str, quantity: int) -> None:
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            raise ValueError("stock quantity must be a nonnegative integer")
        with self._lock:
            self.stock[sku] = quantity

    def available(self, sku: str) -> int:
        with self._lock:
            return self.stock.get(sku, 0)

    def reserve(self, reservation_id: str, sku: str, quantity: int) -> bool:
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("reservation quantity must be a positive integer")
        with self._lock:
            if reservation_id in self.reservations:
                raise ValueError("reservation ID is already active")
            available = self.stock.get(sku, 0)
            if available < quantity:
                return False
            self.stock[sku] = available - quantity
            self.reservations[reservation_id] = (sku, quantity)
            return True

    def release(self, reservation_id: str) -> bool:
        with self._lock:
            reservation = self.reservations.pop(reservation_id, None)
            if reservation is None:
                return False
            sku, quantity = reservation
            self.stock[sku] += quantity
            return True

    def fulfill(self, reservation_id: str) -> bool:
        with self._lock:
            return self.reservations.pop(reservation_id, None) is not None
