from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.middleware.base import BaseHTTPMiddleware

# Request counter by method, endpoint, and status code
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

# Request duration histogram
request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# Request size histogram
request_size = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

# Response size histogram
response_size = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

# Error counter by type
error_count = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"],
)

# Active connections gauge
active_connections = Gauge(
    "http_active_connections",
    "Number of active HTTP connections",
)

# Database connection metrics
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

db_query_count = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation"],
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests.
    
    Collects:
    - Request count by method, endpoint, and status
    - Request duration histogram
    - Request/response size histograms
    - Error counts
    - Active connections gauge
    
    Usage:
        from fastapi import FastAPI
        from middleware_metrics import PrometheusMetricsMiddleware
        
        app = FastAPI()
        app.add_middleware(PrometheusMetricsMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Track active connections
        active_connections.inc()
        
        # Get endpoint label (path template if available, else actual path)
        endpoint = self._get_endpoint_label(request)
        method = request.method
        
        # Get request size
        content_length = request.headers.get("content-length", 0)
        try:
            request_bytes = int(content_length)
            if request_bytes > 0:
                request_size.labels(method=method, endpoint=endpoint).observe(request_bytes)
        except ValueError:
            pass
        
        # Time the request
        start_time = time.perf_counter()
        status_code = 500
        response: Response | None = None
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Record response size if available
            if response.headers.get("content-length"):
                try:
                    response_bytes = int(response.headers["content-length"])
                    response_size.labels(method=method, endpoint=endpoint).observe(response_bytes)
                except ValueError:
                    pass
            
            return response
            
        except Exception as exc:
            # Record error
            error_type = type(exc).__name__
            error_count.labels(
                method=method,
                endpoint=endpoint,
                error_type=error_type,
            ).inc()
            raise
            
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time
            
            # Record metrics
            request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code),
            ).inc()
            
            request_duration.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)
            
            # Decrement active connections
            active_connections.dec()
    
    def _get_endpoint_label(self, request: Request) -> str:
        """Get a normalized endpoint label for the request.
        
        Tries to use the route path if available, otherwise uses the actual path
        with IDs replaced by placeholders.
        """
        # Try to get the route pattern if available
        if hasattr(request.state, "endpoint") and request.state.endpoint:
            return request.state.endpoint
        
        # Normalize the path
        path = request.url.path
        
        # Replace common ID patterns with placeholders
        import re
        
        # Replace UUID-like patterns
        path = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{id}', path)
        
        # Replace common ID patterns (brand-xxx, project-xxx, etc.)
        path = re.sub(r'(brand|project|thread|campaign|run)-[a-z0-9]+', r'\1-{id}', path)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+/', '/{id}/', path)
        path = re.sub(r'/\d+$', '/{id}', path)
        
        return path


class DatabaseMetrics:
    """Helper class to track database query metrics.
    
    Usage:
        from middleware_metrics import DatabaseMetrics
        
        with DatabaseMetrics.track("select"):
            result = session.execute(query)
    """
    
    @staticmethod
    def track(operation: str):
        """Context manager to track a database operation.
        
        Args:
            operation: Type of database operation (select, insert, update, delete)
        """
        class _DatabaseMetricsContext:
            def __enter__(self):
                self.start = time.perf_counter()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.perf_counter() - self.start
                db_query_duration.labels(operation=operation).observe(duration)
                db_query_count.labels(operation=operation).inc()
                return False
        
        return _DatabaseMetricsContext()


def get_prometheus_metrics() -> tuple[bytes, str]:
    """Generate Prometheus metrics output.
    
    Returns:
        Tuple of (metrics_bytes, content_type)
    """
    return generate_latest(), CONTENT_TYPE_LATEST


def metrics_endpoint() -> Response:
    """Create a Starlette Response with Prometheus metrics.
    
    Returns:
        Response with Prometheus metrics in exposition format
    """
    from starlette.responses import Response
    
    data, content_type = get_prometheus_metrics()
    return Response(content=data, media_type=content_type)


def get_metrics_summary() -> dict:
    """Get a summary of current metrics for health checks.
    
    Returns:
        Dictionary with key metrics summary
    """
    from prometheus_client import REGISTRY
    
    summary = {
        "active_connections": 0,
        "total_requests": 0,
        "error_rate": 0.0,
    }
    
    # Get active connections
    for sample in active_connections.collect()[0].samples:
        summary["active_connections"] = int(sample.value)
    
    # Get total requests
    for sample in request_count.collect()[0].samples:
        summary["total_requests"] += int(sample.value)
    
    # Calculate error rate (4xx + 5xx / total)
    total = summary["total_requests"]
    if total > 0:
        errors = 0
        for sample in request_count.collect()[0].samples:
            status = sample.labels.get("status_code", "0")
            if status.startswith(("4", "5")):
                errors += int(sample.value)
        summary["error_rate"] = round(errors / total, 4)
    
    return summary
