from concurrent.futures import ThreadPoolExecutor

import pytest

from problems.rate_limiter import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


def test_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(0, 10)


def test_rejects_non_positive_window():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(3, 0)


def test_allows_requests_up_to_limit():
    limiter = SlidingWindowRateLimiter(2, 10, FakeClock())

    assert limiter.allow("user")
    assert limiter.allow("user")
    assert not limiter.allow("user")


def test_rejected_request_does_not_consume_capacity():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 10, clock)

    assert limiter.allow("user")
    assert not limiter.allow("user")
    clock.now = 10
    assert limiter.allow("user")


def test_keys_have_independent_limits():
    limiter = SlidingWindowRateLimiter(1, 10, FakeClock())

    assert limiter.allow("first")
    assert limiter.allow("second")
    assert not limiter.allow("first")
    assert not limiter.allow("second")


def test_request_expires_at_exact_window_boundary():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 5, clock)

    assert limiter.allow("user")
    clock.now = 5
    assert limiter.allow("user")


def test_request_does_not_expire_before_window_boundary():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 5, clock)

    assert limiter.allow("user")
    clock.now = 4.999
    assert not limiter.allow("user")


def test_rolling_window_expires_only_oldest_request():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(2, 10, clock)

    assert limiter.allow("user")
    clock.now = 5
    assert limiter.allow("user")
    clock.now = 10
    assert limiter.allow("user")
    assert not limiter.allow("user")


def test_remaining_for_unknown_key_is_full_capacity():
    limiter = SlidingWindowRateLimiter(4, 10, FakeClock())

    assert limiter.remaining("missing") == 4


def test_remaining_decreases_after_allowed_request():
    limiter = SlidingWindowRateLimiter(3, 10, FakeClock())

    assert limiter.allow("user")
    assert limiter.remaining("user") == 2


def test_remaining_ignores_expired_requests():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(2, 10, clock)
    assert limiter.allow("user")

    clock.now = 10
    assert limiter.remaining("user") == 2


def test_remaining_does_not_count_rejected_request():
    limiter = SlidingWindowRateLimiter(1, 10, FakeClock())
    assert limiter.allow("user")

    assert not limiter.allow("user")
    assert limiter.remaining("user") == 0


def test_reset_clears_only_requested_key():
    limiter = SlidingWindowRateLimiter(1, 10, FakeClock())
    assert limiter.allow("first")
    assert limiter.allow("second")

    limiter.reset("first")

    assert limiter.remaining("first") == 1
    assert limiter.remaining("second") == 0
    assert limiter.allow("first")


def test_reset_unknown_key_is_safe():
    limiter = SlidingWindowRateLimiter(1, 10, FakeClock())

    limiter.reset("missing")

    assert limiter.remaining("missing") == 1


def test_injected_clock_controls_expiration():
    clock = FakeClock(100)
    limiter = SlidingWindowRateLimiter(1, 2, clock)
    assert limiter.allow("user")

    clock.now = 101.999
    assert not limiter.allow("user")
    clock.now = 102
    assert limiter.allow("user")


def test_concurrent_requests_never_exceed_limit():
    limiter = SlidingWindowRateLimiter(7, 10, FakeClock())

    with ThreadPoolExecutor(max_workers=24) as pool:
        results = list(pool.map(limiter.allow, ["same-key"] * 80))

    assert sum(results) == 7
    assert limiter.remaining("same-key") == 0
