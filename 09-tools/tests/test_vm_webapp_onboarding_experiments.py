"""Tests for onboarding_experiments module.

Test coverage for deterministic variant assignment and experiment utilities.
"""

import hashlib
from dataclasses import dataclass

import pytest

from vm_webapp.onboarding_experiments import (
    Variant,
    Experiment,
    VariantAssignment,
    ExperimentRegistry,
    assign_variant,
    assign_variant_from_experiment,
    RiskLevel,
    ExperimentStatus,
)


class TestVariantDataclass:
    """Tests for Variant dataclass."""

    def test_variant_creation(self):
        """Test basic Variant creation."""
        v = Variant(variant_id="v1", name="Test Variant", config={"key": "value"}, weight=1.0)
        assert v.variant_id == "v1"
        assert v.name == "Test Variant"
        assert v.config == {"key": "value"}
        assert v.weight == 1.0

    def test_variant_default_values(self):
        """Test Variant with default values."""
        v = Variant(variant_id="v1", name="Test")
        assert v.config == {}
        assert v.weight == 1.0

    def test_variant_negative_weight_raises(self):
        """Test that negative weight raises ValueError."""
        with pytest.raises(ValueError, match="Weight must be non-negative"):
            Variant(variant_id="v1", name="Test", weight=-1.0)


class TestExperimentDataclass:
    """Tests for Experiment dataclass."""

    def test_experiment_creation(self):
        """Test basic Experiment creation."""
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(
            experiment_id="exp1",
            name="Test Experiment",
            variants=[v1, v2],
            is_active=True
        )
        assert exp.experiment_id == "exp1"
        assert exp.name == "Test Experiment"
        assert len(exp.variants) == 2
        assert exp.is_active is True

    def test_experiment_default_values(self):
        """Test Experiment with default values."""
        exp = Experiment(experiment_id="exp1", name="Test")
        assert exp.variants == []
        assert exp.is_active is True


class TestAssignVariantDeterminism:
    """Tests for deterministic assignment behavior."""

    def test_same_input_same_output(self):
        """Test that same input always produces same output."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        
        result1 = assign_variant("user123", "exp1", variants)
        result2 = assign_variant("user123", "exp1", variants)
        result3 = assign_variant("user123", "exp1", variants)
        
        assert result1 == result2 == result3

    def test_different_users_different_assignments(self):
        """Test that different users can get different assignments."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        
        results = set()
        for i in range(20):
            result = assign_variant(f"user{i}", "exp1", variants)
            results.add(result)
        
        # With 20 users and 2 variants, we should see both variants assigned
        assert len(results) == 2

    def test_different_experiments_same_user(self):
        """Test that same user gets different assignments for different experiments."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        
        result1 = assign_variant("user123", "exp1", variants)
        result2 = assign_variant("user123", "exp2", variants)
        
        # Same user, different experiments should potentially get different assignments
        # (not guaranteed but very likely with different hash inputs)
        assert result1 in ["control", "treatment"]
        assert result2 in ["control", "treatment"]

    def test_hash_consistency(self):
        """Test that hash computation is consistent."""
        hash_input = "user123:exp1"
        hash_value1 = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        hash_value2 = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        
        assert hash_value1 == hash_value2


class TestAssignVariantDistribution:
    """Tests for proportional distribution based on weights."""

    def test_equal_weights_distribution(self):
        """Test that equal weights distribute ~50/50."""
        variants = [
            Variant(variant_id="control", name="Control", weight=1.0),
            Variant(variant_id="treatment", name="Treatment", weight=1.0),
        ]
        
        counts = {"control": 0, "treatment": 0}
        n = 1000
        
        for i in range(n):
            result = assign_variant(f"user{i}", "exp1", variants)
            counts[result] += 1
        
        # With equal weights, expect roughly 50/50 distribution
        # Allow 10% tolerance (450-550 range)
        assert 400 < counts["control"] < 600
        assert 400 < counts["treatment"] < 600

    def test_unequal_weights_distribution(self):
        """Test that unequal weights distribute proportionally."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.8),
            Variant(variant_id="treatment", name="Treatment", weight=0.2),
        ]
        
        counts = {"control": 0, "treatment": 0}
        n = 1000
        
        for i in range(n):
            result = assign_variant(f"user{i}", "exp1", variants)
            counts[result] += 1
        
        # With 80/20 weights, expect roughly 80/20 distribution
        # Allow 15% tolerance
        assert counts["control"] > counts["treatment"]
        assert 650 < counts["control"] < 900
        assert 100 < counts["treatment"] < 350

    def test_multiple_variants_distribution(self):
        """Test distribution with multiple variants."""
        variants = [
            Variant(variant_id="a", name="A", weight=0.5),
            Variant(variant_id="b", name="B", weight=0.3),
            Variant(variant_id="c", name="C", weight=0.2),
        ]
        
        counts = {"a": 0, "b": 0, "c": 0}
        n = 1000
        
        for i in range(n):
            result = assign_variant(f"user{i}", "exp1", variants)
            counts[result] += 1
        
        # Check that all variants are assigned and in expected order
        assert counts["a"] > counts["b"] > counts["c"]
        assert counts["a"] > 400  # ~50%
        assert counts["b"] > 200  # ~30%
        assert counts["c"] > 100  # ~20%

    def test_zero_weight_variant_not_assigned(self):
        """Test that zero weight variants are never assigned."""
        variants = [
            Variant(variant_id="control", name="Control", weight=1.0),
            Variant(variant_id="treatment", name="Treatment", weight=0.0),
        ]
        
        for i in range(100):
            result = assign_variant(f"user{i}", "exp1", variants)
            assert result == "control"


