"""API endpoints for Quality-First Constrained Optimizer (v25)."""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from vm_webapp.quality_optimizer import (
    ConstraintBounds,
    ProposalState,
    QualityOptimizer,
)

router = APIRouter()

# Global optimizer instance (singleton)
_quality_optimizer: Optional[QualityOptimizer] = None


def get_quality_optimizer() -> QualityOptimizer:
    """Get or create the quality optimizer singleton."""
    global _quality_optimizer
    if _quality_optimizer is None:
        _quality_optimizer = QualityOptimizer()
    return _quality_optimizer


# ============================================================================
# Request/Response Models
# ============================================================================

class ConstraintBoundsModel(BaseModel):
    """Constraint bounds for optimization."""
    max_cost_increase_pct: float = Field(default=10.0, ge=0, le=100)
    max_mttc_increase_pct: float = Field(default=10.0, ge=0, le=100)
    max_incident_rate: float = Field(default=0.05, ge=0, le=1.0)


class RunDataModel(BaseModel):
    """Run data for optimization."""
    run_id: str
    brand_id: str
    quality_score: float = Field(default=65.0, ge=0, le=100)
    v1_score: float = Field(default=60.0, ge=0, le=100)
    cost_per_job: float = Field(default=100.0, ge=0)
    mttc: float = Field(default=300.0, ge=0)
    incident_rate: float = Field(default=0.05, ge=0, le=1.0)
    approval_without_regen_24h: float = Field(default=0.70, ge=0, le=1.0)
    params: dict[str, Any] = Field(default_factory=dict)


class GenerateProposalRequest(BaseModel):
    """Request to generate optimization proposal."""
    current_run: RunDataModel
    historical_runs: list[RunDataModel] = Field(default_factory=list)
    constraints: ConstraintBoundsModel = Field(default_factory=ConstraintBoundsModel)


class ProposalResponse(BaseModel):
    """Response with proposal data."""
    proposal_id: str
    run_id: str
    state: str
    recommended_params: dict[str, Any]
    estimated_v1_improvement: float
    estimated_cost_delta_pct: float
    estimated_mttc_delta_pct: float
    estimated_incident_rate: float
    feasibility_check_passed: bool
    quality_score: float
    created_at: str


class ApplyProposalRequest(BaseModel):
    """Request to apply a proposal."""
    enforce_feasibility: bool = True


class ApplyProposalResponse(BaseModel):
    """Response for apply operation."""
    status: str
    proposal_id: str
    applied_at: Optional[str] = None


class ProposalStatusResponse(BaseModel):
    """Response with full proposal status."""
    proposal_id: str
    run_id: str
    state: str
    feasibility_check_passed: bool
    estimated_v1_improvement: float
    estimated_cost_delta_pct: float
    estimated_mttc_delta_pct: float
    estimated_incident_rate: float
    quality_score: float
    created_at: str
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None


class ProposalSnapshotResponse(BaseModel):
    """Response with proposal snapshot."""
    proposal_id: str
    previous_params: dict[str, Any]
    applied_params: dict[str, Any]
    applied_at: str


class OptimizerStatusResponse(BaseModel):
    """Response with optimizer status."""
    version: str
    total_proposals: int
    proposals_by_state: dict[str, int]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/v2/optimizer/status", response_model=OptimizerStatusResponse)
def get_optimizer_status():
    """Get quality optimizer status and statistics."""
    optimizer = get_quality_optimizer()
    
    # Count proposals by state
    proposals_by_state: dict[str, int] = {
        "pending": 0,
        "applied": 0,
        "rejected": 0,
        "frozen": 0,
        "rolled_back": 0,
    }
    
    total_proposals = 0
    for proposals in optimizer._proposal_history.values():
        for proposal in proposals:
            total_proposals += 1
            state_value = proposal.state.value
            if state_value in proposals_by_state:
                proposals_by_state[state_value] += 1
    
    return OptimizerStatusResponse(
        version=optimizer.version,
        total_proposals=total_proposals,
        proposals_by_state=proposals_by_state,
    )


@router.post("/v2/optimizer/run", response_model=ProposalResponse)
def run_optimizer(request: GenerateProposalRequest):
    """Run optimizer and generate a proposal for current run."""
    optimizer = get_quality_optimizer()
    
    # Convert request models to internal types
    constraints = ConstraintBounds(
        max_cost_increase_pct=request.constraints.max_cost_increase_pct,
        max_mttc_increase_pct=request.constraints.max_mttc_increase_pct,
        max_incident_rate=request.constraints.max_incident_rate,
    )
    
    current_run = request.current_run.model_dump()
    historical_runs = [r.model_dump() for r in request.historical_runs]
    
    # Generate proposal
    proposal = optimizer.generate_proposal(
        current_run=current_run,
        historical_runs=historical_runs,
        constraints=constraints,
    )
    
    return ProposalResponse(
        proposal_id=proposal.proposal_id,
        run_id=proposal.run_id,
        state=proposal.state.value,
        recommended_params=proposal.recommended_params,
        estimated_v1_improvement=proposal.estimated_v1_improvement,
        estimated_cost_delta_pct=proposal.estimated_cost_delta_pct,
        estimated_mttc_delta_pct=proposal.estimated_mttc_delta_pct,
        estimated_incident_rate=proposal.estimated_incident_rate,
        feasibility_check_passed=proposal.feasibility_check_passed,
        quality_score=proposal.quality_score.overall,
        created_at=proposal.created_at,
    )


