"""Tests for hybrid ROI engine with quality guardrails (v36).

TDD: fail -> implement -> pass -> commit
"""

import pytest
from datetime import datetime, timezone, timedelta
from vm_webapp.hybrid_roi_engine import (
    FinancialMetrics,
    OperationalMetrics,
    QualityPenalty,
    ProposalRiskLevel,
    HybridScore,
    Proposal,
    GuardrailRule,
    BlockRule,
    HybridROIEngine,
)
from vm_webapp.outcome_attribution import OutcomeType, TouchpointType


class TestFinancialMetrics:
    """Test financial metrics calculation."""

    def test_financial_metrics_creation(self):
        """Should create financial metrics."""
        metrics = FinancialMetrics(
            revenue_per_activation=100.0,
            cost_per_activation=20.0,
        )
        assert metrics.revenue_per_activation == 100.0
        assert metrics.cost_per_activation == 20.0

    def test_financial_roi_calculation(self):
        """Should calculate financial ROI."""
        metrics = FinancialMetrics(
            revenue_per_activation=100.0,
            cost_per_activation=20.0,
        )
        assert metrics.roi == 4.0  # (100-20)/20

    def test_payback_time_calculation(self):
        """Should calculate payback time in days."""
        metrics = FinancialMetrics(
            revenue_per_activation=100.0,
            cost_per_activation=20.0,
            time_to_revenue_days=14,
        )
        assert metrics.payback_time_days == pytest.approx(2.8, rel=0.01)

    def test_hybrid_roi_index_contribution(self):
        """Should contribute to hybrid ROI index."""
        metrics = FinancialMetrics(
            revenue_per_activation=100.0,
            cost_per_activation=20.0,
        )
        # Financial contributes 60% by default
        assert metrics.to_hybrid_contribution() == pytest.approx(2.4, rel=0.01)


class TestOperationalMetrics:
    """Test operational metrics calculation."""

    def test_operational_metrics_creation(self):
        """Should create operational metrics."""
        metrics = OperationalMetrics(
            human_minutes_per_activation=30.0,
            success_rate=0.85,
        )
        assert metrics.human_minutes_per_activation == 30.0
        assert metrics.success_rate == 0.85

    def test_efficiency_score_calculation(self):
        """Should calculate efficiency score."""
        metrics = OperationalMetrics(
            human_minutes_per_activation=30.0,
            success_rate=0.85,
        )
        # Efficiency = success_rate / (human_minutes / 60)
        assert metrics.efficiency_score == pytest.approx(1.7, rel=0.01)

    def test_hybrid_roi_index_contribution(self):
        """Should contribute to hybrid ROI index."""
        metrics = OperationalMetrics(
            human_minutes_per_activation=30.0,
            success_rate=0.85,
        )
        # Operational contributes 40% by default
        assert metrics.to_hybrid_contribution() == pytest.approx(0.68, rel=0.01)


class TestQualityPenalty:
    """Test quality penalty application."""

    def test_penalty_calculation_incident(self):
        """Should apply incident penalty."""
        penalty = QualityPenalty.for_incident(severity="high")
        assert penalty.factor > 0
        assert penalty.reason == "high_severity_incident"

    def test_penalty_calculation_quality_degradation(self):
        """Should apply quality degradation penalty."""
        penalty = QualityPenalty.for_quality_degradation(
            metric_name="user_satisfaction",
            drop_percentage=15.0,
        )
        assert penalty.factor > 0
        assert "user_satisfaction" in penalty.reason

    def test_penalty_factor_range(self):
        """Penalty factor should be between 0 and 1."""
        penalty = QualityPenalty(factor=0.25, reason="test")
        assert 0 <= penalty.factor <= 1


