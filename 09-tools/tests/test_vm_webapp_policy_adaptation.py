"""Tests for adaptive policy proposal engine with cross-brand divergence guard (v18).

Features:
- Propose diffs with ±10% clamp
- Block by incident/canary/rollback active
- Reduce aggressiveness when p90-p10 gap exceeds limit
"""

import json
import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vm_webapp.models import Base
from vm_webapp.policy_adaptation import (
    PolicyProposalEngine,
    ProposalStatus,
    DivergenceGuard,
    CrossBrandMetrics,
    AdaptationProposal,
)


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestPolicyProposalEngine:
    """Test policy proposal engine."""

    def test_propose_diff_with_clamp_max(self):
        """Proposed diff should be clamped to +10% max."""
        # Arrange
        engine = PolicyProposalEngine(max_adjustment_percent=10.0)
        current = {"threshold": 0.5, "mode": "standard"}
        # Try to propose 20% increase
        suggested = {"threshold": 0.6, "mode": "standard"}  # +20%

        # Act
        proposal = engine.propose_diff("brand1", current, suggested, objective_key="conv")

        # Assert
        assert proposal is not None
        assert proposal.adjustment_percent <= 10.0
        assert proposal.adjustment_percent > 0  # Still positive

    def test_propose_diff_with_clamp_min(self):
        """Proposed diff should be clamped to -10% min."""
        # Arrange
        engine = PolicyProposalEngine(max_adjustment_percent=10.0)
        current = {"threshold": 0.5, "mode": "standard"}
        # Try to propose 20% decrease
        suggested = {"threshold": 0.4, "mode": "standard"}  # -20%

        # Act
        proposal = engine.propose_diff("brand1", current, suggested, objective_key="conv")

        # Assert
        assert proposal is not None
        assert proposal.adjustment_percent >= -10.0
        assert proposal.adjustment_percent < 0  # Still negative

    def test_propose_diff_no_change_returns_none(self):
        """When no change needed, proposal should be None."""
        # Arrange
        engine = PolicyProposalEngine()
        current = {"threshold": 0.5, "mode": "standard"}
        suggested = {"threshold": 0.5, "mode": "standard"}  # Same

        # Act
        proposal = engine.propose_diff("brand1", current, suggested)

        # Assert
        assert proposal is None

    def test_propose_diff_within_bounds(self):
        """Proposals within ±10% should be accepted as-is."""
        # Arrange
        engine = PolicyProposalEngine(max_adjustment_percent=10.0)
        current = {"threshold": 0.5, "mode": "standard"}
        suggested = {"threshold": 0.53, "mode": "standard"}  # +6%

        # Act
        proposal = engine.propose_diff("brand1", current, suggested)

        # Assert
        assert proposal is not None
        assert pytest.approx(proposal.adjustment_percent, 0.01) == 6.0

    def test_proposal_includes_brand_and_objective(self):
        """Proposal should track brand and objective_key."""
        # Arrange
        engine = PolicyProposalEngine()
        current = {"threshold": 0.5}
        suggested = {"threshold": 0.55}  # +10%

        # Act
        proposal = engine.propose_diff(
            "brand1", current, suggested, objective_key="awareness"
        )

        # Assert
        assert proposal.brand_id == "brand1"
        assert proposal.objective_key == "awareness"


class TestDivergenceGuard:
    """Test cross-brand divergence guard."""

    def test_block_by_active_incident(self):
        """Proposals should be blocked when incident is active."""
        # Arrange
        guard = DivergenceGuard()
        guard.register_active_incident("brand1", "incident-123")

        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
        )

        # Act
        result = guard.evaluate_proposal(proposal)

        # Assert
        assert result.is_blocked is True
        assert "incident" in result.reason.lower()

    def test_block_by_active_rollback(self):
        """Proposals should be blocked when rollback is active."""
        # Arrange
        guard = DivergenceGuard()
        guard.register_active_rollback("brand1")

        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
        )

        # Act
        result = guard.evaluate_proposal(proposal)

        # Assert
        assert result.is_blocked is True
        assert "rollback" in result.reason.lower()

    def test_block_by_canary_in_progress(self):
        """Proposals should be blocked when canary is in progress."""
        # Arrange
        guard = DivergenceGuard()
        guard.register_canary_in_progress("brand1", "canary-456")

        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
        )

        # Act
        result = guard.evaluate_proposal(proposal)

        # Assert
        assert result.is_blocked is True
        assert "canary" in result.reason.lower()

    def test_approve_when_no_blocks(self):
        """Proposals should be approved when no blocks active."""
        # Arrange
        guard = DivergenceGuard()
        # No active incidents, rollbacks, or canaries

        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
        )

        # Act
        result = guard.evaluate_proposal(proposal)

        # Assert
        assert result.is_blocked is False
        assert result.can_apply is True

    def test_clear_incident_allows_proposals(self):
        """After clearing incident, proposals should be allowed."""
        # Arrange
        guard = DivergenceGuard()
        guard.register_active_incident("brand1", "incident-123")
        guard.clear_incident("brand1", "incident-123")

        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
        )

        # Act
        result = guard.evaluate_proposal(proposal)

        # Assert
        assert result.is_blocked is False

    def test_different_brand_not_affected(self):
        """Incident in brand1 should not block proposals for brand2."""
        # Arrange
        guard = DivergenceGuard()
        guard.register_active_incident("brand1", "incident-123")

        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand2",  # Different brand
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
        )

        # Act
        result = guard.evaluate_proposal(proposal)

        # Assert
        assert result.is_blocked is False


