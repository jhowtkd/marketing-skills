"""Tests for v31 onboarding activation rule engine."""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

# Import will fail initially - implementation needed
# from vm_webapp.onboarding_activation import (
#     OnboardingActivationEngine,
#     AdjustmentProposal,
#     RiskLevel,
#     ProposalStatus,
# )


class TestOnboardingActivationEngine:
    """Test the onboarding activation rule engine."""

    def test_engine_initialization(self):
        """Test engine can be initialized."""
        # This will fail until we implement the class
        from vm_webapp.onboarding_activation import OnboardingActivationEngine
        
        engine = OnboardingActivationEngine()
        assert engine is not None

    def test_rule_evaluation_low_risk(self):
        """Test evaluation of a low-risk rule (auto-apply eligible)."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine, RiskLevel
        
        engine = OnboardingActivationEngine()
        
        # Mock metrics showing high step 1 dropoff
        metrics = {
            "completion_rate": 0.45,
            "step_1_dropoff_rate": 0.35,
            "average_time_to_first_action_ms": 120000,
        }
        
        proposals = engine.evaluate_rules("brand-123", metrics)
        
        # Should generate at least one low-risk proposal
        low_risk_proposals = [p for p in proposals if p["risk_level"] == RiskLevel.LOW]
        assert len(low_risk_proposals) > 0

    def test_rule_evaluation_medium_risk(self):
        """Test evaluation of a medium-risk rule (approval required)."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine, RiskLevel
        
        engine = OnboardingActivationEngine()
        
        # Mock metrics showing high workspace setup abandon vs template selection
        # This triggers the "reorder_onboarding_steps" medium-risk rule
        metrics = {
            "completion_rate": 0.45,
            "abandon_by_step": {
                "workspace_setup": 35,  # High abandon on workspace setup
                "template_selection": 10,  # Much lower on template selection
            },
        }
        
        proposals = engine.evaluate_rules("brand-123", metrics)
        
        # Should generate at least one medium-risk proposal
        medium_risk = [p for p in proposals if p["risk_level"] == RiskLevel.MEDIUM]
        assert len(medium_risk) > 0

    def test_rule_evaluation_high_risk(self):
        """Test evaluation of a high-risk rule (requires review)."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine, RiskLevel
        
        engine = OnboardingActivationEngine()
        
        # Mock metrics showing significant issues
        metrics = {
            "completion_rate": 0.25,
            "step_1_dropoff_rate": 0.60,
            "total_abandons": 100,
        }
        
        proposals = engine.evaluate_rules("brand-123", metrics)
        
        # Should generate at least one high-risk proposal
        high_risk = [p for p in proposals if p["risk_level"] == RiskLevel.HIGH]
        assert len(high_risk) > 0

    def test_max_adjustment_per_cycle(self):
        """Test that adjustments respect ±10% max per cycle."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine
        
        engine = OnboardingActivationEngine()
        
        # Any proposal should have adjustment within ±10%
        metrics = {"completion_rate": 0.50}
        proposals = engine.evaluate_rules("brand-123", metrics)
        
        for proposal in proposals:
            if "adjustment_percent" in proposal:
                assert -10 <= proposal["adjustment_percent"] <= 10

    def test_proposal_structure(self):
        """Test that generated proposals have required fields."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine
        
        engine = OnboardingActivationEngine()
        metrics = {"completion_rate": 0.40}
        
        proposals = engine.evaluate_rules("brand-123", metrics)
        
        for proposal in proposals:
            assert "id" in proposal
            assert "rule_name" in proposal
            assert "description" in proposal
            assert "risk_level" in proposal
            assert "current_value" in proposal
            assert "target_value" in proposal
            assert "expected_impact" in proposal

    def test_proposal_auto_apply_for_low_risk(self):
        """Test that low-risk proposals can be auto-applied."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine, RiskLevel, ProposalStatus
        
        engine = OnboardingActivationEngine()
        metrics = {"step_1_dropoff_rate": 0.40}
        
        proposals = engine.evaluate_rules("brand-123", metrics)
        low_risk = [p for p in proposals if p["risk_level"] == RiskLevel.LOW]
        
        if low_risk:
            proposal = low_risk[0]
            result = engine.apply_proposal("brand-123", proposal["id"])
            assert result["status"] == ProposalStatus.APPLIED
            assert result["auto_applied"] is True

    def test_proposal_requires_approval_for_medium_risk(self):
        """Test that medium-risk proposals require approval."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine, RiskLevel, ProposalStatus
        
        engine = OnboardingActivationEngine()
        metrics = {"template_to_first_run_conversion": 0.35}
        
        proposals = engine.evaluate_rules("brand-123", metrics)
        medium = [p for p in proposals if p["risk_level"] == RiskLevel.MEDIUM]
        
        if medium:
            proposal = medium[0]
            # Without approval, should be pending
            assert proposal["status"] == ProposalStatus.PENDING

    def test_proposal_freeze(self):
        """Test freezing proposals for a brand."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine
        
        engine = OnboardingActivationEngine()
        
        result = engine.freeze_proposals("brand-123")
        assert result["frozen"] is True
        assert result["brand_id"] == "brand-123"

    def test_proposal_rollback(self):
        """Test rolling back last applied proposal."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine, RiskLevel, ProposalStatus
        
        engine = OnboardingActivationEngine()
        
        # First apply a low-risk proposal
        metrics = {"step_1_dropoff_rate": 0.40}
        proposals = engine.evaluate_rules("brand-123", metrics)
        low_risk = [p for p in proposals if p["risk_level"] == RiskLevel.LOW][0]
        
        engine.apply_proposal("brand-123", low_risk["id"])
        
        # Then rollback
        result = engine.rollback_last("brand-123")
        assert result["rolled_back"] is True

    def test_get_proposals_for_brand(self):
        """Test retrieving proposals for a brand."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine
        
        engine = OnboardingActivationEngine()
        
        # Generate some proposals first
        metrics = {"completion_rate": 0.45}
        engine.evaluate_rules("brand-123", metrics)
        
        proposals = engine.get_proposals("brand-123")
        assert isinstance(proposals, list)
        assert len(proposals) > 0

    def test_top_friction_identification(self):
        """Test identification of top friction points."""
        from vm_webapp.onboarding_activation import OnboardingActivationEngine
        
        engine = OnboardingActivationEngine()
        
        metrics = {
            "abandon_by_step": {
                "workspace_setup": 25,
                "template_selection": 10,
                "customization": 5,
            },
            "abandon_reasons": {
                "too_complex": 20,
                "no_relevant_templates": 8,
                "interruption": 5,
            },
        }
        
        frictions = engine.identify_top_frictions("brand-123", metrics)
        
        assert len(frictions) > 0
        # Top friction should be workspace_setup (25 abandons)
        assert frictions[0]["step"] == "workspace_setup"


class TestAdjustmentProposal:
    """Test the adjustment proposal model."""

    def test_proposal_creation(self):
        """Test creating a proposal."""
        from vm_webapp.onboarding_activation import AdjustmentProposal, RiskLevel
        
        proposal = AdjustmentProposal(
            id="prop-1",
            rule_name="reduce_step_1_complexity",
            description="Simplify workspace setup",
            risk_level=RiskLevel.LOW,
            current_value=0.35,
            target_value=0.25,
            adjustment_percent=-10,
            expected_impact="Reduce dropoff by 5-8%",
        )
        
        assert proposal.id == "prop-1"
        assert proposal.risk_level == RiskLevel.LOW


class TestRiskLevel:
    """Test risk level enum."""

    def test_risk_levels_defined(self):
        """Test that all risk levels are defined."""
        from vm_webapp.onboarding_activation import RiskLevel
        
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
