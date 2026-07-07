"""Redis access with a graceful in-process fallback.

Everything that touches Redis goes through here so the rest of the app never
has to care whether Redis is actually up. If Redis is unreachable, we fall back
to per-process dicts — the bot keeps working (memory/limits just aren't shared
across processes or restarts). This preserves the project rule: a reply must
never crash on an infra hiccup.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from src.config import get_settings
from src.core.logging import logger

try:  # redis.asyncio ships with redis>=4.2
    from redis import asyncio as aioredis
except Exception:  # pragma: no cover - redis always present in prod
    aioredis = None  # type: ignore[assignment]

_redis = None
_redis_ready: bool | None = None

# In-process fallbacks.
_mem_lists: dict[str, deque[str]] = defaultdict(deque)
_mem_counters: dict[str, tuple[int, float]] = {}  # key -> (count, expires_at)


async def _client():
    """Return a live Redis client, or None if unavailable (cached)."""
    global _redis, _redis_ready
    if _redis_ready is False:
        return None
    if _redis is not None:
        return _redis
    if aioredis is None:
        _redis_ready = False
        return None
    try:
        client = aioredis.from_url(
            get_settings().redis_url, encoding="utf-8", decode_responses=True
        )
        await client.ping()
        _redis, _redis_ready = client, True
        logger.info("redis connected")
        return client
    except Exception as exc:
        _redis_ready = False
        logger.warning("redis unavailable ({}); using in-process fallback", exc)
        return None


async def push_trim(key: str, value: str, maxlen: int) -> None:
    """LPUSH + LTRIM to keep the newest `maxlen` items."""
    client = await _client()
    if client is not None:
        try:
            await client.lpush(key, value)
            await client.ltrim(key, 0, maxlen - 1)
            return
        except Exception as exc:
            logger.debug("redis push_trim failed ({}); fallback", exc)
    dq = _mem_lists[key]
    dq.appendleft(value)
    while len(dq) > maxlen:
        dq.pop()


async def lrange(key: str, count: int) -> list[str]:
    """Return the newest→oldest items (up to `count`)."""
    client = await _client()
    if client is not None:
        try:
            return await client.lrange(key, 0, count - 1)
        except Exception as exc:
            logger.debug("redis lrange failed ({}); fallback", exc)
    return list(_mem_lists[key])[:count]


async def incr_with_ttl(key: str, ttl_seconds: int) -> int:
    """Increment a counter that expires after `ttl_seconds`; return new value."""
    client = await _client()
    if client is not None:
        try:
            value = await client.incr(key)
            if value == 1:
                await client.expire(key, ttl_seconds)
            return int(value)
        except Exception as exc:
            logger.debug("redis incr failed ({}); fallback", exc)
    now = time.time()
    count, expires = _mem_counters.get(key, (0, 0.0))
    if now >= expires:
        count, expires = 0, now + ttl_seconds
    count += 1
    _mem_counters[key] = (count, expires)
    return count


async def incrby_with_ttl(key: str, amount: int, ttl_seconds: int) -> int:
    """Add `amount` to a counter that expires after `ttl_seconds`; return total."""
    client = await _client()
    if client is not None:
        try:
            value = await client.incrby(key, amount)
            if value == amount:
                await client.expire(key, ttl_seconds)
            return int(value)
        except Exception as exc:
            logger.debug("redis incrby failed ({}); fallback", exc)
    now = time.time()
    count, expires = _mem_counters.get(key, (0, 0.0))
    if now >= expires:
        count, expires = 0, now + ttl_seconds
    count += amount
    _mem_counters[key] = (count, expires)
    return count
