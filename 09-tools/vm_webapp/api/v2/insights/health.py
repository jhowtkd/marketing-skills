from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request

router = APIRouter(tags=["health", "metrics"])


@router.get("/health/live")
async def health_live_v2(request: Request) -> dict[str, str]:
    """Liveness probe - indicates the service is running."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/ready")
async def health_ready_v2(request: Request) -> dict[str, str | bool]:
    """Readiness probe - indicates the service is ready to accept requests."""
    from vm_webapp.db import session_scope
    
    # Check database connectivity
    db_status = "connected"
    try:
        with session_scope(request.app.state.engine) as session:
            # Simple health check query
            session.execute("SELECT 1")
    except Exception:
        db_status = "disconnected"
    
    is_ready = db_status == "connected"
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/metrics")
async def metrics_v2(request: Request) -> dict[str, object]:
    """Application metrics."""
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
            "SELECT status, COUNT(*) FROM runs GROUP BY status"
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
