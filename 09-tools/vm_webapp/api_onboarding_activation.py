"""v31 Onboarding Activation API endpoints for learning loop operations."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from vm_webapp.onboarding_activation import (
    OnboardingActivationEngine,
    RiskLevel,
    ProposalStatus,
)

router = APIRouter()

# Shared engine instance (in production, use dependency injection)
_engine = OnboardingActivationEngine()

# In-memory metrics store (in production, use database)
_brand_metrics: Dict[str, dict] = {}


# Pydantic models
class ProposalResponse(BaseModel):
    id: str
    rule_name: str
    description: str
    risk_level: str
    current_value: float
    target_value: float
    adjustment_percent: float
    expected_impact: str
    status: str
    brand_id: Optional[str]
    created_at: str


class StatusResponse(BaseModel):
    brand_id: str
    metrics: dict
    top_frictions: List[dict]
    active_proposals_count: int
    frozen: bool


class RunResponse(BaseModel):
    brand_id: str
    proposals_generated: int
    proposals: List[ProposalResponse]
    frozen: bool = False


class ProposalsListResponse(BaseModel):
    proposals: List[ProposalResponse]


class ApplyResponse(BaseModel):
    proposal_id: str
    status: str
    auto_applied: bool = False


class RejectRequest(BaseModel):
    reason: str = ""


class RejectResponse(BaseModel):
    proposal_id: str
    status: str
    reason: str


class FreezeResponse(BaseModel):
    brand_id: str
    frozen: bool
    frozen_at: str


class RollbackResponse(BaseModel):
    brand_id: str
    proposal_id: Optional[str]
    rolled_back: bool
    rolled_back_at: str


def _get_mock_metrics(brand_id: str) -> dict:
    """Get mock metrics for a brand (in production, fetch from DB)."""
    if brand_id not in _brand_metrics:
        # Generate some realistic mock metrics
        import random
        _brand_metrics[brand_id] = {
            "completion_rate": round(random.uniform(0.30, 0.70), 2),
            "step_1_dropoff_rate": round(random.uniform(0.20, 0.50), 2),
            "template_to_first_run_conversion": round(random.uniform(0.30, 0.60), 2),
            "average_time_to_first_action_ms": random.randint(60000, 180000),
            "total_abandons": random.randint(20, 100),
            "abandon_by_step": {
                "workspace_setup": random.randint(10, 40),
                "template_selection": random.randint(5, 20),
                "customization": random.randint(3, 15),
            },
            "abandon_reasons": {
                "too_complex": random.randint(5, 25),
                "no_relevant_templates": random.randint(3, 15),
                "interruption": random.randint(2, 10),
            },
        }
    return _brand_metrics[brand_id]


@router.get("/status", response_model=StatusResponse)
async def get_activation_status(brand_id: str) -> StatusResponse:
    """Get onboarding activation status for a brand."""
    metrics = _get_mock_metrics(brand_id)
    
    # Get top frictions
    top_frictions = _engine.identify_top_frictions(brand_id, metrics)
    
    # Count active proposals
    all_proposals = _engine.get_proposals(brand_id)
    active_count = len([p for p in all_proposals if p["status"] == "pending"])
    
    # Check if frozen
    frozen = brand_id in _engine._frozen_brands
    
    return StatusResponse(
        brand_id=brand_id,
        metrics=metrics,
        top_frictions=top_frictions,
        active_proposals_count=active_count,
        frozen=frozen,
    )


@router.post("/run", response_model=RunResponse)
async def run_activation(brand_id: str) -> RunResponse:
    """Run the activation engine to generate proposals."""
    metrics = _get_mock_metrics(brand_id)
    
    # Check if frozen
    if brand_id in _engine._frozen_brands:
        return RunResponse(
            brand_id=brand_id,
            proposals_generated=0,
            proposals=[],
            frozen=True,
        )
    
    # Generate proposals
    proposals = _engine.evaluate_rules(brand_id, metrics)
    
    # Auto-apply low-risk proposals
    for proposal in proposals:
        if proposal["risk_level"] == RiskLevel.LOW.value:
            _engine.apply_proposal(brand_id, proposal["id"])
    
    # Refresh proposals to get updated statuses
    proposals = _engine.get_proposals(brand_id)
    
    return RunResponse(
        brand_id=brand_id,
        proposals_generated=len(proposals),
        proposals=[ProposalResponse(**p) for p in proposals],
    )


@router.get("/proposals", response_model=ProposalsListResponse)
async def get_proposals(
    brand_id: str,
    status: Optional[str] = Query(None, description="Filter by status: pending, applied, rejected")
) -> ProposalsListResponse:
    """Get proposals for a brand."""
    proposals = _engine.get_proposals(brand_id, status=status)
    return ProposalsListResponse(proposals=[ProposalResponse(**p) for p in proposals])


@router.post("/proposals/{proposal_id}/apply", response_model=ApplyResponse)
async def apply_proposal(brand_id: str, proposal_id: str) -> ApplyResponse:
    """Apply a proposal."""
    result = _engine.apply_proposal(brand_id, proposal_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return ApplyResponse(
        proposal_id=proposal_id,
        status=result["status"],
        auto_applied=result.get("auto_applied", False),
    )


@router.post("/proposals/{proposal_id}/reject", response_model=RejectResponse)
async def reject_proposal(
    brand_id: str,
    proposal_id: str,
    request: RejectRequest
) -> RejectResponse:
    """Reject a proposal."""
    result = _engine.reject_proposal(brand_id, proposal_id, request.reason)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return RejectResponse(
        proposal_id=proposal_id,
        status=result["status"],
        reason=request.reason,
    )


@router.post("/freeze", response_model=FreezeResponse)
async def freeze_proposals(brand_id: str) -> FreezeResponse:
    """Freeze proposals for a brand."""
    result = _engine.freeze_proposals(brand_id)
    
    return FreezeResponse(
        brand_id=brand_id,
        frozen=result["frozen"],
        frozen_at=result["frozen_at"],
    )


@router.post("/rollback", response_model=RollbackResponse)
async def rollback_last(brand_id: str) -> RollbackResponse:
    """Rollback the last applied proposal."""
    result = _engine.rollback_last(brand_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return RollbackResponse(
        brand_id=brand_id,
        proposal_id=result.get("proposal_id"),
        rolled_back=result["rolled_back"],
        rolled_back_at=result["rolled_back_at"],
    )
