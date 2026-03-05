"""Tests for onboarding_experiments module.

Test coverage for deterministic variant assignment and experiment utilities.
v45: Added RolloutPolicy integration tests.
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
    RolloutPolicy,
    RolloutMode,
    RolloutPolicyStatus,
    RolloutPolicyManager,
    get_variant_with_policy,
    assign_variant_with_policy,
    get_global_policy_manager,
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


# =============================================================================
# v45: RolloutPolicy Integration Tests
# =============================================================================

class TestRolloutPolicy:
    """Tests for RolloutPolicy dataclass."""

    def test_policy_creation_defaults(self):
        """Test RolloutPolicy with default values."""
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
        )
        assert policy.policy_id == "policy-001"
        assert policy.experiment_id == "exp-001"
        assert policy.active_variant == "control"
        assert policy.mode == RolloutMode.MANUAL
        assert policy.status == RolloutPolicyStatus.INACTIVE

    def test_policy_creation_custom(self):
        """Test RolloutPolicy with custom values."""
        policy = RolloutPolicy(
            policy_id="policy-002",
            experiment_id="exp-002",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        assert policy.active_variant == "treatment"
        assert policy.mode == RolloutMode.AUTO
        assert policy.status == RolloutPolicyStatus.ACTIVE

    def test_policy_activate(self):
        """Test activating a policy."""
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
        )
        policy.activate(variant_id="variant_a")
        assert policy.status == RolloutPolicyStatus.ACTIVE
        assert policy.active_variant == "variant_a"
        assert policy.activated_at is not None

    def test_policy_deactivate(self):
        """Test deactivating a policy."""
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
            status=RolloutPolicyStatus.ACTIVE,
        )
        policy.deactivate()
        assert policy.status == RolloutPolicyStatus.INACTIVE

    def test_policy_rollback(self):
        """Test rolling back a policy."""
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
            status=RolloutPolicyStatus.ACTIVE,
        )
        policy.rollback()
        assert policy.status == RolloutPolicyStatus.ROLLED_BACK

    def test_policy_is_active(self):
        """Test is_active check."""
        active_policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="e1",
            status=RolloutPolicyStatus.ACTIVE,
        )
        inactive_policy = RolloutPolicy(
            policy_id="p2",
            experiment_id="e2",
            status=RolloutPolicyStatus.INACTIVE,
        )
        assert active_policy.is_active() is True
        assert inactive_policy.is_active() is False

    def test_policy_is_auto(self):
        """Test is_auto check."""
        auto_policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="e1",
            mode=RolloutMode.AUTO,
        )
        manual_policy = RolloutPolicy(
            policy_id="p2",
            experiment_id="e2",
            mode=RolloutMode.MANUAL,
        )
        assert auto_policy.is_auto() is True
        assert manual_policy.is_auto() is False

    def test_policy_should_apply(self):
        """Test should_apply_policy logic."""
        # Auto + active + non-control = should apply
        should_apply = RolloutPolicy(
            policy_id="p1",
            experiment_id="e1",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
            active_variant="treatment",
        )
        assert should_apply.should_apply_policy() is True

        # Control variant should not apply
        control_policy = RolloutPolicy(
            policy_id="p2",
            experiment_id="e2",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
            active_variant="control",
        )
        assert control_policy.should_apply_policy() is False

        # Manual mode should not apply
        manual_policy = RolloutPolicy(
            policy_id="p3",
            experiment_id="e3",
            mode=RolloutMode.MANUAL,
            status=RolloutPolicyStatus.ACTIVE,
            active_variant="treatment",
        )
        assert manual_policy.should_apply_policy() is False


class TestRolloutPolicyManager:
    """Tests for RolloutPolicyManager."""

    def test_manager_register_and_get(self):
        """Test registering and retrieving a policy."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
        )
        manager.register_policy(policy)
        
        retrieved = manager.get_policy("policy-001")
        assert retrieved.policy_id == "policy-001"

    def test_manager_register_duplicate_raises(self):
        """Test that registering duplicate policy raises error."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
        )
        manager.register_policy(policy)
        
        with pytest.raises(ValueError, match="Policy already registered"):
            manager.register_policy(policy)

    def test_manager_get_nonexistent_raises(self):
        """Test that getting nonexistent policy raises error."""
        manager = RolloutPolicyManager()
        with pytest.raises(ValueError, match="Policy not found"):
            manager.get_policy("nonexistent")

    def test_manager_get_policy_for_experiment(self):
        """Test getting policy by experiment ID."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        found = manager.get_policy_for_experiment("exp-001")
        assert found is not None
        assert found.policy_id == "policy-001"

    def test_manager_get_policy_for_experiment_inactive(self):
        """Test that inactive policies are not returned."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
            status=RolloutPolicyStatus.INACTIVE,
        )
        manager.register_policy(policy)
        
        found = manager.get_policy_for_experiment("exp-001")
        assert found is None

    def test_manager_get_policy_no_match(self):
        """Test that non-matching experiment returns None."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="policy-001",
            experiment_id="exp-001",
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        found = manager.get_policy_for_experiment("exp-999")
        assert found is None

    def test_manager_list_policies(self):
        """Test listing all policies."""
        manager = RolloutPolicyManager()
        manager.register_policy(RolloutPolicy(policy_id="p1", experiment_id="e1"))
        manager.register_policy(RolloutPolicy(policy_id="p2", experiment_id="e2"))
        
        policies = manager.list_policies()
        assert len(policies) == 2

    def test_manager_clear(self):
        """Test clearing all policies."""
        manager = RolloutPolicyManager()
        manager.register_policy(RolloutPolicy(policy_id="p1", experiment_id="e1"))
        manager.clear()
        
        assert len(manager.list_policies()) == 0


