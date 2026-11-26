"""Inventory management."""


class Inventory:
    def __init__(self, initial_stock: dict[str, int]):
        for sku, quantity in initial_stock.items():
            if not isinstance(sku, str):
                raise ValueError("SKU names must be strings")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
                raise ValueError("Stock quantities must be nonnegative integers")
        self._stock = initial_stock.copy()

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def _reserve(self, sku: str, quantity: int) -> None:
        self._stock[sku] = self.available(sku) - quantity

    def _restore(self, sku: str, quantity: int) -> None:
        self._stock[sku] = self.available(sku) + quantity
