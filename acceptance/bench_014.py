"""Independent performance benchmark for Experiment 014."""

import json
import random
import statistics
import time

from problems.pair_counter import count_pairs


def measure(numbers, target, repetitions=5):
    durations = []

    for _ in range(repetitions):
        start = time.perf_counter()
        result = count_pairs(numbers, target)
        durations.append(time.perf_counter() - start)

    return {
        "result": result,
        "median_ms": round(statistics.median(durations) * 1000, 3),
    }


def main():
    rng = random.Random(14014)

    cases = {
        "random_10k": (
            [rng.randint(-10000, 10000) for _ in range(10000)],
            100,
        ),
        "duplicates_10k": ([7] * 10000, 14),
        "unique_10k": (list(range(10000)), 9999),
    }

    results = {
        name: measure(numbers, target)
        for name, (numbers, target) in cases.items()
    }

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
