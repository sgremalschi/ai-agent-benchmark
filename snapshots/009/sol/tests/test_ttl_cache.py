from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import pytest

from problems.ttl_cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


def test_empty_cache(clock):
    cache = TTLCache(10, clock=clock)
    assert cache.get("missing") is None
    assert cache.delete("missing") is False
    assert len(cache) == 0


def test_value_round_trip(clock):
    cache = TTLCache(10, clock=clock)
    value = object()
    cache.set("key", value)
    assert cache.get("key") is value
    assert len(cache) == 1


@pytest.mark.parametrize("now,live", [(9.999, True), (10, False), (10.001, False)])
def test_expiration_boundary(clock, now, live):
    cache = TTLCache(10, clock=clock)
    cache.set("key", "value")
    clock.now = now
    assert cache.get("key") == ("value" if live else None)
    assert len(cache) == int(live)


def test_length_excludes_expired_without_get(clock):
    cache = TTLCache(10, clock=clock)
    cache.set("short", 1, ttl=2)
    cache.set("long", 2)
    clock.now = 2
    assert len(cache) == 1
    assert cache.get("long") == 2


def test_ttl_starts_at_set_time(clock):
    cache = TTLCache(3, clock=clock)
    clock.now = 100
    cache.set("key", 1)
    clock.now = 102
    assert cache.get("key") == 1
    clock.now = 103
    assert cache.get("key") is None


def test_overwrite_resets_expiration(clock):
    cache = TTLCache(10, clock=clock)
    cache.set("key", "old")
    clock.now = 9
    cache.set("key", "new")
    clock.now = 10
    assert cache.get("key") == "new"
    assert len(cache) == 1
    clock.now = 19
    assert cache.get("key") is None


def test_overwrite_uses_new_ttl(clock):
    cache = TTLCache(10, clock=clock)
    cache.set("key", 1)
    cache.set("key", 2, ttl=1)
    clock.now = 1
    assert cache.get("key") is None


def test_get_does_not_extend_ttl(clock):
    cache = TTLCache(10, clock=clock)
    cache.set("key", 1)
    clock.now = 9
    assert cache.get("key") == 1
    clock.now = 10
    assert cache.get("key") is None


def test_lru_eviction(clock):
    cache = TTLCache(10, max_size=2, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 2


@pytest.mark.parametrize("touch", ["get", "set"])
def test_access_updates_recency(clock, touch):
    cache = TTLCache(10, max_size=2, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    if touch == "get":
        assert cache.get("a") == 1
    else:
        cache.set("a", 1)
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_expired_mru_removed_before_live_lru(clock):
    cache = TTLCache(10, max_size=2, clock=clock)
    cache.set("live", 1)
    cache.set("expired", 2, ttl=1)
    clock.now = 1
    cache.set("new", 3)
    assert cache.get("live") == 1
    assert cache.get("expired") is None
    assert cache.get("new") == 3


def test_capacity_one_and_expired_overwrite(clock):
    cache = TTLCache(1, max_size=1, clock=clock)
    cache.set("a", 1)
    clock.now = 1
    cache.set("a", 2)
    assert cache.get("a") == 2
    cache.set("b", 3)
    assert cache.get("a") is None
    assert len(cache) == 1


@pytest.mark.parametrize("ttl", [0, -1, -0.1])
def test_invalid_default_ttl(ttl):
    with pytest.raises(ValueError):
        TTLCache(ttl)


@pytest.mark.parametrize("size", [0, -1])
def test_invalid_capacity(size):
    with pytest.raises(ValueError):
        TTLCache(1, max_size=size)


@pytest.mark.parametrize("ttl", [0, -1, -0.1])
def test_invalid_entry_ttl_preserves_value(clock, ttl):
    cache = TTLCache(10, clock=clock)
    cache.set("key", 1)
    with pytest.raises(ValueError):
        cache.set("key", 2, ttl=ttl)
    assert cache.get("key") == 1


def test_none_value_is_live_and_updates_recency(clock):
    cache = TTLCache(10, max_size=2, clock=clock)
    cache.set("none", None)
    cache.set("other", 1)
    assert cache.get("none") is None
    cache.set("new", 2)
    assert cache.get("other") is None
    assert len(cache) == 2
    assert cache.delete("none") is True


@pytest.mark.parametrize("now,expected", [(9, True), (10, False), (11, False)])
def test_delete_live_and_expired(clock, now, expected):
    cache = TTLCache(10, clock=clock)
    cache.set("key", 1)
    clock.now = now
    assert cache.delete("key") is expected
    assert cache.delete("key") is False
    assert len(cache) == 0


def test_clear_and_reuse(clock):
    cache = TTLCache(10, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2, ttl=1)
    clock.now = 1
    cache.clear()
    cache.clear()
    assert len(cache) == 0
    assert cache.get("a") is None
    cache.set("c", 3)
    assert cache.get("c") == 3


def test_default_clock_uses_monotonic():
    with patch("problems.ttl_cache.monotonic", return_value=100) as clock:
        cache = TTLCache(1)
        cache.set("key", 1)
        clock.return_value = 101
        assert cache.get("key") is None


def test_concurrent_unique_keys(clock):
    cache = TTLCache(10, max_size=800, clock=clock)
    barrier = Barrier(8)

    def worker(worker_id):
        barrier.wait()
        for index in range(100):
            key = f"{worker_id}:{index}"
            cache.set(key, index)
            assert cache.get(key) == index
            if index % 2 == 0:
                assert cache.delete(key) is True

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(8)))
    assert len(cache) == 400


def test_concurrent_delete_has_one_winner(clock):
    cache = TTLCache(10, clock=clock)
    cache.set("key", None)
    barrier = Barrier(8)

    def worker(_):
        barrier.wait()
        return cache.delete("key")

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(worker, range(8)))
    assert sum(results) == 1
    assert len(cache) == 0


def test_concurrent_mixed_operations_respect_capacity(clock):
    cache = TTLCache(10, max_size=3, clock=clock)
    barrier = Barrier(8)

    def worker(worker_id):
        barrier.wait()
        for index in range(200):
            key = str((index + worker_id) % 7)
            cache.set(key, index)
            cache.get(key)
            assert len(cache) <= 3
            cache.delete(str(index % 7))
            if index % 17 == 0:
                cache.clear()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(8)))
    cache.clear()
    cache.set("final", 1)
    assert cache.get("final") == 1
    assert len(cache) == 1
