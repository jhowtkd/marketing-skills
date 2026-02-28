"""Tests for ROI Weighted Policy Optimizer (v19).

Weights:
- business: 40%
- quality: 35%
- efficiency: 25%
"""

import pytest
from datetime import datetime, timezone

from vm_webapp.roi_optimizer import (
    RoiScoreInput,
    RoiCompositeScore,
    RoiScoreCalculator,
    RoiProposal,
    ProposalStatus,
    RiskLevel,
    RoiOptimizer,
)


class TestRoiCompositeScoreCalculation:
    """Test ROI composite score calculation with weighted pillars."""

    def test_roi_composite_score_with_default_weights(self):
        """Composite score calculated with 40/35/25 weights."""
        input_data = RoiScoreInput(
            # Business proxies (40%)
            approval_without_regen_24h=0.75,  # 75% approval rate
            revenue_attribution_usd=100000,
            # Quality proxies (35%)
            regen_per_job=0.5,  # 0.5 regen/job
            quality_score_avg=0.85,
            # Efficiency proxies (25%)
            avg_latency_ms=150,
            cost_per_job_usd=0.05,
        )
        
        calculator = RoiScoreCalculator()
        result = calculator.calculate(input_data)
        
        # Verify score structure
        assert isinstance(result, RoiCompositeScore)
        assert 0.0 <= result.total_score <= 1.0
        
        # Verify weights sum to 100%
        assert result.weights.business == 0.40
        assert result.weights.quality == 0.35
        assert result.weights.efficiency == 0.25
        
        # Verify weighted contributions
        expected_total = (
            result.pillar_scores.business * 0.40 +
            result.pillar_scores.quality * 0.35 +
            result.pillar_scores.efficiency * 0.25
        )
        assert abs(result.total_score - expected_total) < 0.001

    def test_pillar_contributions_sum_to_total(self):
        """Each pillar's weighted contribution is correctly calculated."""
        input_data = RoiScoreInput(
            approval_without_regen_24h=0.80,
            revenue_attribution_usd=150000,
            regen_per_job=0.3,
            quality_score_avg=0.90,
            avg_latency_ms=120,
            cost_per_job_usd=0.04,
        )
        
        calculator = RoiScoreCalculator()
        result = calculator.calculate(input_data)
        
        # Verify individual pillar contributions
        assert result.contributions.business == result.pillar_scores.business * 0.40
        assert result.contributions.quality == result.pillar_scores.quality * 0.35
        assert result.contributions.efficiency == result.pillar_scores.efficiency * 0.25
        
        # Sum of contributions equals total
        total_contribution = (
            result.contributions.business +
            result.contributions.quality +
            result.contributions.efficiency
        )
        assert abs(result.total_score - total_contribution) < 0.001

    def test_normalization_of_proxies(self):
        """Raw proxy values are normalized to 0-1 scale."""
        calculator = RoiScoreCalculator()
        
        # Test with various input ranges
        test_cases = [
            # (approval_rate, regen_per_job, latency_ms) -> should normalize to 0-1
            (0.0, 2.0, 500),   # Worst case
            (0.5, 1.0, 250),   # Middle case
            (1.0, 0.0, 50),    # Best case
        ]
        
        for approval, regen, latency in test_cases:
            input_data = RoiScoreInput(
                approval_without_regen_24h=approval,
                revenue_attribution_usd=50000 + approval * 200000,
                regen_per_job=regen,
                quality_score_avg=0.5 + (1 - regen) * 0.5,
                avg_latency_ms=latency,
                cost_per_job_usd=0.10 - approval * 0.08,
            )
            
            result = calculator.calculate(input_data)
            
            # All pillar scores should be in 0-1 range
            assert 0.0 <= result.pillar_scores.business <= 1.0
            assert 0.0 <= result.pillar_scores.quality <= 1.0
            assert 0.0 <= result.pillar_scores.efficiency <= 1.0

    def test_business_pillar_dominates_with_40_percent(self):
        """Business pillar has highest weight influence."""
        input_data = RoiScoreInput(
            approval_without_regen_24h=1.0,  # Perfect business
            revenue_attribution_usd=500000,
            regen_per_job=2.0,  # Poor quality
            quality_score_avg=0.0,
            avg_latency_ms=1000,  # Poor efficiency
            cost_per_job_usd=1.0,
        )
        
        calculator = RoiScoreCalculator()
        result = calculator.calculate(input_data)
        
        # Business contribution (40%) should offset poor other pillars
        assert result.contributions.business == 0.40  # Perfect score * 40%
        assert result.pillar_scores.business == 1.0


