from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from .base import VMBaseModel


class CopilotSuggestion(VMBaseModel):
    suggestion_id: str
    thread_id: str
    suggestion_type: Literal["content", "optimization", "workflow", "policy"]
    title: str
    description: str
    confidence: float = 0.8
    created_at: datetime
    context: dict = {}


class CopilotSuggestionsListResponse(VMBaseModel):
    suggestions: list[CopilotSuggestion]


class CopilotFeedback(VMBaseModel):
    suggestion_id: str
    thread_id: str
    feedback_type: Literal["helpful", "not_helpful", "irrelevant"]
    comment: Optional[str] = None


class CopilotFeedbackResponse(VMBaseModel):
    feedback_id: str
    status: Literal["received", "processed"]
    created_at: datetime
