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
