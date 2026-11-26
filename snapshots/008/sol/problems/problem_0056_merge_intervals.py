def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Merge overlapping closed intervals without modifying the input.

    Raise ValueError for intervals with other than two endpoints or start > end.
    Time complexity is O(n log n); auxiliary space is O(n).
    """
    for interval in intervals:
        if len(interval) != 2 or interval[0] > interval[1]:
            raise ValueError("Each interval must contain two endpoints with start <= end")

    merged: list[list[int]] = []
    for start, end in sorted(intervals, key=lambda interval: interval[0]):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    return merged
