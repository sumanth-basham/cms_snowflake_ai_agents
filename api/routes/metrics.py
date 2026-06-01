"""
api/routes/metrics.py — GET /metrics endpoint.

Exposes basic query performance and usage metrics.
"""

import logging
import time
from typing import Dict, Any

from fastapi import APIRouter

from api.models import MetricsResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level counters (process-local; use Redis/Prometheus in production)
_start_time = time.time()
_metrics: Dict[str, Any] = {
    "total_queries": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "total_latency_ms": 0,
    "error_count": 0,
}


def record_query(latency_ms: int, cached: bool = False, error: bool = False) -> None:
    """Update in-memory metrics after each query."""
    _metrics["total_queries"] += 1
    if cached:
        _metrics["cache_hits"] += 1
    else:
        _metrics["cache_misses"] += 1
        _metrics["total_latency_ms"] += latency_ms
    if error:
        _metrics["error_count"] += 1


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Query performance metrics",
    tags=["Operations"],
)
def get_metrics() -> MetricsResponse:
    """Return current query performance and usage metrics."""
    total = _metrics["total_queries"]
    cache_misses = _metrics["cache_misses"]
    avg_latency = (
        _metrics["total_latency_ms"] / cache_misses if cache_misses > 0 else 0.0
    )
    return MetricsResponse(
        total_queries=total,
        cache_hits=_metrics["cache_hits"],
        cache_misses=cache_misses,
        avg_latency_ms=round(avg_latency, 2),
        error_count=_metrics["error_count"],
        uptime_seconds=round(time.time() - _start_time, 1),
    )
