"""Inventory management."""


class Inventory:
    def __init__(self, initial_stock: dict[str, int]):
        raise NotImplementedError

    def available(self, sku: str) -> int:
        raise NotImplementedError
