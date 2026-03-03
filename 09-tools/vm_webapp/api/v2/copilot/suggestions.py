from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request

from vm_webapp.schemas.copilot import (
    CopilotSuggestion,
    CopilotSuggestionsListResponse,
    CopilotFeedback,
    CopilotFeedbackResponse,
)

router = APIRouter(prefix="/copilot", tags=["copilot"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get("/suggestions", response_model=CopilotSuggestionsListResponse)
async def get_copilot_suggestions_v2(
    request: Request,
    thread_id: str,
) -> CopilotSuggestionsListResponse:
    """Get AI-powered suggestions for a thread."""
    from vm_webapp.db import session_scope
    from vm_webapp.repo import get_thread_view, list_timeline_items_view
    
    suggestions = []
    
    with session_scope(request.app.state.engine) as session:
        thread = get_thread_view(session, thread_id)
        if thread is None:
            return CopilotSuggestionsListResponse(suggestions=[])
        
        # Analyze thread context to generate suggestions
        timeline = list_timeline_items_view(session, thread_id=thread_id)
        
        # Generate contextual suggestions based on thread state
        if len(timeline) > 3:
            suggestions.append(CopilotSuggestion(
                suggestion_id=_auto_id("sugg"),
                thread_id=thread_id,
                suggestion_type="optimization",
                title="Optimize content flow",
                description="Thread has multiple items. Consider consolidating similar topics.",
                confidence=0.75,
                created_at=datetime.now(),
                context={"item_count": len(timeline)},
            ))
        
        # Suggest workflow based on thread status
        if thread.is_open:
            suggestions.append(CopilotSuggestion(
                suggestion_id=_auto_id("sugg"),
                thread_id=thread_id,
                suggestion_type="workflow",
                title="Complete thread tasks",
                description="Thread has open tasks. Consider reviewing pending items.",
                confidence=0.85,
                created_at=datetime.now(),
                context={"status": "open"},
            ))
    
    return CopilotSuggestionsListResponse(suggestions=suggestions)


@router.post("/feedback", response_model=CopilotFeedbackResponse)
async def submit_copilot_feedback_v2(
    data: CopilotFeedback,
    request: Request,
) -> CopilotFeedbackResponse:
    """Submit feedback on a copilot suggestion."""
    # Placeholder implementation
    # Real implementation would store feedback for model improvement
    
    return CopilotFeedbackResponse(
        feedback_id=_auto_id("feedback"),
        status="received",
        created_at=datetime.now(),
    )