class TestProposalRiskLevel:
    """Test proposal risk level enumeration."""

    def test_risk_levels(self):
        """Should have expected risk levels."""
        assert ProposalRiskLevel.LOW.value == "low"
        assert ProposalRiskLevel.MEDIUM.value == "medium"
        assert ProposalRiskLevel.HIGH.value == "high"

    def test_from_score_classification(self):
        """Should classify scores into risk levels."""
        assert ProposalRiskLevel.from_hybrid_score(0.15) == ProposalRiskLevel.LOW
        assert ProposalRiskLevel.from_hybrid_score(0.10) == ProposalRiskLevel.MEDIUM
        assert ProposalRiskLevel.from_hybrid_score(0.05) == ProposalRiskLevel.HIGH


class TestHybridScore:
    """Test hybrid score calculation."""

    def test_score_creation(self):
        """Should create hybrid score."""
        score = HybridScore(
            financial_component=2.0,
            operational_component=1.0,
            quality_penalty=QualityPenalty(factor=0.1, reason="minor_issue"),
        )
        assert score.financial_component == 2.0
        assert score.operational_component == 1.0

    def test_hybrid_index_calculation(self):
        """Should calculate hybrid ROI index."""
        score = HybridScore(
            financial_component=2.0,
            operational_component=1.0,
        )
        # (2.0 * 0.6) + (1.0 * 0.4) = 1.6
        assert score.hybrid_index == pytest.approx(1.6, rel=0.01)

    def test_penalty_application(self):
        """Should apply quality penalty to index."""
        score = HybridScore(
            financial_component=2.0,
            operational_component=1.0,
            quality_penalty=QualityPenalty(factor=0.25, reason="test"),
        )
        # Base: 1.6, after 25% penalty: 1.2
        assert score.penalized_index == pytest.approx(1.2, rel=0.01)

    def test_explanation_generation(self):
        """Should generate human-readable explanation."""
        score = HybridScore(
            financial_component=2.0,
            operational_component=1.0,
            quality_penalty=QualityPenalty(factor=0.1, reason="incident"),
        )
        explanation = score.explain()
        assert "financial" in explanation.lower()
        assert "operational" in explanation.lower()
        assert "penalty" in explanation.lower()


class TestProposal:
    """Test proposal structure."""

    def test_proposal_creation(self):
        """Should create proposal."""
        score = HybridScore(
            financial_component=2.0,
            operational_component=1.0,
        )
        proposal = Proposal(
            proposal_id="prop_001",
            brand_id="brand_123",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            action="increase_priority",
            expected_impact={"completion_rate": 0.05},
            score=score,
        )
        assert proposal.proposal_id == "prop_001"
        assert proposal.risk_level == ProposalRiskLevel.LOW

    def test_proposal_risk_classification(self):
        """Should classify proposal risk from score."""
        low_score = HybridScore(financial_component=2.0, operational_component=2.0)
        medium_score = HybridScore(financial_component=0.15, operational_component=0.05)  # ~0.11
        high_score = HybridScore(financial_component=0.05, operational_component=0.05)  # ~0.05
        
        low_proposal = Proposal(
            proposal_id="p1", brand_id="b1",
            touchpoint_type=TouchpointType.NUDGE,
            action="test", expected_impact={},
            score=low_score,
        )
        medium_proposal = Proposal(
            proposal_id="p2", brand_id="b1",
            touchpoint_type=TouchpointType.NUDGE,
            action="test", expected_impact={},
            score=medium_score,
        )
        high_proposal = Proposal(
            proposal_id="p3", brand_id="b1",
            touchpoint_type=TouchpointType.NUDGE,
            action="test", expected_impact={},
            score=high_score,
        )
        
        assert low_proposal.risk_level == ProposalRiskLevel.LOW
        assert medium_proposal.risk_level == ProposalRiskLevel.MEDIUM
        assert high_proposal.risk_level == ProposalRiskLevel.HIGH

    def test_proposal_to_dict(self):
        """Should convert proposal to dictionary."""
        score = HybridScore(financial_component=1.5, operational_component=1.0)
        proposal = Proposal(
            proposal_id="prop_001",
            brand_id="brand_123",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            action="optimize_flow",
            expected_impact={"human_minutes": -5},
            score=score,
        )
        data = proposal.to_dict()
        assert data["proposal_id"] == "prop_001"
        assert "hybrid_index" in data


