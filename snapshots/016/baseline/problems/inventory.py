"""Simple inventory reservation service."""


class Inventory:
    def __init__(self):
        self.stock = {}
        self.reservations = {}

    def add_stock(self, sku: str, quantity: int) -> None:
        if quantity < 0:
            raise ValueError("negative quantity")
        self.stock[sku] = quantity

    def available(self, sku: str) -> int:
        return self.stock.get(sku, 0)

    def reserve(self, reservation_id: str, sku: str, quantity: int) -> bool:
        if quantity < 0:
            raise ValueError("negative quantity")
        if self.available(sku) < quantity:
            return False
        self.stock[sku] -= quantity
        self.reservations[reservation_id] = (sku, quantity)
        return True

    def release(self, reservation_id: str) -> bool:
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            return False
        sku, quantity = reservation
        self.stock[sku] += quantity
        return True

    def fulfill(self, reservation_id: str) -> bool:
        if reservation_id not in self.reservations:
            return False
        del self.reservations[reservation_id]
        return True
