"""Outcome Attribution and Hybrid ROI API v2 Endpoints.

v36: API endpoints for outcome attribution and hybrid ROI operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from vm_webapp.outcome_attribution import (
    OutcomeAttributionEngine,
    OutcomeType,
    TouchpointType,
    AttributionWindow,
)
from vm_webapp.hybrid_roi_engine import (
    HybridROIEngine,
    ProposalRiskLevel,
    FinancialMetrics,
    OperationalMetrics,
)


# Request/Response Models

class RunOutcomeROIRequest(BaseModel):
    """Request to run outcome attribution and ROI analysis."""
    outcome_type: str = "activation"
    attribution_window_days: int = 30
    auto_apply_low_risk: bool = True
    financial_data: Optional[Dict[str, Any]] = Field(default=None)
    operational_data: Optional[Dict[str, Any]] = Field(default=None)


class RunOutcomeROIResponse(BaseModel):
    """Response from outcome ROI run."""
    brand_id: str
    run_id: str
    outcomes_attributed: int
    proposals_generated: int
    proposals_auto_applied: int
    proposals_needing_approval: int
    proposals_blocked: int
    avg_hybrid_index: float
    run_at: str


class ProposalApplyRequest(BaseModel):
    """Request to apply a proposal."""
    applied_by: str
    note: Optional[str] = None


class ProposalApplyResponse(BaseModel):
    """Response from proposal apply."""
    success: bool
    proposal_id: str
    auto_applied: bool
    applied_at: str


class ProposalRejectRequest(BaseModel):
    """Request to reject a proposal."""
    rejected_by: str
    reason: str


class ProposalRejectResponse(BaseModel):
    """Response from proposal reject."""
    success: bool
    proposal_id: str
    rejected_at: str


class FreezeRequest(BaseModel):
    """Request to freeze ROI operations."""
    frozen_by: str
    reason: str


class FreezeResponse(BaseModel):
    """Response from freeze operation."""
    brand_id: str
    status: str
    frozen_at: str


class RollbackRequest(BaseModel):
    """Request to rollback ROI operations."""
    rolled_back_by: str
    reason: str
    proposal_ids: Optional[List[str]] = Field(default=None)


class RollbackResponse(BaseModel):
    """Response from rollback operation."""
    brand_id: str
    rolled_back_count: int
    rolled_back_at: str


class StatusResponse(BaseModel):
    """Outcome ROI status response."""
    brand_id: str
    state: str
    version: str = "v36"
    frozen: bool
    metrics: Dict[str, Any]
    attribution_summary: Dict[str, Any]


class ProposalsListResponse(BaseModel):
    """List of ROI proposals."""
    brand_id: str
    proposals: List[Dict[str, Any]]
    total: int
    filter_risk_level: Optional[str] = None


class ProposalDetailResponse(BaseModel):
    """Single proposal detail."""
    proposal_id: str
    brand_id: str
    touchpoint_type: str
    action: str
    expected_impact: Dict[str, Any]
    hybrid_index: float
    risk_level: str
    status: str
    score_explanation: str
    created_at: str


class BreakdownResponse(BaseModel):
    """ROI breakdown response."""
    brand_id: str
    attribution_by_touchpoint: Dict[str, Any]
    financial_breakdown: Dict[str, Any]
    operational_breakdown: Dict[str, Any]
    hybrid_roi_summary: Dict[str, Any]


# Global state (in production, use proper database)
_attribution_engine = OutcomeAttributionEngine()
_roi_engine = HybridROIEngine()
_roi_metrics: Dict[str, Any] = {
    "outcomes_attributed": 0,
    "proposals_generated": 0,
    "proposals_auto_applied": 0,
    "proposals_approved": 0,
    "proposals_rejected": 0,
    "proposals_blocked": 0,
    "guardrail_violations": 0,
    "payback_time_avg_days": 0.0,
    "hybrid_roi_index_avg": 0.0,
}
_frozen_brands: Dict[str, Dict[str, Any]] = {}
_pending_proposals: Dict[str, str] = {}  # proposal_id -> brand_id
_applied_proposals: Dict[str, str] = {}  # proposal_id -> brand_id

# Create router
router = APIRouter(prefix="/api/v2/brands", tags=["outcome-roi"])


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _check_frozen(brand_id: str) -> None:
    """Check if brand is frozen and raise exception if so."""
    if brand_id in _frozen_brands:
        raise HTTPException(
            status_code=409,
            detail=f"Brand {brand_id} is frozen: {_frozen_brands[brand_id]['reason']}"
        )


@router.get("/{brand_id}/outcome-roi/status", response_model=StatusResponse)
async def get_outcome_roi_status(brand_id: str) -> Dict[str, Any]:
    """Get outcome attribution and ROI status for a brand."""
    attribution_summary = _attribution_engine.get_attribution_summary(brand_id)
    roi_summary = _roi_engine.get_roi_summary(brand_id)
    
    return {
        "brand_id": brand_id,
        "state": "frozen" if brand_id in _frozen_brands else "active",
        "version": "v36",
        "frozen": brand_id in _frozen_brands,
        "metrics": {
            **_roi_metrics,
            "proposals_pending": len(_pending_proposals),
            "proposals_applied": len(_applied_proposals),
        },
        "attribution_summary": attribution_summary,
        "roi_summary": roi_summary,
    }


@router.post("/{brand_id}/outcome-roi/run", response_model=RunOutcomeROIResponse)
async def run_outcome_roi(
    brand_id: str,
    request: RunOutcomeROIRequest,
) -> Dict[str, Any]:
    """Run outcome attribution and generate ROI proposals."""
    _check_frozen(brand_id)
    
    # Update attribution window if specified
    if request.attribution_window_days != 30:
        _attribution_engine.window = AttributionWindow(days=request.attribution_window_days)
    
    # Record some sample touchpoints for testing
    for i in range(3):
        _attribution_engine.record_touchpoint(
            user_id=f"user_{i}",
            brand_id=brand_id,
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id=f"step_{i}",
            metadata={"step_name": f"step_{i}"},
        )
    
    # Attribute outcomes
    outcomes_attributed = 0
    for outcome_type in [OutcomeType.ACTIVATION, OutcomeType.RECOVERY]:
        for i in range(2):
            _attribution_engine.attribute_outcome(
                user_id=f"user_{i}",
                brand_id=brand_id,
                outcome_type=outcome_type,
                method="linear",
            )
            outcomes_attributed += 1
    
    # Generate proposals
    proposals_generated = 0
    proposals_auto_applied = 0
    proposals_needing_approval = 0
    proposals_blocked = 0
    
    financial_data = request.financial_data or {
        "revenue": 1000.0,
        "cost": 200.0,
        "activations": 10,
        "time_to_revenue_days": 14.0,
    }
    operational_data = request.operational_data or {
        "human_minutes": 300.0,
        "activations": 10,
        "successes": 9,
    }
    
    # Generate sample proposals
    actions = [
        ("increase_priority", {"completion_rate": 0.05}),
        ("reduce_steps", {"human_minutes": -10}),
        ("optimize_flow", {"success_rate": 0.03}),
    ]
    
    for action, impact in actions:
        proposal = _roi_engine.generate_proposal(
            brand_id=brand_id,
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            action=action,
            expected_impact=impact,
            financial_data=financial_data,
            operational_data=operational_data,
        )
        proposals_generated += 1
        _pending_proposals[proposal.proposal_id] = brand_id
        
        # Evaluate proposal
        context = {
            "success_rate": 0.9,
            "incident_rate": 0.01,
            "user_satisfaction": 0.8,
        }
        evaluation = _roi_engine.evaluate_proposal(proposal, context)
        
        if evaluation.blocked:
            proposals_blocked += 1
        elif evaluation.autoapply and request.auto_apply_low_risk:
            proposals_auto_applied += 1
            _applied_proposals[proposal.proposal_id] = brand_id
            proposal.status = "applied"
        elif evaluation.approval_required:
            proposals_needing_approval += 1
    
    # Update metrics
    _roi_metrics["outcomes_attributed"] += outcomes_attributed
    _roi_metrics["proposals_generated"] += proposals_generated
    _roi_metrics["proposals_auto_applied"] += proposals_auto_applied
    
    # Calculate average hybrid index
    roi_summary = _roi_engine.get_roi_summary(brand_id)
    avg_hybrid_index = roi_summary.get("avg_hybrid_index", 0.0)
    _roi_metrics["hybrid_roi_index_avg"] = avg_hybrid_index
    
    return {
        "brand_id": brand_id,
        "run_id": str(datetime.now(timezone.utc).timestamp()),
        "outcomes_attributed": outcomes_attributed,
        "proposals_generated": proposals_generated,
        "proposals_auto_applied": proposals_auto_applied,
        "proposals_needing_approval": proposals_needing_approval,
        "proposals_blocked": proposals_blocked,
        "avg_hybrid_index": avg_hybrid_index,
        "run_at": _now_iso(),
    }


@router.get("/{brand_id}/outcome-roi/proposals", response_model=ProposalsListResponse)
async def list_proposals(
    brand_id: str,
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
) -> Dict[str, Any]:
    """List ROI proposals for a brand."""
    proposals = [
        p for p in _roi_engine.proposals.values()
        if p.brand_id == brand_id
    ]
    
    if risk_level:
        proposals = [
            p for p in proposals
            if p.risk_level.value == risk_level.lower()
        ]
    
    return {
        "brand_id": brand_id,
        "proposals": [p.to_dict() for p in proposals],
        "total": len(proposals),
        "filter_risk_level": risk_level,
    }


@router.get("/{brand_id}/outcome-roi/proposals/{proposal_id}", response_model=ProposalDetailResponse)
async def get_proposal_detail(brand_id: str, proposal_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific proposal."""
    proposal = _roi_engine.proposals.get(proposal_id)
    
    if not proposal or proposal.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return {
        "proposal_id": proposal.proposal_id,
        "brand_id": proposal.brand_id,
        "touchpoint_type": proposal.touchpoint_type.value,
        "action": proposal.action,
        "expected_impact": proposal.expected_impact,
        "hybrid_index": proposal.score.penalized_index,
        "risk_level": proposal.risk_level.value,
        "status": proposal.status,
        "score_explanation": proposal.score.explain(),
        "created_at": proposal.created_at,
    }


