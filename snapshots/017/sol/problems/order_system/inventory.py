"""Inventory management."""


class Inventory:
    def __init__(self, initial_stock: dict[str, int]):
        if any(
            isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0
            for quantity in initial_stock.values()
        ):
            raise ValueError("Initial stock must contain nonnegative integer quantities")
        self._stock = dict(initial_stock)

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserve(self, sku: str, quantity: int) -> None:
        self._validate_quantity(quantity)
        if self.available(sku) < quantity:
            raise ValueError(f"Insufficient stock for {sku!r}")
        self._stock[sku] -= quantity

    def release(self, sku: str, quantity: int) -> None:
        self._validate_quantity(quantity)
        self._stock[sku] = self.available(sku) + quantity

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
