"""Simple, thread-safe inventory reservation service."""

from threading import RLock


class Inventory:
    def __init__(self):
        self.stock = {}
        self.reservations = {}
        self._lock = RLock()

    @staticmethod
    def _validate_quantity(quantity: int, *, allow_zero: bool) -> None:
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise ValueError("quantity must be an integer")
        if quantity < 0 or (not allow_zero and quantity == 0):
            raise ValueError("invalid quantity")

    def add_stock(self, sku: str, quantity: int) -> None:
        self._validate_quantity(quantity, allow_zero=True)
        with self._lock:
            self.stock[sku] = quantity

    def available(self, sku: str) -> int:
        with self._lock:
            return self.stock.get(sku, 0)

    def reserve(self, reservation_id: str, sku: str, quantity: int) -> bool:
        self._validate_quantity(quantity, allow_zero=False)
        with self._lock:
            if reservation_id in self.reservations:
                raise ValueError("duplicate active reservation ID")
            if self.stock.get(sku, 0) < quantity:
                return False
            self.stock[sku] -= quantity
            self.reservations[reservation_id] = (sku, quantity)
            return True

    def release(self, reservation_id: str) -> bool:
        with self._lock:
            reservation = self.reservations.pop(reservation_id, None)
            if reservation is None:
                return False
            sku, quantity = reservation
            self.stock[sku] = self.stock.get(sku, 0) + quantity
            return True

    def fulfill(self, reservation_id: str) -> bool:
        with self._lock:
            return self.reservations.pop(reservation_id, None) is not None
