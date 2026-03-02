"""Tests for onboarding experiment registry and deterministic assignment."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from vm_webapp.onboarding_experiments import (
    Experiment,
    ExperimentRegistry,
    ExperimentStatus,
    ExperimentVariant,
    RiskLevel,
    VariantAssignment,
)


class TestExperimentVariant:
    """Test experiment variant model."""

    def test_variant_creation(self):
        """Test creating a variant."""
        variant = ExperimentVariant(
            variant_id="control",
            name="Control",
            config={"nudge_delay_ms": 5000},
            traffic_allocation=50,
        )
        assert variant.variant_id == "control"
        assert variant.name == "Control"
        assert variant.config == {"nudge_delay_ms": 5000}
        assert variant.traffic_allocation == 50

    def test_variant_traffic_allocation_validation(self):
        """Test traffic allocation must be between 0 and 100."""
        with pytest.raises(ValueError, match="Traffic allocation must be between 0 and 100"):
            ExperimentVariant(
                variant_id="test",
                name="Test",
                config={},
                traffic_allocation=150,
            )


class TestExperiment:
    """Test experiment model."""

    def test_experiment_creation(self):
        """Test creating an experiment."""
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {"nudge_delay_ms": 3000}, 50),
        ]
        experiment = Experiment(
            experiment_id="onboarding_nudge_timing_v1",
            name="Onboarding Nudge Timing",
            description="Testing different nudge delays",
            hypothesis="Shorter delay increases activation",
            primary_metric="template_to_first_run_conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        assert experiment.experiment_id == "onboarding_nudge_timing_v1"
        assert experiment.status == ExperimentStatus.DRAFT
        assert len(experiment.variants) == 2
        assert experiment.risk_level == RiskLevel.LOW

    def test_experiment_variants_must_sum_to_100(self):
        """Test variant allocations must sum to 100."""
        variants = [
            ExperimentVariant("control", "Control", {}, 40),
            ExperimentVariant("treatment", "Treatment", {}, 40),
        ]
        with pytest.raises(ValueError, match="Variant traffic allocations must sum to 100"):
            Experiment(
                experiment_id="test",
                name="Test",
                description="Test",
                hypothesis="Test",
                primary_metric="metric",
                variants=variants,
                risk_level=RiskLevel.LOW,
                min_sample_size=100,
                min_confidence=0.95,
                max_lift_threshold=0.10,
            )

    def test_experiment_requires_at_least_two_variants(self):
        """Test experiment needs at least 2 variants."""
        variants = [ExperimentVariant("control", "Control", {}, 100)]
        with pytest.raises(ValueError, match="At least 2 variants required"):
            Experiment(
                experiment_id="test",
                name="Test",
                description="Test",
                hypothesis="Test",
                primary_metric="metric",
                variants=variants,
                risk_level=RiskLevel.LOW,
                min_sample_size=100,
                min_confidence=0.95,
                max_lift_threshold=0.10,
            )


class TestVariantAssignment:
    """Test deterministic variant assignment."""

    def test_deterministic_assignment(self):
        """Test assignment is deterministic for same user."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        registry.start_experiment("test_exp")

        # Same user should always get same variant
        assignment1 = registry.get_assignment("test_exp", "user_123", "workspace_456")
        assignment2 = registry.get_assignment("test_exp", "user_123", "workspace_456")
        assert assignment1.variant_id == assignment2.variant_id
        assert assignment1.user_id == "user_123"
        assert assignment1.workspace_id == "workspace_456"

    def test_assignment_sticky_per_user_workspace(self):
        """Test assignment is sticky per user+workspace combination."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        registry.start_experiment("test_exp")

        # Different users should potentially get different variants
        assignment1 = registry.get_assignment("test_exp", "user_1", "workspace_1")
        assignment2 = registry.get_assignment("test_exp", "user_2", "workspace_1")
        
        # Both should have valid variant IDs
        assert assignment1.variant_id in ["control", "treatment"]
        assert assignment2.variant_id in ["control", "treatment"]

    def test_assignment_distribution_approximates_allocation(self):
        """Test assignment distribution matches traffic allocation."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=1000,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        registry.start_experiment("test_exp")

        # Assign many users
        control_count = 0
        treatment_count = 0
        for i in range(1000):
            assignment = registry.get_assignment("test_exp", f"user_{i}", f"workspace_{i}")
            if assignment.variant_id == "control":
                control_count += 1
            else:
                treatment_count += 1

        # Should be roughly 50/50 (within 10% margin)
        total = control_count + treatment_count
        control_pct = control_count / total
        assert 0.40 <= control_pct <= 0.60, f"Control percentage {control_pct} outside expected range"

    def test_assignment_fails_for_nonexistent_experiment(self):
        """Test assignment fails for non-existent experiment."""
        registry = ExperimentRegistry()
        with pytest.raises(ValueError, match="Experiment not found"):
            registry.get_assignment("nonexistent", "user_123", "workspace_456")

    def test_assignment_fails_for_non_running_experiment(self):
        """Test assignment fails for experiment not in running status."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        with pytest.raises(ValueError, match="Experiment not running"):
            registry.get_assignment("test_exp", "user_123", "workspace_456")


class TestExperimentRegistry:
    """Test experiment registry operations."""

    def test_register_experiment(self):
        """Test registering an experiment."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        retrieved = registry.get_experiment("test_exp")
        assert retrieved.experiment_id == "test_exp"

    def test_register_duplicate_experiment_fails(self):
        """Test registering duplicate experiment fails."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        with pytest.raises(ValueError, match="Experiment already registered"):
            registry.register(experiment)

    def test_start_experiment(self):
        """Test starting an experiment."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        registry.start_experiment("test_exp")
        
        retrieved = registry.get_experiment("test_exp")
        assert retrieved.status == ExperimentStatus.RUNNING
        assert retrieved.started_at is not None

    def test_pause_experiment(self):
        """Test pausing an experiment."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        registry.start_experiment("test_exp")
        registry.pause_experiment("test_exp")
        
        retrieved = registry.get_experiment("test_exp")
        assert retrieved.status == ExperimentStatus.PAUSED

    def test_list_experiments(self):
        """Test listing experiments."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        
        for i in range(3):
            experiment = Experiment(
                experiment_id=f"test_exp_{i}",
                name=f"Test {i}",
                description="Test",
                hypothesis="Test",
                primary_metric="metric",
                variants=variants,
                risk_level=RiskLevel.LOW,
                min_sample_size=100,
                min_confidence=0.95,
                max_lift_threshold=0.10,
            )
            registry.register(experiment)
        
        experiments = registry.list_experiments()
        assert len(experiments) == 3

    def test_get_variant_config(self):
        """Test getting variant config for assignment."""
        registry = ExperimentRegistry()
        variants = [
            ExperimentVariant("control", "Control", {"delay": 5000}, 50),
            ExperimentVariant("treatment", "Treatment", {"delay": 3000}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="metric",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        registry.start_experiment("test_exp")
        
        assignment = registry.get_assignment("test_exp", "user_123", "workspace_456")
        config = registry.get_variant_config("test_exp", assignment.variant_id)
        
        assert "delay" in config
        assert config["delay"] in [3000, 5000]
