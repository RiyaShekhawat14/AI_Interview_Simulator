import copy
import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    created_at: float


_CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").strip().lower() not in {"0", "false", "no"}
_DEFAULT_TTL_SECONDS = int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "60"))
_MAX_ITEMS = max(50, int(os.getenv("CACHE_MAX_ITEMS", "500")))
_REDIS_URL = os.getenv("REDIS_URL", "").strip()
_REDIS_NAMESPACE = os.getenv("REDIS_NAMESPACE", "ai_interview")

_cache: dict[str, CacheEntry] = {}
_lock = threading.Lock()
_hits = 0
_misses = 0
_sets = 0
_evictions = 0
_backend_mode = "memory"
_redis_client = None


def _get_redis_client():
    global _redis_client, _backend_mode
    if not _CACHE_ENABLED or not _REDIS_URL or redis is None:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        client = redis.from_url(_REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        _backend_mode = "redis"
        return _redis_client
    except Exception:
        _backend_mode = "memory"
        _redis_client = None
        return None


def cache_enabled() -> bool:
    return _CACHE_ENABLED


def _scoped_key(key: str) -> str:
    return f"{_REDIS_NAMESPACE}:{key}"


def _prune_expired(now: float | None = None) -> None:
    global _evictions
    now = now or time.time()
    expired_keys = [key for key, entry in _cache.items() if entry.expires_at <= now]
    for key in expired_keys:
        _cache.pop(key, None)
    _evictions += len(expired_keys)


def _evict_if_needed() -> None:
    global _evictions
    if len(_cache) < _MAX_ITEMS:
        return
    oldest_key = min(_cache, key=lambda key: _cache[key].created_at)
    _cache.pop(oldest_key, None)
    _evictions += 1


def make_cache_key(prefix: str, payload: Any) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def get_cached(key: str) -> Any | None:
    global _hits, _misses
    if not _CACHE_ENABLED:
        _misses += 1
        return None

    client = _get_redis_client()
    if client is not None:
        payload = client.get(_scoped_key(key))
        if payload is None:
            _misses += 1
            return None
        _hits += 1
        return json.loads(payload)

    with _lock:
        _prune_expired()
        entry = _cache.get(key)
        if not entry:
            _misses += 1
            return None
        _hits += 1
        return copy.deepcopy(entry.value)


def set_cached(key: str, value: Any, ttl_seconds: int | None = None) -> Any:
    global _sets
    if not _CACHE_ENABLED:
        return value

    ttl = max(1, int(ttl_seconds or _DEFAULT_TTL_SECONDS))
    client = _get_redis_client()
    if client is not None:
        client.setex(_scoped_key(key), ttl, json.dumps(value, default=str))
        _sets += 1
        return value

    now = time.time()
    entry = CacheEntry(
        value=copy.deepcopy(value),
        created_at=now,
        expires_at=now + ttl,
    )
    with _lock:
        _prune_expired(now)
        _evict_if_needed()
        _cache[key] = entry
        _sets += 1
    return value


def get_or_set_cached(key: str, loader: Callable[[], Any], ttl_seconds: int | None = None) -> Any:
    cached = get_cached(key)
    if cached is not None:
        return cached
    value = loader()
    set_cached(key, value, ttl_seconds=ttl_seconds)
    return value


def invalidate_prefix(prefix: str) -> int:
    global _evictions
    removed = 0
    client = _get_redis_client()
    if client is not None:
        keys = client.keys(_scoped_key(f"{prefix}*"))
        if keys:
            removed = client.delete(*keys)
        _evictions += int(removed)
        return int(removed)

    with _lock:
        keys_to_remove = [key for key in _cache if key.startswith(prefix)]
        for key in keys_to_remove:
            _cache.pop(key, None)
            removed += 1
        _evictions += removed
    return removed


def cache_stats() -> dict[str, Any]:
    client = _get_redis_client()
    if client is not None:
        try:
            size = len(client.keys(_scoped_key("*")))
        except Exception:
            size = 0
        return {
            "enabled": _CACHE_ENABLED,
            "backend": _backend_mode,
            "default_ttl_seconds": _DEFAULT_TTL_SECONDS,
            "max_items": _MAX_ITEMS,
            "size": size,
            "hits": _hits,
            "misses": _misses,
            "sets": _sets,
            "evictions": _evictions,
            "hit_rate": round(_hits / max(_hits + _misses, 1), 4),
            "redis_configured": bool(_REDIS_URL),
            "redis_available": True,
        }

    with _lock:
        _prune_expired()
        return {
            "enabled": _CACHE_ENABLED,
            "backend": _backend_mode,
            "default_ttl_seconds": _DEFAULT_TTL_SECONDS,
            "max_items": _MAX_ITEMS,
            "size": len(_cache),
            "hits": _hits,
            "misses": _misses,
            "sets": _sets,
            "evictions": _evictions,
            "hit_rate": round(_hits / max(_hits + _misses, 1), 4),
            "redis_configured": bool(_REDIS_URL),
            "redis_available": False,
        }
