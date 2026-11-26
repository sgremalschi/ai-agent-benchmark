from concurrent.futures import ThreadPoolExecutor

import pytest

from problems.ttl_cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_get_and_length():
    cache = TTLCache(10)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert len(cache) == 1


def test_expiration_boundary_and_length():
    clock = FakeClock()
    cache = TTLCache(2, clock=clock)
    cache.set("a", 1)
    clock.now = 2
    assert cache.get("a") is None
    assert len(cache) == 0


def test_custom_ttl():
    clock = FakeClock()
    cache = TTLCache(5, clock=clock)
    cache.set("a", 1, 1)
    clock.now = 1
    assert cache.get("a") is None


def test_overwrite_value_and_expiration():
    clock = FakeClock()
    cache = TTLCache(10, clock=clock)
    cache.set("a", 1, 1)
    clock.now = 0.5
    cache.set("a", 2, 3)
    clock.now = 1
    assert cache.get("a") == 2


def test_update_recency():
    cache = TTLCache(10, max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 3)
    cache.set("c", 4)
    assert cache.get("a") == 3
    assert cache.get("b") is None


def test_get_recency():
    cache = TTLCache(10, max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)
    assert cache.get("a") == 1


def test_expired_cleaned_before_eviction():
    clock = FakeClock()
    cache = TTLCache(2, max_size=1, clock=clock)
    cache.set("a", 1)
    clock.now = 2
    cache.set("b", 2)
    assert cache.get("b") == 2


@pytest.mark.parametrize("ttl", [0, -1])
def test_invalid_default_ttl(ttl):
    with pytest.raises(ValueError):
        TTLCache(ttl)


@pytest.mark.parametrize("size", [0, -1])
def test_invalid_capacity(size):
    with pytest.raises(ValueError):
        TTLCache(1, max_size=size)


@pytest.mark.parametrize("ttl", [0, -1])
def test_invalid_entry_ttl(ttl):
    with pytest.raises(ValueError):
        TTLCache(1).set("a", 1, ttl)


def test_none_is_stored():
    cache = TTLCache(1)
    cache.set("a", None)
    assert cache.get("a") is None
    assert len(cache) == 1


def test_delete_existing_and_missing():
    cache = TTLCache(1)
    cache.set("a", 1)
    assert cache.delete("a") is True
    assert cache.delete("a") is False


def test_delete_expired():
    clock = FakeClock()
    cache = TTLCache(1, clock=clock)
    cache.set("a", 1)
    clock.now = 1
    assert cache.delete("a") is False


def test_clear():
    cache = TTLCache(1)
    cache.set("a", 1)
    cache.clear()
    assert len(cache) == 0


def test_thread_safe_concurrent_operations():
    cache = TTLCache(100, max_size=1000)

    def add(value):
        cache.set(str(value), value)
        return cache.get(str(value))

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(add, range(100))) == list(range(100))
    assert len(cache) == 100


def test_stats_initial_counters():
    assert TTLCache(10).stats() == dict(hits=0, misses=0, evictions=0, expirations=0)


def test_stats_live_hits_and_missing_misses():
    cache = TTLCache(10)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.get("a") == 1
    assert cache.get("missing") is None
    assert cache.stats() == dict(hits=2, misses=1, evictions=0, expirations=0)


def test_stats_none_counts_as_hit():
    cache = TTLCache(10)
    cache.set("a", None)
    assert cache.get("a") is None
    assert cache.stats() == dict(hits=1, misses=0, evictions=0, expirations=0)


def test_stats_get_expiration_counted_once():
    clock = FakeClock()
    cache = TTLCache(1, clock=clock)
    cache.set("a", 1)
    clock.now = 1
    assert cache.get("a") is None
    assert cache.get("a") is None
    assert cache.delete("a") is False
    assert len(cache) == 0
    assert cache.stats() == dict(hits=0, misses=2, evictions=0, expirations=1)


def test_stats_delete_expired_entry():
    clock = FakeClock()
    cache = TTLCache(1, clock=clock)
    cache.set("a", 1)
    clock.now = 1
    assert cache.delete("a") is False
    assert cache.delete("a") is False
    assert cache.stats() == dict(hits=0, misses=0, evictions=0, expirations=1)


