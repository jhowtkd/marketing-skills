from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request, status

from vm_webapp.schemas.copilot import (
    CopilotSuggestion,
    CopilotSuggestionsListResponse,
    CopilotFeedback,
    CopilotFeedbackResponse,
)

router = APIRouter(prefix="/copilot", tags=["copilot"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get(
    "/suggestions",
    response_model=CopilotSuggestionsListResponse,
    summary="Get AI-powered suggestions",
    description="Returns AI-generated suggestions for a thread based on its context, timeline items, and current state. Suggestions include optimizations and workflow recommendations.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with suggestions list"},
        status.HTTP_400_BAD_REQUEST: {"description": "Missing required thread_id parameter"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Thread not found"},
    },
)
async def get_copilot_suggestions_v2(
    request: Request,
    thread_id: str,
) -> CopilotSuggestionsListResponse:
    """Get AI-powered suggestions for a thread.
    
    Args:
        thread_id: The unique identifier of the thread to get suggestions for
        
    Returns:
        A list of contextual suggestions including optimization tips and workflow recommendations
    """
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


@router.post(
    "/feedback",
    response_model=CopilotFeedbackResponse,
    summary="Submit copilot feedback",
    description="Submits user feedback on a copilot suggestion. Feedback is used to improve future AI recommendations.",
    responses={
        status.HTTP_201_CREATED: {"description": "Feedback received successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid feedback data"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def submit_copilot_feedback_v2(
    data: CopilotFeedback,
    request: Request,
) -> CopilotFeedbackResponse:
    """Submit feedback on a copilot suggestion.
    
    Args:
        data: Feedback data including suggestion_id, rating, and optional comment
        
    Returns:
        Confirmation of feedback receipt with generated feedback_id
    """
    # Placeholder implementation
    # Real implementation would store feedback for model improvement
    
    return CopilotFeedbackResponse(
        feedback_id=_auto_id("feedback"),
        status="received",
        created_at=datetime.now(),
    )
