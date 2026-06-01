"""
api/routes/health.py — GET /health endpoint.

Returns service health status and optional Snowflake connectivity check.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter

from api.models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level startup time for uptime calculation
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    tags=["Operations"],
)
def health_check() -> HealthResponse:
    """
    Return service health status.

    Checks:
    - API is running
    - Optional: Snowflake connectivity (lightweight ping)
    """
    from config.settings import get_settings

    settings = get_settings()
    snowflake_ok = _check_snowflake(settings)

    return HealthResponse(
        status="ok" if snowflake_ok else "degraded",
        version=settings.api_version,
        snowflake_connected=snowflake_ok,
        details={
            "uptime_seconds": round(time.time() - _start_time, 1),
            "snowflake_account": settings.snowflake_account or "not configured",
            "semantic_model": "medication_adherence.yaml",
        },
    )


def _check_snowflake(settings) -> bool:
    """Lightweight Snowflake connectivity test — returns False if not configured."""
    if not settings.snowflake_account:
        return False
    try:
        from cortex.connection import snowflake_cursor

        with snowflake_cursor(settings, dict_cursor=False) as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception as exc:
        logger.warning("Snowflake health check failed: %s", exc)
        return False