def test_stats_delete_live_and_missing_entries():
    cache = TTLCache(10)
    cache.set("a", 1)
    assert cache.delete("a") is True
    assert cache.delete("missing") is False
    assert cache.stats() == dict(hits=0, misses=0, evictions=0, expirations=0)


def test_stats_length_removes_multiple_expired_entries_once():
    clock = FakeClock()
    cache = TTLCache(2, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3, ttl=3)
    clock.now = 2
    assert len(cache) == 1
    assert len(cache) == 1
    assert cache.stats() == dict(hits=0, misses=0, evictions=0, expirations=2)


def test_stats_expired_entry_removed_before_live_lru_eviction():
    clock = FakeClock()
    cache = TTLCache(10, max_size=2, clock=clock)
    cache.set("live", 1)
    cache.set("expired", 2, ttl=1)
    clock.now = 1
    cache.set("new", 3)
    assert cache.stats() == dict(hits=0, misses=0, evictions=0, expirations=1)
    assert cache.get("live") == 1


def test_stats_live_lru_eviction():
    cache = TTLCache(10, max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.stats() == dict(hits=1, misses=1, evictions=1, expirations=0)


def test_stats_overwrite_at_capacity_resets_ttl_and_recency():
    clock = FakeClock()
    cache = TTLCache(2, max_size=2, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2, ttl=10)
    clock.now = 1
    cache.set("a", 3)
    assert cache.stats()["evictions"] == 0
    clock.now = 2
    cache.set("c", 4)
    assert cache.get("a") == 3
    assert cache.get("b") is None
    assert cache.stats() == dict(hits=1, misses=1, evictions=1, expirations=0)


def test_stats_replacing_expired_key_counts_expiration():
    clock = FakeClock()
    cache = TTLCache(1, max_size=1, clock=clock)
    cache.set("a", 1)
    clock.now = 1
    cache.set("a", 2)
    assert cache.get("a") == 2
    assert cache.stats() == dict(hits=1, misses=0, evictions=0, expirations=1)


def test_stats_clear_preserves_all_counters_and_skips_expiration():
    clock = FakeClock()
    cache = TTLCache(1, max_size=1, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("b") == 2
    assert cache.get("missing") is None
    clock.now = 1
    assert len(cache) == 0
    cache.set("c", 3)
    clock.now = 2
    cache.clear()
    assert len(cache) == 0
    assert cache.stats() == dict(hits=1, misses=1, evictions=1, expirations=1)


def test_stats_snapshots_are_independent():
    cache = TTLCache(10)
    first = cache.stats()
    cache.get("missing")
    second = cache.stats()
    first["hits"] = 99
    second["misses"] = 99
    assert first["misses"] == 0
    assert cache.stats() == dict(hits=0, misses=1, evictions=0, expirations=0)


def test_stats_does_not_read_clock_or_clean_expired_entries():
    clock = FakeClock()
    cache = TTLCache(1, clock=clock)
    cache.set("a", 1)
    clock.now = 1

    def forbidden_clock():
        pytest.fail("stats must not read the clock")

    cache._clock = forbidden_clock
    assert cache.stats() == dict(hits=0, misses=0, evictions=0, expirations=0)
    cache._clock = clock
    assert cache.delete("a") is False
    assert cache.stats()["expirations"] == 1


def test_stats_concurrent_access_exact_totals():
    cache = TTLCache(10, max_size=1000, clock=lambda: 0)

    def exercise(value):
        key = str(value)
        cache.set(key, None)
        assert cache.get(key) is None
        assert cache.get("missing") is None
        snapshot = cache.stats()
        assert set(snapshot) == {"hits", "misses", "evictions", "expirations"}
        assert all(isinstance(count, int) and count >= 0 for count in snapshot.values())
        assert cache.delete(key) is True

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(exercise, range(500)))
    assert cache.stats() == dict(hits=500, misses=500, evictions=0, expirations=0)
    assert len(cache) == 0


def test_stats_concurrent_expiration_counted_once():
    clock = FakeClock()
    cache = TTLCache(1, clock=clock)
    cache.set("a", 1)
    clock.now = 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(lambda _: cache.get("a"), range(100))) == [None] * 100
    assert cache.stats() == dict(hits=0, misses=100, evictions=0, expirations=1)