class TestAssignVariantWithPolicy:
    """Tests for assign_variant_with_policy function."""

    def test_no_policy_uses_hash(self):
        """Test that without policy, hash assignment is used."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        
        variant_id, source = assign_variant_with_policy("user123", "exp1", variants)
        assert variant_id in ["control", "treatment"]
        assert source == "hash"

    def test_inactive_policy_uses_hash(self):
        """Test that inactive policy falls back to hash."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.INACTIVE,
        )
        
        variant_id, source = assign_variant_with_policy("user123", "exp1", variants, policy)
        assert variant_id in ["control", "treatment"]
        assert source == "hash"

    def test_auto_policy_applies_active_variant(self):
        """Test that auto mode applies active_variant directly."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        
        variant_id, source = assign_variant_with_policy("user123", "exp1", variants, policy)
        assert variant_id == "treatment"
        assert source == "policy_auto"

    def test_manual_policy_uses_hash(self):
        """Test that manual mode uses hash assignment."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.MANUAL,
            status=RolloutPolicyStatus.ACTIVE,
        )
        
        variant_id, source = assign_variant_with_policy("user123", "exp1", variants, policy)
        assert variant_id in ["control", "treatment"]
        assert source == "policy_manual"

    def test_invalid_variant_fallback_to_control(self):
        """Test that invalid active_variant falls back to control."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="nonexistent",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        
        variant_id, source = assign_variant_with_policy("user123", "exp1", variants, policy)
        assert variant_id == "control"
        assert source == "control_fallback"

    def test_control_variant_no_override(self):
        """Test that control active_variant doesn't override."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="control",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        
        # should_apply_policy returns False for control
        variant_id, source = assign_variant_with_policy("user123", "exp1", variants, policy)
        # Falls through to hash because should_apply_policy is False
        assert variant_id in ["control", "treatment"]
        assert source == "hash"


