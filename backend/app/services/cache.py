"""Tiny async TTL cache used to keep polled endpoints fast.

The UI polls a handful of read-only endpoints. Some of them talk to slow
third-party APIs (Gmail, Ollama). Caching the result for a few seconds keeps
the API loop responsive and removes duplicate work.
"""
import asyncio
import time
from typing import Any, Awaitable, Callable

_cache: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}
_cache_lock = asyncio.Lock()


def _lock_for(key: str) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


def get(key: str) -> Any | None:
    item = _cache.get(key)
    if not item:
        return None
    expires, value = item
    if expires < time.time():
        _cache.pop(key, None)
        return None
    return value


def set(key: str, value: Any, ttl: float) -> Any:
    _cache[key] = (time.time() + ttl, value)
    return value


def invalidate(prefix: str = "") -> None:
    if not prefix:
        _cache.clear()
        return
    for key in list(_cache):
        if key.startswith(prefix):
            _cache.pop(key, None)


async def get_or_set(key: str, ttl: float, factory: Callable[[], Awaitable[Any]]) -> Any:
    hit = get(key)
    if hit is not None:
        return hit
    async with _lock_for(key):
        hit = get(key)
        if hit is not None:
            return hit
        value = await factory()
        return set(key, value, ttl)
