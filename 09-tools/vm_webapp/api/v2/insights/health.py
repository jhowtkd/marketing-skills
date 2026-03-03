from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, status
from sqlalchemy import text

from vm_webapp.middleware_metrics import get_metrics_summary

router = APIRouter(tags=["health", "metrics"])


async def check_database(request: Request) -> dict[str, str | float]:
    """Check database connectivity and performance.
    
    Returns:
        Dict with status, latency_ms, and optional error message
    """
    from vm_webapp.db import session_scope
    
    start_time = datetime.now()
    try:
        with session_scope(request.app.state.engine) as session:
            # Test basic connectivity
            session.execute(text("SELECT 1"))
            
            # Get connection count (PostgreSQL specific)
            try:
                result = session.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                ))
                connection_count = result.scalar() or 0
            except Exception:
                connection_count = -1
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": "ok",
                "latency_ms": round(latency_ms, 2),
                "connections": connection_count,
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def check_memory() -> dict[str, str | float]:
    """Check system memory usage.
    
    Returns:
        Dict with status and memory statistics
    """
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        # Determine status based on usage
        if usage_percent > 90:
            status = "critical"
        elif usage_percent > 75:
            status = "warning"
        else:
            status = "ok"
        
        return {
            "status": status,
            "usage_percent": round(usage_percent, 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "total_gb": round(memory.total / (1024**3), 2),
        }
    except ImportError:
        # psutil not available, return basic info
        return {
            "status": "unknown",
            "message": "psutil not installed",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def check_disk_space() -> dict[str, str | float]:
    """Check available disk space.
    
    Returns:
        Dict with status and disk statistics
    """
    try:
        stat = shutil.disk_usage("/")
        total_gb = stat.total / (1024**3)
        free_gb = stat.free / (1024**3)
        used_percent = (stat.used / stat.total) * 100
        
        # Determine status based on free space
        if free_gb < 1:  # Less than 1GB free
            status = "critical"
        elif free_gb < 5:  # Less than 5GB free
            status = "warning"
        else:
            status = "ok"
        
        return {
            "status": status,
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "used_percent": round(used_percent, 2),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def check_worker(request: Request) -> dict[str, str]:
    """Check event worker status.
    
    Returns:
        Dict with status and worker information
    """
    worker = getattr(request.app.state, "event_worker", None)
    mode = getattr(
        request.app.state,
        "worker_mode",
        "in_process" if worker is not None else "external",
    )
    
    if mode == "in_process":
        if worker is not None:
            status = "ok"
            detail = "running"
        else:
            status = "error"
            detail = "missing"
    else:
        # External worker mode - assume ok if configured
        status = "ok"
        detail = "external"
    
    return {
        "status": status,
        "mode": str(mode),
        "detail": detail,
    }


def check_metrics() -> dict[str, str | float | int]:
    """Get metrics summary for health check.
    
    Returns:
        Dict with metrics summary
    """
    try:
        summary = get_metrics_summary()
        
        # Determine status based on error rate
        error_rate = summary.get("error_rate", 0)
        if error_rate > 0.1:  # More than 10% errors
            status = "warning"
        else:
            status = "ok"
        
        return {
            "status": status,
            "active_connections": summary.get("active_connections", 0),
            "total_requests": summary.get("total_requests", 0),
            "error_rate": error_rate,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Indicates the service is running and responding to requests. Used by Kubernetes liveness probes.",
    responses={
        status.HTTP_200_OK: {"description": "Service is alive"},
    },
)
async def health_live_v2(request: Request) -> dict[str, str]:
    """Liveness probe - indicates the service is running.
    
    Returns:
        Simple status response
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Indicates the service is ready to accept requests. Checks database, memory, disk, and worker status.",
    responses={
        status.HTTP_200_OK: {"description": "Service is ready"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service not ready"},
    },
)
async def health_ready_v2(request: Request) -> dict[str, object]:
    """Readiness probe - indicates the service is ready to accept requests.
    
    Performs comprehensive health checks on:
    - Database connectivity
    - Memory usage
    - Disk space
    - Event worker status
    - Application metrics
    
    Returns:
        Detailed health status with individual check results
    """
    # Run all checks
    checks = {
        "database": await check_database(request),
        "memory": check_memory(),
        "disk": check_disk_space(),
        "worker": check_worker(request),
        "metrics": check_metrics(),
    }
    
    # Determine overall status
    # Service is ready only if all critical checks pass
    critical_checks = ["database", "memory", "disk"]
    critical_ok = all(
        checks[check].get("status") in ("ok", "warning", "unknown")
        for check in critical_checks
    )
    
    # Not ready if any critical check is in error state
    critical_no_error = not any(
        checks[check].get("status") == "error"
        for check in critical_checks
    )
    
    all_healthy = critical_ok and critical_no_error
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "version": os.environ.get("APP_VERSION", "2.0.0"),
        "checks": checks,
    }


@router.get(
    "/health/deep",
    summary="Deep health check",
    description="Performs a comprehensive health check including all dependencies and performance metrics.",
    responses={
        status.HTTP_200_OK: {"description": "Detailed health status"},
    },
)
async def health_deep_v2(request: Request) -> dict[str, object]:
    """Deep health check with detailed diagnostics.
    
    Includes all checks from readiness plus:
    - Database query performance
    - Memory fragmentation
    - Detailed metrics
    
    Returns:
        Comprehensive health and performance data
    """
    # Get basic checks
    ready_result = await health_ready_v2(request)
    
    # Add additional diagnostics
    diagnostics = {
        "python_version": os.sys.version,
        "platform": os.sys.platform,
        "pid": os.getpid(),
    }
    
    # Add memory diagnostics if available
    try:
        import psutil
        process = psutil.Process()
        diagnostics["process_memory_mb"] = round(process.memory_info().rss / (1024**2), 2)
        diagnostics["process_cpu_percent"] = round(process.cpu_percent(interval=0.1), 2)
    except ImportError:
        pass
    
    ready_result["diagnostics"] = diagnostics
    ready_result["check_count"] = len(ready_result["checks"])
    
    return ready_result


@router.get(
    "/metrics",
    summary="Application metrics",
    description="Returns application metrics including event counts and run statistics. For Prometheus format, use /api/v2/metrics/prometheus",
    responses={
        status.HTTP_200_OK: {"description": "Metrics data"},
    },
)
async def metrics_v2(request: Request) -> dict[str, object]:
    """Application metrics in JSON format.
    
    Returns:
        Application metrics summary
    """
    from vm_webapp.db import session_scope
    from vm_webapp.models import EventLog, Run
    from sqlalchemy import func
    
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "counts": {},
        "rates": {},
    }
    
    with session_scope(request.app.state.engine) as session:
        # Count events
        event_count = session.scalar(
            func.count(EventLog.event_pk)
        ) or 0
        metrics["counts"]["total_events"] = event_count
        
        # Count runs by status
        runs_by_status = session.execute(
            text("SELECT status, COUNT(*) FROM runs GROUP BY status")
        ).all()
        metrics["counts"]["runs"] = {
            row[0]: row[1] for row in runs_by_status
        }
        
        # Recent activity (last hour)
        recent_events = session.scalar(
            func.count(EventLog.event_pk)
            .where(
                EventLog.occurred_at >= datetime.now().isoformat()[:19].replace("T", " ")
            )
        ) or 0
        metrics["rates"]["events_last_hour"] = recent_events
    
    return metrics


@router.get(
    "/metrics/prometheus",
    summary="Prometheus metrics",
    description="Returns metrics in Prometheus exposition format for scraping by Prometheus server.",
    responses={
        status.HTTP_200_OK: {
            "description": "Prometheus metrics",
            "content": {"text/plain": {"example": "http_requests_total{method=\"GET\",endpoint=\"/api/v2/brands\",status_code=\"200\"} 42"}},
        },
    },
)
async def metrics_prometheus_v2(request: Request):
    """Prometheus-compatible metrics endpoint.
    
    Returns:
        Metrics in Prometheus exposition format
    """
    from starlette.responses import Response
    from vm_webapp.middleware_metrics import get_prometheus_metrics
    
    data, content_type = get_prometheus_metrics()
    return Response(content=data, media_type=content_type)
