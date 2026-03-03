from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.responses import Response


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id
        if hasattr(record, "method"):
            log_obj["method"] = record.method
        if hasattr(record, "path"):
            log_obj["path"] = record.path
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "user_agent"):
            log_obj["user_agent"] = record.user_agent
        if hasattr(record, "client_ip"):
            log_obj["client_ip"] = record.client_ip
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, default=str)


def configure_structured_logging(*, level: str = "INFO", json_format: bool = True) -> None:
    """Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs as JSON (True) or plain text (False)
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    
    root_logger.addHandler(console_handler)
    
    # Configure vm_webapp loggers
    for logger_name in ["vm_webapp.http", "vm_webapp.api", "vm_webapp.middleware"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.propagate = False
        logger.addHandler(console_handler)


async def request_id_middleware(request: Request, call_next) -> Response:
    """Middleware to track requests with unique IDs and structured logging.
    
    Adds the following to each request:
    - request_id: Unique identifier for this request
    - correlation_id: For tracing across services
    - Structured logging with timing, status, and user agent
    
    Response headers:
    - X-Request-Id: The request ID
    - X-Correlation-Id: The correlation ID
    - X-Response-Time-Ms: Response time in milliseconds
    """
    # Extract or generate request/correlation IDs
    request_id = (
        request.headers.get("X-Request-Id")
        or request.headers.get("X-Request-ID")
        or f"req-{uuid4().hex[:12]}"
    )
    correlation_id = (
        request.headers.get("X-Correlation-Id")
        or request.headers.get("X-Correlation-ID")
        or request_id
    )
    
    # Store in request state for access in route handlers
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    
    # Get client info
    client_ip = (
        request.headers.get("X-Forwarded-For", "")
        .split(",")[0]
        .strip()
        or request.client.host
        if request.client
        else "unknown"
    )
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Start timing
    start = time.perf_counter()
    status_code = 500
    response: Response | None = None
    
    # Create logger with extra context
    logger = logging.getLogger("vm_webapp.http")
    
    try:
        response = await call_next(request)
        status_code = int(response.status_code)
        return response
    except Exception as exc:
        # Log exception before re-raising
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        extra = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "duration_ms": elapsed_ms,
            "user_agent": user_agent,
            "client_ip": client_ip,
        }
        logger.error(
            f"Request failed: {exc}",
            extra=extra,
            exc_info=True
        )
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        
        # Log request completion
        extra = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": elapsed_ms,
            "user_agent": user_agent,
            "client_ip": client_ip,
        }
        
        # Log at appropriate level based on status
        if status_code >= 500:
            logger.error("Request completed with server error", extra=extra)
        elif status_code >= 400:
            logger.warning("Request completed with client error", extra=extra)
        else:
            logger.info("Request completed successfully", extra=extra)
        
        # Add headers to response
        if response is not None:
            response.headers["X-Request-Id"] = request_id
            response.headers["X-Correlation-Id"] = correlation_id
            response.headers["X-Response-Time-Ms"] = str(elapsed_ms)


def get_request_logger(request: Request) -> logging.Logger:
    """Get a logger with request context pre-populated.
    
    Usage in route handlers:
        logger = get_request_logger(request)
        logger.info("Processing brand creation")
    
    Args:
        request: The current request object
        
    Returns:
        A logger with request_id and correlation_id bound
    """
    logger = logging.getLogger("vm_webapp.api")
    
    # Create adapter with request context
    request_id = getattr(request.state, "request_id", "unknown")
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    extra = {
        "request_id": request_id,
        "correlation_id": correlation_id,
    }
    
    return logging.LoggerAdapter(logger, extra)


def log_access(
    logger: logging.Logger,
    *,
    request: Request,
    response_status: int,
    duration_ms: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log an access event with full context.
    
    Args:
        logger: Logger instance
        request: The request being logged
        response_status: HTTP status code
        duration_ms: Request duration in milliseconds
        extra: Additional fields to include in log
    """
    request_id = getattr(request.state, "request_id", "unknown")
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    user_agent = request.headers.get("User-Agent", "unknown")
    client_ip = (
        request.headers.get("X-Forwarded-For", "")
        .split(",")[0]
        .strip()
        or request.client.host
        if request.client
        else "unknown"
    )
    
    log_data = {
        "request_id": request_id,
        "correlation_id": correlation_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response_status,
        "duration_ms": duration_ms,
        "user_agent": user_agent,
        "client_ip": client_ip,
    }
    
    if extra:
        log_data.update(extra)
    
    if response_status >= 500:
        logger.error("Access log", extra=log_data)
    elif response_status >= 400:
        logger.warning("Access log", extra=log_data)
    else:
        logger.info("Access log", extra=log_data)
