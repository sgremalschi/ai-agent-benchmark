from copy import deepcopy

import pytest

from problems.problem_0056_merge_intervals import merge_intervals


def test_empty():
    assert merge_intervals([]) == []


def test_single_interval():
    assert merge_intervals([[2, 5]]) == [[2, 5]]


def test_unsorted_disjoint_intervals():
    assert merge_intervals([[8, 10], [1, 2], [4, 6]]) == [[1, 2], [4, 6], [8, 10]]


def test_nested_intervals():
    assert merge_intervals([[1, 10], [2, 3], [4, 8], [9, 10]]) == [[1, 10]]


def test_duplicate_intervals():
    assert merge_intervals([[2, 4], [2, 4], [2, 4]]) == [[2, 4]]


def test_negative_endpoints():
    assert merge_intervals([[-3, 2], [-10, -7], [-8, -4], [1, 5]]) == [[-10, -4], [-3, 5]]


def test_transitive_overlap():
    assert merge_intervals([[5, 7], [1, 3], [3, 5]]) == [[1, 7]]


def test_equal_starts():
    assert merge_intervals([[1, 2], [1, 8], [1, 4]]) == [[1, 8]]


def test_zero_length_intervals():
    assert merge_intervals([[3, 3], [1, 1], [1, 3], [5, 5]]) == [[1, 3], [5, 5]]


def test_input_immutability():
    intervals = [[8, 10], [2, 6], [1, 3], [9, 12]]
    original = deepcopy(intervals)
    original_intervals = intervals.copy()

    result = merge_intervals(intervals)

    assert result == [[1, 6], [8, 12]]
    assert intervals == original
    assert all(current is previous for current, previous in zip(intervals, original_intervals))
    assert result is not intervals
    assert all(merged is not interval for merged in result for interval in intervals)
    result[0][0] = -100
    assert intervals == original


@pytest.mark.parametrize("invalid", [[], [1], [1, 2, 3], [5, 2]])
def test_invalid_interval(invalid):
    intervals = [[8, 10], invalid, [1, 3]]
    original = deepcopy(intervals)

    with pytest.raises(ValueError):
        merge_intervals(intervals)

    assert intervals == original