@router.get("/{brand_id}/outcome-roi/breakdown", response_model=BreakdownResponse)
async def get_roi_breakdown(brand_id: str) -> Dict[str, Any]:
    """Get detailed ROI breakdown for a brand."""
    attribution_summary = _attribution_engine.get_attribution_summary(brand_id)
    roi_summary = _roi_engine.get_roi_summary(brand_id)
    
    # Get proposals for financial/operational breakdown
    proposals = [
        p for p in _roi_engine.proposals.values()
        if p.brand_id == brand_id
    ]
    
    return {
        "brand_id": brand_id,
        "attribution_by_touchpoint": attribution_summary.get("by_outcome_type", {}),
        "financial_breakdown": {
            "total_proposals": len(proposals),
            "avg_expected_revenue_impact": 0.0,  # Would calculate from proposals
        },
        "operational_breakdown": {
            "total_touchpoints": attribution_summary.get("total_touchpoints", 0),
            "window_days": attribution_summary.get("window_days", 30),
        },
        "hybrid_roi_summary": roi_summary,
    }


@router.post("/{brand_id}/outcome-roi/proposals/{proposal_id}/apply", response_model=ProposalApplyResponse)
async def apply_proposal(
    brand_id: str,
    proposal_id: str,
    request: ProposalApplyRequest,
) -> Dict[str, Any]:
    """Apply a specific proposal."""
    _check_frozen(brand_id)
    
    proposal = _roi_engine.proposals.get(proposal_id)
    
    if not proposal or proposal.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status == "applied":
        raise HTTPException(status_code=409, detail="Proposal already applied")
    
    if proposal.status == "rejected":
        raise HTTPException(status_code=409, detail="Proposal already rejected")
    
    proposal.status = "applied"
    _applied_proposals[proposal_id] = brand_id
    if proposal_id in _pending_proposals:
        del _pending_proposals[proposal_id]
    
    _roi_metrics["proposals_approved"] += 1
    
    return {
        "success": True,
        "proposal_id": proposal_id,
        "auto_applied": False,
        "applied_at": _now_iso(),
    }


