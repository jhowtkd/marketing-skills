from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.responses import Response


def configure_structured_logging(*, level: str = "INFO") -> None:
    logger = logging.getLogger("vm_webapp.http")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = True


async def request_id_middleware(request: Request, call_next) -> Response:
    request_id = (
        request.headers.get("X-Request-Id")
        or request.headers.get("X-Request-ID")
        or uuid4().hex[:12]
    )
    correlation_id = (
        request.headers.get("X-Correlation-Id")
        or request.headers.get("X-Correlation-ID")
        or request_id
    )

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    start = time.perf_counter()
    status_code = 500
    response: Response | None = None
    try:
        response = await call_next(request)
        status_code = int(response.status_code)
        return response
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logging.getLogger("vm_webapp.http").info(
            "request_id=%s correlation_id=%s method=%s path=%s status_code=%s duration_ms=%s",
            request_id,
            correlation_id,
            request.method,
            request.url.path,
            status_code,
            elapsed_ms,
        )
        if response is not None:
            response.headers["X-Request-Id"] = request_id
            response.headers["X-Correlation-Id"] = correlation_id
