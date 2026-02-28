"""Policy operations service for v18 API endpoints.

Provides:
- Effective policy resolution
- Proposal management (create, approve, reject, apply)
- Policy freeze/unfreeze
- Policy rollback
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from vm_webapp.policy_hierarchy import resolve_effective_policy, EffectivePolicy
from vm_webapp.policy_adaptation import (
    PolicyProposalEngine,
    AdaptationProposal,
    ProposalStatus,
    DivergenceGuard,
)


class ProposalNotFoundError(Exception):
    """Raised when a proposal is not found."""
    pass


class ProposalNotApprovedError(Exception):
    """Raised when trying to apply a non-approved proposal."""
    pass


class PolicyFrozenError(Exception):
    """Raised when trying to modify a frozen policy."""
    pass


@dataclass
class PolicyFreeze:
    """Policy freeze record."""

    freeze_id: str
    brand_id: str
    reason: str
    frozen_at: str
    frozen: bool = True
    duration_hours: Optional[int] = None


@dataclass
class PolicyRollback:
    """Policy rollback record."""

    rollback_id: str
    brand_id: str
    previous_version: dict[str, Any]
    rolled_back: bool
    reason: Optional[str] = None
    rolled_back_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PolicyOperationsService:
    """Service for policy operations.
    
    Manages:
    - Effective policy resolution
    - Proposal lifecycle
    - Policy freeze/unfreeze
    - Policy rollback
    """

    def __init__(self, session: Session):
        self.session = session
        self._proposal_engine = PolicyProposalEngine(max_adjustment_percent=10.0)
        self._divergence_guard = DivergenceGuard()
        self._proposals: dict[str, AdaptationProposal] = {}
        self._frozen_brands: set[str] = set()
        self._freeze_records: dict[str, PolicyFreeze] = {}
        self._policy_history: dict[str, list[dict[str, Any]]] = {}

    def get_effective_policy(
        self,
        brand_id: str,
        segment: Optional[str] = None,
        objective_key: Optional[str] = None,
    ) -> EffectivePolicy:
        """Get effective policy for brand.
        
        Args:
            brand_id: Brand identifier
            segment: Optional segment
            objective_key: Optional objective key
            
        Returns:
            EffectivePolicy with resolved values
        """
        return resolve_effective_policy(
            self.session,
            brand_id=brand_id,
            segment=segment,
            objective_key=objective_key,
        )

    def create_proposal(
        self,
        brand_id: str,
        current: dict[str, Any],
        suggested: dict[str, Any],
        objective_key: Optional[str] = None,
    ) -> Optional[AdaptationProposal]:
        """Create a new policy proposal.
        
        Args:
            brand_id: Brand identifier
            current: Current policy params
            suggested: Suggested policy params
            objective_key: Optional objective key
            
        Returns:
            Created proposal or None if no changes
            
        Raises:
            PolicyFrozenError: If brand is frozen
        """
        if brand_id in self._frozen_brands:
            raise PolicyFrozenError(f"Brand {brand_id} is frozen")

        # Check divergence guard
        test_proposal = AdaptationProposal(
            proposal_id="test",
            brand_id=brand_id,
            objective_key=objective_key,
            current_value=0.0,
            proposed_value=0.0,
            adjustment_percent=0.0,
        )
        
        guard_result = self._divergence_guard.evaluate_proposal(test_proposal)
        if guard_result.is_blocked:
            # Store as blocked proposal
            proposal = self._proposal_engine.propose_diff(
                brand_id, current, suggested, objective_key
            )
            if proposal:
                proposal.status = ProposalStatus.BLOCKED
                proposal.blocked_reason = guard_result.reason
                self._proposals[proposal.proposal_id] = proposal
            return proposal

        # Create proposal normally
        proposal = self._proposal_engine.propose_diff(
            brand_id, current, suggested, objective_key
        )
        
        if proposal:
            self._proposals[proposal.proposal_id] = proposal
            
        return proposal

    def approve_proposal(
        self,
        brand_id: str,
        proposal_id: str,
        approver: str,
    ) -> AdaptationProposal:
        """Approve a proposal.
        
        Args:
            brand_id: Brand identifier
            proposal_id: Proposal identifier
            approver: Approver identifier
            
        Returns:
            Updated proposal
            
        Raises:
            ProposalNotFoundError: If proposal not found
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")
        
        self._proposal_engine.approve_proposal(proposal, approver)
        return proposal

    def reject_proposal(
        self,
        brand_id: str,
        proposal_id: str,
        reason: str,
    ) -> AdaptationProposal:
        """Reject a proposal.
        
        Args:
            brand_id: Brand identifier
            proposal_id: Proposal identifier
            reason: Rejection reason
            
        Returns:
            Updated proposal
            
        Raises:
            ProposalNotFoundError: If proposal not found
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")
        
        self._proposal_engine.reject_proposal(proposal, reason)
        return proposal

    def apply_proposal(
        self,
        brand_id: str,
        proposal_id: str,
    ) -> dict[str, Any]:
        """Apply an approved proposal.
        
        Args:
            brand_id: Brand identifier
            proposal_id: Proposal identifier
            
        Returns:
            New policy params
            
        Raises:
            ProposalNotFoundError: If proposal not found
            ProposalNotApprovedError: If proposal not approved
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")
        
        if proposal.status != ProposalStatus.APPROVED:
            raise ProposalNotApprovedError(
                f"Cannot apply proposal with status {proposal.status}"
            )
        
        # Store current params in history before applying
        if brand_id not in self._policy_history:
            self._policy_history[brand_id] = []
        self._policy_history[brand_id].append(proposal.current_params.copy())
        
        return self._proposal_engine.apply_proposal(proposal)

    def list_proposals(
        self,
        brand_id: str,
        status: Optional[ProposalStatus] = None,
        objective_key: Optional[str] = None,
    ) -> list[AdaptationProposal]:
        """List proposals for brand.
        
        Args:
            brand_id: Brand identifier
            status: Optional status filter
            objective_key: Optional objective key filter
            
        Returns:
            List of proposals
        """
        results = []
        for proposal in self._proposals.values():
            if proposal.brand_id != brand_id:
                continue
            if status is not None and proposal.status != status:
                continue
            if objective_key is not None and proposal.objective_key != objective_key:
                continue
            results.append(proposal)
        return sorted(results, key=lambda p: p.created_at, reverse=True)

    def freeze_policy(
        self,
        brand_id: str,
        reason: str,
        duration_hours: Optional[int] = None,
    ) -> PolicyFreeze:
        """Freeze policy changes for brand.
        
        Args:
            brand_id: Brand identifier
            reason: Freeze reason
            duration_hours: Optional duration
            
        Returns:
            Freeze record
            
        Raises:
            PolicyFrozenError: If brand already frozen
        """
        if brand_id in self._frozen_brands:
            raise PolicyFrozenError(f"Brand {brand_id} is already frozen")
        
        freeze_id = str(uuid.uuid4())
        freeze = PolicyFreeze(
            freeze_id=freeze_id,
            brand_id=brand_id,
            reason=reason,
            frozen_at=datetime.now(timezone.utc).isoformat(),
            frozen=True,
            duration_hours=duration_hours,
        )
        
        self._frozen_brands.add(brand_id)
        self._freeze_records[freeze_id] = freeze
        
        return freeze

    def unfreeze_policy(self, brand_id: str) -> PolicyFreeze:
        """Unfreeze a frozen brand.
        
        Args:
            brand_id: Brand identifier
            
        Returns:
            Updated freeze record
            
        Raises:
            ValueError: If brand not frozen
        """
        if brand_id not in self._frozen_brands:
            raise ValueError(f"Brand {brand_id} is not frozen")
        
        self._frozen_brands.discard(brand_id)
        
        # Find and update freeze record
        for freeze in self._freeze_records.values():
            if freeze.brand_id == brand_id and freeze.frozen:
                freeze.frozen = False
                return freeze
        
        raise ValueError(f"No active freeze record for brand {brand_id}")

    def is_frozen(self, brand_id: str) -> bool:
        """Check if brand is frozen."""
        return brand_id in self._frozen_brands

    def rollback_policy(
        self,
        brand_id: str,
        steps: int = 1,
        reason: Optional[str] = None,
    ) -> PolicyRollback:
        """Rollback to previous policy version.
        
        Args:
            brand_id: Brand identifier
            steps: Number of steps to rollback
            reason: Optional rollback reason
            
        Returns:
            Rollback record
            
        Raises:
            ValueError: If no history to rollback
        """
        history = self._policy_history.get(brand_id, [])
        if not history or len(history) < steps:
            raise ValueError(f"Not enough history to rollback {steps} steps")
        
        # Get previous version
        previous_version = history[-steps]
        
        rollback = PolicyRollback(
            rollback_id=str(uuid.uuid4()),
            brand_id=brand_id,
            previous_version=previous_version.copy(),
            rolled_back=True,
            reason=reason,
        )
        
        return rollback

    def register_active_incident(self, brand_id: str, incident_id: str) -> None:
        """Register an active incident for divergence guard."""
        self._divergence_guard.register_active_incident(brand_id, incident_id)

    def clear_incident(self, brand_id: str, incident_id: str) -> None:
        """Clear an active incident."""
        self._divergence_guard.clear_incident(brand_id, incident_id)

    def register_active_rollback(self, brand_id: str) -> None:
        """Register an active rollback for divergence guard."""
        self._divergence_guard.register_active_rollback(brand_id)

    def clear_rollback(self, brand_id: str) -> None:
        """Clear an active rollback."""
        self._divergence_guard.clear_rollback(brand_id)

    def register_canary(self, brand_id: str, canary_id: str) -> None:
        """Register a canary in progress for divergence guard."""
        self._divergence_guard.register_canary_in_progress(brand_id, canary_id)

    def clear_canary(self, brand_id: str) -> None:
        """Clear a canary in progress."""
        self._divergence_guard.clear_canary(brand_id)
