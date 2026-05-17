import os
import threading
import time
from collections import defaultdict
from typing import Any


_RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in {"0", "false", "no"}
_RATE_LIMIT_WINDOW_SECONDS = max(10, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")))
_RATE_LIMIT_MAX_REQUESTS = max(10, int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120")))
_lock = threading.Lock()
_request_log: dict[str, list[float]] = defaultdict(list)
_blocked_requests = 0


def rate_limit_enabled() -> bool:
    return _RATE_LIMIT_ENABLED


def _prune(now: float) -> None:
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
    stale_keys = []
    for key, timestamps in _request_log.items():
        _request_log[key] = [stamp for stamp in timestamps if stamp >= cutoff]
        if not _request_log[key]:
            stale_keys.append(key)
    for key in stale_keys:
        _request_log.pop(key, None)


def check_rate_limit(identity: str) -> tuple[bool, dict[str, Any]]:
    global _blocked_requests
    if not _RATE_LIMIT_ENABLED:
      return True, {
          "enabled": False,
          "window_seconds": _RATE_LIMIT_WINDOW_SECONDS,
          "max_requests": _RATE_LIMIT_MAX_REQUESTS,
      }

    now = time.time()
    with _lock:
        _prune(now)
        history = _request_log[identity]
        allowed = len(history) < _RATE_LIMIT_MAX_REQUESTS
        if allowed:
            history.append(now)
        else:
            _blocked_requests += 1
        remaining = max(_RATE_LIMIT_MAX_REQUESTS - len(history), 0)
        reset_in_seconds = 0
        if history:
            reset_in_seconds = max(int(history[0] + _RATE_LIMIT_WINDOW_SECONDS - now), 0)
        return allowed, {
            "enabled": True,
            "window_seconds": _RATE_LIMIT_WINDOW_SECONDS,
            "max_requests": _RATE_LIMIT_MAX_REQUESTS,
            "remaining": remaining,
            "reset_in_seconds": reset_in_seconds,
        }


def rate_limit_stats() -> dict[str, Any]:
    now = time.time()
    with _lock:
        _prune(now)
        active_identities = len(_request_log)
        return {
            "enabled": _RATE_LIMIT_ENABLED,
            "window_seconds": _RATE_LIMIT_WINDOW_SECONDS,
            "max_requests": _RATE_LIMIT_MAX_REQUESTS,
            "active_identities": active_identities,
            "blocked_requests": _blocked_requests,
        }
