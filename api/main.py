"""
api/main.py — FastAPI application for CMS Snowflake AI Agents.

Exposes the Snowflake Cortex Agent as a REST API for medication adherence
analytics.  Bridges natural language questions to Snowflake Cortex Analyst
and returns structured responses with answers, SQL, data, and viz hints.

Endpoints:
    POST  /ask      — Submit a natural language query
    GET   /health   — Service health check
    GET   /metrics  — Query performance metrics
    GET   /schemas  — Available semantic views / schemas

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import logging
import sys

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth import verify_api_key
from api.middleware.logging import RequestLoggingMiddleware
from api.routes import ask, health, metrics, schemas

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
try:
    from config.settings import get_settings
    _settings = get_settings()
    _title = _settings.api_title
    _version = _settings.api_version
    _description = _settings.api_description
    _debug = _settings.api_debug
    _cors_origins = _settings.cors_origins
except Exception:
    _title = "CMS Snowflake AI Agents API"
    _version = "1.0.0"
    _description = "Medicare Part D Patient Medication Adherence — Cortex Agent API"
    _debug = False
    _cors_origins = ["*"]

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=_title,
    version=_version,
    description=_description,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# Protected routes require API key when configured.
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(schemas.router)

# POST /ask is protected by API key when configured
app.include_router(
    ask.router,
    dependencies=[Depends(verify_api_key)],
)

# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    return {
        "service": _title,
        "version": _version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=_settings.api_host if hasattr(_settings, "api_host") else "0.0.0.0",
        port=_settings.api_port if hasattr(_settings, "api_port") else 8000,
        reload=_debug,
    )
