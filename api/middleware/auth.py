"""
api/middleware/auth.py — API key authentication middleware.

Supports optional API key validation via the X-API-Key header or
?api_key= query parameter.  When no API key is configured in settings,
authentication is bypassed (development mode).
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from fastapi import Security

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)


async def verify_api_key(
    header_key: Optional[str] = Security(API_KEY_HEADER),
    query_key: Optional[str] = Security(API_KEY_QUERY),
) -> Optional[str]:
    """
    Verify the API key from header or query parameter.

    - If no API key is configured in settings, bypass authentication.
    - Otherwise require a matching key via X-API-Key header or api_key param.
    """
    try:
        from config.settings import get_settings
        settings = get_settings()
        configured_key = settings.api_key
    except Exception:
        configured_key = None

    if not configured_key:
        # Development mode: no key required
        return None

    provided = header_key or query_key
    if not provided or provided != configured_key:
        logger.warning("Rejected request with invalid/missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Valid API key required"},
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return provided
