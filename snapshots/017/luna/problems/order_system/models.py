"""Order and event domain models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    order_id: str
    sku: str
    quantity: int
    status: str


@dataclass(frozen=True)
class Event:
    event_type: str
    order_id: str
    sku: str
    quantity: int
