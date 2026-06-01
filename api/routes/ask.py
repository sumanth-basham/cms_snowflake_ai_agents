"""
api/routes/ask.py — POST /ask endpoint.

Accepts natural language questions about Medicare Part D medication adherence,
calls Snowflake Cortex Analyst, and returns structured responses.
"""

import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.models import AskRequest, AskResponse, VizHint
from api.utils.validators import validate_question
from api.utils.cache import get_cache, make_cache_key
from cortex.cortex_client import ask_cortex_analyst

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Submit a natural language query",
    tags=["Analytics"],
)
def ask(request: AskRequest, http_request: Request) -> AskResponse:
    """
    Submit a natural language question about medication adherence data.

    The question is forwarded to Snowflake Cortex Analyst, which:
    1. Interprets the question against the medication adherence semantic model
    2. Generates and executes SQL
    3. Returns a natural language answer, the SQL, result data, and viz hints

    Results are cached for repeated identical questions.
    """
    # --- Input validation ---
    issues = validate_question(request.question)
    if issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_FAILED", "message": "; ".join(issues)},
        )

    from config.settings import get_settings
    settings = get_settings()

    session_id = request.context.session_id or str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    # --- Cache lookup ---
    cache = get_cache()
    cache_key = make_cache_key(request.question, request.max_rows)
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("Cache hit for question: %.60s", request.question)
        cached["cached"] = True
        cached["trace_id"] = trace_id
        cached["session_id"] = session_id
        return AskResponse(**cached)

    # --- Call Cortex Analyst ---
    start = time.time()
    try:
        semantic_model = (
            request.context.semantic_model
            or getattr(settings, "cortex_semantic_model", None)
            or "@CMS_STARS_DB.SCHEMA_RAW.CMS_SEMANTIC_MODELS_STAGE/medication_adherence.yaml"
        )

        result = ask_cortex_analyst(
            question=request.question,
            semantic_model_path=semantic_model,
            max_rows=request.max_rows,
            session_id=session_id,
            settings=settings,
        )
    except Exception as exc:
        logger.error("Cortex Analyst query failed: trace=%s error=%s", trace_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "CORTEX_ERROR",
                "message": "Failed to query Snowflake Cortex Analyst",
                "trace_id": trace_id,
            },
        )

    latency_ms = int((time.time() - start) * 1000)

    # --- Paginate results ---
    all_data = result.get("data", [])
    page_start = (request.page - 1) * request.page_size
    page_end = page_start + request.page_size
    paged_data = all_data[page_start:page_end]

    viz = result.get("viz_hint", {})
    response_payload = {
        "answer": result.get("answer", ""),
        "sql": result.get("sql") if request.include_sql else None,
        "data": paged_data,
        "viz_hint": VizHint(
            chart=viz.get("chart", "table"),
            x=viz.get("x"),
            y=viz.get("y"),
            title=viz.get("title"),
        ),
        "trace_id": trace_id,
        "session_id": session_id,
        "row_count": len(paged_data),
        "total_rows": len(all_data),
        "page": request.page,
        "page_size": request.page_size,
        "truncated": result.get("truncated", False),
        "latency_ms": latency_ms,
        "cached": False,
    }

    # --- Cache the result ---
    cache_payload = {**response_payload}
    cache[cache_key] = cache_payload

    return AskResponse(**response_payload)
