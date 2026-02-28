"""Editorial Copilot API v2 endpoints.

Provides:
- GET /api/v2/threads/{thread_id}/copilot/suggestions - Get phase-based suggestions
- POST /api/v2/threads/{thread_id}/copilot/feedback - Submit feedback on suggestions
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, field_validator

from vm_webapp.db import session_scope
from vm_webapp.editorial_copilot import (
    generate_suggestions,
    record_feedback,
    SuggestionPhase,
    FeedbackAction,
)
from vm_webapp.repo import (
    get_thread_view,
    insert_copilot_suggestion,
    insert_copilot_feedback,
    list_first_run_outcomes,
)

router = APIRouter()


# Valid phase values
VALID_PHASES = {"initial", "refine", "strategy"}
VALID_ACTIONS = {"accepted", "edited", "ignored"}


class CopilotFeedbackRequest(BaseModel):
    """Request model for copilot feedback submission."""
    
    suggestion_id: str
    phase: str
    action: str
    edited_content: str | None = None
    
    @field_validator("phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        if v not in VALID_PHASES:
            raise ValueError(f"phase must be one of: {VALID_PHASES}")
        return v
    
    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_ACTIONS:
            raise ValueError(f"action must be one of: {VALID_ACTIONS}")
        return v


def _convert_outcomes_to_dict(outcomes: list) -> list[dict]:
    """Convert FirstRunOutcomeView objects to dict format for suggestion engine."""
    return [
        {
            "profile": o.profile,
            "mode": o.mode,
            "total_runs": o.total_runs,
            "success_24h_count": o.success_24h_count,
            "success_rate": o.success_24h_count / o.total_runs if o.total_runs > 0 else 0.0,
            "avg_quality_score": o.quality_score,
            "avg_duration_ms": o.duration_ms,
        }
        for o in outcomes
    ]


@router.get("/v2/threads/{thread_id}/copilot/suggestions")
def get_copilot_suggestions(
    thread_id: str,
    request: Request,
    phase: str = "initial",
) -> dict[str, object]:
    """Get editorial copilot suggestions for a specific phase.
    
    Args:
        thread_id: The thread ID
        phase: One of 'initial', 'refine', 'strategy' (default: 'initial')
    
    Returns:
        Suggestions with confidence, reason_codes, why, and expected_impact
    """
    # Validate phase
    if phase not in VALID_PHASES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid phase: {phase}. Must be one of: {VALID_PHASES}"
        )
    
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        context = {
            "thread_id": thread_id,
            "brand_id": thread.brand_id,
            "project_id": thread.project_id,
        }
        
        # Generate suggestions based on phase
        if phase == "initial":
            # Get first-run outcomes for ranking
            outcomes = list_first_run_outcomes(session, thread_id=thread_id)
            outcomes_data = _convert_outcomes_to_dict(outcomes) if outcomes else None
            suggestion = generate_suggestions("initial", context, outcomes=outcomes_data)
        elif phase == "refine":
            # For refine phase, we would get scorecard gaps from quality evaluation
            # For now, return a passive suggestion (no gaps identified)
            suggestion = generate_suggestions("refine", context, scorecard_gaps=[])
        else:  # strategy
            # For strategy phase, we would get risk signals from alerts/forecast
            # For now, return a passive suggestion (no risk signals)
            suggestion = generate_suggestions("strategy", context, risk_signals=[])
        
        # Persist suggestion to read model
        insert_copilot_suggestion(
            session,
            suggestion_id=suggestion.suggestion_id,
            thread_id=thread_id,
            phase=phase,
            content=suggestion.content,
            confidence=suggestion.confidence,
            reason_codes=suggestion.reason_codes,
            why=suggestion.why,
            expected_impact=suggestion.expected_impact,
        )
        
        # Record metric
        request.app.state.workflow_runtime.metrics.record_count("copilot_suggestion_generated_total")
        request.app.state.workflow_runtime.metrics.record_count(f"copilot_suggestion_phase:{phase}")
        
        return {
            "thread_id": thread_id,
            "phase": phase,
            "suggestions": [
                {
                    "suggestion_id": suggestion.suggestion_id,
                    "content": suggestion.content,
                    "confidence": suggestion.confidence,
                    "reason_codes": suggestion.reason_codes,
                    "why": suggestion.why,
                    "expected_impact": suggestion.expected_impact,
                    "created_at": suggestion.created_at,
                }
            ] if suggestion.content else [],  # Only return if has content (not passive)
            "guardrail_applied": suggestion.confidence < 0.4,
        }


@router.post("/v2/threads/{thread_id}/copilot/feedback")
def submit_copilot_feedback(
    thread_id: str,
    request: Request,
    body: CopilotFeedbackRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> dict[str, object]:
    """Submit feedback on a copilot suggestion.
    
    Args:
        thread_id: The thread ID
        body: Feedback request with suggestion_id, phase, action, and optional edited_content
    
    Returns:
        Feedback record confirmation
    """
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        # Create feedback record
        feedback = record_feedback(
            suggestion_id=body.suggestion_id,
            thread_id=thread_id,
            phase=body.phase,  # type: ignore
            action=body.action,  # type: ignore
            edited_content=body.edited_content,
            metadata={"idempotency_key": idempotency_key},
        )
        
        # Persist to read model
        insert_copilot_feedback(
            session,
            feedback_id=feedback.feedback_id,
            suggestion_id=feedback.suggestion_id,
            thread_id=thread_id,
            phase=feedback.phase,
            action=feedback.action,
            edited_content=feedback.edited_content,
            metadata={"idempotency_key": idempotency_key},
        )
        
        # Record metrics
        request.app.state.workflow_runtime.metrics.record_count("copilot_feedback_submitted_total")
        request.app.state.workflow_runtime.metrics.record_count(f"copilot_feedback_action:{body.action}")
        
        return {
            "feedback_id": feedback.feedback_id,
            "suggestion_id": body.suggestion_id,
            "thread_id": thread_id,
            "phase": body.phase,
            "action": body.action,
            "created_at": feedback.created_at,
        }
