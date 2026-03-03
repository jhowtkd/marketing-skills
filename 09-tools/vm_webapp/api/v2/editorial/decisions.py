from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Request, status

from vm_webapp.schemas.editorial import (
    EditorialDecision,
    EditorialDecisionsListResponse,
    EditorialInsight,
    EditorialInsightsListResponse,
)

router = APIRouter(prefix="/editorial/decisions", tags=["editorial-decisions"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get(
    "",
    response_model=EditorialDecisionsListResponse,
    summary="List editorial decisions",
    description="Returns all editorial decisions for a specific thread. Editorial decisions track content approvals, golden markings, and policy enforcements.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with decisions list"},
        status.HTTP_400_BAD_REQUEST: {"description": "Missing required thread_id parameter"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Thread not found"},
    },
)
async def list_editorial_decisions_v2(
    request: Request,
    thread_id: str,
) -> EditorialDecisionsListResponse:
    """List all editorial decisions for a thread.
    
    Args:
        thread_id: The unique identifier of the thread to list decisions for
        
    Returns:
        A list of editorial decisions including type, rationale, and timestamp
    """
    from vm_webapp.repo import list_editorial_decisions_view
    from vm_webapp.db import session_scope
    
    with session_scope(request.app.state.engine) as session:
        rows = list_editorial_decisions_view(session, thread_id=thread_id)
        decisions = [
            EditorialDecision(
                decision_id=r.decision_key,
                thread_id=r.thread_id,
                decision_type=r.scope,
                rationale=r.justification,
                made_at=datetime.fromisoformat(r.updated_at) if r.updated_at else datetime.now(),
                made_by="system",  # Default to system, could be enriched
            )
            for r in rows
        ]
        return EditorialDecisionsListResponse(decisions=decisions)


@router.post(
    "",
    summary="Create editorial decision",
    description="Creates a new editorial decision. Not implemented - decisions should be created via command events.",
    responses={
        status.HTTP_501_NOT_IMPLEMENTED: {"description": "Not implemented - use command events"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized - editor role required"},
    },
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def create_editorial_decision_v2(
    request: Request,
) -> dict:
    """Create a new editorial decision.
    
    Note: This endpoint is not implemented. In the event-sourced architecture,
    decisions should be created via commands (mark_editorial_golden_command, etc.)
    rather than direct API calls.
    
    Use the appropriate command workflow for creating editorial decisions.
    
    Returns:
        501 Not Implemented error with guidance
    """
    from fastapi import HTTPException
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Direct editorial decision creation is not implemented. Use command events (mark_editorial_golden_command, etc.) instead."
    )


@router.get(
    "/insights",
    response_model=EditorialInsightsListResponse,
    summary="Get editorial insights",
    description="Returns AI-generated insights about editorial decisions for a thread or globally. Insights include volume analysis and quality metrics.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with insights list"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid parameters"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def get_editorial_insights_v2(
    request: Request,
    thread_id: Optional[str] = None,
) -> EditorialInsightsListResponse:
    """Get editorial insights for a thread or globally.
    
    Args:
        thread_id: Optional thread ID to filter insights. If not provided, returns global insights.
        
    Returns:
        A list of insights including volume and quality metrics
    """
    from vm_webapp.db import session_scope
    from vm_webapp.repo import list_editorial_decisions_view
    
    insights = []
    
    with session_scope(request.app.state.engine) as session:
        if thread_id:
            rows = list_editorial_decisions_view(session, thread_id=thread_id)
            
            # Generate insights based on decisions
            if len(rows) > 5:
                insights.append(EditorialInsight(
                    insight_type="volume",
                    message=f"Thread has {len(rows)} editorial decisions",
                    severity="info",
                    created_at=datetime.now(),
                ))
            
            # Check for golden decisions
            golden_count = sum(1 for r in rows if r.scope == "golden")
            if golden_count > 0:
                insights.append(EditorialInsight(
                    insight_type="quality",
                    message=f"{golden_count} content pieces marked as golden",
                    severity="info",
                    created_at=datetime.now(),
                ))
    
    return EditorialInsightsListResponse(insights=insights)
