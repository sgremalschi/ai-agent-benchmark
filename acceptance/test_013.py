"""Independent behavioral regression tests for Experiment 013."""

import json
from pathlib import Path

import pytest

from problems.order_processor import process_order


DATA = json.loads(
    (Path(__file__).with_name("013_cases.json")).read_text()
)


@pytest.mark.parametrize(
    "case",
    DATA["cases"],
    ids=lambda case: str(case["order"])[:70],
)
def test_preserves_legacy_behavior(case):
    order = case["order"]
    catalog = DATA["catalog"]
    tax_rates = DATA["tax_rates"]

    if "error" in case:
        expected = case["error"]

        with pytest.raises(Exception) as caught:
            process_order(order, catalog, tax_rates)

        assert type(caught.value).__name__ == expected["type"]
        assert str(caught.value) == expected["message"]
    else:
        assert process_order(order, catalog, tax_rates) == case["result"]