class TestRoiProposalGeneration:
    """Test proposal generation with guardrails."""

    def test_proposal_generation_with_expected_roi_delta(self):
        """Proposals include expected ROI delta calculation."""
        optimizer = RoiOptimizer()
        
        current_state = RoiScoreInput(
            approval_without_regen_24h=0.70,
            revenue_attribution_usd=100000,
            regen_per_job=0.8,
            quality_score_avg=0.75,
            avg_latency_ms=200,
            cost_per_job_usd=0.08,
        )
        
        # Generate proposals for improvement
        proposals = optimizer.generate_proposals(
            current_state=current_state,
            target_improvement=0.10,  # +10% target
        )
        
        assert len(proposals) > 0
        
        for proposal in proposals:
            assert isinstance(proposal, RoiProposal)
            assert proposal.expected_roi_delta is not None
            assert proposal.expected_roi_delta > 0  # Should improve
            assert proposal.description is not None
            assert len(proposal.description) > 0

    def test_hard_stop_when_incident_rate_increases(self):
        """Hard guardrail: block if incident_rate would increase."""
        optimizer = RoiOptimizer()
        
        current_state = RoiScoreInput(
            approval_without_regen_24h=0.70,
            revenue_attribution_usd=100000,
            regen_per_job=0.5,
            quality_score_avg=0.80,
            avg_latency_ms=150,
            cost_per_job_usd=0.05,
            incident_rate=0.02,  # 2% current incident rate
        )
        
        # Try to generate proposal that would increase incidents
        proposals = optimizer.generate_proposals(
            current_state=current_state,
            projected_incident_rate=0.025,  # Would increase incidents
        )
        
        # Should be blocked by hard guardrail
        blocked = [p for p in proposals if p.status == ProposalStatus.BLOCKED]
        assert len(blocked) > 0
        
        for proposal in blocked:
            assert "incident" in proposal.block_reason.lower() or \
                   "risco" in proposal.block_reason.lower()

    def test_clamp_10_percent_per_cycle(self):
        """Adjustments limited to ±10% per cycle."""
        optimizer = RoiOptimizer()
        
        current_state = RoiScoreInput(
            approval_without_regen_24h=0.70,
            revenue_attribution_usd=100000,
            regen_per_job=0.5,
            quality_score_avg=0.80,
            avg_latency_ms=150,
            cost_per_job_usd=0.05,
        )
        
        proposals = optimizer.generate_proposals(
            current_state=current_state,
            target_improvement=0.20,  # Wants 20% improvement
        )
        
        for proposal in proposals:
            if proposal.adjustments:
                for param, delta in proposal.adjustments.items():
                    # Each adjustment must be within ±10%
                    assert abs(delta) <= 0.10, f"{param} delta {delta} exceeds 10% limit"

    def test_low_risk_autoapply_eligibility(self):
        """Low-risk proposals are marked for auto-apply."""
        optimizer = RoiOptimizer()
        
        current_state = RoiScoreInput(
            approval_without_regen_24h=0.85,  # Good state
            revenue_attribution_usd=200000,
            regen_per_job=0.3,
            quality_score_avg=0.90,
            avg_latency_ms=100,
            cost_per_job_usd=0.03,
            incident_rate=0.001,  # Very low incidents
        )
        
        proposals = optimizer.generate_proposals(current_state=current_state)
        
        # Find low-risk proposals
        low_risk = [p for p in proposals if p.risk_level == RiskLevel.LOW]
        
        for proposal in low_risk:
            assert proposal.autoapply_eligible is True
            assert proposal.status == ProposalStatus.PENDING

    def test_high_risk_proposals_require_manual_approval(self):
        """High-risk proposals are not auto-apply eligible."""
        optimizer = RoiOptimizer()
        
        current_state = RoiScoreInput(
            approval_without_regen_24h=0.50,  # Risky state
            revenue_attribution_usd=50000,
            regen_per_job=1.5,  # High regen
            quality_score_avg=0.50,
            avg_latency_ms=500,
            cost_per_job_usd=0.20,
            incident_rate=0.05,  # Higher incidents
        )
        
        proposals = optimizer.generate_proposals(current_state=current_state)
        
        # Find high-risk proposals
        high_risk = [p for p in proposals if p.risk_level == RiskLevel.HIGH]
        
        for proposal in high_risk:
            assert proposal.autoapply_eligible is False


class TestRoiOptimizerModes:
    """Test optimizer operation modes."""

    def test_semi_automatic_mode_default(self):
        """Default mode is semi-automatic (proposals need approval)."""
        optimizer = RoiOptimizer(mode="semi-automatic")
        
        assert optimizer.mode == "semi-automatic"
        
        # In semi-auto, low-risk proposals are eligible for auto-apply
        current_state = RoiScoreInput(
            approval_without_regen_24h=0.90,
            revenue_attribution_usd=300000,
            regen_per_job=0.2,
            quality_score_avg=0.95,
            avg_latency_ms=80,
            cost_per_job_usd=0.02,
        )
        
        proposals = optimizer.generate_proposals(current_state=current_state)
        
        # At least one low-risk proposal should be eligible for auto-apply
        eligible_proposals = [p for p in proposals if p.autoapply_eligible]
        assert len(eligible_proposals) >= 1

    def test_weekly_cadence_default(self):
        """Default cadence is weekly."""
        optimizer = RoiOptimizer()
        
        assert optimizer.cadence == "weekly"


class TestRoiScoreInputValidation:
    """Test input validation."""

    def test_approval_rate_clamped_to_0_1(self):
        """Approval rate must be between 0 and 1."""
        with pytest.raises(ValueError):
            RoiScoreInput(
                approval_without_regen_24h=1.5,  # Invalid > 1
                revenue_attribution_usd=100000,
                regen_per_job=0.5,
                quality_score_avg=0.80,
                avg_latency_ms=150,
                cost_per_job_usd=0.05,
            )

    def test_quality_score_clamped_to_0_1(self):
        """Quality score must be between 0 and 1."""
        with pytest.raises(ValueError):
            RoiScoreInput(
                approval_without_regen_24h=0.70,
                revenue_attribution_usd=100000,
                regen_per_job=0.5,
                quality_score_avg=1.5,  # Invalid > 1
                avg_latency_ms=150,
                cost_per_job_usd=0.05,
            )

    def test_negative_values_rejected(self):
        """Negative values are rejected."""
        with pytest.raises(ValueError):
            RoiScoreInput(
                approval_without_regen_24h=-0.1,  # Invalid negative
                revenue_attribution_usd=100000,
                regen_per_job=0.5,
                quality_score_avg=0.80,
                avg_latency_ms=150,
                cost_per_job_usd=0.05,
            )
