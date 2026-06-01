"""
api/models.py — Pydantic request and response models for the Cortex Agent API.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class QueryContext(BaseModel):
    """Optional context for a natural language query."""
    role: Optional[str] = Field(default=None, description="User role for access control")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation continuity")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Pre-applied data filters")
    semantic_model: Optional[str] = Field(default=None, description="Override semantic model path")


class AskRequest(BaseModel):
    """Request body for the POST /ask endpoint."""
    question: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Natural language question about medication adherence data",
    )
    context: QueryContext = Field(default_factory=QueryContext)
    max_rows: int = Field(default=100, ge=1, le=1000, description="Maximum result rows")
    include_sql: bool = Field(default=True, description="Include generated SQL in response")
    page: int = Field(default=1, ge=1, description="Result page number")
    page_size: int = Field(default=100, ge=1, le=500, description="Page size")

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class VizHint(BaseModel):
    """Visualization hint for rendering the query result."""
    chart: str = Field(description="Chart type: line, bar, scatter, histogram, table, metric")
    x: Optional[str] = Field(default=None, description="Recommended X-axis column")
    y: Optional[str] = Field(default=None, description="Recommended Y-axis column")
    title: Optional[str] = Field(default=None, description="Suggested chart title")


class AskResponse(BaseModel):
    """Response body for the POST /ask endpoint."""
    answer: str = Field(description="Natural language answer")
    sql: Optional[str] = Field(default=None, description="Generated SQL query")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Query result rows")
    viz_hint: VizHint = Field(description="Visualization recommendation")
    trace_id: str = Field(description="Query trace ID for audit/debugging")
    session_id: Optional[str] = Field(default=None)
    row_count: int = Field(default=0)
    total_rows: Optional[int] = Field(default=None)
    page: int = Field(default=1)
    page_size: int = Field(default=100)
    truncated: bool = Field(default=False)
    latency_ms: int = Field(description="Query latency in milliseconds")
    cached: bool = Field(default=False, description="Whether result was served from cache")


class HealthResponse(BaseModel):
    """Response for GET /health."""
    status: str
    version: str
    snowflake_connected: bool
    details: Optional[Dict[str, Any]] = None


class MetricsResponse(BaseModel):
    """Response for GET /metrics."""
    total_queries: int
    cache_hits: int
    cache_misses: int
    avg_latency_ms: float
    error_count: int
    uptime_seconds: float


class SchemaInfo(BaseModel):
    """Metadata about an available schema or table."""
    name: str
    type: str = Field(description="TABLE, VIEW, or SCHEMA")
    description: Optional[str] = None
    columns: Optional[List[Dict[str, str]]] = None


class SchemasResponse(BaseModel):
    """Response for GET /schemas."""
    schemas: List[SchemaInfo]
    semantic_model: Optional[str] = None


class ErrorDetail(BaseModel):
    """Structured error detail."""
    code: str
    message: str
    trace_id: Optional[str] = None
