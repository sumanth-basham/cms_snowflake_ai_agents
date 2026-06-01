"""
cortex/connection.py — Snowflake connection factory.

Thin wrapper around python/db_helpers.py that integrates with the
unified config/settings.py layer.  Supports key-pair, PAT, and password auth.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

logger = logging.getLogger(__name__)


def _build_connection_params(settings=None) -> dict:
    """
    Build Snowflake connection parameters from settings or environment.

    Authentication priority:
      1. PAT (SNOWFLAKE_PAT) → authenticator=oauth
      2. Key-pair (SNOWFLAKE_AUTHENTICATOR=snowflake_jwt)
      3. SSO (SNOWFLAKE_AUTHENTICATOR=externalbrowser)
      4. Password (SNOWFLAKE_PASSWORD) — least preferred for production
    """
    if settings is None:
        try:
            from config.settings import get_settings
            settings = get_settings()
            params = {
                "account": settings.snowflake_account,
                "user": settings.snowflake_user,
                "role": settings.snowflake_role,
                "warehouse": settings.snowflake_warehouse,
                "database": settings.snowflake_database,
                "schema": settings.snowflake_schema,
            }
            pat = settings.snowflake_pat
            authenticator = settings.snowflake_authenticator
            password = settings.snowflake_password
        except Exception:
            params = {
                "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
                "user": os.getenv("SNOWFLAKE_USER", ""),
                "role": os.getenv("SNOWFLAKE_ROLE", "CMS_STARS_ANALYST"),
                "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "CMS_STARS_WH"),
                "database": os.getenv("SNOWFLAKE_DATABASE", "CMS_STARS_DB"),
                "schema": os.getenv("SNOWFLAKE_SCHEMA", "SCHEMA_GOLD"),
            }
            pat = os.getenv("SNOWFLAKE_PAT")
            authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR")
            password = os.getenv("SNOWFLAKE_PASSWORD")
    else:
        params = {
            "account": settings.snowflake_account,
            "user": settings.snowflake_user,
            "role": settings.snowflake_role,
            "warehouse": settings.snowflake_warehouse,
            "database": settings.snowflake_database,
            "schema": settings.snowflake_schema,
        }
        pat = getattr(settings, "snowflake_pat", None)
        authenticator = getattr(settings, "snowflake_authenticator", None)
        password = getattr(settings, "snowflake_password", None)

    if pat:
        params["authenticator"] = "oauth"
        params["token"] = pat
    elif authenticator:
        params["authenticator"] = authenticator
    elif password:
        params["password"] = password

    return params


def get_connection(settings=None):
    """Create and return an authenticated Snowflake connection."""
    import snowflake.connector

    params = _build_connection_params(settings)
    logger.debug(
        "Connecting to Snowflake: account=%s user=%s role=%s",
        params.get("account"),
        params.get("user"),
        params.get("role"),
    )
    return snowflake.connector.connect(**params)


@contextmanager
def snowflake_cursor(settings=None, dict_cursor: bool = True) -> Generator:
    """Context manager yielding an authenticated Snowflake cursor."""
    from snowflake.connector import DictCursor

    conn = get_connection(settings)
    try:
        cursor = conn.cursor(DictCursor) if dict_cursor else conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    finally:
        conn.close()
