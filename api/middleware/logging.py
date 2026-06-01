"""
api/middleware/logging.py — Request/response logging middleware.

Logs every request with method, path, status code, and latency.
Audit-grade: includes trace-id correlation for all requests.
"""

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with latency and trace ID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        start = time.time()

        response = await call_next(request)

        latency_ms = int((time.time() - start) * 1000)
        response.headers["X-Trace-Id"] = trace_id

        logger.info(
            "method=%s path=%s status=%s latency_ms=%d trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            trace_id,
        )
        return response
