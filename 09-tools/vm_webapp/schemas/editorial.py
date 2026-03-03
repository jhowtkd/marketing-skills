from __future__ import annotations

from datetime import datetime
from typing import Literal, Any, Optional

from .base import VMBaseModel


class EditorialDecision(VMBaseModel):
    decision_id: str
    thread_id: str
    decision_type: str
    rationale: str
    made_at: datetime
    made_by: str


class EditorialDecisionsListResponse(VMBaseModel):
    decisions: list[EditorialDecision]


class EditorialSLO(VMBaseModel):
    brand_id: str
    max_decisions_per_week: int = 10
    auto_approve_threshold: float = 0.8
    require_approval_above: Optional[float] = None


class EditorialPolicy(VMBaseModel):
    brand_id: str
    policy_json: dict[str, Any]
    version: int = 1


class EditorialInsight(VMBaseModel):
    insight_type: str
    message: str
    severity: Literal["info", "warning", "critical"]
    created_at: datetime


class EditorialInsightsListResponse(VMBaseModel):
    insights: list[EditorialInsight]
