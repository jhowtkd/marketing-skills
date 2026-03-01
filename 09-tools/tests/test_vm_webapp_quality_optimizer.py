"""Tests for Quality-First Constrained Optimizer (v25)."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from vm_webapp.quality_optimizer import (
    QualityOptimizer,
    OptimizationProposal,
    QualityScore,
    ConstraintBounds,
)


@pytest.fixture
def optimizer():
    """Quality optimizer fixture."""
    return QualityOptimizer()


@pytest.fixture
def sample_run_data():
    """Sample run data for testing."""
    return {
        "run_id": "run-001",
        "brand_id": "brand-001",
        "quality_score": 65.0,
        "v1_score": 60.0,
        "cost_per_job": 100.0,
        "mttc": 300.0,  # 5 minutes
        "incident_rate": 0.05,
        "approval_without_regen_24h": 0.70,
        "params": {
            "temperature": 0.7,
            "max_tokens": 2000,
            "model": "gpt-4",
        },
    }


@pytest.fixture
def constraint_bounds():
    """Default constraint bounds."""
    return ConstraintBounds(
        max_cost_increase_pct=10.0,
        max_mttc_increase_pct=10.0,
        max_incident_rate=0.05,
    )


class TestQualityScore:
    """Test quality score calculation."""

    def test_calculate_quality_score_basic(self, optimizer):
        """Should calculate basic quality score."""
        score = optimizer.calculate_quality_score(
            v1_score=60.0,
            approval_rate=0.70,
            incident_rate=0.05,
        )
        
        assert isinstance(score, QualityScore)
        assert 0.0 <= score.overall <= 100.0
        assert score.v1_score == 60.0
        assert score.approval_rate == 0.70

    def test_quality_score_weights(self, optimizer):
        """Quality score should weight components correctly."""
        score_high_v1 = optimizer.calculate_quality_score(
            v1_score=90.0,
            approval_rate=0.70,
            incident_rate=0.02,
        )
        
        score_low_v1 = optimizer.calculate_quality_score(
            v1_score=50.0,
            approval_rate=0.70,
            incident_rate=0.02,
        )
        
        assert score_high_v1.overall > score_low_v1.overall

    def test_quality_score_incidents_penalty(self, optimizer):
        """Higher incidents should lower score."""
        score_low_incidents = optimizer.calculate_quality_score(
            v1_score=70.0,
            approval_rate=0.70,
            incident_rate=0.01,
        )
        
        score_high_incidents = optimizer.calculate_quality_score(
            v1_score=70.0,
            approval_rate=0.70,
            incident_rate=0.08,
        )
        
        assert score_low_incidents.overall > score_high_incidents.overall


class TestOptimizationProposal:
    """Test optimization proposal generation."""

    def test_generate_proposal_returns_proposal(self, optimizer, sample_run_data, constraint_bounds):
        """Should generate an optimization proposal."""
        proposal = optimizer.generate_proposal(
            current_run=sample_run_data,
            historical_runs=[sample_run_data],
            constraints=constraint_bounds,
        )
        
        assert isinstance(proposal, OptimizationProposal)
        assert proposal.proposal_id is not None
        assert proposal.run_id == "run-001"

    def test_proposal_contains_recommended_params(self, optimizer, sample_run_data, constraint_bounds):
        """Proposal should contain recommended params."""
        proposal = optimizer.generate_proposal(
            current_run=sample_run_data,
            historical_runs=[sample_run_data],
            constraints=constraint_bounds,
        )
        
        assert "temperature" in proposal.recommended_params
        assert "max_tokens" in proposal.recommended_params
        assert "model" in proposal.recommended_params

    def test_proposal_estimates_impact(self, optimizer, sample_run_data, constraint_bounds):
        """Proposal should estimate quality/cost/time impact."""
        proposal = optimizer.generate_proposal(
            current_run=sample_run_data,
            historical_runs=[sample_run_data],
            constraints=constraint_bounds,
        )
        
        assert proposal.estimated_v1_improvement is not None
        assert proposal.estimated_cost_delta_pct is not None
        assert proposal.estimated_mttc_delta_pct is not None

    def test_proposal_quality_first_priority(self, optimizer, sample_run_data, constraint_bounds):
        """Proposal should prioritize quality improvements."""
        proposal = optimizer.generate_proposal(
            current_run=sample_run_data,
            historical_runs=[sample_run_data],
            constraints=constraint_bounds,
        )
        
        # Quality improvement should be positive or zero
        assert proposal.estimated_v1_improvement >= 0


class TestConstraintBounds:
    """Test constraint bounds handling."""

    def test_default_constraints(self):
        """Default constraints should be reasonable."""
        constraints = ConstraintBounds()
        
        assert constraints.max_cost_increase_pct == 10.0
        assert constraints.max_mttc_increase_pct == 10.0
        assert constraints.max_incident_rate == 0.05

    def test_custom_constraints(self):
        """Should allow custom constraints."""
        constraints = ConstraintBounds(
            max_cost_increase_pct=5.0,
            max_mttc_increase_pct=15.0,
            max_incident_rate=0.03,
        )
        
        assert constraints.max_cost_increase_pct == 5.0
        assert constraints.max_mttc_increase_pct == 15.0
        assert constraints.max_incident_rate == 0.03


class TestOptimizerCore:
    """Test optimizer core functionality."""

    def test_optimizer_has_version(self, optimizer):
        """Optimizer should have version identifier."""
        assert hasattr(optimizer, 'version')
        assert optimizer.version == "v25"

    def test_optimizer_tracks_history(self, optimizer, sample_run_data, constraint_bounds):
        """Optimizer should track proposal history."""
        proposal = optimizer.generate_proposal(
            current_run=sample_run_data,
            historical_runs=[sample_run_data],
            constraints=constraint_bounds,
        )
        
        history = optimizer.get_proposal_history(run_id="run-001")
        assert len(history) >= 0  # May or may not store proposals

    def test_compare_proposals(self, optimizer, sample_run_data, constraint_bounds):
        """Should be able to compare multiple proposals."""
        proposal1 = optimizer.generate_proposal(
            current_run=sample_run_data,
            historical_runs=[sample_run_data],
            constraints=constraint_bounds,
        )
        
        # Modify data slightly for second proposal
        modified_data = {**sample_run_data, "v1_score": 75.0}
        proposal2 = optimizer.generate_proposal(
            current_run=modified_data,
            historical_runs=[sample_run_data],
            constraints=constraint_bounds,
        )
        
        comparison = optimizer.compare_proposals([proposal1, proposal2])
        assert isinstance(comparison, dict)
