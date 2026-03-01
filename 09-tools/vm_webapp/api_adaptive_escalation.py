"""API endpoints for Adaptive Escalation (v21)."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vm_webapp.adaptive_escalation import AdaptiveEscalationEngine

router = APIRouter()

# Global engine instance (will be initialized on first use)
_escalation_engine: Optional[AdaptiveEscalationEngine] = None


def get_escalation_engine() -> AdaptiveEscalationEngine:
    """Get or create the escalation engine singleton."""
    global _escalation_engine
    if _escalation_engine is None:
        _escalation_engine = AdaptiveEscalationEngine()
    return _escalation_engine


class EscalationWindowsRequest(BaseModel):
    """Request for calculating escalation windows."""
    step_id: str
    risk_level: str  # low, medium, high, critical
    approver_id: Optional[str] = None
    pending_count: int = 0
    current_time: Optional[datetime] = None


class EscalationWindowsResponse(BaseModel):
    """Response with escalation windows."""
    windows: List[int]  # Timeout values in seconds for each level
    adaptive_factors: dict


class RecordApprovalRequest(BaseModel):
    """Request to record an approval."""
    approver_id: str
    step_id: str
    response_time_seconds: float


class RecordTimeoutRequest(BaseModel):
    """Request to record a timeout."""
    approver_id: str
    step_id: str


class RecordResponse(BaseModel):
    """Response for record operations."""
    status: str
    approver_id: str


@router.post("/v2/escalation/windows", response_model=EscalationWindowsResponse)
def get_escalation_windows(request: EscalationWindowsRequest):
    """Calculate adaptive escalation windows for a step."""
    engine = get_escalation_engine()
    
    windows = engine.calculate_escalation_windows(
        step_id=request.step_id,
        risk_level=request.risk_level,
        approver_id=request.approver_id,
        pending_count=request.pending_count,
        current_time=request.current_time,
    )
    
    # Calculate adaptive factors for transparency
    factors = {
        "base_timeout": AdaptiveEscalationEngine()._approver_profiles.get(
            request.approver_id or "", None
        ),
        "risk_level": request.risk_level,
        "pending_load": request.pending_count,
    }
    
    return EscalationWindowsResponse(
        windows=windows,
        adaptive_factors=factors,
    )


@router.post("/v2/escalation/approvals", response_model=RecordResponse)
def record_approval(request: RecordApprovalRequest):
    """Record a successful approval for adaptive learning."""
    engine = get_escalation_engine()
    
    engine.record_approval(
        approver_id=request.approver_id,
        step_id=request.step_id,
        response_time_seconds=request.response_time_seconds,
    )
    
    return RecordResponse(
        status="recorded",
        approver_id=request.approver_id,
    )


@router.post("/v2/escalation/timeouts", response_model=RecordResponse)
def record_timeout(request: RecordTimeoutRequest):
    """Record a timeout for adaptive learning."""
    engine = get_escalation_engine()
    
    engine.record_timeout(
        approver_id=request.approver_id,
        step_id=request.step_id,
    )
    
    return RecordResponse(
        status="recorded",
        approver_id=request.approver_id,
    )


@router.get("/v2/escalation/profiles/{approver_id}")
def get_approver_profile(approver_id: str):
    """Get approver profile with historical data."""
    engine = get_escalation_engine()
    profile = engine.get_or_create_profile(approver_id)
    
    return {
        "approver_id": profile.approver_id,
        "avg_response_time_minutes": profile.avg_response_time_minutes,
        "approvals_count": profile.approvals_count,
        "timeouts_count": profile.timeouts_count,
        "timeout_rate": profile.timeout_rate,
        "total_count": profile.total_count,
    }


@router.get("/v2/escalation/metrics")
def get_escalation_metrics():
    """Get escalation engine metrics."""
    engine = get_escalation_engine()
    return engine.get_metrics()
