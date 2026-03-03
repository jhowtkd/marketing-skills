from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Request

from vm_webapp.schemas.optimizer import (
    OptimizerQueueItem,
    OptimizerQueueListResponse,
    OptimizerRequest,
    OptimizerRequestResponse,
)

router = APIRouter(prefix="/optimizer", tags=["optimizer"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get("/queue", response_model=OptimizerQueueListResponse)
async def list_optimizer_queue_v2(
    request: Request,
    brand_id: Optional[str] = None,
) -> OptimizerQueueListResponse:
    """List optimizer queue items."""
    from vm_webapp.db import session_scope
    from vm_webapp.repo import list_runs_by_thread, get_thread_view
    
    items = []
    
    # This is a simplified implementation
    # Real implementation would query a dedicated queue table
    with session_scope(request.app.state.engine) as session:
        # Get runs that are in pending/running status as proxy for queue
        # In a real implementation, this would be a proper queue system
        pass
    
    return OptimizerQueueListResponse(
        items=items,
        total_count=len(items),
        processing_count=sum(1 for i in items if i.status == "processing"),
        queued_count=sum(1 for i in items if i.status == "queued"),
    )


@router.post("/request", response_model=OptimizerRequestResponse)
async def create_optimizer_request_v2(
    data: OptimizerRequest,
    request: Request,
) -> OptimizerRequestResponse:
    """Create a new optimizer request."""
    from vm_webapp.db import session_scope
    from vm_webapp.repo import get_thread_view
    
    request_id = _auto_id("opt")
    
    with session_scope(request.app.state.engine) as session:
        thread = get_thread_view(session, data.thread_id)
        if thread is None:
            raise ValueError(f"Thread not found: {data.thread_id}")
        
        # In a real implementation, this would add to a queue
        # For now, we return a placeholder response
        return OptimizerRequestResponse(
            request_id=request_id,
            status="queued",
            estimated_wait_seconds=data.priority * 10,
            queue_position=1,
        )
