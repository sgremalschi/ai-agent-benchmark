def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Merge overlapping intervals without changing the input."""
    ordered: list[tuple[int, int]] = []

    for interval in intervals:
        try:
            if len(interval) != 2:
                raise ValueError("each interval must contain exactly two endpoints")
            start, end = interval
        except TypeError as error:
            raise ValueError("each interval must contain exactly two endpoints") from error

        if start > end:
            raise ValueError("an interval start cannot be greater than its end")
        ordered.append((start, end))

    if not ordered:
        return []

    ordered.sort()
    merged: list[list[int]] = [[ordered[0][0], ordered[0][1]]]

    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    return merged
