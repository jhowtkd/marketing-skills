"""Onboarding Recovery Reactivation API v2 Endpoints.

v34: API endpoints for recovery operations with approval gates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from vm_webapp.onboarding_recovery import (
    DropoffDetector,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryPriority,
)
from vm_webapp.onboarding_recovery_strategy import (
    ReactivationStrategyEngine,
    StrategyType,
)


# Request/Response Models

class SessionInput(BaseModel):
    """Input session data for dropoff detection."""
    user_id: str
    brand_id: Optional[str] = None
    current_step: int = 0
    total_steps: int = 7
    last_activity: Optional[str] = None
    step_start_time: Optional[str] = None
    error_occurred: bool = False
    error_code: Optional[str] = None


class RunRecoveryRequest(BaseModel):
    """Request to run recovery detection and proposal generation."""
    sessions: List[SessionInput] = Field(default_factory=list)


class RunRecoveryResponse(BaseModel):
    """Response from recovery run."""
    brand_id: str
    cases_detected: int
    proposals_generated: int
    auto_applied: int
    pending_approval: int
    run_at: str


class ApplyRecoveryRequest(BaseModel):
    """Request to apply a recovery proposal."""
    applied_by: str
    reason: str


class ApplyRecoveryResponse(BaseModel):
    """Response from apply operation."""
    case_id: str
    status: str  # "applied", "pending_approval", "rejected"
    message: str


class RejectRecoveryRequest(BaseModel):
    """Request to reject a recovery proposal."""
    rejected_by: str
    reason: str


class RejectRecoveryResponse(BaseModel):
    """Response from reject operation."""
    case_id: str
    status: str
    rejected_at: str


class FreezeRecoveryRequest(BaseModel):
    """Request to freeze recovery operations."""
    frozen_by: str
    reason: str


class FreezeRecoveryResponse(BaseModel):
    """Response from freeze operation."""
    brand_id: str
    status: str
    frozen_at: str


class RollbackRecoveryRequest(BaseModel):
    """Request to rollback recovery actions."""
    rolled_back_by: str
    reason: str


class RollbackRecoveryResponse(BaseModel):
    """Response from rollback operation."""
    brand_id: str
    rolled_back_count: int
    rolled_back_at: str


class StatusResponse(BaseModel):
    """Recovery status response."""
    brand_id: str
    state: str
    version: str = "v34"
    frozen: bool
    metrics: Dict[str, Any]
    recoverable_cases: List[Dict[str, Any]]
    pending_approvals: List[Dict[str, Any]]


class CasesListResponse(BaseModel):
    """List of recovery cases."""
    brand_id: str
    cases: List[Dict[str, Any]]
    total: int
    filter_status: Optional[str] = None
    filter_priority: Optional[str] = None


# Global state (in production, use proper database)
_dropoff_detector = DropoffDetector()
_strategy_engine = ReactivationStrategyEngine()
_recovery_metrics: Dict[str, int] = {
    "cases_detected": 0,
    "cases_recovered": 0,
    "cases_expired": 0,
    "proposals_generated": 0,
    "proposals_auto_applied": 0,
    "proposals_approved": 0,
    "proposals_rejected": 0,
}
_pending_approvals: Dict[str, Dict[str, Any]] = {}
_frozen_brands: Dict[str, Dict[str, Any]] = {}


# Router
router = APIRouter(prefix="/api/v2/brands", tags=["onboarding-recovery"])


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


@router.get("/{brand_id}/onboarding-recovery/status", response_model=StatusResponse)
async def get_recovery_status(brand_id: str) -> Dict[str, Any]:
    """Get onboarding recovery status for a brand.
    
    Returns metrics, recoverable cases, and pending approvals.
    """
    # Get all cases for this brand
    brand_cases = _dropoff_detector.get_cases_by_brand(brand_id)
    recoverable = [c for c in brand_cases if c.status == RecoveryCaseStatus.RECOVERABLE]
    
    # Get pending approvals for this brand
    brand_approvals = [
        {**approval, "proposal_id": pid}
        for pid, approval in _pending_approvals.items()
        if approval.get("brand_id") == brand_id
    ]
    
    # Calculate metrics
    metrics = {
        "cases_total": len(brand_cases),
        "cases_recoverable": len(recoverable),
        "cases_recovered": len([c for c in brand_cases if c.status == RecoveryCaseStatus.RECOVERED]),
        "cases_expired": len([c for c in brand_cases if c.status == RecoveryCaseStatus.EXPIRED]),
        **_recovery_metrics,
    }
    
    return {
        "brand_id": brand_id,
        "state": "frozen" if brand_id in _frozen_brands else "active",
        "version": "v34",
        "frozen": brand_id in _frozen_brands,
        "metrics": metrics,
        "recoverable_cases": [c.to_dict() for c in recoverable],
        "pending_approvals": brand_approvals,
    }


@router.post("/{brand_id}/onboarding-recovery/run", response_model=RunRecoveryResponse)
async def run_recovery(brand_id: str, request: RunRecoveryRequest) -> Dict[str, Any]:
    """Run recovery detection and generate proposals.
    
    Detects dropoffs from sessions and generates recovery proposals.
    Low-touch strategies are auto-applied; high-touch require approval.
    """
    if brand_id in _frozen_brands:
        raise HTTPException(status_code=403, detail="Recovery operations frozen for this brand")
    
    cases_detected = 0
    proposals_generated = 0
    auto_applied = 0
    pending_approval = 0
    
    for session_input in request.sessions:
        # Enrich session with brand_id
        session_data = session_input.model_dump()
        session_data["brand_id"] = brand_id
        
        # Detect dropoff
        case = _dropoff_detector.detect_dropoff(session_data)
        if case:
            cases_detected += 1
            _recovery_metrics["cases_detected"] += 1
            
            # Generate proposal
            proposal = _strategy_engine.generate_proposal(case)
            proposals_generated += 1
            _recovery_metrics["proposals_generated"] += 1
            
            if proposal["requires_approval"]:
                # Queue for approval
                proposal_id = f"proposal-{case.case_id}"
                _pending_approvals[proposal_id] = {
                    "brand_id": brand_id,
                    "case_id": case.case_id,
                    "proposal": proposal,
                    "status": "pending_approval",
                    "requested_at": _now_iso(),
                }
                pending_approval += 1
            else:
                # Auto-apply
                auto_applied += 1
                _recovery_metrics["proposals_auto_applied"] += 1
    
    return {
        "brand_id": brand_id,
        "cases_detected": cases_detected,
        "proposals_generated": proposals_generated,
        "auto_applied": auto_applied,
        "pending_approval": pending_approval,
        "run_at": _now_iso(),
    }


@router.get("/{brand_id}/onboarding-recovery/cases", response_model=CasesListResponse)
async def list_recovery_cases(
    brand_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
) -> Dict[str, Any]:
    """List recovery cases for a brand.
    
    Supports filtering by status and priority.
    """
    cases = _dropoff_detector.get_cases_by_brand(brand_id)
    
    # Apply filters
    if status:
        cases = [c for c in cases if c.status.value == status]
    if priority:
        cases = [c for c in cases if c.priority.value == priority]
    
    return {
        "brand_id": brand_id,
        "cases": [c.to_dict() for c in cases],
        "total": len(cases),
        "filter_status": status,
        "filter_priority": priority,
    }


@router.post(
    "/{brand_id}/onboarding-recovery/cases/{case_id}/apply",
    response_model=ApplyRecoveryResponse,
)
async def apply_recovery(
    brand_id: str, case_id: str, request: ApplyRecoveryRequest
) -> Dict[str, Any]:
    """Apply a recovery proposal.
    
    For high-touch strategies, may require approval.
    """
    if brand_id in _frozen_brands:
        raise HTTPException(status_code=403, detail="Recovery operations frozen for this brand")
    
    case = _dropoff_detector.get_case(case_id)
    if not case or case.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Generate proposal to check strategy type
    proposal = _strategy_engine.generate_proposal(case)
    
    if proposal["requires_approval"]:
        # Check if already pending
        proposal_id = f"proposal-{case_id}"
        if proposal_id in _pending_approvals:
            return {
                "case_id": case_id,
                "status": "pending_approval",
                "message": "Proposal is pending approval",
            }
        
        # Queue for approval
        _pending_approvals[proposal_id] = {
            "brand_id": brand_id,
            "case_id": case_id,
            "proposal": proposal,
            "status": "pending_approval",
            "requested_by": request.applied_by,
            "reason": request.reason,
            "requested_at": _now_iso(),
        }
        return {
            "case_id": case_id,
            "status": "pending_approval",
            "message": "Proposal queued for approval",
        }
    
    # Apply immediately
    _dropoff_detector.mark_recovered(case_id)
    _recovery_metrics["proposals_approved"] += 1
    _recovery_metrics["cases_recovered"] += 1
    
    return {
        "case_id": case_id,
        "status": "applied",
        "message": "Recovery strategy applied successfully",
    }


@router.post(
    "/{brand_id}/onboarding-recovery/cases/{case_id}/reject",
    response_model=RejectRecoveryResponse,
)
async def reject_recovery(
    brand_id: str, case_id: str, request: RejectRecoveryRequest
) -> Dict[str, Any]:
    """Reject a recovery proposal."""
    case = _dropoff_detector.get_case(case_id)
    if not case or case.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Remove from pending approvals if exists
    proposal_id = f"proposal-{case_id}"
    if proposal_id in _pending_approvals:
        del _pending_approvals[proposal_id]
    
    _recovery_metrics["proposals_rejected"] += 1
    
    return {
        "case_id": case_id,
        "status": "rejected",
        "rejected_at": _now_iso(),
    }


@router.post("/{brand_id}/onboarding-recovery/freeze", response_model=FreezeRecoveryResponse)
async def freeze_recovery(brand_id: str, request: FreezeRecoveryRequest) -> Dict[str, Any]:
    """Freeze all recovery operations for a brand."""
    _frozen_brands[brand_id] = {
        "frozen_by": request.frozen_by,
        "reason": request.reason,
        "frozen_at": _now_iso(),
    }
    
    return {
        "brand_id": brand_id,
        "status": "frozen",
        "frozen_at": _now_iso(),
    }


@router.post("/{brand_id}/onboarding-recovery/rollback", response_model=RollbackRecoveryResponse)
async def rollback_recovery(
    brand_id: str, request: RollbackRecoveryRequest
) -> Dict[str, Any]:
    """Rollback recovery actions for a brand.
    
    Marks recoverable cases as expired and clears pending approvals.
    """
    # Get brand cases
    brand_cases = _dropoff_detector.get_cases_by_brand(brand_id)
    rolled_back_count = 0
    
    # Mark recoverable cases as expired
    for case in brand_cases:
        if case.status == RecoveryCaseStatus.RECOVERABLE:
            _dropoff_detector.mark_expired(case.case_id)
            rolled_back_count += 1
    
    # Clear pending approvals for this brand
    proposals_to_remove = [
        pid for pid, p in _pending_approvals.items()
        if p.get("brand_id") == brand_id
    ]
    for pid in proposals_to_remove:
        del _pending_approvals[pid]
    
    return {
        "brand_id": brand_id,
        "rolled_back_count": rolled_back_count,
        "rolled_back_at": _now_iso(),
    }
