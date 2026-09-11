"""A tiny thread-safe TTL cache + a decorator for caching tool results."""

from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

from .config import get_settings

T = TypeVar("T")


class TTLCache:
    def __init__(self, max_entries: int, ttl: int) -> None:
        self.max_entries = max_entries
        self.ttl = ttl
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if time.time() > expires:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            if len(self._data) >= self.max_entries:
                # drop the soonest-to-expire entry
                oldest = min(self._data, key=lambda k: self._data[k][0])
                self._data.pop(oldest, None)
            self._data[key] = (time.time() + (ttl or self.ttl), value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"entries": len(self._data), "max_entries": self.max_entries}


_cache: TTLCache | None = None


def cache() -> TTLCache:
    global _cache
    if _cache is None:
        s = get_settings()
        _cache = TTLCache(s.cache_max_entries, s.cache_ttl_seconds)
    return _cache


def _key(name: str, args: tuple, kwargs: dict) -> str:
    blob = json.dumps([name, args, sorted(kwargs.items())], default=str, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()


def cached(ttl: int | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache a *sync* function's return value by its arguments."""

    def deco(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            k = _key(fn.__qualname__, args, kwargs)
            hit = cache().get(k)
            if hit is not None:
                return hit
            value = fn(*args, **kwargs)
            cache().set(k, value, ttl)
            return value

        return wrapper

    return deco