class TestGuardrailRule:
    """Test guardrail rule evaluation."""

    def test_rule_creation(self):
        """Should create guardrail rule."""
        rule = GuardrailRule(
            name="min_success_rate",
            check=lambda m: m.success_rate > 0.8,
            message="Success rate must be > 80%",
        )
        assert rule.name == "min_success_rate"

    def test_rule_evaluation_pass(self):
        """Should pass when condition met."""
        rule = GuardrailRule(
            name="min_success_rate",
            check=lambda m: m.get("success_rate", 0) > 0.8,
            message="Success rate must be > 80%",
        )
        metrics = {"success_rate": 0.9}
        assert rule.evaluate(metrics) is True

    def test_rule_evaluation_fail(self):
        """Should fail when condition not met."""
        rule = GuardrailRule(
            name="min_success_rate",
            check=lambda m: m.get("success_rate", 0) > 0.8,
            message="Success rate must be > 80%",
        )
        metrics = {"success_rate": 0.7}
        assert rule.evaluate(metrics) is False


class TestBlockRule:
    """Test block rule enforcement."""

    def test_block_rule_creation(self):
        """Should create block rule."""
        rule = BlockRule(
            name="no_incident_spike",
            condition=lambda ctx: ctx.get("incident_rate", 0) < 0.05,
            block_message="Blocked: incident rate spike detected",
        )
        assert rule.name == "no_incident_spike"

    def test_block_rule_allows(self):
        """Should allow when condition passes."""
        rule = BlockRule(
            name="no_incident_spike",
            condition=lambda ctx: ctx.get("incident_rate", 0) < 0.05,
            block_message="Blocked: incident rate spike detected",
        )
        context = {"incident_rate": 0.02}
        assert rule.check(context).blocked is False

    def test_block_rule_blocks(self):
        """Should block when condition fails."""
        rule = BlockRule(
            name="no_incident_spike",
            condition=lambda ctx: ctx.get("incident_rate", 0) < 0.05,
            block_message="Blocked: incident rate spike detected",
        )
        context = {"incident_rate": 0.08}
        result = rule.check(context)
        assert result.blocked is True
        assert "incident" in result.reason.lower()


