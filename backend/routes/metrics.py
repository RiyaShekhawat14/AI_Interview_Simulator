from fastapi import APIRouter

from services.cache_service import cache_stats
from services.metrics_service import metrics_snapshot
from services.rate_limit_service import rate_limit_stats


router = APIRouter(tags=["ops"])


@router.get("/metrics")
def get_metrics():
    return {
        "service": "ai-interview-backend",
        "metrics": metrics_snapshot(),
        "cache": cache_stats(),
        "rate_limit": rate_limit_stats(),
    }
