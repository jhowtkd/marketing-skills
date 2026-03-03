from __future__ import annotations

from datetime import datetime
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
    response_model=EditorialDecision,
    summary="Create editorial decision",
    description="Creates a new editorial decision. In the event-sourced architecture, decisions are typically created via commands. This endpoint provides a simplified interface for manual decisions.",
    responses={
        status.HTTP_201_CREATED: {"description": "Decision created successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid decision data"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized - editor role required"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden - insufficient permissions"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_editorial_decision_v2(
    request: Request,
) -> EditorialDecision:
    """Create a new editorial decision.
    
    Note: In the event-sourced architecture, decisions are typically
    created via commands. This endpoint provides a simplified interface.
    
    Requires editor or admin role.
    
    Returns:
        The newly created editorial decision
    """
    from vm_webapp.db import session_scope
    
    # Placeholder implementation
    # Real implementation would use mark_editorial_golden_command or similar
    decision_id = _auto_id("dec")
    
    return EditorialDecision(
        decision_id=decision_id,
        thread_id="placeholder",
        decision_type="manual",
        rationale="Created via API",
        made_at=datetime.now(),
        made_by="api",
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
    thread_id: str | None = None,
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
