from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request

router = APIRouter(tags=["health", "metrics"])


@router.get("/health/live")
async def health_live_v2(request: Request) -> dict[str, str]:
    """Liveness probe - indicates the service is running."""
    return {
        "status": "live",
    }


@router.get("/health/ready")
async def health_ready_v2(request: Request) -> dict[str, object]:
    """Readiness probe - indicates the service is ready to accept requests."""
    from vm_webapp.db import session_scope
    
    # Check database connectivity
    db_status = "ok"
    try:
        with session_scope(request.app.state.engine) as session:
            # Simple health check query
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    
    is_ready = db_status == "ok"
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": {
            "database": {
                "status": db_status,
            },
            "worker": {
                "status": "ok",
                "mode": "in_process",
            },
        },
    }


@router.get("/metrics")
async def metrics_v2(request: Request) -> dict[str, object]:
    """Application metrics."""
    from vm_webapp.db import session_scope
    from vm_webapp.models import EventLog, Run
    from sqlalchemy import func, select
    
    # Start from runtime collector snapshot so API-level counters
    # (e.g., copilot_* metrics) are always exposed.
    metrics = request.app.state.workflow_runtime.metrics.snapshot()
    counts = metrics.get("counts")
    if not isinstance(counts, dict):
        counts = {}
    metrics["counts"] = counts
    
    with session_scope(request.app.state.engine) as session:
        # Count events
        event_count = session.scalar(
            select(func.count(EventLog.event_pk))
        ) or 0
        counts["total_events"] = event_count
        
        # Count runs by status
        runs_by_status = session.execute(
            select(Run.status, func.count(Run.run_id)).group_by(Run.status)
        ).all()
        counts["runs"] = {
            row[0]: row[1] for row in runs_by_status
        }
    
    return metrics
