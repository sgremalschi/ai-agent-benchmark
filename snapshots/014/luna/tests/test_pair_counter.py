from problems.pair_counter import count_pairs


def test_empty_input():
    assert count_pairs([], 0) == 0


def test_single_number():
    assert count_pairs([4], 8) == 0


def test_simple_pair():
    assert count_pairs([1, 4], 5) == 1


def test_no_matching_pair():
    assert count_pairs([1, 2, 3], 20) == 0


def test_duplicate_values_count_distinct_indices():
    assert count_pairs([3, 3, 3, 3], 6) == 6


def test_duplicate_complements():
    assert count_pairs([1, 1, 4, 4], 5) == 4


def test_negative_values():
    assert count_pairs([-8, 3, -2, 10], 1) == 1


def test_zero_values():
    assert count_pairs([0, 0, 0], 0) == 3


def test_negative_target():
    assert count_pairs([-5, -2, -3, 1], -8) == 1


def test_zero_target_with_opposites():
    assert count_pairs([-7, 7, 0, 0], 0) == 2


def test_large_integers():
    huge = 10**100
    assert count_pairs([huge, -huge, huge + 1, -huge - 1], 0) == 2


def test_input_is_not_mutated():
    numbers = [2, -1, 3, 0, 2]
    original = numbers.copy()
    count_pairs(numbers, 2)
    assert numbers == original


def test_pair_count_can_be_large():
    assert count_pairs([1] * 100, 2) == 4950


def test_matches_expected_count_for_mixed_values():
    assert count_pairs([1, 5, 7, -1, 5], 6) == 3
