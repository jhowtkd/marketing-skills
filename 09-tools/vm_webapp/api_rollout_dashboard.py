"""API v2 endpoints for Rollout Dashboard operations.

v46: Rollout Dashboard + Approval UX
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from vm_webapp.onboarding_rollout_policy import (
    BenchmarkMetrics,
    RolloutMode,
    RolloutPolicy,
    evaluate_promotion,
    evaluate_rollback,
    get_telemetry_logs,
    list_active_policies,
    load_policy,
    rollback,
    save_policy,
)

router = APIRouter()


def _now_iso() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _get_policy_status(policy: RolloutPolicy) -> str:
    """Determine policy status based on active variant and mode."""
    if policy.active_variant == "control":
        if policy.decision_reason and "rollback" in policy.decision_reason.lower():
            return "rolled_back"
        if policy.decision_reason and "rejected" in policy.decision_reason.lower():
            return "blocked"
        return "evaluating"
    else:
        # Check if we have approval pending (manual mode with non-control variant)
        if policy.rollout_mode == RolloutMode.MANUAL and not policy.last_evaluation:
            return "pending_review"
        return "promoted"


def _get_policy_metrics(policy: RolloutPolicy) -> dict[str, Any]:
    """Get metrics for a policy (placeholder for actual metrics integration)."""
    # In production, this would query actual metrics from analytics
    return {
        "experiment_id": policy.experiment_id,
        "active_variant": policy.active_variant,
        "variant_traffic": 100 if policy.active_variant != "control" else 0,
        "control_traffic": 0 if policy.active_variant != "control" else 100,
        "last_updated": policy.last_evaluation,
    }


def _get_policy_timeline(policy: RolloutPolicy) -> list[dict[str, Any]]:
    """Get timeline of policy decisions."""
    timeline = []
    
    # Get telemetry logs for this experiment
    logs = get_telemetry_logs(limit=50)
    
    for log in logs:
        if log.get("experiment_id") == policy.experiment_id or (
            log.get("type") == "promotion" and log.get("variant_id")
        ):
            event = {
                "timestamp": log.get("timestamp", _now_iso()),
                "type": log.get("type", "unknown"),
                "details": log.get("reason", ""),
            }
            if log.get("variant_id"):
                event["variant_id"] = log.get("variant_id")
            if log.get("success") is not None:
                event["success"] = log.get("success")
            timeline.append(event)
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return timeline


# =============================================================================
# Request/Response Models
# =============================================================================

class RolloutPolicyResponse(BaseModel):
    """Response model for rollout policy."""
    experiment_id: str
    active_variant: str
    mode: str  # AUTO, MANUAL, SUPERVISED
    status: str  # promoted, blocked, rolled_back, pending_review, evaluating
    last_evaluation_at: Optional[str] = None
    decision_reason: str
    rollback_target: str
    can_rollback: bool
    timeline: list[dict[str, Any]]
    metrics: dict[str, Any]


class ApproveRequest(BaseModel):
    """Request model for approving promotion."""
    operator_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=10)
    variant: Optional[str] = None

    @field_validator("operator_id")
    @classmethod
    def validate_operator_id(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("operator_id is required")
        return v.strip()

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("reason must be at least 10 characters")
        return v.strip()


class RejectRequest(BaseModel):
    """Request model for rejecting promotion."""
    operator_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=10)

    @field_validator("operator_id")
    @classmethod
    def validate_operator_id(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("operator_id is required")
        return v.strip()

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("reason must be at least 10 characters")
        return v.strip()


class RollbackRequest(BaseModel):
    """Request model for manual rollback."""
    operator_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=10)

    @field_validator("operator_id")
    @classmethod
    def validate_operator_id(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("operator_id is required")
        return v.strip()

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("reason must be at least 10 characters")
        return v.strip()


class ActionResponse(BaseModel):
    """Response model for action endpoints."""
    success: bool
    new_status: str
    timestamp: str
    message: Optional[str] = None


class DashboardResponse(BaseModel):
    """Response model for dashboard."""
    policies: list[RolloutPolicyResponse]
    total_count: int
    promoted_count: int
    evaluating_count: int
    rolled_back_count: int
    pending_review_count: int


class HistoryResponse(BaseModel):
    """Response model for policy history."""
    experiment_id: str
    timeline: list[dict[str, Any]]
    total_events: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/api/v2/onboarding/rollout-dashboard")
def get_rollout_dashboard() -> DashboardResponse:
    """Get all rollout policies for dashboard.
    
    Returns a comprehensive view of all rollout policies including:
    - Current status of each experiment
    - Active variant
    - Decision history
    - Metrics snapshot
    """
    policies = list_active_policies()
    
    # If no policies exist, return empty dashboard
    if not policies:
        return DashboardResponse(
            policies=[],
            total_count=0,
            promoted_count=0,
            evaluating_count=0,
            rolled_back_count=0,
            pending_review_count=0,
        )
    
    policy_responses = []
    status_counts = {
        "promoted": 0,
        "evaluating": 0,
        "rolled_back": 0,
        "pending_review": 0,
        "blocked": 0,
    }
    
    for policy in policies:
        policy_status = _get_policy_status(policy)
        status_counts[policy_status] = status_counts.get(policy_status, 0) + 1
        
        can_rollback = (
            policy.active_variant != "control" and 
            policy.active_variant != policy.rollback_target
        )
        
        policy_responses.append(RolloutPolicyResponse(
            experiment_id=policy.experiment_id,
            active_variant=policy.active_variant,
            mode=policy.rollout_mode.value.upper(),
            status=policy_status,
            last_evaluation_at=policy.last_evaluation,
            decision_reason=policy.decision_reason or "No evaluation yet",
            rollback_target=policy.rollback_target,
            can_rollback=can_rollback,
            timeline=_get_policy_timeline(policy),
            metrics=_get_policy_metrics(policy),
        ))
    
    return DashboardResponse(
        policies=policy_responses,
        total_count=len(policies),
        promoted_count=status_counts.get("promoted", 0),
        evaluating_count=status_counts.get("evaluating", 0),
        rolled_back_count=status_counts.get("rolled_back", 0),
        pending_review_count=status_counts.get("pending_review", 0),
    )


@router.post("/api/v2/onboarding/rollout-policy/{experiment_id}/approve")
def approve_promotion(experiment_id: str, request: ApproveRequest) -> ActionResponse:
    """Manually approve promotion of a variant.
    
    This endpoint is used in SUPERVISED or MANUAL mode to approve
    the promotion of a variant to production traffic.
    
    Args:
        experiment_id: ID of the experiment
        request: Approval request with operator_id and reason
        
    Returns:
        ActionResponse with success status and new policy status
    """
    policy = load_policy(experiment_id)
    
    # Determine variant to promote
    variant_to_promote = request.variant or "variant-a"
    if request.variant:
        variant_to_promote = request.variant
    elif policy.active_variant != "control":
        variant_to_promote = policy.active_variant
    
    # Update policy
    policy.active_variant = variant_to_promote
    policy.rollout_mode = RolloutMode.AUTO  # After approval, switch to auto
    policy.last_evaluation = _now_iso()
    policy.decision_reason = (
        f"Manually approved by {request.operator_id}: {request.reason}"
    )
    
    save_policy(policy)
    
    return ActionResponse(
        success=True,
        new_status=_get_policy_status(policy),
        timestamp=_now_iso(),
        message=f"Variant '{variant_to_promote}' promoted to 100% traffic",
    )


@router.post("/api/v2/onboarding/rollout-policy/{experiment_id}/reject")
def reject_promotion(experiment_id: str, request: RejectRequest) -> ActionResponse:
    """Manually reject promotion of a variant.
    
    This endpoint is used in SUPERVISED or MANUAL mode to reject
    the promotion and keep or rollback to control.
    
    Args:
        experiment_id: ID of the experiment
        request: Rejection request with operator_id and reason
        
    Returns:
        ActionResponse with success status and new policy status
    """
    policy = load_policy(experiment_id)
    
    # Revert to control
    previous_variant = policy.active_variant
    policy.active_variant = "control"
    policy.last_evaluation = _now_iso()
    policy.decision_reason = (
        f"Promotion rejected by {request.operator_id}: {request.reason}"
    )
    
    save_policy(policy)
    
    return ActionResponse(
        success=True,
        new_status="blocked",
        timestamp=_now_iso(),
        message=f"Promotion rejected. Rolled back from '{previous_variant}' to 'control'",
    )


@router.post("/api/v2/onboarding/rollout-policy/{experiment_id}/rollback")
def manual_rollback(experiment_id: str, request: RollbackRequest) -> ActionResponse:
    """Manually rollback to control variant.
    
    This endpoint allows operators to manually trigger a rollback
    when they detect issues or want to revert to the control variant.
    
    Args:
        experiment_id: ID of the experiment
        request: Rollback request with operator_id and reason
        
    Returns:
        ActionResponse with success status and new policy status
    """
    policy = load_policy(experiment_id)
    
    # Check if already on control
    if policy.active_variant == "control":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already on control variant, no rollback needed",
        )
    
    # Execute rollback
    rollback_reason = f"Manual rollback by {request.operator_id}: {request.reason}"
    updated_policy = rollback(experiment_id, reason=rollback_reason)
    
    return ActionResponse(
        success=True,
        new_status="rolled_back",
        timestamp=_now_iso(),
        message=f"Rolled back to '{updated_policy.rollback_target}'",
    )


@router.get("/api/v2/onboarding/rollout-policy/{experiment_id}/history")
def get_policy_history(experiment_id: str) -> HistoryResponse:
    """Get decision history for an experiment.
    
    Returns a timeline of all decisions (promotions, rollbacks, etc.)
    for the specified experiment.
    
    Args:
        experiment_id: ID of the experiment
        
    Returns:
        HistoryResponse with timeline of events
    """
    policy = load_policy(experiment_id)
    
    timeline = _get_policy_timeline(policy)
    
    # Add current state as first event
    current_event = {
        "timestamp": policy.last_evaluation or _now_iso(),
        "type": "current_state",
        "active_variant": policy.active_variant,
        "mode": policy.rollout_mode.value,
        "reason": policy.decision_reason or "Initial state",
    }
    timeline.insert(0, current_event)
    
    return HistoryResponse(
        experiment_id=experiment_id,
        timeline=timeline,
        total_events=len(timeline),
    )


# =============================================================================
# Additional Utility Endpoints
# =============================================================================

@router.get("/api/v2/onboarding/rollout-policy/{experiment_id}")
def get_rollout_policy(experiment_id: str) -> RolloutPolicyResponse:
    """Get detailed information about a specific rollout policy.
    
    Args:
        experiment_id: ID of the experiment
        
    Returns:
        RolloutPolicyResponse with full policy details
    """
    policy = load_policy(experiment_id)
    
    can_rollback = (
        policy.active_variant != "control" and 
        policy.active_variant != policy.rollback_target
    )
    
    return RolloutPolicyResponse(
        experiment_id=policy.experiment_id,
        active_variant=policy.active_variant,
        mode=policy.rollout_mode.value.upper(),
        status=_get_policy_status(policy),
        last_evaluation_at=policy.last_evaluation,
        decision_reason=policy.decision_reason or "No evaluation yet",
        rollback_target=policy.rollback_target,
        can_rollback=can_rollback,
        timeline=_get_policy_timeline(policy),
        metrics=_get_policy_metrics(policy),
    )


@router.post("/api/v2/onboarding/rollout-policy/{experiment_id}/evaluate")
def evaluate_policy(
    experiment_id: str,
    benchmark_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Trigger evaluation of a rollout policy with optional benchmark data.
    
    This endpoint allows triggering an evaluation cycle for the policy,
    optionally providing benchmark metrics data.
    
    Args:
        experiment_id: ID of the experiment
        benchmark_data: Optional benchmark metrics for evaluation
        
    Returns:
        Evaluation result with promotion or rollback decision
    """
    policy = load_policy(experiment_id)
    
    # If benchmark data provided, run evaluation
    if benchmark_data:
        # Convert benchmark data to BenchmarkMetrics
        benchmark_metrics = {}
        for variant_id, metrics in benchmark_data.items():
            benchmark_metrics[variant_id] = BenchmarkMetrics(
                ttfv=metrics.get("ttfv", 120.0),
                completion_rate=metrics.get("completion_rate", 0.75),
                abandonment_rate=metrics.get("abandonment_rate", 0.15),
                score=metrics.get("score", 0.80),
                sample_size=metrics.get("sample_size", 100),
            )
        
        if policy.active_variant == "control":
            # Evaluate promotion
            result = evaluate_promotion(experiment_id, benchmark_metrics)
            return {
                "experiment_id": experiment_id,
                "type": "promotion_evaluation",
                "can_promote": result.success,
                "variant_id": result.variant_id,
                "gates_passed": result.gates_passed,
                "gates_failed": result.gates_failed,
                "reason": result.reason,
            }
        else:
            # Evaluate rollback
            result = evaluate_rollback(policy, benchmark_metrics)
            return {
                "experiment_id": experiment_id,
                "type": "rollback_evaluation",
                "should_rollback": result.should_rollback,
                "from_variant": result.from_variant,
                "to_variant": result.to_variant,
                "reason": result.reason,
            }
    
    # No benchmark data, return current policy status
    return {
        "experiment_id": experiment_id,
        "type": "status",
        "active_variant": policy.active_variant,
        "mode": policy.rollout_mode.value,
        "status": _get_policy_status(policy),
        "last_evaluation": policy.last_evaluation,
    }