class TestHybridROIEngine:
    """Test hybrid ROI engine."""

    def test_engine_creation(self):
        """Should create engine with default rules."""
        engine = HybridROIEngine()
        assert engine is not None
        assert len(engine.guardrail_rules) > 0
        assert len(engine.block_rules) > 0

    def test_calculate_financial_metrics(self):
        """Should calculate financial metrics from data."""
        engine = HybridROIEngine()
        data = {
            "revenue": 1000.0,
            "cost": 200.0,
            "activations": 10,
            "time_to_revenue_days": 14.0,
        }
        metrics = engine.calculate_financial_metrics(data)
        assert metrics.revenue_per_activation == 100.0
        assert metrics.cost_per_activation == 20.0

    def test_calculate_operational_metrics(self):
        """Should calculate operational metrics from data."""
        engine = HybridROIEngine()
        data = {
            "human_minutes": 300.0,
            "activations": 10,
            "successes": 9,
        }
        metrics = engine.calculate_operational_metrics(data)
        assert metrics.human_minutes_per_activation == 30.0
        assert metrics.success_rate == 0.9

    def test_calculate_hybrid_score(self):
        """Should calculate hybrid score from metrics."""
        engine = HybridROIEngine()
        financial = FinancialMetrics(
            revenue_per_activation=100.0,
            cost_per_activation=20.0,
        )
        operational = OperationalMetrics(
            human_minutes_per_activation=30.0,
            success_rate=0.9,
        )
        score = engine.calculate_hybrid_score(financial, operational)
        assert score.hybrid_index > 0

    def test_generate_proposal(self):
        """Should generate optimization proposal."""
        engine = HybridROIEngine()
        proposal = engine.generate_proposal(
            brand_id="brand_123",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            action="reduce_steps",
            expected_impact={"human_minutes": -10},
            financial_data={
                "revenue": 1000.0, "cost": 200.0,
                "activations": 10, "time_to_revenue_days": 14.0,
            },
            operational_data={
                "human_minutes": 300.0, "activations": 10, "successes": 9,
            },
        )
        assert proposal.proposal_id is not None
        assert proposal.brand_id == "brand_123"

    def test_check_guardrails_pass(self):
        """Should pass guardrails check."""
        engine = HybridROIEngine()
        context = {"success_rate": 0.9, "incident_rate": 0.01, "user_satisfaction": 0.8}
        result = engine.check_guardrails(context)
        assert result.passed is True
        assert len(result.violations) == 0

    def test_check_guardrails_fail(self):
        """Should fail guardrails check with violations."""
        engine = HybridROIEngine()
        context = {"success_rate": 0.7, "incident_rate": 0.01}
        result = engine.check_guardrails(context)
        assert result.passed is False
        assert len(result.violations) > 0

    def test_check_blocks_pass(self):
        """Should pass block rules check."""
        engine = HybridROIEngine()
        context = {"incident_rate": 0.02}
        result = engine.check_blocks(context)
        assert result.blocked is False

    def test_check_blocks_fail(self):
        """Should fail block rules check."""
        engine = HybridROIEngine()
        context = {"incident_rate": 0.08}
        result = engine.check_blocks(context)
        assert result.blocked is True
        assert result.reason is not None

    def test_evaluate_proposal_autoapply_low_risk(self):
        """Should auto-approve low-risk proposals."""
        engine = HybridROIEngine()
        score = HybridScore(financial_component=2.0, operational_component=2.0)
        proposal = Proposal(
            proposal_id="p1", brand_id="b1",
            touchpoint_type=TouchpointType.NUDGE,
            action="test", expected_impact={},
            score=score,
        )
        context = {"success_rate": 0.9, "incident_rate": 0.01, "user_satisfaction": 0.8}
        result = engine.evaluate_proposal(proposal, context)
        assert result.autoapply is True
        assert result.approval_required is False

    def test_evaluate_proposal_needs_approval_medium_risk(self):
        """Should require approval for medium-risk proposals."""
        engine = HybridROIEngine()
        score = HybridScore(financial_component=1.0, operational_component=0.8)
        proposal = Proposal(
            proposal_id="p1", brand_id="b1",
            touchpoint_type=TouchpointType.NUDGE,
            action="test", expected_impact={},
            score=score,
        )
        context = {"success_rate": 0.85, "incident_rate": 0.02}
        result = engine.evaluate_proposal(proposal, context)
        assert result.autoapply is False
        assert result.approval_required is True

    def test_evaluate_proposal_blocked(self):
        """Should block proposals violating block rules."""
        engine = HybridROIEngine()
        score = HybridScore(financial_component=2.0, operational_component=2.0)
        proposal = Proposal(
            proposal_id="p1", brand_id="b1",
            touchpoint_type=TouchpointType.NUDGE,
            action="test", expected_impact={},
            score=score,
        )
        context = {"success_rate": 0.9, "incident_rate": 0.08}  # High incident rate
        result = engine.evaluate_proposal(proposal, context)
        assert result.blocked is True

    def test_get_roi_summary(self):
        """Should provide ROI summary."""
        engine = HybridROIEngine()
        # Generate some proposals
        for i in range(3):
            engine.generate_proposal(
                brand_id="brand_123",
                touchpoint_type=TouchpointType.ONBOARDING_STEP,
                action=f"action_{i}",
                expected_impact={},
                financial_data={"revenue": 1000, "cost": 200, "activations": 10, "time_to_revenue_days": 14},
                operational_data={"human_minutes": 300, "activations": 10, "successes": 9},
            )
        
        summary = engine.get_roi_summary(brand_id="brand_123")
        assert "total_proposals" in summary
        assert "avg_hybrid_index" in summary
        assert "by_risk_level" in summary
