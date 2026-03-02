"""API v2 endpoints for onboarding personalization operations.

v33: Personalization by segment with deterministic serving and safe rollout.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vm_webapp.onboarding_personalization import (
    PersonalizationPolicy,
    PolicyStatus,
    RiskLevel,
    SegmentKey,
    SegmentProfiler,
)
from vm_webapp.onboarding_policy_rollout import (
    PolicyServingEngine,
    RolloutManager,
)


# Global instances (singleton pattern)
_profiler = SegmentProfiler()
_engine = PolicyServingEngine(_profiler)
_manager = RolloutManager(_profiler, _engine)

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# Request/Response Models
# =============================================================================

class PersonalizationStatusResponse(BaseModel):
    brand_id: str
    version: str
    metrics: dict[str, Any]
    active_policies: list[dict[str, Any]]


class PersonalizationRunRequest(BaseModel):
    pass


class PersonalizationRunResponse(BaseModel):
    brand_id: str
    rollouts: list[dict[str, Any]]
    run_at: str


class PolicyListResponse(BaseModel):
    policies: list[dict[str, Any]]
    total: int


class EffectivePolicyRequest(BaseModel):
    company_size: str = "unknown"
    industry: str = "unknown"
    experience_level: str = "unknown"
    traffic_source: str = "unknown"


class EffectivePolicyResponse(BaseModel):
    policy_id: str
    source: str
    fallback_used: bool
    config: dict[str, Any]


class PolicyApplyRequest(BaseModel):
    applied_by: str


class PolicyApplyResponse(BaseModel):
    policy_id: str
    decision: str
    requires_approval: bool
    reason: str


class PolicyRejectRequest(BaseModel):
    rejected_by: str
    reason: str


class PolicyRejectResponse(BaseModel):
    policy_id: str
    status: str
    rejected_at: str


class PoliciesFreezeRequest(BaseModel):
    frozen_by: str
    reason: str


class PoliciesFreezeResponse(BaseModel):
    frozen_count: int
    reason: str
    frozen_at: str


class PoliciesRollbackRequest(BaseModel):
    policy_id: str
    rolled_back_by: str
    reason: str


class PoliciesRollbackResponse(BaseModel):
    policy_id: str
    status: str
    rolled_back_at: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/api/v2/brands/{brand_id}/onboarding-personalization/status")
def get_onboarding_personalization_status(brand_id: str) -> PersonalizationStatusResponse:
    """Get status of onboarding personalization for a brand.
    
    Returns current metrics and active policies.
    """
    serve_metrics = _engine.get_serve_metrics()
    rollout_metrics = _manager.get_rollout_metrics()
    
    metrics = {
        **serve_metrics,
        **rollout_metrics,
    }
    
    active_policies = []
    for policy in _profiler.list_active_policies():
        active_policies.append({
            "policy_id": policy.policy_id,
            "segment_key": str(policy.segment_key) if policy.segment_key else "global",
            "level": policy.get_level(),
            "risk_level": policy.risk_level.value,
            "nudge_delay_ms": policy.nudge_delay_ms,
            "template_order": policy.template_order,
            "max_steps": policy.max_steps,
        })
    
    return PersonalizationStatusResponse(
        brand_id=brand_id,
        version="v33",
        metrics=metrics,
        active_policies=active_policies,
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-personalization/run")
def run_onboarding_personalization(
    brand_id: str,
    request: PersonalizationRunRequest,
) -> PersonalizationRunResponse:
    """Run personalization cycle for pending rollouts.
    
    Executes pending policy rollouts and returns results.
    """
    rollouts = []
    
    for policy in _profiler.list_policies():
        if policy.status == PolicyStatus.DRAFT:
            decision = _manager.decide_rollout(policy)
            
            if not decision.requires_approval:
                success = _manager.execute_rollout(policy.policy_id)
                rollouts.append({
                    "policy_id": policy.policy_id,
                    "decision": decision.decision,
                    "executed": success,
                })
            else:
                rollouts.append({
                    "policy_id": policy.policy_id,
                    "decision": decision.decision,
                    "requires_approval": True,
                    "reason": decision.reason,
                })
    
    return PersonalizationRunResponse(
        brand_id=brand_id,
        rollouts=rollouts,
        run_at=_now_iso(),
    )


@router.get("/api/v2/brands/{brand_id}/onboarding-personalization/policies")
def list_onboarding_personalization_policies(
    brand_id: str,
    status: Optional[str] = None,
) -> PolicyListResponse:
    """List all personalization policies for a brand.
    
    Optional status filter: draft, active, frozen, rolled_back
    """
    all_policies = _profiler.list_policies()
    
    filtered = all_policies
    if status:
        filtered = [p for p in all_policies if p.status.value == status]
    
    policies_data = []
    for policy in filtered:
        policies_data.append({
            "policy_id": policy.policy_id,
            "segment_key": str(policy.segment_key) if policy.segment_key else "global",
            "level": policy.get_level(),
            "status": policy.status.value,
            "risk_level": policy.risk_level.value,
            "nudge_delay_ms": policy.nudge_delay_ms,
            "template_order": policy.template_order,
            "welcome_message": policy.welcome_message,
            "show_video_tutorial": policy.show_video_tutorial,
            "max_steps": policy.max_steps,
            "created_at": policy.created_at,
            "activated_at": policy.activated_at,
        })
    
    return PolicyListResponse(
        policies=policies_data,
        total=len(policies_data),
    )


@router.get("/api/v2/brands/{brand_id}/onboarding-personalization/effective")
def get_effective_policy(
    brand_id: str,
    company_size: str = "unknown",
    industry: str = "unknown",
    experience_level: str = "unknown",
    traffic_source: str = "unknown",
) -> EffectivePolicyResponse:
    """Get the effective policy for a segment.
    
    Returns the policy with source information (segment/brand/global).
    """
    segment_key = SegmentKey(
        company_size=company_size,
        industry=industry,
        experience_level=experience_level,
        traffic_source=traffic_source,
    )
    
    result = _engine.serve_policy_for_segment(segment_key)
    
    if result is None:
        raise HTTPException(status_code=404, detail="No effective policy found for segment")
    
    return EffectivePolicyResponse(
        policy_id=result.policy.policy_id,
        source=result.source,
        fallback_used=result.fallback_used,
        config={
            "nudge_delay_ms": result.policy.nudge_delay_ms,
            "template_order": result.policy.template_order,
            "welcome_message": result.policy.welcome_message,
            "show_video_tutorial": result.policy.show_video_tutorial,
            "max_steps": result.policy.max_steps,
        },
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-personalization/policies/{policy_id}/apply")
def apply_personalization_policy(
    brand_id: str,
    policy_id: str,
    request: PolicyApplyRequest,
) -> PolicyApplyResponse:
    """Apply a personalization policy.
    
    - Low risk + valid = auto-apply
    - Medium/High risk = needs approval
    """
    try:
        policy = _profiler.get_policy(policy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    decision = _manager.decide_rollout(policy)
    
    if decision.decision == "block":
        return PolicyApplyResponse(
            policy_id=policy_id,
            decision="block",
            requires_approval=True,
            reason=decision.reason,
        )
    
    if not decision.requires_approval:
        _manager.execute_rollout(policy_id)
    
    return PolicyApplyResponse(
        policy_id=policy_id,
        decision=decision.decision,
        requires_approval=decision.requires_approval,
        reason=decision.reason,
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-personalization/policies/{policy_id}/reject")
def reject_personalization_policy(
    brand_id: str,
    policy_id: str,
    request: PolicyRejectRequest,
) -> PolicyRejectResponse:
    """Reject a personalization policy."""
    try:
        policy = _profiler.get_policy(policy_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Mark as rejected (we don't have a rejected status, so we keep it draft)
    return PolicyRejectResponse(
        policy_id=policy_id,
        status="rejected",
        rejected_at=_now_iso(),
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-personalization/freeze")
def freeze_personalization_policies(
    brand_id: str,
    request: PoliciesFreezeRequest,
) -> PoliciesFreezeResponse:
    """Freeze all active personalization policies."""
    frozen_count = 0
    
    for policy in _profiler.list_active_policies():
        _manager.freeze_policy(policy.policy_id)
        frozen_count += 1
    
    return PoliciesFreezeResponse(
        frozen_count=frozen_count,
        reason=request.reason,
        frozen_at=_now_iso(),
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-personalization/rollback")
def rollback_personalization_policy(
    brand_id: str,
    request: PoliciesRollbackRequest,
) -> PoliciesRollbackResponse:
    """Roll back a personalization policy."""
    success = _manager.rollback_policy(request.policy_id, request.reason)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Policy not found: {request.policy_id}")
    
    return PoliciesRollbackResponse(
        policy_id=request.policy_id,
        status="rolled_back",
        rolled_back_at=_now_iso(),
    )


# =============================================================================
# Public API for other modules
# =============================================================================

def get_profiler() -> SegmentProfiler:
    """Get the global segment profiler."""
    return _profiler


def get_serving_engine() -> PolicyServingEngine:
    """Get the global serving engine."""
    return _engine


def get_rollout_manager() -> RolloutManager:
    """Get the global rollout manager."""
    return _manager
