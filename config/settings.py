"""
config/settings.py — Unified application settings for CMS Snowflake AI Agents.

Merges Snowflake connection settings with API, frontend, and Claude settings.
Uses pydantic-settings for environment variable loading and validation.
"""

import os
from functools import lru_cache
from typing import List, Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field
except ImportError:
    # Fallback: re-export config constants from legacy python/config.py
    from python.config import (  # noqa: F401
        DATABASE,
        SCHEMA_RAW,
        SCHEMA_CURATED,
        SCHEMA_GOLD,
        WAREHOUSE,
        CORTEX_LLM_MODEL,
    )

    class BaseSettings:  # type: ignore[no-redef]
        pass

    def Field(*args, **kwargs):  # noqa: N802
        return None

    SettingsConfigDict = None


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    ) if SettingsConfigDict else {}

    # ------------------------------------------------------------------
    # Snowflake connection
    # ------------------------------------------------------------------
    snowflake_account: str = Field(default="")
    snowflake_user: str = Field(default="")
    snowflake_password: str = Field(default="")
    snowflake_role: str = Field(default="CMS_STARS_ANALYST")
    snowflake_warehouse: str = Field(default="CMS_STARS_WH")
    snowflake_database: str = Field(default="CMS_STARS_DB")
    snowflake_schema: str = Field(default="SCHEMA_GOLD")
    snowflake_authenticator: Optional[str] = Field(default=None)
    snowflake_pat: Optional[str] = Field(default=None)
    snowflake_private_key_path: Optional[str] = Field(default=None)

    # ------------------------------------------------------------------
    # Cortex / AI model settings
    # ------------------------------------------------------------------
    cortex_llm_model: str = Field(default="mistral-large2")
    cortex_embed_model: str = Field(default="snowflake-arctic-embed-l-v2.0")
    measurement_year: int = Field(default=2024)

    # ------------------------------------------------------------------
    # Claude / Anthropic
    # ------------------------------------------------------------------
    anthropic_api_key: Optional[str] = Field(default=None)
    claude_model: str = Field(default="claude-3-5-sonnet-20241022")

    # ------------------------------------------------------------------
    # API settings
    # ------------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=False)
    api_key: Optional[str] = Field(default=None)
    api_title: str = "CMS Snowflake AI Agents API"
    api_version: str = "1.0.0"
    api_description: str = (
        "Medicare Part D Patient Medication Adherence — Cortex Agent API"
    )

    # Query limits and pagination
    max_result_rows: int = Field(default=1000)
    default_page_size: int = Field(default=100)
    query_timeout_seconds: int = Field(default=60)

    # ------------------------------------------------------------------
    # Cache settings
    # ------------------------------------------------------------------
    cache_ttl_seconds: int = Field(default=300)
    cache_max_size: int = Field(default=256)

    # ------------------------------------------------------------------
    # CORS / security
    # ------------------------------------------------------------------
    cors_origins: List[str] = Field(
        default=["http://localhost:8501", "http://localhost:3000"]
    )

    # ------------------------------------------------------------------
    # Frontend settings
    # ------------------------------------------------------------------
    frontend_api_url: str = Field(default="http://localhost:8000")
    frontend_page_title: str = "CMS Stars AI Agents"
    frontend_page_icon: str = "💊"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
