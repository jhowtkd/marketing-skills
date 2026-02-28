"""Tests for API v2 operations - multibrand policy operations (v18).

Endpoints:
- GET /v2/brands/{brand_id}/policy/effective
- GET /v2/brands/{brand_id}/policy/proposals
- POST /v2/brands/{brand_id}/policy/proposals/{proposal_id}/approve
- POST /v2/brands/{brand_id}/policy/proposals/{proposal_id}/reject
- POST /v2/brands/{brand_id}/policy/freeze
- POST /v2/brands/{brand_id}/policy/rollback
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

# Test imports from the modules being tested
from vm_webapp.policy_operations import (
    PolicyOperationsService,
    PolicyFreeze,
    PolicyRollback,
    ProposalNotFoundError,
    ProposalNotApprovedError,
    PolicyFrozenError,
)
from vm_webapp.policy_adaptation import (
    PolicyProposalEngine,
    AdaptationProposal,
    ProposalStatus,
    DivergenceGuard,
)
from vm_webapp.policy_hierarchy import (
    resolve_effective_policy,
    EffectivePolicy,
    PolicySource,
)


class TestPolicyOperationsService:
    """Test PolicyOperationsService."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create PolicyOperationsService with mocked session."""
        return PolicyOperationsService(mock_session)

    def test_get_effective_policy(self, service, mock_session):
        """Should return effective policy for brand."""
        # Arrange
        with patch('vm_webapp.policy_operations.resolve_effective_policy') as mock_resolve:
            mock_resolve.return_value = EffectivePolicy(
                threshold=0.5,
                mode="standard",
                source=PolicySource.GLOBAL,
            )
            
            # Act
            result = service.get_effective_policy("brand1")

            # Assert
            assert result.threshold == 0.5
            assert result.mode == "standard"
            assert result.source == PolicySource.GLOBAL
            mock_resolve.assert_called_once()

    def test_get_effective_policy_with_segment(self, service, mock_session):
        """Should return effective policy with segment resolution."""
        # Arrange
        with patch('vm_webapp.policy_operations.resolve_effective_policy') as mock_resolve:
            mock_resolve.return_value = EffectivePolicy(
                threshold=0.7,
                mode="enterprise",
                source=PolicySource.SEGMENT,
                source_brand_id="brand1",
                source_segment="enterprise",
            )
            
            # Act
            result = service.get_effective_policy("brand1", segment="enterprise")

            # Assert
            assert result.source == PolicySource.SEGMENT
            assert result.source_segment == "enterprise"

    def test_create_proposal(self, service, mock_session):
        """Should create a new proposal."""
        # Arrange
        current = {"threshold": 0.5, "mode": "standard"}
        suggested = {"threshold": 0.55, "mode": "strict"}
        
        # Mock the proposal engine's propose_diff method directly
        mock_proposal = AdaptationProposal(
            proposal_id="prop-123",
            brand_id="brand1",
            objective_key="conversion",
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )
        service._proposal_engine._proposals = {}  # Clear any existing
        with patch.object(service._proposal_engine, 'propose_diff', return_value=mock_proposal):
            # Act
            result = service.create_proposal("brand1", current, suggested, objective_key="conversion")

            # Assert
            assert result is not None
            assert result.proposal_id == "prop-123"
            assert result.brand_id == "brand1"
            assert result.status == ProposalStatus.PENDING

    def test_create_proposal_frozen_brand(self, service, mock_session):
        """Should raise error when brand is frozen."""
        # Arrange
        service._frozen_brands = {"brand1"}
        current = {"threshold": 0.5}
        suggested = {"threshold": 0.55}
        
        # Act & Assert
        with pytest.raises(PolicyFrozenError):
            service.create_proposal("brand1", current, suggested)

    def test_approve_proposal(self, service, mock_session):
        """Should approve a pending proposal."""
        # Arrange
        proposal = AdaptationProposal(
            proposal_id="prop-123",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )
        service._proposals = {"prop-123": proposal}
        
        # Act
        result = service.approve_proposal("brand1", "prop-123", approver="admin")

        # Assert
        assert result.status == ProposalStatus.APPROVED
        assert result.approved_by == "admin"
        assert result.approved_at is not None

    def test_approve_nonexistent_proposal(self, service, mock_session):
        """Should raise error for non-existent proposal."""
        # Act & Assert
        with pytest.raises(ProposalNotFoundError):
            service.approve_proposal("brand1", "nonexistent", approver="admin")

    def test_reject_proposal(self, service, mock_session):
        """Should reject a pending proposal."""
        # Arrange
        proposal = AdaptationProposal(
            proposal_id="prop-123",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )
        service._proposals = {"prop-123": proposal}
        
        # Act
        result = service.reject_proposal("brand1", "prop-123", reason="Too aggressive")

        # Assert
        assert result.status == ProposalStatus.REJECTED
        assert result.rejection_reason == "Too aggressive"

    def test_apply_proposal(self, service, mock_session):
        """Should apply an approved proposal."""
        # Arrange
        proposal = AdaptationProposal(
            proposal_id="prop-123",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.APPROVED,
            current_params={"threshold": 0.5},
            proposed_params={"threshold": 0.55},
        )
        service._proposals = {"prop-123": proposal}
        
        # Act
        result = service.apply_proposal("brand1", "prop-123")

        # Assert
        assert result["threshold"] == 0.55
        assert proposal.status == ProposalStatus.APPLIED
        assert proposal.applied_at is not None

    def test_apply_pending_proposal_fails(self, service, mock_session):
        """Should fail to apply non-approved proposal."""
        # Arrange
        proposal = AdaptationProposal(
            proposal_id="prop-123",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )
        service._proposals = {"prop-123": proposal}
        
        # Act & Assert
        with pytest.raises(ProposalNotApprovedError):
            service.apply_proposal("brand1", "prop-123")

    def test_freeze_policy(self, service, mock_session):
        """Should freeze policy changes for brand."""
        # Act
        result = service.freeze_policy("brand1", reason="Incident investigation")

        # Assert
        assert result.frozen is True
        assert result.brand_id == "brand1"
        assert result.reason == "Incident investigation"
        assert "brand1" in service._frozen_brands

    def test_freeze_already_frozen(self, service, mock_session):
        """Should raise error if already frozen."""
        # Arrange
        service.freeze_policy("brand1", reason="First freeze")
        
        # Act & Assert
        with pytest.raises(PolicyFrozenError):
            service.freeze_policy("brand1", reason="Second freeze")

    def test_unfreeze_policy(self, service, mock_session):
        """Should unfreeze a frozen brand."""
        # Arrange
        service.freeze_policy("brand1", reason="Freeze")
        
        # Act
        result = service.unfreeze_policy("brand1")

        # Assert
        assert result.frozen is False
        assert "brand1" not in service._frozen_brands

    def test_rollback_policy(self, service, mock_session):
        """Should rollback to previous policy version."""
        # Arrange - create some history
        service._policy_history["brand1"] = [
            {"threshold": 0.4},
            {"threshold": 0.5},
        ]
        
        # Act
        result = service.rollback_policy("brand1", steps=1)

        # Assert
        assert result.rolled_back is True
        assert result.previous_version == {"threshold": 0.5}

    def test_rollback_without_history(self, service, mock_session):
        """Should raise error if no history to rollback."""
        # Act & Assert
        with pytest.raises(ValueError):
            service.rollback_policy("brand1", steps=1)

    def test_list_proposals(self, service, mock_session):
        """Should list proposals for brand."""
        # Arrange
        proposal1 = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )
        proposal2 = AdaptationProposal(
            proposal_id="prop-2",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.52,
            adjustment_percent=4.0,
            status=ProposalStatus.APPROVED,
        )
        service._proposals = {"prop-1": proposal1, "prop-2": proposal2}
        
        # Act
        result = service.list_proposals("brand1")

        # Assert
        assert len(result) == 2

    def test_list_proposals_filtered_by_status(self, service, mock_session):
        """Should filter proposals by status."""
        # Arrange
        proposal1 = AdaptationProposal(
            proposal_id="prop-1",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.55,
            adjustment_percent=10.0,
            status=ProposalStatus.PENDING,
        )
        proposal2 = AdaptationProposal(
            proposal_id="prop-2",
            brand_id="brand1",
            objective_key=None,
            current_value=0.5,
            proposed_value=0.52,
            adjustment_percent=4.0,
            status=ProposalStatus.APPROVED,
        )
        service._proposals = {"prop-1": proposal1, "prop-2": proposal2}
        
        # Act
        result = service.list_proposals("brand1", status=ProposalStatus.PENDING)

        # Assert
        assert len(result) == 1
        assert result[0].proposal_id == "prop-1"


class TestPolicyFreeze:
    """Test PolicyFreeze dataclass."""

    def test_policy_freeze_creation(self):
        """Should create PolicyFreeze with correct attributes."""
        freeze = PolicyFreeze(
            freeze_id="freeze-123",
            brand_id="brand1",
            reason="Incident",
            frozen_at=datetime.now(timezone.utc).isoformat(),
            frozen=True,
        )
        
        assert freeze.freeze_id == "freeze-123"
        assert freeze.brand_id == "brand1"
        assert freeze.reason == "Incident"
        assert freeze.frozen is True


class TestPolicyRollback:
    """Test PolicyRollback dataclass."""

    def test_policy_rollback_creation(self):
        """Should create PolicyRollback with correct attributes."""
        rollback = PolicyRollback(
            rollback_id="rollback-123",
            brand_id="brand1",
            previous_version={"threshold": 0.5},
            rolled_back=True,
            reason="Revert failed experiment",
        )
        
        assert rollback.rollback_id == "rollback-123"
        assert rollback.brand_id == "brand1"
        assert rollback.previous_version == {"threshold": 0.5}
        assert rollback.rolled_back is True
