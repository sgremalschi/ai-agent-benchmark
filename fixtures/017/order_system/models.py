"""Order and event domain models."""

from dataclasses import dataclass


@dataclass
class Order:
    order_id: str
    sku: str
    quantity: int
    status: str


@dataclass
class Event:
    event_type: str
    order_id: str
    sku: str
    quantity: int
