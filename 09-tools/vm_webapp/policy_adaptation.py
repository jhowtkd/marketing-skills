"""Adaptive policy proposal engine with cross-brand divergence guard (v18).

Features:
- Propose diffs with ±10% clamp
- Block by incident/canary/rollback active
- Reduce aggressiveness when p90-p10 gap exceeds limit
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class ProposalStatus(str, Enum):
    """Status of an adaptation proposal."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    BLOCKED = "blocked"
    FROZEN = "frozen"


@dataclass
class AdaptationProposal:
    """Proposal for policy adaptation."""

    proposal_id: str
    brand_id: str
    objective_key: Optional[str]
    current_value: float
    proposed_value: float
    adjustment_percent: float
    current_params: dict[str, Any] = field(default_factory=dict)
    proposed_params: dict[str, Any] = field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    applied_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    blocked_reason: Optional[str] = None


@dataclass
class ProposalEvaluation:
    """Result of evaluating a proposal against guards."""

    is_blocked: bool
    can_apply: bool
    reason: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class CrossBrandMetrics:
    """Metrics across all brands for gap analysis."""

    p90_threshold: float
    p10_threshold: float
    p90_p10_gap: float
    brand_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DivergenceGuard:
    """Cross-brand divergence guard for policy proposals.
    
    Blocks proposals when:
    - Active incident for brand
    - Active rollback for brand
    - Canary in progress for brand
    """

    def __init__(self):
        self._active_incidents: dict[str, set[str]] = {}  # brand_id -> set of incident_ids
        self._active_rollbacks: set[str] = set()  # set of brand_ids
        self._canary_in_progress: dict[str, str] = {}  # brand_id -> canary_id

    def register_active_incident(self, brand_id: str, incident_id: str) -> None:
        """Register an active incident for a brand."""
        if brand_id not in self._active_incidents:
            self._active_incidents[brand_id] = set()
        self._active_incidents[brand_id].add(incident_id)

    def clear_incident(self, brand_id: str, incident_id: str) -> None:
        """Clear an active incident for a brand."""
        if brand_id in self._active_incidents:
            self._active_incidents[brand_id].discard(incident_id)
            if not self._active_incidents[brand_id]:
                del self._active_incidents[brand_id]

    def register_active_rollback(self, brand_id: str) -> None:
        """Register an active rollback for a brand."""
        self._active_rollbacks.add(brand_id)

    def clear_rollback(self, brand_id: str) -> None:
        """Clear an active rollback for a brand."""
        self._active_rollbacks.discard(brand_id)

    def register_canary_in_progress(self, brand_id: str, canary_id: str) -> None:
        """Register a canary in progress for a brand."""
        self._canary_in_progress[brand_id] = canary_id

    def clear_canary(self, brand_id: str) -> None:
        """Clear canary in progress for a brand."""
        self._canary_in_progress.pop(brand_id, None)

    def evaluate_proposal(self, proposal: AdaptationProposal) -> ProposalEvaluation:
        """Evaluate a proposal against all guards.
        
        Args:
            proposal: The proposal to evaluate
            
        Returns:
            ProposalEvaluation with block status and reason
        """
        brand_id = proposal.brand_id
        warnings = []

        # Check for active incident
        if brand_id in self._active_incidents and self._active_incidents[brand_id]:
            incident_ids = self._active_incidents[brand_id]
            return ProposalEvaluation(
                is_blocked=True,
                can_apply=False,
                reason=f"Active incident(s) for brand: {incident_ids}",
                warnings=warnings,
            )

        # Check for active rollback
        if brand_id in self._active_rollbacks:
            return ProposalEvaluation(
                is_blocked=True,
                can_apply=False,
                reason="Active rollback in progress for brand",
                warnings=warnings,
            )

        # Check for canary in progress
        if brand_id in self._canary_in_progress:
            canary_id = self._canary_in_progress[brand_id]
            return ProposalEvaluation(
                is_blocked=True,
                can_apply=False,
                reason=f"Canary in progress: {canary_id}",
                warnings=warnings,
            )

        return ProposalEvaluation(
            is_blocked=False,
            can_apply=True,
            reason=None,
            warnings=warnings,
        )

    def has_active_blocks(self, brand_id: str) -> bool:
        """Check if brand has any active blocks."""
        has_incident = brand_id in self._active_incidents and bool(self._active_incidents[brand_id])
        has_rollback = brand_id in self._active_rollbacks
        has_canary = brand_id in self._canary_in_progress
        return has_incident or has_rollback or has_canary


