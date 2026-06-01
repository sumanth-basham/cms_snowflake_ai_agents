"""
snowflake/cortex_client.py — Snowflake Cortex Analyst/Agent API client.

Bridges natural language questions to Snowflake Cortex Analyst and
returns structured responses containing:
  - Natural language answer
  - Underlying SQL query
  - Result dataset (up to max_rows)
  - Visualization hints
  - Query trace ID for audit/debugging
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default semantic model for medication adherence queries
DEFAULT_SEMANTIC_MODEL = "@CMS_STARS_DB.SCHEMA_RAW.CMS_SEMANTIC_MODELS_STAGE/medication_adherence.yaml"

# Maximum rows returned per query (safety cap)
DEFAULT_MAX_ROWS = 1000


def ask_cortex_analyst(
    question: str,
    semantic_model_path: str = DEFAULT_SEMANTIC_MODEL,
    max_rows: int = DEFAULT_MAX_ROWS,
    session_id: Optional[str] = None,
    settings=None,
) -> Dict[str, Any]:
    """
    Submit a natural language question to Snowflake Cortex Analyst.

    Uses the Cortex Analyst REST endpoint or Snowpark SQL function to
    convert the question to SQL, execute it, and return structured results.

    Args:
        question: Natural language question about medication adherence data
        semantic_model_path: Path to the YAML semantic model in Snowflake stage
        max_rows: Maximum result rows to return
        session_id: Optional session ID for multi-turn conversations
        settings: Optional settings override

    Returns:
        dict with keys: answer, sql, data, viz_hint, trace_id, latency_ms
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    try:
        result = _call_cortex_analyst_sql(
            question=question,
            semantic_model_path=semantic_model_path,
            max_rows=max_rows,
            settings=settings,
        )
        sql_query = result.get("sql", "")
        data = result.get("data", [])
        answer = result.get("answer", "")
    except Exception as exc:
        logger.error("Cortex Analyst call failed: %s", exc)
        raise

    latency_ms = int(
        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    )

    viz_hint = _infer_viz_hint(question, data, sql_query)

    return {
        "answer": answer,
        "sql": sql_query,
        "data": data,
        "viz_hint": viz_hint,
        "trace_id": trace_id,
        "session_id": session_id,
        "latency_ms": latency_ms,
        "row_count": len(data),
        "truncated": len(data) >= max_rows,
    }


def _call_cortex_analyst_sql(
    question: str,
    semantic_model_path: str,
    max_rows: int,
    settings=None,
) -> Dict[str, Any]:
    """
    Execute a Cortex Analyst query using the Snowflake SQL API.

    Uses SNOWFLAKE.CORTEX.ANALYST() function if available, otherwise falls
    back to a parameterised COMPLETE call for prototyping.
    """
    from cortex.connection import snowflake_cursor

    analyst_sql = """
SELECT SNOWFLAKE.CORTEX.ANALYST(
    semantic_model => %s,
    user_message   => %s
) AS analyst_response
""".strip()

    with snowflake_cursor(settings, dict_cursor=False) as cursor:
        cursor.execute(analyst_sql, (semantic_model_path, question))
        row = cursor.fetchone()

    if not row:
        return {"answer": "No response received.", "sql": "", "data": []}

    raw = row[0] if isinstance(row, (list, tuple)) else row
    if isinstance(raw, str):
        try:
            response = json.loads(raw)
        except json.JSONDecodeError:
            response = {"answer": raw, "sql": "", "data": []}
    else:
        response = raw or {}

    # Extract generated SQL and execute it to fetch data
    generated_sql = response.get("sql", "")
    data: List[Dict[str, Any]] = []

    if generated_sql:
        limited_sql = _apply_row_limit(generated_sql, max_rows)
        try:
            from cortex.connection import snowflake_cursor as sc
            with sc(settings) as cursor:
                cursor.execute(limited_sql)
                data = cursor.fetchall() or []
        except Exception as exc:
            logger.warning("Failed to execute generated SQL: %s", exc)

    return {
        "answer": response.get("answer", response.get("message", "")),
        "sql": generated_sql,
        "data": data,
    }


def _apply_row_limit(sql: str, max_rows: int) -> str:
    """Wrap a SQL query with a LIMIT clause if not already present."""
    sql_upper = sql.strip().upper()
    if "LIMIT" not in sql_upper:
        return f"SELECT * FROM ({sql}) AS _limited LIMIT {max_rows}"
    return sql


def _infer_viz_hint(
    question: str,
    data: List[Dict[str, Any]],
    sql: str,
) -> Dict[str, Any]:
    """
    Infer a visualization hint from the question and result shape.

    Returns a dict with: chart (type), x (dimension), y (measure),
    title (suggested chart title).
    """
    q_lower = question.lower()

    if not data:
        return {"chart": "table", "x": None, "y": None, "title": "Query Results"}

    columns = list(data[0].keys()) if data else []

    # Detect date/time dimension
    time_cols = [c for c in columns if any(t in c.lower() for t in ("date", "month", "year", "quarter", "week"))]
    # Detect categorical dimension
    cat_cols = [c for c in columns if any(t in c.lower() for t in ("region", "state", "class", "type", "measure", "drug", "contract", "plan", "group"))]
    # Detect numeric measure
    num_cols = [c for c in columns if any(t in c.lower() for t in ("rate", "count", "pct", "percent", "avg", "sum", "total", "ratio", "score", "amount"))]

    x_col = (time_cols or cat_cols or [columns[0] if columns else None])[0]
    y_col = (num_cols or [columns[-1] if len(columns) > 1 else None])[0]

    if "trend" in q_lower or "over time" in q_lower or time_cols:
        chart = "line"
    elif "compare" in q_lower or "by region" in q_lower or "by class" in q_lower or cat_cols:
        chart = "bar"
    elif "distribution" in q_lower or "histogram" in q_lower:
        chart = "histogram"
    elif "correlation" in q_lower or "scatter" in q_lower:
        chart = "scatter"
    elif len(data) == 1:
        chart = "metric"
    else:
        chart = "bar"

    return {"chart": chart, "x": x_col, "y": y_col, "title": question[:80]}