class TestGetVariantWithPolicy:
    """Tests for get_variant_with_policy function."""

    def test_no_policy_returns_hash(self):
        """Test that without policy, hash assignment is returned."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        variant_id, policy, source = get_variant_with_policy("user123", exp)
        assert variant_id in ["control", "treatment"]
        assert policy is None
        assert source == "hash"

    def test_inactive_experiment_returns_control(self):
        """Test that inactive experiment returns control."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=False)
        
        variant_id, policy, source = get_variant_with_policy("user123", exp)
        assert variant_id == "control"
        assert policy is None
        assert source == "control_fallback"

    def test_auto_policy_returns_active_variant(self):
        """Test that auto policy returns active_variant."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        variant_id, used_policy, source = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "treatment"
        assert used_policy == policy
        assert source == "policy_auto"

    def test_manual_policy_returns_hash(self):
        """Test that manual policy returns hash assignment."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.MANUAL,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        variant_id, used_policy, source = get_variant_with_policy("user123", exp, manager)
        assert variant_id in ["control", "treatment"]
        assert used_policy == policy
        assert source == "policy_manual"

    def test_invalid_variant_fallback(self):
        """Test that invalid policy variant falls back to control."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="nonexistent",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        variant_id, used_policy, source = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "control"
        assert used_policy == policy
        assert source == "control_fallback"

    def test_global_registry_fallback(self):
        """Test fallback to global policy registry."""
        from vm_webapp.onboarding_experiments import _rollout_policy_registry
        
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        _rollout_policy_registry["p1"] = policy
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        variant_id, used_policy, source = get_variant_with_policy("user123", exp)
        assert variant_id == "treatment"
        assert used_policy == policy
        
        # Cleanup
        del _rollout_policy_registry["p1"]


class TestControlPromoteRollbackFlow:
    """Integration tests for control -> promote -> rollback flow."""

    def test_control_to_promote_flow(self):
        """Test flow from control to promoted variant."""
        manager = RolloutPolicyManager()
        
        # Start with manual policy (control)
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="control",
            mode=RolloutMode.MANUAL,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        # Initially in manual mode, should use hash
        variant_id, _, source = get_variant_with_policy("user123", exp, manager)
        assert source == "policy_manual"
        
        # Promote: activate treatment in auto mode
        policy.activate(variant_id="treatment")
        policy.mode = RolloutMode.AUTO
        
        variant_id, _, source = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "treatment"
        assert source == "policy_auto"

    def test_promote_to_rollback_flow(self):
        """Test flow from promoted to rolled back."""
        manager = RolloutPolicyManager()
        
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        # Initially auto-promoted
        variant_id, _, source = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "treatment"
        assert source == "policy_auto"
        
        # Rollback
        policy.rollback()
        
        variant_id, _, source = get_variant_with_policy("user123", exp, manager)
        assert source == "hash"  # Rolled back policy is not active

    def test_multiple_users_consistent_with_policy(self):
        """Test that all users get consistent assignment with policy."""
        manager = RolloutPolicyManager()
        
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        # All users should get treatment with auto policy
        for i in range(100):
            variant_id, _, source = get_variant_with_policy(f"user{i}", exp, manager)
            assert variant_id == "treatment"
            assert source == "policy_auto"


class TestBackwardCompatibilityV44:
    """Tests to ensure backward compatibility with v44 behavior."""

    def test_v44_hash_assignment_unchanged(self):
        """Test that v44 hash assignment behavior is preserved."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        
        # Same user should get same variant (deterministic)
        result1 = assign_variant("user123", "exp1", variants)
        result2 = assign_variant("user123", "exp1", variants)
        result3 = assign_variant("user123", "exp1", variants)
        
        assert result1 == result2 == result3

    def test_v44_distribution_unchanged(self):
        """Test that v44 distribution behavior is preserved."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        
        counts = {"control": 0, "treatment": 0}
        n = 1000
        
        for i in range(n):
            result = assign_variant(f"user{i}", "exp1", variants)
            counts[result] += 1
        
        # Should be roughly 50/50
        assert 400 < counts["control"] < 600
        assert 400 < counts["treatment"] < 600

    def test_v44_registry_behavior_unchanged(self):
        """Test that v44 registry behavior is preserved."""
        registry = ExperimentRegistry()
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        registry.register(exp)
        
        # Assignment should be sticky
        a1 = registry.get_assignment("exp1", "user123", "ws1")
        a2 = registry.get_assignment("exp1", "user123", "ws1")
        
        assert a1.variant_id == a2.variant_id

    def test_v44_empty_variants_returns_control(self):
        """Test that v44 empty variants behavior is preserved."""
        result = assign_variant("user123", "exp1", [])
        assert result == "control"

    def test_v44_inactive_experiment_returns_control(self):
        """Test that v44 inactive experiment behavior is preserved."""
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=False)
        
        result = assign_variant_from_experiment("user123", exp)
        assert result == "control"


class TestPolicyIntegrationEdgeCases:
    """Edge case tests for policy integration."""

    def test_policy_with_single_variant(self):
        """Test policy with single variant experiment."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="only",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="only", name="Only", weight=1.0),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        variant_id, _, source = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "only"
        assert source == "policy_auto"

    def test_policy_with_multiple_treatment_variants(self):
        """Test policy selecting one of multiple treatment variants."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="variant_b",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.25),
            Variant(variant_id="variant_a", name="A", weight=0.25),
            Variant(variant_id="variant_b", name="B", weight=0.25),
            Variant(variant_id="variant_c", name="C", weight=0.25),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        variant_id, _, source = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "variant_b"
        assert source == "policy_auto"

    def test_policy_switching_modes(self):
        """Test switching policy between auto and manual modes."""
        manager = RolloutPolicyManager()
        policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.MANUAL,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.5),
            Variant(variant_id="treatment", name="Treatment", weight=0.5),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        # Manual mode - hash assignment
        _, _, source1 = get_variant_with_policy("user123", exp, manager)
        assert source1 == "policy_manual"
        
        # Switch to auto
        policy.mode = RolloutMode.AUTO
        variant_id, _, source2 = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "treatment"
        assert source2 == "policy_auto"

    def test_multiple_policies_same_experiment(self):
        """Test that only active policy is considered."""
        manager = RolloutPolicyManager()
        
        # Inactive policy (first)
        inactive_policy = RolloutPolicy(
            policy_id="p1",
            experiment_id="exp1",
            active_variant="treatment",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.INACTIVE,
        )
        manager.register_policy(inactive_policy)
        
        # Active policy (second)
        active_policy = RolloutPolicy(
            policy_id="p2",
            experiment_id="exp1",
            active_variant="variant_a",
            mode=RolloutMode.AUTO,
            status=RolloutPolicyStatus.ACTIVE,
        )
        manager.register_policy(active_policy)
        
        variants = [
            Variant(variant_id="control", name="Control", weight=0.33),
            Variant(variant_id="treatment", name="Treatment", weight=0.33),
            Variant(variant_id="variant_a", name="A", weight=0.34),
        ]
        exp = Experiment(experiment_id="exp1", name="Test", variants=variants, is_active=True)
        
        # Should use the active policy
        variant_id, used_policy, _ = get_variant_with_policy("user123", exp, manager)
        assert variant_id == "variant_a"
        assert used_policy == active_policy

    def test_global_policy_manager_singleton(self):
        """Test that global policy manager is accessible."""
        manager = get_global_policy_manager()
        assert manager is not None
        
        # Should be same instance
        manager2 = get_global_policy_manager()
        assert manager is manager2