class PolicyProposalEngine:
    """Engine for proposing and managing policy adaptations.
    
    Features:
    - Propose diffs with ±10% clamp (configurable)
    - Reduce aggressiveness when p90-p10 gap exceeds limit
    - Track cross-brand metrics for divergence detection
    """

    def __init__(
        self,
        max_adjustment_percent: float = 10.0,
        max_p90_p10_gap: float = 0.15,
        critical_gap_threshold: float = 0.25,
    ):
        self.max_adjustment_percent = max_adjustment_percent
        self.max_p90_p10_gap = max_p90_p10_gap
        self.critical_gap_threshold = critical_gap_threshold
        self._cross_brand_metrics: Optional[CrossBrandMetrics] = None
        self._proposals: dict[str, AdaptationProposal] = {}

    def update_cross_brand_metrics(self, metrics: CrossBrandMetrics) -> None:
        """Update cross-brand metrics for gap analysis."""
        self._cross_brand_metrics = metrics

    def _calculate_percent_change(self, current: float, proposed: float) -> float:
        """Calculate percentage change between current and proposed values."""
        if current == 0:
            return 0.0 if proposed == 0 else float('inf') if proposed > 0 else float('-inf')
        return ((proposed - current) / current) * 100.0

    def _apply_gap_adjustment(self, adjustment_percent: float) -> float:
        """Adjust the proposal based on cross-brand gap metrics.
        
        - If gap exceeds max: reduce adjustment by 50%
        - If gap is critical: block (return 0)
        - Otherwise: keep original adjustment
        """
        if self._cross_brand_metrics is None:
            return adjustment_percent

        gap = self._cross_brand_metrics.p90_p10_gap

        # Critical gap - block all adjustments
        if gap >= self.critical_gap_threshold:
            return 0.0

        # Gap exceeds limit - reduce aggressiveness by 50%
        if gap > self.max_p90_p10_gap:
            return adjustment_percent * 0.5

        # Gap within limits - allow full adjustment
        return adjustment_percent

    def _clamp_adjustment(self, adjustment_percent: float) -> float:
        """Clamp adjustment to ±max_adjustment_percent."""
        return max(
            -self.max_adjustment_percent,
            min(self.max_adjustment_percent, adjustment_percent)
        )

    def propose_diff(
        self,
        brand_id: str,
        current: dict[str, Any],
        suggested: dict[str, Any],
        objective_key: Optional[str] = None,
    ) -> Optional[AdaptationProposal]:
        """Propose a diff between current and suggested policy params.
        
        Args:
            brand_id: Brand identifier
            current: Current policy parameters
            suggested: Suggested policy parameters
            objective_key: Optional objective key for specificity
            
        Returns:
            AdaptationProposal if changes needed, None otherwise
        """
        # Find numeric params that changed
        changes = {}
        for key, new_value in suggested.items():
            old_value = current.get(key)
            if old_value != new_value:
                changes[key] = (old_value, new_value)

        if not changes:
            return None  # No changes needed

        # Calculate adjustment on threshold (primary metric)
        # or first numeric change found
        adjustment_percent = 0.0
        current_value = 0.0
        proposed_value = 0.0

        for key, (old_val, new_val) in changes.items():
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                adjustment_percent = self._calculate_percent_change(old_val, new_val)
                current_value = float(old_val)
                proposed_value = float(new_val)
                break

        if adjustment_percent == 0.0:
            return None  # No numeric changes

        # Apply gap-based adjustment reduction
        adjustment_percent = self._apply_gap_adjustment(adjustment_percent)

        # If critical gap blocked the adjustment
        if adjustment_percent == 0.0:
            return None

        # Clamp to max adjustment
        adjustment_percent = self._clamp_adjustment(adjustment_percent)

        # Recalculate proposed value based on clamped percentage
        if current_value != 0:
            proposed_value = current_value * (1 + adjustment_percent / 100.0)

        # Create proposal
        proposal = AdaptationProposal(
            proposal_id=str(uuid.uuid4()),
            brand_id=brand_id,
            objective_key=objective_key,
            current_value=current_value,
            proposed_value=proposed_value,
            adjustment_percent=round(adjustment_percent, 2),
            current_params=current.copy(),
            proposed_params=suggested.copy(),
            status=ProposalStatus.PENDING,
        )

        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def approve_proposal(self, proposal: AdaptationProposal, approver: str) -> None:
        """Approve a proposal.
        
        Args:
            proposal: The proposal to approve
            approver: Identifier of the approver
        """
        proposal.status = ProposalStatus.APPROVED
        proposal.approved_by = approver
        proposal.approved_at = datetime.now(timezone.utc).isoformat()

    def reject_proposal(self, proposal: AdaptationProposal, reason: str) -> None:
        """Reject a proposal.
        
        Args:
            proposal: The proposal to reject
            reason: Reason for rejection
        """
        proposal.status = ProposalStatus.REJECTED
        proposal.rejection_reason = reason

    def apply_proposal(self, proposal: AdaptationProposal) -> dict[str, Any]:
        """Apply an approved proposal.
        
        Args:
            proposal: The approved proposal to apply
            
        Returns:
            The new policy parameters
            
        Raises:
            ValueError: If proposal is not approved
        """
        if proposal.status != ProposalStatus.APPROVED:
            raise ValueError(f"Cannot apply proposal with status {proposal.status}")

        proposal.status = ProposalStatus.APPLIED
        proposal.applied_at = datetime.now(timezone.utc).isoformat()

        return proposal.proposed_params.copy()

    def freeze_proposal(self, proposal: AdaptationProposal, reason: str) -> None:
        """Freeze a proposal, preventing further action.
        
        Args:
            proposal: The proposal to freeze
            reason: Reason for freezing
        """
        proposal.status = ProposalStatus.FROZEN
        proposal.blocked_reason = reason

    def rollback_proposal(self, proposal: AdaptationProposal) -> dict[str, Any]:
        """Rollback an applied proposal.
        
        Args:
            proposal: The applied proposal to rollback
            
        Returns:
            The original policy parameters
            
        Raises:
            ValueError: If proposal is not applied
        """
        if proposal.status != ProposalStatus.APPLIED:
            raise ValueError(f"Cannot rollback proposal with status {proposal.status}")

        # Mark as pending again (can be re-approved or rejected)
        proposal.status = ProposalStatus.PENDING
        proposal.applied_at = None

        return proposal.current_params.copy()

    def get_proposal(self, proposal_id: str) -> Optional[AdaptationProposal]:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        brand_id: Optional[str] = None,
        status: Optional[ProposalStatus] = None,
        objective_key: Optional[str] = None,
    ) -> list[AdaptationProposal]:
        """List proposals with optional filtering."""
        results = []
        for proposal in self._proposals.values():
            if brand_id is not None and proposal.brand_id != brand_id:
                continue
            if status is not None and proposal.status != status:
                continue
            if objective_key is not None and proposal.objective_key != objective_key:
                continue
            results.append(proposal)
        return sorted(results, key=lambda p: p.created_at, reverse=True)
