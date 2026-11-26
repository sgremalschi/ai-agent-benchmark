"""Count index pairs whose values sum to a target."""


def count_pairs(numbers: list[int], target: int) -> int:
    """Count pairs (i, j) where i < j and numbers[i] + numbers[j] == target."""
    count = 0

    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if numbers[i] + numbers[j] == target:
                count += 1

    return count