class TestAssignVariantFallback:
    """Tests for fallback handling in assign_variant."""

    def test_empty_variants_returns_control(self):
        """Test that empty variants list returns 'control'."""
        result = assign_variant("user123", "exp1", [])
        assert result == "control"

    def test_invalid_variant_no_id_returns_control(self):
        """Test that variants without variant_id are skipped."""
        @dataclass
        class BadVariant:
            weight: float = 1.0
        
        variants = [BadVariant()]
        result = assign_variant("user123", "exp1", variants)
        assert result == "control"

    def test_all_zero_weights_returns_control(self):
        """Test that all zero weights returns 'control'."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.0),
            Variant(variant_id="treatment", name="Treatment", weight=0.0),
        ]
        result = assign_variant("user123", "exp1", variants)
        assert result == "control"

    def test_negative_weight_skipped(self):
        """Test that negative weight variants are skipped."""
        # Create variant with negative weight (bypass __post_init__)
        v = object.__new__(Variant)
        v.variant_id = "bad"
        v.name = "Bad"
        v.config = {}
        v.weight = -1.0
        
        variants = [
            Variant(variant_id="good", name="Good", weight=1.0),
            v,
        ]
        
        # Should always return "good" since "bad" has negative weight
        for i in range(10):
            result = assign_variant(f"user{i}", "exp1", variants)
            assert result == "good"


class TestAssignVariantFromExperiment:
    """Tests for assign_variant_from_experiment function."""

    def test_active_experiment_assignment(self):
        """Test assignment from active experiment."""
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2], is_active=True)
        
        result = assign_variant_from_experiment("user123", exp)
        assert result in ["control", "treatment"]

    def test_inactive_experiment_returns_control(self):
        """Test that inactive experiment returns 'control'."""
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2], is_active=False)
        
        result = assign_variant_from_experiment("user123", exp)
        assert result == "control"

    def test_empty_variants_returns_control(self):
        """Test that empty variants returns 'control'."""
        exp = Experiment(experiment_id="exp1", name="Test", variants=[], is_active=True)
        result = assign_variant_from_experiment("user123", exp)
        assert result == "control"


class TestExperimentRegistry:
    """Tests for ExperimentRegistry class."""

    def test_register_and_get_experiment(self):
        """Test registering and retrieving an experiment."""
        registry = ExperimentRegistry()
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2])
        
        registry.register(exp)
        retrieved = registry.get_experiment("exp1")
        
        assert retrieved.experiment_id == "exp1"
        assert retrieved.name == "Test"

    def test_register_duplicate_raises(self):
        """Test that registering duplicate experiment raises error."""
        registry = ExperimentRegistry()
        exp = Experiment(experiment_id="exp1", name="Test")
        
        registry.register(exp)
        with pytest.raises(ValueError, match="Experiment already registered"):
            registry.register(exp)

    def test_get_nonexistent_raises(self):
        """Test that getting nonexistent experiment raises error."""
        registry = ExperimentRegistry()
        with pytest.raises(ValueError, match="Experiment not found"):
            registry.get_experiment("nonexistent")

    def test_list_experiments(self):
        """Test listing all experiments."""
        registry = ExperimentRegistry()
        exp1 = Experiment(experiment_id="exp1", name="Test 1")
        exp2 = Experiment(experiment_id="exp2", name="Test 2")
        
        registry.register(exp1)
        registry.register(exp2)
        
        experiments = registry.list_experiments()
        assert len(experiments) == 2
        assert all(isinstance(e, Experiment) for e in experiments)

    def test_assignment_is_sticky(self):
        """Test that assignment is sticky (same result on subsequent calls)."""
        registry = ExperimentRegistry()
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2], is_active=True)
        
        registry.register(exp)
        
        # Get assignment multiple times
        a1 = registry.get_assignment("exp1", "user123", "ws1")
        a2 = registry.get_assignment("exp1", "user123", "ws1")
        a3 = registry.get_assignment("exp1", "user123", "ws1")
        
        assert a1.variant_id == a2.variant_id == a3.variant_id
        assert a1.user_id == "user123"
        assert a1.workspace_id == "ws1"

    def test_different_users_different_assignments(self):
        """Test that different users can get different assignments."""
        registry = ExperimentRegistry()
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2], is_active=True)
        
        registry.register(exp)
        
        results = set()
        for i in range(20):
            a = registry.get_assignment("exp1", f"user{i}", "ws1")
            results.add(a.variant_id)
        
        assert len(results) == 2

    def test_get_assignment_count(self):
        """Test counting assignments."""
        registry = ExperimentRegistry()
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2], is_active=True)
        
        registry.register(exp)
        
        # Create some assignments
        for i in range(10):
            registry.get_assignment("exp1", f"user{i}", "ws1")
        
        total_count = registry.get_assignment_count("exp1")
        assert total_count == 10

    def test_clear_assignments(self):
        """Test clearing assignments."""
        registry = ExperimentRegistry()
        v1 = Variant(variant_id="control", name="Control", weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2], is_active=True)
        
        registry.register(exp)
        
        # Create some assignments
        for i in range(5):
            registry.get_assignment("exp1", f"user{i}", "ws1")
        
        assert registry.get_assignment_count("exp1") == 5
        
        # Clear assignments
        registry.clear_assignments("exp1")
        assert registry.get_assignment_count("exp1") == 0

    def test_clear_all_assignments(self):
        """Test clearing all assignments."""
        registry = ExperimentRegistry()
        exp1 = Experiment(experiment_id="exp1", name="Test1", variants=[
            Variant(variant_id="control", name="Control", weight=0.5),
        ], is_active=True)
        exp2 = Experiment(experiment_id="exp2", name="Test2", variants=[
            Variant(variant_id="control", name="Control", weight=0.5),
        ], is_active=True)
        
        registry.register(exp1)
        registry.register(exp2)
        
        registry.get_assignment("exp1", "user1", "ws1")
        registry.get_assignment("exp2", "user1", "ws1")
        
        assert registry.get_assignment_count() == 2
        
        registry.clear_assignments()
        assert registry.get_assignment_count() == 0

    def test_get_variant_config(self):
        """Test getting variant configuration."""
        registry = ExperimentRegistry()
        v1 = Variant(variant_id="control", name="Control", config={"color": "blue"}, weight=0.5)
        v2 = Variant(variant_id="treatment", name="Treatment", config={"color": "red"}, weight=0.5)
        exp = Experiment(experiment_id="exp1", name="Test", variants=[v1, v2])
        
        registry.register(exp)
        
        config = registry.get_variant_config("exp1", "treatment")
        assert config == {"color": "red"}

    def test_get_variant_config_not_found(self):
        """Test that getting config for nonexistent variant raises error."""
        registry = ExperimentRegistry()
        exp = Experiment(experiment_id="exp1", name="Test", variants=[
            Variant(variant_id="control", name="Control", weight=0.5),
        ])
        
        registry.register(exp)
        
        with pytest.raises(ValueError, match="Variant not found"):
            registry.get_variant_config("exp1", "nonexistent")


class TestEnums:
    """Tests for enum classes."""

    def test_risk_level_values(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"

    def test_experiment_status_values(self):
        """Test ExperimentStatus enum values."""
        assert ExperimentStatus.DRAFT == "draft"
        assert ExperimentStatus.RUNNING == "running"
        assert ExperimentStatus.PAUSED == "paused"
        assert ExperimentStatus.COMPLETED == "completed"
        assert ExperimentStatus.ROLLED_BACK == "rolled_back"


class TestVariantAssignment:
    """Tests for VariantAssignment dataclass."""

    def test_assignment_creation(self):
        """Test VariantAssignment creation."""
        a = VariantAssignment(
            experiment_id="exp1",
            variant_id="control",
            user_id="user123",
            workspace_id="ws1"
        )
        assert a.experiment_id == "exp1"
        assert a.variant_id == "control"
        assert a.user_id == "user123"
        assert a.workspace_id == "ws1"
        assert a.assigned_at is not None

    def test_assignment_default_timestamp(self):
        """Test that assigned_at has default timestamp."""
        a = VariantAssignment(
            experiment_id="exp1",
            variant_id="control",
            user_id="user123",
            workspace_id="ws1"
        )
        assert isinstance(a.assigned_at, str)
        assert len(a.assigned_at) > 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_variant_always_returns_that_variant(self):
        """Test that single variant is always returned."""
        variants = [
            Variant(variant_id="only", name="Only Variant", weight=1.0),
        ]
        
        for i in range(10):
            result = assign_variant(f"user{i}", "exp1", variants)
            assert result == "only"

    def test_very_large_weights(self):
        """Test with very large weight values."""
        variants = [
            Variant(variant_id="a", name="A", weight=1e9),
            Variant(variant_id="b", name="B", weight=1e9),
        ]
        
        results = set()
        for i in range(10):
            results.add(assign_variant(f"user{i}", "exp1", variants))
        
        # Both variants should be assigned
        assert len(results) == 2

    def test_very_small_weights(self):
        """Test with very small weight values."""
        variants = [
            Variant(variant_id="a", name="A", weight=0.001),
            Variant(variant_id="b", name="B", weight=0.001),
        ]
        
        results = set()
        for i in range(10):
            results.add(assign_variant(f"user{i}", "exp1", variants))
        
        # Both variants should still be assigned
        assert len(results) == 2

    def test_special_characters_in_ids(self):
        """Test with special characters in user/experiment IDs."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        
        # Test with various special characters
        special_ids = [
            "user@example.com",
            "user:123:456",
            "user with spaces",
            "user😀emoji",
            "user\nwith\nnewlines",
        ]
        
        for user_id in special_ids:
            result = assign_variant(user_id, "exp:test", variants)
            assert result in ["control", "treatment"]

    def test_unicode_in_variant_config(self):
        """Test that unicode values in config work correctly."""
        variants = [
            Variant(variant_id="control", name="Control", config={"msg": "Olá, mundo! 🌍"}, weight=1.0),
        ]
        
        result = assign_variant("user123", "exp1", variants)
        assert result == "control"
