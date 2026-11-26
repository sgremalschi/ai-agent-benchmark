"""Generate reference cases from the original legacy implementation."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures/013/order_processor.py"
OUTPUT = ROOT / "acceptance/013_cases.json"

spec = importlib.util.spec_from_file_location("legacy_order_processor", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

catalog = {
    "A": {"price": "12.345"},
    "B": {"price": "49.99"},
    "C": {"price": "100"},
    "FREE": {"price": "0"},
}
tax_rates = {"GA": "7.5", "NY": "8.875", "ZERO": "0"}

orders = [
    {"customer": "Alice", "items": [{"sku": "A", "quantity": 1}]},
    {"customer": "Bob", "items": [{"sku": "B", "quantity": 2}]},
    {"customer": "Cara", "items": [{"sku": "C", "quantity": 1}]},
    {"customer": "Dan", "items": [{"sku": "A", "quantity": 3, "discount": 10}], "region": "GA"},
    {"customer": "Eve", "items": [{"sku": "B", "quantity": 3}], "region": "NY", "priority": "express"},
    {"customer": "Frank", "items": [{"sku": "FREE", "quantity": 1}], "region": "ZERO"},
    {"customer": "Grace", "items": [{"sku": "A", "quantity": 2}, {"sku": "B", "quantity": 1}], "region": "GA"},
    {"customer": "Hank", "items": [{"sku": "C", "quantity": 1, "discount": 100}]},
    {"customer": "Ivy", "items": [{"sku": "A", "quantity": 1, "discount": -10}]},
    {"customer": "Jay", "items": [{"sku": "B", "quantity": 1, "discount": 12.5}]},
    {"customer": "Kim", "items": [{"sku": "C", "quantity": 1}], "priority": "standard"},
    {"customer": "Lee", "items": [{"sku": "A", "quantity": 8}], "priority": "express"},
    {"customer": "Mia", "items": [{"sku": "A", "quantity": 1}], "region": "UNKNOWN"},
    {"customer": "Nia", "items": [{"sku": "A", "quantity": 1}], "region": "GA", "priority": "express"},
    {"customer": "Omar", "items": [{"sku": "A", "quantity": 1, "discount": 33.333}]},
    {"customer": "Pam", "items": [{"sku": "A", "quantity": 1}, {"sku": "A", "quantity": 1}]},
]

invalid_orders = [
    None,
    [],
    {},
    {"items": []},
    {"customer": "A"},
    {"customer": "A", "items": []},
    {"customer": "A", "items": "invalid"},
    {"customer": "A", "items": [{}]},
    {"customer": "A", "items": [{"sku": "A"}]},
    {"customer": "A", "items": [{"sku": "MISSING", "quantity": 1}]},
    {"customer": "A", "items": [{"sku": "A", "quantity": 0}]},
    {"customer": "A", "items": [{"sku": "A", "quantity": -1}]},
    {"customer": "A", "items": [{"sku": "A", "quantity": 1.5}]},
    {"customer": "A", "items": [{"sku": "A", "quantity": "2"}]},
]

cases = []

for order in orders + invalid_orders:
    case = {"order": order}
    try:
        case["result"] = module.process_order(order, catalog, tax_rates)
    except Exception as exc:
        case["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    cases.append(case)

OUTPUT.write_text(json.dumps({
    "catalog": catalog,
    "tax_rates": tax_rates,
    "cases": cases,
}, indent=2) + "\n")

print(f"Generated {len(cases)} reference cases: {OUTPUT}")