@router.get("/v2/optimizer/proposals/{proposal_id}", response_model=ProposalStatusResponse)
def get_proposal(proposal_id: str):
    """Get proposal details by ID."""
    optimizer = get_quality_optimizer()
    
    status = optimizer.get_proposal_status(proposal_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    
    return ProposalStatusResponse(
        proposal_id=status["proposal_id"],
        run_id=status["run_id"],
        state=status["state"],
        feasibility_check_passed=status["feasibility_check_passed"],
        estimated_v1_improvement=status["estimated_v1_improvement"],
        estimated_cost_delta_pct=status["estimated_cost_delta_pct"],
        estimated_mttc_delta_pct=status["estimated_mttc_delta_pct"],
        estimated_incident_rate=status["estimated_incident_rate"],
        quality_score=status["quality_score"],
        created_at=status["created_at"],
        applied_at=status.get("applied_at"),
        rolled_back_at=status.get("rolled_back_at"),
    )


@router.get("/v2/optimizer/runs/{run_id}/proposals")
def get_run_proposals(run_id: str):
    """Get all proposals for a run."""
    optimizer = get_quality_optimizer()
    
    proposals = optimizer.get_proposal_history(run_id)
    
    return {
        "run_id": run_id,
        "proposal_count": len(proposals),
        "proposals": [
            {
                "proposal_id": p.proposal_id,
                "state": p.state.value,
                "feasibility_check_passed": p.feasibility_check_passed,
                "estimated_v1_improvement": p.estimated_v1_improvement,
                "quality_score": p.quality_score.overall,
                "created_at": p.created_at,
            }
            for p in proposals
        ],
    }


@router.post("/v2/optimizer/proposals/{proposal_id}/apply", response_model=ApplyProposalResponse)
def apply_proposal(proposal_id: str, request: ApplyProposalRequest = ApplyProposalRequest()):
    """Apply a proposal."""
    optimizer = get_quality_optimizer()
    
    # Check if proposal exists
    status = optimizer.get_proposal_status(proposal_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    
    # Apply the proposal
    success = optimizer.apply_proposal(
        proposal_id=proposal_id,
        enforce_feasibility=request.enforce_feasibility,
    )
    
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot apply proposal {proposal_id}: not feasible or invalid state",
        )
    
    return ApplyProposalResponse(
        status="applied",
        proposal_id=proposal_id,
        applied_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/v2/optimizer/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str):
    """Reject a proposal."""
    optimizer = get_quality_optimizer()
    
    # Check if proposal exists
    status = optimizer.get_proposal_status(proposal_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    
    # Reject the proposal
    success = optimizer.reject_proposal(proposal_id)
    
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject proposal {proposal_id}: invalid state",
        )
    
    return {
        "status": "rejected",
        "proposal_id": proposal_id,
    }


@router.post("/v2/optimizer/proposals/{proposal_id}/freeze")
def freeze_proposal(proposal_id: str):
    """Freeze a proposal (prevents any transition)."""
    optimizer = get_quality_optimizer()
    
    # Check if proposal exists
    status = optimizer.get_proposal_status(proposal_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    
    # Freeze the proposal
    success = optimizer.freeze_proposal(proposal_id)
    
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot freeze proposal {proposal_id}: invalid state",
        )
    
    return {
        "status": "frozen",
        "proposal_id": proposal_id,
    }


@router.post("/v2/optimizer/proposals/{proposal_id}/rollback")
def rollback_proposal(proposal_id: str):
    """Rollback an applied proposal."""
    optimizer = get_quality_optimizer()
    
    # Check if proposal exists
    status = optimizer.get_proposal_status(proposal_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    
    # Rollback the proposal
    success = optimizer.rollback_proposal(proposal_id)
    
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot rollback proposal {proposal_id}: not applied or already rolled back",
        )
    
    return {
        "status": "rolled_back",
        "proposal_id": proposal_id,
    }


@router.get("/v2/optimizer/proposals/{proposal_id}/snapshot", response_model=ProposalSnapshotResponse)
def get_proposal_snapshot(proposal_id: str):
    """Get snapshot (previous state) for an applied proposal."""
    optimizer = get_quality_optimizer()
    
    snapshot = optimizer.get_proposal_snapshot(proposal_id)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot not found for proposal: {proposal_id}",
        )
    
    return ProposalSnapshotResponse(
        proposal_id=snapshot["proposal_id"],
        previous_params=snapshot["previous_params"],
        applied_params=snapshot["applied_params"],
        applied_at=snapshot["applied_at"],
    )