class TestGapReduction:
    """Test quality gap reduction (p90-p10) across brands."""

    def test_reduce_aggressiveness_when_gap_exceeds_limit(self):
        """When p90-p10 gap exceeds limit, reduce adjustment by 50%."""
        # Arrange
        engine = PolicyProposalEngine(
            max_adjustment_percent=10.0,
            max_p90_p10_gap=0.15,  # 15% max gap
        )

        # Current metrics show 20% gap (exceeds 15% limit)
        cross_brand = CrossBrandMetrics(
            p90_threshold=0.8,
            p10_threshold=0.6,
            p90_p10_gap=0.2,  # 20% gap > 15% limit
        )
        engine.update_cross_brand_metrics(cross_brand)

        current = {"threshold": 0.5}
        suggested = {"threshold": 0.55}  # +10% normally

        # Act
        proposal = engine.propose_diff("brand1", current, suggested)

        # Assert - should be reduced to ~5% (50% of 10%)
        assert proposal is not None
        assert proposal.adjustment_percent <= 5.5  # Reduced
        assert proposal.adjustment_percent > 0  # But still positive

    def test_full_adjustment_when_gap_within_limit(self):
        """When p90-p10 gap within limit, allow full adjustment."""
        # Arrange
        engine = PolicyProposalEngine(
            max_adjustment_percent=10.0,
            max_p90_p10_gap=0.15,
        )

        # Current metrics show 10% gap (within 15% limit)
        cross_brand = CrossBrandMetrics(
            p90_threshold=0.7,
            p10_threshold=0.6,
            p90_p10_gap=0.1,  # 10% gap < 15% limit
        )
        engine.update_cross_brand_metrics(cross_brand)

        current = {"threshold": 0.5}
        suggested = {"threshold": 0.55}  # +10%

        # Act
        proposal = engine.propose_diff("brand1", current, suggested)

        # Assert - should allow full 10%
        assert proposal is not None
        assert pytest.approx(proposal.adjustment_percent, 0.01) == 10.0

    def test_block_when_gap_critical(self):
        """When gap is critical, block all adjustments."""
        # Arrange
        engine = PolicyProposalEngine(
            max_adjustment_percent=10.0,
            max_p90_p10_gap=0.15,
            critical_gap_threshold=0.25,
        )

        # Current metrics show 30% gap (critical)
        cross_brand = CrossBrandMetrics(
            p90_threshold=0.9,
            p10_threshold=0.6,
            p90_p10_gap=0.3,  # 30% gap > 25% critical
        )
        engine.update_cross_brand_metrics(cross_brand)

        current = {"threshold": 0.5}
        suggested = {"threshold": 0.55}  # +10%

        # Act
        proposal = engine.propose_diff("brand1", current, suggested)

        # Assert - should be blocked
        assert proposal is None  # No proposal when critical gap


class TestProposalLifecycle:
    """Test proposal lifecycle (create, approve, reject, apply)."""

    def test_create_proposal_pending_status(self):
        """New proposals should have pending status."""
        # Arrange
        engine = PolicyProposalEngine()
        current = {"threshold": 0.5}
        suggested = {"threshold": 0.55}

        # Act
        proposal = engine.propose_diff("brand1", current, suggested)

        # Assert
        assert proposal is not None
        assert proposal.status == ProposalStatus.PENDING

    def test_approve_proposal_changes_status(self):
        """Approving proposal should change status to approved."""
        # Arrange
        engine = PolicyProposalEngine()
        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )

        # Act
        engine.approve_proposal(proposal, approver="admin")

        # Assert
        assert proposal.status == ProposalStatus.APPROVED
        assert proposal.approved_by == "admin"
        assert proposal.approved_at is not None

    def test_reject_proposal_changes_status(self):
        """Rejecting proposal should change status to rejected."""
        # Arrange
        engine = PolicyProposalEngine()
        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )

        # Act
        engine.reject_proposal(proposal, reason="Too aggressive")

        # Assert
        assert proposal.status == ProposalStatus.REJECTED
        assert proposal.rejection_reason == "Too aggressive"

    def test_apply_approved_proposal(self):
        """Applying approved proposal should return new policy params."""
        # Arrange
        engine = PolicyProposalEngine()
        proposal = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key="conv",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            current_params={"threshold": 0.5, "mode": "standard"},
            proposed_params={"threshold": 0.55, "mode": "standard"},
            status=ProposalStatus.APPROVED,
        )

        # Act
        result = engine.apply_proposal(proposal)

        # Assert
        assert result["threshold"] == 0.55
        assert proposal.status == ProposalStatus.APPLIED
        assert proposal.applied_at is not None


class TestMultiObjectiveProposals:
    """Test handling proposals for different objectives."""

    def test_separate_proposals_per_objective(self):
        """Each objective_key should have separate proposals."""
        # Arrange
        engine = PolicyProposalEngine()
        current = {"threshold": 0.5}

        # Act
        prop1 = engine.propose_diff(
            "brand1", current, {"threshold": 0.55}, objective_key="conversion"
        )
        prop2 = engine.propose_diff(
            "brand1", current, {"threshold": 0.52}, objective_key="awareness"
        )

        # Assert
        assert prop1.objective_key == "conversion"
        assert prop2.objective_key == "awareness"
        assert prop1.proposed_value == 0.55
        assert prop2.proposed_value == 0.52
