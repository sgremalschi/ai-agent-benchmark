from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest

from problems.rate_limiter import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.mark.parametrize("limit, window", [(0, 1), (-1, 1), (1, 0), (1, -1)])
def test_rejects_nonpositive_configuration(limit, window):
    with pytest.raises(ValueError, match="positive"):
        SlidingWindowRateLimiter(limit, window)


def test_new_key_has_full_capacity(clock):
    limiter = SlidingWindowRateLimiter(3, 10, clock)
    assert limiter.remaining("new") == 3


def test_allows_exactly_limit_requests(clock):
    limiter = SlidingWindowRateLimiter(3, 10, clock)
    assert [limiter.allow("a") for _ in range(5)] == [True, True, True, False, False]
    assert limiter.remaining("a") == 0


def test_keys_have_independent_capacity(clock):
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.remaining("b") == 1
    assert limiter.allow("b")


def test_request_stays_active_just_before_expiry(clock):
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    assert limiter.allow("a")
    clock.now = 9.999
    assert limiter.remaining("a") == 0
    assert not limiter.allow("a")


def test_allow_expires_request_at_exact_boundary(clock):
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    assert limiter.allow("a")
    clock.now = 10
    assert limiter.allow("a")
    assert not limiter.allow("a")


def test_remaining_expires_requests_at_exact_boundary(clock):
    limiter = SlidingWindowRateLimiter(2, 10, clock)
    assert limiter.allow("a")
    clock.now = 10
    assert limiter.remaining("a") == 2


def test_expiry_after_long_idle_period(clock):
    limiter = SlidingWindowRateLimiter(2, 10, clock)
    assert limiter.allow("a")
    assert limiter.allow("a")
    clock.now = 1000
    assert limiter.remaining("a") == 2
    assert limiter.allow("a")


def test_window_rolls_over_staggered_requests(clock):
    limiter = SlidingWindowRateLimiter(2, 10, clock)
    assert limiter.allow("a")
    clock.now = 4
    assert limiter.allow("a")
    clock.now = 10
    assert limiter.remaining("a") == 1
    assert limiter.allow("a")
    clock.now = 13
    assert not limiter.allow("a")
    clock.now = 14
    assert limiter.remaining("a") == 1
    assert limiter.allow("a")


def test_rejections_do_not_consume_capacity_or_extend_expiry(clock):
    limiter = SlidingWindowRateLimiter(2, 10, clock)
    assert limiter.allow("a")
    clock.now = 2
    assert limiter.allow("a")
    for now in (3, 5, 9):
        clock.now = now
        assert not limiter.allow("a")
    clock.now = 12
    assert limiter.remaining("a") == 2
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")


def test_remaining_does_not_consume_capacity(clock):
    limiter = SlidingWindowRateLimiter(2, 10, clock)
    assert limiter.allow("a")
    assert [limiter.remaining("a") for _ in range(5)] == [1] * 5
    assert limiter.allow("a")


def test_reset_restores_capacity(clock):
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    assert limiter.allow("a")
    assert limiter.reset("a") is None
    assert limiter.remaining("a") == 1
    assert limiter.allow("a")


def test_reset_preserves_other_keys(clock):
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    assert limiter.allow("a")
    assert limiter.allow("b")
    limiter.reset("a")
    assert limiter.remaining("b") == 0
    assert not limiter.allow("b")


def test_reset_missing_key_is_idempotent(clock):
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    limiter.reset("missing")
    limiter.reset("missing")
    assert limiter.remaining("missing") == 1
    assert limiter.allow("missing")


def test_fractional_window_and_nonzero_clock_origin():
    clock = FakeClock(100.0)
    limiter = SlidingWindowRateLimiter(1, 0.25, clock)
    assert limiter.allow("a")
    clock.now = 100.125
    assert not limiter.allow("a")
    clock.now = 100.25
    assert limiter.allow("a")


def test_falsey_injected_clock_is_used():
    class FalseyClock(FakeClock):
        def __bool__(self):
            return False

    clock = FalseyClock()
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    assert limiter.allow("a")
    clock.now = 10
    assert limiter.remaining("a") == 1


def test_default_clock_is_usable():
    limiter = SlidingWindowRateLimiter(1, 3600)
    assert limiter.allow("a")
    assert limiter.remaining("a") == 0


def test_concurrent_requests_cannot_exceed_capacity(clock):
    limiter = SlidingWindowRateLimiter(7, 10, clock)
    barrier = Barrier(32)

    def request(_):
        barrier.wait(timeout=5)
        return limiter.allow("a")

    with ThreadPoolExecutor(max_workers=32) as executor:
        results = list(executor.map(request, range(32)))

    assert sum(results) == 7
    assert limiter.remaining("a") == 0


class ObservedLock:
    """Expose lock acquisition attempts for deterministic synchronization tests."""

    def __init__(self):
        self.lock = Lock()
        self.attempted = Event()

    def __enter__(self):
        self.attempted.set()
        self.lock.acquire()

    def __exit__(self, *args):
        self.lock.release()


@pytest.mark.parametrize("operation", ["allow", "remaining", "reset"])
def test_operations_wait_for_shared_lock(operation, clock):
    limiter = SlidingWindowRateLimiter(1, 10, clock)
    assert limiter.allow("a")
    observed = ObservedLock()
    limiter._lock = observed

    with ThreadPoolExecutor(max_workers=1) as executor:
        with observed.lock:
            future = executor.submit(getattr(limiter, operation), "a")
            assert observed.attempted.wait(timeout=5)
            assert not future.done()
        result = future.result(timeout=5)

    assert result == {"allow": False, "remaining": 0, "reset": None}[operation]


@pytest.mark.parametrize("operation", ["allow", "remaining"])
def test_clock_is_sampled_after_lock_acquisition(operation):
    observed = ObservedLock()

    def clock():
        assert observed.lock.locked()
        return 0

    limiter = SlidingWindowRateLimiter(1, 10, clock)
    limiter._lock = observed
    getattr(limiter, operation)("a")
