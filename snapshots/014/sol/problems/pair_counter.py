"""Count index pairs whose values sum to a target."""


def count_pairs(numbers: list[int], target: int) -> int:
    """Count pairs (i, j) with i < j whose values sum to target.

    Uses O(n) expected time and O(n) additional space.
    """
    count = 0
    seen: dict[int, int] = {}

    for number in numbers:
        # Only earlier indices can pair with this number.
        count += seen.get(target - number, 0)
        seen[number] = seen.get(number, 0) + 1

    return count
