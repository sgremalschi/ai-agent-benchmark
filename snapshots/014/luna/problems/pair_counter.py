"""Count index pairs whose values sum to a target."""


def count_pairs(numbers: list[int], target: int) -> int:
    """Count pairs (i, j) where i < j and numbers[i] + numbers[j] == target."""
    count = 0
    seen: dict[int, int] = {}

    for number in numbers:
        count += seen.get(target - number, 0)
        seen[number] = seen.get(number, 0) + 1

    return count
