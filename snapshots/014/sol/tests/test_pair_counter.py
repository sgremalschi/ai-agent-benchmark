from itertools import product

from problems.pair_counter import count_pairs


def test_empty_list():
    assert count_pairs([], 0) == 0


def test_single_element_cannot_pair_with_itself():
    assert count_pairs([3], 6) == 0


def test_two_matching_elements():
    assert count_pairs([2, 5], 7) == 1


def test_no_matching_pairs():
    assert count_pairs([1, 2, 3, 4], 20) == 0


def test_multiple_distinct_pairs():
    assert count_pairs([1, 2, 3, 4, 5], 6) == 2


def test_duplicate_complements_count_every_index_pair():
    assert count_pairs([1, 1, 4, 4, 4], 5) == 6


def test_identical_values_count_combinations():
    assert count_pairs([3, 3, 3, 3, 3], 6) == 10


def test_identical_values_with_wrong_target():
    assert count_pairs([3, 3, 3], 3) == 0


def test_all_zeros():
    assert count_pairs([0, 0, 0, 0], 0) == 6


def test_zeros_pair_with_nonzero_values():
    assert count_pairs([0, 5, 0, 5], 5) == 4


def test_negative_values_and_target():
    assert count_pairs([-1, -2, -3, -4, -5], -6) == 2


def test_mixed_signs_with_zero_target():
    assert count_pairs([-2, 2, -2, 2, 0, 0], 0) == 5


def test_negative_and_positive_values_with_positive_target():
    assert count_pairs([-3, 7, -1, 5, 2, 2], 4) == 3


def test_arbitrary_precision_integers():
    large = 10**100
    assert count_pairs([large, -large, large, -large, 0, 0], 0) == 5


def test_arbitrary_precision_target():
    large = 10**100
    assert count_pairs([large, large - 1, 1, 0], large) == 2


def test_input_order_does_not_affect_count():
    assert count_pairs([4, 1, 4, 1, 4], 5) == 6


def test_input_list_is_not_mutated():
    numbers = [4, -1, 0, 4, 1, -4]
    original = numbers.copy()
    assert count_pairs(numbers, 0) == 3
    assert numbers == original


def test_calls_do_not_share_frequency_state():
    assert count_pairs([1, 1], 2) == 1
    assert count_pairs([1], 2) == 0
    assert count_pairs([1, 1], 2) == 1


def test_large_duplicate_count():
    size = 100_000
    assert count_pairs([7] * size, 14) == size * (size - 1) // 2


def test_exhaustive_small_inputs_against_brute_force():
    for size in range(6):
        for values in product((-1, 0, 1), repeat=size):
            numbers = list(values)
            for target in range(-3, 4):
                expected = sum(
                    numbers[i] + numbers[j] == target
                    for i in range(size)
                    for j in range(i + 1, size)
                )
                assert count_pairs(numbers, target) == expected, (numbers, target)
