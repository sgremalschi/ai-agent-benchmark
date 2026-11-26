"""Independent correctness tests for Experiment 014."""

import random

import pytest

from problems.pair_counter import count_pairs


def reference(numbers, target):
    return sum(
        numbers[i] + numbers[j] == target
        for i in range(len(numbers))
        for j in range(i + 1, len(numbers))
    )


@pytest.mark.parametrize(
    ("numbers", "target", "expected"),
    [
        ([], 0, 0),
        ([1], 2, 0),
        ([1, 2], 3, 1),
        ([1, 1], 2, 1),
        ([1, 1, 1, 1], 2, 6),
        ([0] * 100, 0, 4950),
        ([-3, -1, 0, 1, 3], 0, 2),
        ([1, 2, 3, 4, 5], 6, 2),
        ([2, 2, 3, 3], 5, 4),
        ([10**20, -(10**20)], 0, 1),
    ],
)
def test_known_cases(numbers, target, expected):
    original = numbers.copy()
    assert count_pairs(numbers, target) == expected
    assert numbers == original


@pytest.mark.parametrize("seed", range(20))
def test_randomized_against_reference(seed):
    rng = random.Random(seed)
    numbers = [rng.randint(-30, 30) for _ in range(100)]
    target = rng.randint(-40, 40)

    original = numbers.copy()
    assert count_pairs(numbers, target) == reference(numbers, target)
    assert numbers == original


def test_large_duplicate_count():
    assert count_pairs([7] * 1000, 14) == 499500
