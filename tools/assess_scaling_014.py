#!/usr/bin/env python3
"""Separate scaling evidence; no absolute speed threshold or model calls."""

import importlib.util
import json
import platform
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def measure(function, size):
    values = list(range(size))
    samples = []
    for _ in range(5):
        start = time.perf_counter()
        assert function(values, size - 1) == size // 2
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def main():
    results = {}
    sources = {
        "quadratic_control": ROOT / "fixtures/014/pair_counter.py",
        "luna": ROOT / "snapshots/014/luna/problems/pair_counter.py",
        "sol": ROOT / "snapshots/014/sol/problems/pair_counter.py",
    }
    for name, path in sources.items():
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sizes = [1000, 2000, 4000, 8000]
        seconds = [measure(module.count_pairs, size) for size in sizes]
        ratios = [b / a for a, b in zip(seconds, seconds[1:])]
        results[name] = {"sizes": sizes, "median_seconds": seconds, "doubling_ratios": ratios}
    print(json.dumps({"python": platform.python_version(), "platform": platform.system(),
                      "repetitions": 5, "results": results}, indent=2))


if __name__ == "__main__":
    main()
