import threading
import time
from collections import defaultdict
from typing import Any


_started_at = time.time()
_lock = threading.Lock()
_total_requests = 0
_total_errors = 0
_route_stats: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "count": 0,
        "errors": 0,
        "total_duration_ms": 0.0,
        "avg_duration_ms": 0.0,
        "last_status_code": 200,
        "last_seen_at": None,
    }
)


def record_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    global _total_requests, _total_errors
    route_key = f"{method.upper()} {path}"
    with _lock:
        _total_requests += 1
        if status_code >= 400:
            _total_errors += 1

        route = _route_stats[route_key]
        route["count"] += 1
        route["total_duration_ms"] += float(duration_ms)
        route["avg_duration_ms"] = round(route["total_duration_ms"] / route["count"], 2)
        route["last_status_code"] = int(status_code)
        route["last_seen_at"] = int(time.time())
        if status_code >= 400:
            route["errors"] += 1


def metrics_snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "uptime_seconds": int(time.time() - _started_at),
            "requests": {
                "total": _total_requests,
                "errors": _total_errors,
                "success_rate": round(
                    (_total_requests - _total_errors) / max(_total_requests, 1),
                    4,
                ),
            },
            "routes": dict(_route_stats),
        }
