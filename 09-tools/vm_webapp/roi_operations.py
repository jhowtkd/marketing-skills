"""ROI Operations Service for API v2.

Provides business logic for ROI optimizer endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from vm_webapp.roi_optimizer import (
    RoiCompositeScore,
    RoiOptimizer,
    RoiProposal,
    RoiScoreCalculator,
    RoiScoreInput,
    RiskLevel,
    ProposalStatus,
)


@dataclass
class ProposalView:
    """View model for a proposal (serializable)."""
    id: str
    description: str
    expected_roi_delta: float
    risk_level: str
    status: str
    adjustments: dict[str, float] = field(default_factory=dict)
    autoapply_eligible: bool = False
    block_reason: Optional[str] = None
    created_at: str = ""
    applied_at: Optional[str] = None

    @classmethod
    def from_proposal(cls, proposal: RoiProposal) -> "ProposalView":
        """Create view from domain proposal."""
        return cls(
            id=proposal.id,
            description=proposal.description,
            expected_roi_delta=proposal.expected_roi_delta,
            risk_level=proposal.risk_level.value,
            status=proposal.status.value,
            adjustments=proposal.adjustments,
            autoapply_eligible=proposal.autoapply_eligible,
            block_reason=proposal.block_reason,
            created_at=proposal.created_at.isoformat() if proposal.created_at else "",
            applied_at=proposal.applied_at.isoformat() if proposal.applied_at else None,
        )


@dataclass
class OptimizerStatus:
    """Status of the ROI optimizer."""
    mode: str
    cadence: str
    weights: dict[str, float]
    current_score: Optional[dict[str, Any]] = None
    last_run_at: Optional[str] = None


class RoiOperationsService:
    """Service for ROI optimizer operations."""
    
    def __init__(self):
        self._optimizer = RoiOptimizer(mode="semi-automatic", cadence="weekly")
        self._proposals: dict[str, RoiProposal] = {}
        self._last_run_at: Optional[datetime] = None
        self._current_score: Optional[RoiCompositeScore] = None
        self._applied_history: list[str] = []  # Stack of applied proposal IDs
    
    def get_status(self) -> OptimizerStatus:
        """Get current optimizer status."""
        current_score_dict = None
        if self._current_score:
            current_score_dict = {
                "total": self._current_score.total_score,
                "business": self._current_score.pillar_scores.business,
                "quality": self._current_score.pillar_scores.quality,
                "efficiency": self._current_score.pillar_scores.efficiency,
            }
        
        return OptimizerStatus(
            mode=self._optimizer.mode,
            cadence=self._optimizer.cadence,
            weights={
                "business": self._optimizer.calculator.weights.business,
                "quality": self._optimizer.calculator.weights.quality,
                "efficiency": self._optimizer.calculator.weights.efficiency,
            },
            current_score=current_score_dict,
            last_run_at=self._last_run_at.isoformat() if self._last_run_at else None,
        )
    
    def list_proposals(self, status: Optional[str] = None) -> list[ProposalView]:
        """List all proposals with optional filtering."""
        views = []
        for proposal in self._proposals.values():
            if status is None or proposal.status.value == status:
                views.append(ProposalView.from_proposal(proposal))
        return sorted(views, key=lambda p: p.created_at, reverse=True)
    
    def run_optimization(
        self,
        current_state: dict[str, Any],
        target_improvement: Optional[float] = None,
        projected_incident_rate: Optional[float] = None,
    ) -> dict[str, Any]:
        """Run optimization and generate proposals.
        
        Returns:
            Dict with proposals, score_before, score_after
        """
        # Build input from dict
        input_data = RoiScoreInput(
            approval_without_regen_24h=current_state.get("approval_without_regen_24h", 0.7),
            revenue_attribution_usd=current_state.get("revenue_attribution_usd", 100000),
            regen_per_job=current_state.get("regen_per_job", 0.5),
            quality_score_avg=current_state.get("quality_score_avg", 0.8),
            avg_latency_ms=current_state.get("avg_latency_ms", 150),
            cost_per_job_usd=current_state.get("cost_per_job_usd", 0.05),
            incident_rate=current_state.get("incident_rate", 0.0),
        )
        
        # Calculate current score
        self._current_score = self._optimizer.calculator.calculate(input_data)
        
        # Generate proposals
        proposals = self._optimizer.generate_proposals(
            current_state=input_data,
            target_improvement=target_improvement,
            projected_incident_rate=projected_incident_rate,
        )
        
        # Store proposals
        for proposal in proposals:
            self._proposals[proposal.id] = proposal
        
        self._last_run_at = datetime.now(timezone.utc)
        
        # Calculate hypothetical score after (simplified)
        score_after = self._current_score.total_score
        if proposals and not all(p.status == ProposalStatus.BLOCKED for p in proposals):
            # Assume best proposal would achieve its expected delta
            best_proposal = max(proposals, key=lambda p: p.expected_roi_delta)
            score_after = min(1.0, self._current_score.total_score + best_proposal.expected_roi_delta)
        
        return {
            "proposals": [ProposalView.from_proposal(p).__dict__ for p in proposals],
            "score_before": self._current_score.total_score,
            "score_after": score_after,
        }
    
    def apply_proposal(self, proposal_id: str) -> Optional[ProposalView]:
        """Apply a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None
        
        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Cannot apply proposal with status {proposal.status}")
        
        proposal.status = ProposalStatus.APPLIED
        proposal.applied_at = datetime.now(timezone.utc)
        self._applied_history.append(proposal_id)
        
        return ProposalView.from_proposal(proposal)
    
    def reject_proposal(self, proposal_id: str, reason: str) -> Optional[ProposalView]:
        """Reject a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None
        
        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Cannot reject proposal with status {proposal.status}")
        
        proposal.status = ProposalStatus.REJECTED
        proposal.block_reason = reason
        
        return ProposalView.from_proposal(proposal)
    
    def rollback_last(self) -> Optional[dict[str, Any]]:
        """Rollback the last applied proposal."""
        if not self._applied_history:
            return None
        
        last_proposal_id = self._applied_history.pop()
        proposal = self._proposals.get(last_proposal_id)
        
        if not proposal:
            return None
        
        proposal.status = ProposalStatus.PENDING
        proposal.applied_at = None
        
        return {
            "rolled_back_proposal": ProposalView.from_proposal(proposal).__dict__,
            "restored_params": {},  # Would restore actual params in real impl
        }
    
    def get_proposal(self, proposal_id: str) -> Optional[ProposalView]:
        """Get a single proposal by ID."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None
        return ProposalView.from_proposal(proposal)


# Singleton service instance
_roi_service: Optional[RoiOperationsService] = None


def get_roi_service() -> RoiOperationsService:
    """Get or create the singleton ROI service."""
    global _roi_service
    if _roi_service is None:
        _roi_service = RoiOperationsService()
    return _roi_service
