from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request

from vm_webapp.schemas.editorial import (
    EditorialDecision,
    EditorialDecisionsListResponse,
    EditorialInsight,
    EditorialInsightsListResponse,
)

router = APIRouter(prefix="/editorial/decisions", tags=["editorial-decisions"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get("", response_model=EditorialDecisionsListResponse)
async def list_editorial_decisions_v2(
    request: Request,
    thread_id: str,
) -> EditorialDecisionsListResponse:
    """List all editorial decisions for a thread."""
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


@router.post("", response_model=EditorialDecision)
async def create_editorial_decision_v2(
    request: Request,
) -> EditorialDecision:
    """Create a new editorial decision.
    
    Note: In the event-sourced architecture, decisions are typically
    created via commands. This endpoint provides a simplified interface.
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


@router.get("/insights", response_model=EditorialInsightsListResponse)
async def get_editorial_insights_v2(
    request: Request,
    thread_id: str | None = None,
) -> EditorialInsightsListResponse:
    """Get editorial insights for a thread or globally."""
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
