import pytest

from problems.problem_0056_merge_intervals import merge_intervals


def test_empty_input():
    assert merge_intervals([]) == []


def test_single_interval():
    assert merge_intervals([[1, 4]]) == [[1, 4]]


def test_intervals_sharing_endpoint_are_merged():
    assert merge_intervals([[1, 2], [2, 3]]) == [[1, 3]]


def test_nested_interval_is_absorbed():
    assert merge_intervals([[1, 10], [3, 4], [5, 7]]) == [[1, 10]]


def test_duplicate_intervals_are_merged():
    assert merge_intervals([[2, 5], [2, 5], [2, 5]]) == [[2, 5]]


def test_negative_endpoints():
    assert merge_intervals([[-8, -3], [-5, 1], [3, 4]]) == [[-8, 1], [3, 4]]


def test_disjoint_intervals_remain_separate():
    assert merge_intervals([[1, 2], [4, 5], [7, 8]]) == [[1, 2], [4, 5], [7, 8]]


def test_zero_length_intervals_merge_at_shared_endpoint():
    assert merge_intervals([[2, 2], [2, 2], [1, 2]]) == [[1, 2]]


def test_input_and_nested_intervals_are_not_mutated():
    intervals = [[5, 7], [1, 3], [2, 6]]
    original = [interval.copy() for interval in intervals]

    result = merge_intervals(intervals)

    assert result == [[1, 7]]
    assert intervals == original
    assert all(
        result_interval is not input_interval
        for result_interval in result
        for input_interval in intervals
    )


@pytest.mark.parametrize("interval", [[1], [1, 2, 3], []])
def test_rejects_intervals_with_wrong_number_of_endpoints(interval):
    with pytest.raises(ValueError):
        merge_intervals([interval])


def test_rejects_interval_with_start_after_end():
    with pytest.raises(ValueError):
        merge_intervals([[3, 2]])