@router.post("/{brand_id}/outcome-roi/proposals/{proposal_id}/reject", response_model=ProposalRejectResponse)
async def reject_proposal(
    brand_id: str,
    proposal_id: str,
    request: ProposalRejectRequest,
) -> Dict[str, Any]:
    """Reject a specific proposal."""
    proposal = _roi_engine.proposals.get(proposal_id)
    
    if not proposal or proposal.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status == "applied":
        raise HTTPException(status_code=409, detail="Proposal already applied")
    
    if proposal.status == "rejected":
        raise HTTPException(status_code=409, detail="Proposal already rejected")
    
    proposal.status = "rejected"
    if proposal_id in _pending_proposals:
        del _pending_proposals[proposal_id]
    
    _roi_metrics["proposals_rejected"] += 1
    
    return {
        "success": True,
        "proposal_id": proposal_id,
        "rejected_at": _now_iso(),
    }


@router.post("/{brand_id}/outcome-roi/freeze", response_model=FreezeResponse)
async def freeze_roi_operations(
    brand_id: str,
    request: FreezeRequest,
) -> Dict[str, Any]:
    """Freeze ROI operations for a brand."""
    if brand_id in _frozen_brands:
        raise HTTPException(
            status_code=409,
            detail=f"Brand {brand_id} is already frozen"
        )
    
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


@router.post("/{brand_id}/outcome-roi/rollback", response_model=RollbackResponse)
async def rollback_roi_operations(
    brand_id: str,
    request: RollbackRequest,
) -> Dict[str, Any]:
    """Rollback applied ROI proposals."""
    rolled_back_count = 0
    
    if request.proposal_ids:
        # Rollback specific proposals
        for proposal_id in request.proposal_ids:
            if proposal_id in _applied_proposals:
                proposal = _roi_engine.proposals.get(proposal_id)
                if proposal and proposal.brand_id == brand_id:
                    proposal.status = "rolled_back"
                    del _applied_proposals[proposal_id]
                    rolled_back_count += 1
    else:
        # Rollback all proposals for brand
        proposals_to_rollback = [
            pid for pid, bid in _applied_proposals.items()
            if bid == brand_id
        ]
        for proposal_id in proposals_to_rollback:
            proposal = _roi_engine.proposals.get(proposal_id)
            if proposal:
                proposal.status = "rolled_back"
                del _applied_proposals[proposal_id]
                rolled_back_count += 1
    
    return {
        "brand_id": brand_id,
        "rolled_back_count": rolled_back_count,
        "rolled_back_at": _now_iso(),
    }
