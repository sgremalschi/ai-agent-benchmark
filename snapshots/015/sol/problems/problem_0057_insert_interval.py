class Solution:
    def insert(self, intervals: list[list[int]], newInterval: list[int]) -> list[list[int]]:
        intervals.sort(key=lambda x: x[1])

        result = []

        for i, interval in enumerate(intervals):
            if interval[1] < newInterval[0]:
                result.append(interval)
            elif newInterval[1] < interval[0]:
                result.append(newInterval)
                result += intervals[i:]
                return result
            else:
                newInterval[0] = min(newInterval[0], interval[0])
                newInterval[1] = max(newInterval[1], interval[1])

        result.append(newInterval)
        return result
