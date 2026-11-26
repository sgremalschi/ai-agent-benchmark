"""Independent acceptance tests for Experiment 012."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from problems.rate_limiter import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self, start=0.0):
        self.value = start
        self.lock = threading.Lock()

    def __call__(self):
        with self.lock:
            return self.value

    def advance(self, seconds):
        with self.lock:
            self.value += seconds


def make_limiter(limit=3, window=10.0):
    clock = FakeClock()
    return SlidingWindowRateLimiter(limit, window, clock), clock


def test_invalid_limit_zero():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(0, 10)


def test_invalid_limit_negative():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(-1, 10)


def test_invalid_window_zero():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(3, 0)


def test_invalid_window_negative():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(3, -1)


def test_exact_capacity():
    limiter, _ = make_limiter()
    assert [limiter.allow("a") for _ in range(4)] == [
        True, True, True, False
    ]


def test_independent_keys():
    limiter, _ = make_limiter(limit=1)
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")
    assert not limiter.allow("b")


def test_window_boundary():
    limiter, clock = make_limiter(limit=1)
    assert limiter.allow("a")
    clock.advance(10)
    assert limiter.allow("a")


def test_just_before_window_boundary():
    limiter, clock = make_limiter(limit=1)
    assert limiter.allow("a")
    clock.advance(9.999)
    assert not limiter.allow("a")


def test_rejected_requests_do_not_consume_capacity():
    limiter, clock = make_limiter(limit=1)
    assert limiter.allow("a")
    assert not limiter.allow("a")
    clock.advance(10)
    assert limiter.allow("a")
    assert limiter.remaining("a") == 0


def test_remaining_initial_capacity():
    limiter, _ = make_limiter()
    assert limiter.remaining("unknown") == 3


def test_remaining_after_requests():
    limiter, _ = make_limiter()
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert limiter.remaining("a") == 1


def test_remaining_after_expiration():
    limiter, clock = make_limiter(limit=2)
    assert limiter.allow("a")
    assert limiter.remaining("a") == 1
    clock.advance(10)
    assert limiter.remaining("a") == 2


def test_reset_restores_capacity():
    limiter, _ = make_limiter(limit=1)
    assert limiter.allow("a")
    assert not limiter.allow("a")
    limiter.reset("a")
    assert limiter.allow("a")


def test_reset_does_not_affect_other_keys():
    limiter, _ = make_limiter(limit=1)
    assert limiter.allow("a")
    assert limiter.allow("b")
    limiter.reset("a")
    assert limiter.allow("a")
    assert not limiter.allow("b")


def test_rolling_window_partial_expiration():
    limiter, clock = make_limiter(limit=2)
    assert limiter.allow("a")
    clock.advance(5)
    assert limiter.allow("a")
    clock.advance(5)
    assert limiter.allow("a")
    assert limiter.remaining("a") == 0
    clock.advance(5)
    assert limiter.remaining("a") == 1


def test_concurrent_requests_respect_capacity():
    limiter, _ = make_limiter(limit=20)

    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(limiter.allow, ["a"] * 200))

    assert sum(results) == 20


def test_concurrent_distinct_keys():
    limiter, _ = make_limiter(limit=10)
    keys = ["a"] * 100 + ["b"] * 100

    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(limiter.allow, keys))

    assert sum(results) == 20


def test_remaining_never_negative():
    limiter, _ = make_limiter(limit=1)
    for _ in range(100):
        limiter.allow("a")
    assert limiter.remaining("a") == 0
