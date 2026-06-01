"""
api/utils/cache.py — In-process LRU cache for repeated query results.

Uses cachetools.TTLCache to store query results with a time-to-live.
Cache settings are driven by config/settings.py.

In production, swap for Redis or Snowflake result caching.
"""

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_cache: Optional[Any] = None


def _get_ttl_cache():
    """Lazy-initialize the TTL cache singleton."""
    global _cache
    if _cache is not None:
        return _cache

    try:
        from cachetools import TTLCache
        from config.settings import get_settings

        settings = get_settings()
        _cache = TTLCache(
            maxsize=settings.cache_max_size,
            ttl=settings.cache_ttl_seconds,
        )
    except ImportError:
        # cachetools not installed: use a simple dict (no TTL)
        logger.warning("cachetools not installed; using unbounded dict cache")
        _cache = {}
    except Exception as exc:
        logger.warning("Cache init failed, using dict fallback: %s", exc)
        _cache = {}

    return _cache


def get_cache():
    """Return the active cache instance."""
    return _get_ttl_cache()


def make_cache_key(question: str, max_rows: int) -> str:
    """Create a deterministic cache key from question text and row limit."""
    payload = json.dumps({"q": question.strip().lower(), "rows": max_rows}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def invalidate_cache() -> None:
    """Clear all cached results (useful for testing or forced refresh)."""
    global _cache
    if _cache is not None:
        _cache.clear()
    logger.info("Query cache invalidated")
