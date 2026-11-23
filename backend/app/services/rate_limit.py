"""In-memory rate limiting for the public API.

JARVIS runs as a single process, so a dictionary of timestamps per client is
enough. Each limiter is keyed by client IP and a bucket name, letting costly
LLM calls have a much tighter budget than ordinary reads. Behind a reverse
proxy the real client address is read from X-Forwarded-For / X-Real-IP.
"""
import time
from collections import deque
from threading import Lock

_lock = Lock()
_hits: dict[str, deque[float]] = {}
_MAX_KEYS = 10_000


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    real = request.headers.get("x-real-ip") or ""
    if real:
        return real.strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", None) or "unknown"


def allow(bucket: str, ip: str, limit: int, window: int = 60) -> tuple[bool, int]:
    """Record a hit and report whether the caller is under the limit.

    Returns (allowed, retry_after_seconds). A limit of 0 disables the bucket.
    """
    if limit <= 0:
        return True, 0

    now = time.monotonic()
    key = f"{bucket}:{ip}"
    with _lock:
        if len(_hits) > _MAX_KEYS:
            for stale in list(_hits)[: _MAX_KEYS // 2]:
                _hits.pop(stale, None)
        hits = _hits.get(key)
        if hits is None:
            hits = deque()
            _hits[key] = hits
        cutoff = now - window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = int(window - (now - hits[0])) + 1
            return False, max(retry_after, 1)
        hits.append(now)
    return True, 0
