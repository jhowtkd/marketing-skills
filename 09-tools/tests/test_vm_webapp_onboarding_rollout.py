"""Tests for v45 Auto-Rollout motor de decisão/promote/rollback.

Testes abrangentes para o motor de rollout de onboarding com:
- Validação de promoção
- Bloqueio por critérios
- Rollback por degradação
- Fallback seguro
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from vm_webapp.onboarding_rollout_policy import (
    # Enums
    RolloutMode,
    GateName,
    # Data structures
    BenchmarkMetrics,
    PromotionResult,
    RolloutPolicy,
    RollbackDecision,
    # Promotion Engine
    check_promotion_gates,
    evaluate_promotion,
    # Rollback Engine
    check_rollback_conditions,
    evaluate_rollback,
    rollback,
    # Policy Persistence
    load_policy,
    save_policy,
    list_active_policies,
    delete_policy,
    reset_policy,
    # Telemetry
    log_promotion_decision,
    log_rollback_decision,
    get_telemetry_logs,
    clear_telemetry_logs,
    # Orchestrator
    run_auto_rollout,
    # Constants
    GATE_THRESHOLDS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory for tests."""
    config_dir = tmp_path / "config" / "rollout_policies"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Patch the config dir function
    import vm_webapp.onboarding_rollout_policy as policy_module
    original_get_config_dir = policy_module._get_config_dir
    policy_module._get_config_dir = lambda: config_dir
    
    yield config_dir
    
    # Restore original function
    policy_module._get_config_dir = original_get_config_dir
    clear_telemetry_logs()


@pytest.fixture
def sample_control_metrics():
    """Sample control metrics."""
    return BenchmarkMetrics(
        ttfv=120.0,
        completion_rate=0.75,
        abandonment_rate=0.15,
        score=0.80,
        sample_size=100,
    )


@pytest.fixture
def sample_variant_metrics():
    """Sample variant metrics (better than control)."""
    return BenchmarkMetrics(
        ttfv=110.0,
        completion_rate=0.78,
        abandonment_rate=0.14,
        score=0.85,
        sample_size=50,
    )


@pytest.fixture
def sample_policy():
    """Sample rollout policy."""
    return RolloutPolicy(
        experiment_id="test-exp-001",
        active_variant="control",
        rollout_mode=RolloutMode.AUTO,
        rollback_target="control",
    )


# =============================================================================
# TESTS: DATA STRUCTURES
# =============================================================================

class TestBenchmarkMetrics:
    """Test BenchmarkMetrics dataclass."""
    
    def test_benchmark_metrics_creation(self):
        """Test creating BenchmarkMetrics."""
        metrics = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        assert metrics.ttfv == 120.0
        assert metrics.completion_rate == 0.75
        assert metrics.abandonment_rate == 0.15
        assert metrics.score == 0.80
        assert metrics.sample_size == 100
    
    def test_benchmark_metrics_zero_values(self):
        """Test BenchmarkMetrics with zero values."""
        metrics = BenchmarkMetrics(
            ttfv=0.0,
            completion_rate=0.0,
            abandonment_rate=0.0,
            score=0.0,
            sample_size=0,
        )
        assert metrics.ttfv == 0.0
        assert metrics.sample_size == 0


class TestPromotionResult:
    """Test PromotionResult dataclass."""
    
    def test_promotion_result_success(self):
        """Test successful PromotionResult."""
        result = PromotionResult(
            success=True,
            variant_id="variant-a",
            gates_passed=["gain_gate", "stability_gate"],
            gates_failed=[],
            reason="All gates passed",
        )
        assert result.success is True
        assert result.variant_id == "variant-a"
        assert len(result.gates_passed) == 2
        assert len(result.gates_failed) == 0
    
    def test_promotion_result_failure(self):
        """Test failed PromotionResult."""
        result = PromotionResult(
            success=False,
            variant_id="variant-b",
            gates_passed=["stability_gate"],
            gates_failed=["gain_gate"],
            reason="Gain gate failed",
        )
        assert result.success is False
        assert len(result.gates_passed) == 1
        assert len(result.gates_failed) == 1


class TestRolloutPolicy:
    """Test RolloutPolicy dataclass."""
    
    def test_rollout_policy_defaults(self):
        """Test RolloutPolicy default values."""
        policy = RolloutPolicy(experiment_id="exp-001")
        assert policy.active_variant == "control"
        assert policy.rollout_mode == RolloutMode.AUTO
        assert policy.rollback_target == "control"
        assert policy.last_evaluation is None
    
    def test_rollout_policy_custom_values(self):
        """Test RolloutPolicy with custom values."""
        now = datetime.now(timezone.utc).isoformat()
        policy = RolloutPolicy(
            experiment_id="exp-002",
            active_variant="variant-a",
            rollout_mode=RolloutMode.SUPERVISED,
            last_evaluation=now,
            decision_reason="Promoted after evaluation",
            rollback_target="control",
        )
        assert policy.active_variant == "variant-a"
        assert policy.rollout_mode == RolloutMode.SUPERVISED
        assert policy.last_evaluation == now


class TestRollbackDecision:
    """Test RollbackDecision dataclass."""
    
    def test_rollback_decision_should_rollback(self):
        """Test RollbackDecision when rollback is needed."""
        decision = RollbackDecision(
            should_rollback=True,
            reason="Degradation detected",
            from_variant="variant-a",
            to_variant="control",
        )
        assert decision.should_rollback is True
        assert decision.from_variant == "variant-a"
        assert decision.to_variant == "control"
    
    def test_rollback_decision_no_rollback(self):
        """Test RollbackDecision when no rollback needed."""
        decision = RollbackDecision(
            should_rollback=False,
            reason="No degradation",
            from_variant="control",
            to_variant="control",
        )
        assert decision.should_rollback is False


# =============================================================================
# TESTS: PROMOTION ENGINE - GATES
# =============================================================================

class TestCheckPromotionGates:
    """Test check_promotion_gates function."""
    
    def test_all_gates_pass(self, sample_control_metrics, sample_variant_metrics):
        """Test when all gates pass."""
        gates = check_promotion_gates(sample_control_metrics, sample_variant_metrics)
        
        assert gates[GateName.GAIN] is True  # 0.85 > 0.80 * 1.005
        assert gates[GateName.STABILITY] is True  # 50 >= 30
        assert gates[GateName.RISK] is True  # 0.78 >= 0.75 * 0.95
        assert gates[GateName.ABANDONMENT] is True  # 0.14 <= 0.15 * 1.10
        assert gates[GateName.REGRESSION] is True  # 110 <= 120 * 1.10
    
    def test_gain_gate_fail(self, sample_control_metrics):
        """Test gain gate failure when score is not high enough."""
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.78,
            abandonment_rate=0.14,
            score=0.80,  # Same as control, not > 0.5%
            sample_size=50,
        )
        gates = check_promotion_gates(sample_control_metrics, variant)
        
        assert gates[GateName.GAIN] is False
        assert gates[GateName.STABILITY] is True
    
    def test_stability_gate_fail(self, sample_control_metrics):
        """Test stability gate failure with low sample size."""
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.78,
            abandonment_rate=0.14,
            score=0.85,
            sample_size=20,  # Less than 30
        )
        gates = check_promotion_gates(sample_control_metrics, variant)
        
        assert gates[GateName.STABILITY] is False
        assert gates[GateName.GAIN] is True
    
    def test_risk_gate_fail(self, sample_control_metrics):
        """Test risk gate failure with low completion rate."""
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.70,  # Less than 0.75 * 0.95 = 0.7125
            abandonment_rate=0.14,
            score=0.85,
            sample_size=50,
        )
        gates = check_promotion_gates(sample_control_metrics, variant)
        
        assert gates[GateName.RISK] is False
    
    def test_abandonment_gate_fail(self, sample_control_metrics):
        """Test abandonment gate failure with high abandonment."""
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.78,
            abandonment_rate=0.20,  # More than 0.15 * 1.10 = 0.165
            score=0.85,
            sample_size=50,
        )
        gates = check_promotion_gates(sample_control_metrics, variant)
        
        assert gates[GateName.ABANDONMENT] is False
    
    def test_regression_gate_fail(self, sample_control_metrics):
        """Test regression gate failure with high TTFV."""
        variant = BenchmarkMetrics(
            ttfv=150.0,  # More than 120 * 1.10 = 132
            completion_rate=0.78,
            abandonment_rate=0.14,
            score=0.85,
            sample_size=50,
        )
        gates = check_promotion_gates(sample_control_metrics, variant)
        
        assert gates[GateName.REGRESSION] is False
    
    def test_custom_thresholds(self, sample_control_metrics, sample_variant_metrics):
        """Test with custom thresholds."""
        custom_thresholds = {
            GateName.GAIN: 1.10,  # Require 10% gain
            GateName.STABILITY: 50,
            GateName.RISK: 0.90,
            GateName.ABANDONMENT: 1.20,
            GateName.REGRESSION: 1.20,
        }
        gates = check_promotion_gates(
            sample_control_metrics,
            sample_variant_metrics,
            custom_thresholds,
        )
        
        # With 10% gain threshold, variant score 0.85 < 0.80 * 1.10 = 0.88
        assert gates[GateName.GAIN] is False
        # With 50 sample threshold, variant sample 50 >= 50
        assert gates[GateName.STABILITY] is True
    
    def test_exact_threshold_gain_gate(self, sample_control_metrics):
        """Test gain gate at exact threshold."""
        # Exact threshold: 0.80 * 1.005 = 0.804
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.78,
            abandonment_rate=0.14,
            score=0.804,  # Just above threshold
            sample_size=50,
        )
        gates = check_promotion_gates(sample_control_metrics, variant)
        assert gates[GateName.GAIN] is True
        
        variant.score = 0.803  # Just below threshold
        gates = check_promotion_gates(sample_control_metrics, variant)
        assert gates[GateName.GAIN] is False


# =============================================================================
# TESTS: PROMOTION ENGINE - EVALUATION
# =============================================================================

class TestEvaluatePromotion:
    """Test evaluate_promotion function."""
    
    def test_valid_promotion(self, sample_control_metrics, sample_variant_metrics):
        """Test valid promotion when all gates pass."""
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": sample_variant_metrics,
        }
        
        result = evaluate_promotion("exp-001", benchmark)
        
        assert result.success is True
        assert result.variant_id == "variant-a"
        assert len(result.gates_passed) == 5
        assert len(result.gates_failed) == 0
        assert "All 5 gates passed" in result.reason
    
    def test_blocked_promotion_missing_control(self, sample_variant_metrics):
        """Test promotion blocked when control is missing."""
        benchmark = {
            "variant-a": sample_variant_metrics,
        }
        
        result = evaluate_promotion("exp-001", benchmark)
        
        assert result.success is False
        assert "Missing control metrics" in result.reason
    
    def test_blocked_promotion_low_score(self, sample_control_metrics):
        """Test promotion blocked due to low score."""
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.78,
            abandonment_rate=0.14,
            score=0.80,  # Not high enough
            sample_size=50,
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": variant,
        }
        
        result = evaluate_promotion("exp-001", benchmark)
        
        assert result.success is False
        assert GateName.GAIN in result.gates_failed
        assert "Failed gates" in result.reason
    
    def test_blocked_promotion_low_sample(self, sample_control_metrics):
        """Test promotion blocked due to low sample size."""
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.78,
            abandonment_rate=0.14,
            score=0.85,
            sample_size=10,  # Too low
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": variant,
        }
        
        result = evaluate_promotion("exp-001", benchmark)
        
        assert result.success is False
        assert GateName.STABILITY in result.gates_failed
    
    def test_promotion_no_variant_found(self, sample_control_metrics):
        """Test when no variant candidates found."""
        benchmark = {
            "control": sample_control_metrics,
        }
        
        result = evaluate_promotion("exp-001", benchmark)
        
        assert result.success is False
        assert "No variant candidates" in result.reason
    
    def test_promotion_specific_variant(self, sample_control_metrics, sample_variant_metrics):
        """Test evaluating a specific variant."""
        variant_b = BenchmarkMetrics(
            ttfv=115.0,
            completion_rate=0.76,
            abandonment_rate=0.15,
            score=0.82,
            sample_size=50,
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": sample_variant_metrics,
            "variant-b": variant_b,
        }
        
        result = evaluate_promotion("exp-001", benchmark, variant_id="variant-b")
        
        assert result.variant_id == "variant-b"
    
    def test_promotion_invalid_variant(self, sample_control_metrics):
        """Test with invalid variant ID."""
        benchmark = {
            "control": sample_control_metrics,
        }
        
        result = evaluate_promotion("exp-001", benchmark, variant_id="nonexistent")
        
        assert result.success is False
        assert "not found in benchmark results" in result.reason


# =============================================================================
# TESTS: ROLLBACK ENGINE
# =============================================================================

class TestCheckRollbackConditions:
    """Test check_rollback_conditions function."""
    
    def test_no_rollback_needed(self, sample_control_metrics):
        """Test when no rollback is needed."""
        current = sample_control_metrics
        new = BenchmarkMetrics(
            ttfv=125.0,
            completion_rate=0.74,
            abandonment_rate=0.16,
            score=0.78,
            sample_size=100,
        )
        
        assert check_rollback_conditions(current, new) is False
    
    def test_rollback_score_degradation(self, sample_control_metrics):
        """Test rollback due to score degradation > 10%."""
        current = sample_control_metrics
        new = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.70,  # 12.5% drop
            sample_size=100,
        )
        
        assert check_rollback_conditions(current, new) is True
    
    def test_rollback_completion_degradation(self, sample_control_metrics):
        """Test rollback due to completion rate degradation > 15%."""
        current = sample_control_metrics
        new = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.60,  # 20% drop
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        
        assert check_rollback_conditions(current, new) is True
    
    def test_rollback_abandonment_spike(self, sample_control_metrics):
        """Test rollback due to abandonment spike > 20%."""
        current = sample_control_metrics
        new = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.20,  # 33% increase
            score=0.80,
            sample_size=100,
        )
        
        assert check_rollback_conditions(current, new) is True
    
    def test_rollback_ttfv_regression(self, sample_control_metrics):
        """Test rollback due to TTFV regression > 25%."""
        current = sample_control_metrics
        new = BenchmarkMetrics(
            ttfv=160.0,  # 33% increase
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        
        assert check_rollback_conditions(current, new) is True
    
    def test_exact_threshold_score_rollback(self, sample_control_metrics):
        """Test score rollback at exact threshold."""
        current = sample_control_metrics
        
        # Threshold for 10% drop: score < 0.80 * 0.90 = 0.72 (float precision: ~0.7200000000000001)
        # Just above threshold (0.73 > 0.72): should NOT rollback
        new_above = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.73,  # Above threshold
            sample_size=100,
        )
        assert check_rollback_conditions(current, new_above) is False
        
        # Below threshold should trigger rollback
        new_below = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.71,  # Below threshold
            sample_size=100,
        )
        assert check_rollback_conditions(current, new_below) is True


class TestEvaluateRollback:
    """Test evaluate_rollback function."""
    
    def test_already_on_control(self):
        """Test when already on control variant."""
        policy = RolloutPolicy(
            experiment_id="exp-001",
            active_variant="control",
        )
        benchmark = {}
        
        decision = evaluate_rollback(policy, benchmark)
        
        assert decision.should_rollback is False
        assert "Already on control" in decision.reason
    
    def test_missing_metrics(self):
        """Test when metrics for active variant are missing."""
        policy = RolloutPolicy(
            experiment_id="exp-001",
            active_variant="variant-a",
        )
        benchmark = {}
        
        decision = evaluate_rollback(policy, benchmark)
        
        assert decision.should_rollback is False
        assert "No metrics available" in decision.reason
    
    def test_rollback_recommended(self, sample_control_metrics):
        """Test rollback recommendation."""
        policy = RolloutPolicy(
            experiment_id="exp-001",
            active_variant="variant-a",
            rollback_target="control",
        )
        current = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        new = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.60,  # 20% drop
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        benchmark = {
            "control": current,
            "variant-a": new,
        }
        
        decision = evaluate_rollback(policy, benchmark)
        
        assert decision.should_rollback is True
        assert decision.from_variant == "variant-a"
        assert decision.to_variant == "control"
    
    def test_no_rollback_recommended(self, sample_control_metrics):
        """Test when no rollback is recommended."""
        policy = RolloutPolicy(
            experiment_id="exp-001",
            active_variant="variant-a",
            rollback_target="control",
        )
        variant = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": variant,
        }
        
        decision = evaluate_rollback(policy, benchmark)
        
        assert decision.should_rollback is False
        assert "No degradation detected" in decision.reason


class TestRollback:
    """Test rollback function."""
    
    def test_rollback_to_control(self, temp_config_dir):
        """Test rollback to control variant."""
        # Setup: create policy with active variant
        policy = RolloutPolicy(
            experiment_id="exp-rollback-001",
            active_variant="variant-a",
            rollout_mode=RolloutMode.AUTO,
        )
        save_policy(policy)
        
        # Execute rollback
        result = rollback("exp-rollback-001", reason="Test rollback")
        
        assert result.active_variant == "control"
        assert "Test rollback" in result.decision_reason
        assert result.last_evaluation is not None
    
    def test_rollback_specific_target(self, temp_config_dir):
        """Test rollback to specific target."""
        policy = RolloutPolicy(
            experiment_id="exp-rollback-002",
            active_variant="variant-b",
            rollback_target="variant-a",
        )
        save_policy(policy)
        
        result = rollback("exp-rollback-002", target_variant="control")
        
        assert result.active_variant == "control"
    
    def test_rollback_creates_default_policy(self, temp_config_dir):
        """Test rollback creates default policy if not exists."""
        result = rollback("exp-new", reason="New experiment")
        
        assert result.active_variant == "control"
        assert result.experiment_id == "exp-new"


# =============================================================================
# TESTS: POLICY PERSISTENCE
# =============================================================================

class TestPolicyPersistence:
    """Test policy persistence functions."""
    
    def test_save_and_load_policy(self, temp_config_dir):
        """Test saving and loading a policy."""
        policy = RolloutPolicy(
            experiment_id="exp-save-001",
            active_variant="variant-a",
            rollout_mode=RolloutMode.SUPERVISED,
            decision_reason="Test save",
        )
        
        save_policy(policy)
        loaded = load_policy("exp-save-001")
        
        assert loaded.experiment_id == "exp-save-001"
        assert loaded.active_variant == "variant-a"
        assert loaded.rollout_mode == RolloutMode.SUPERVISED
        assert loaded.decision_reason == "Test save"
    
    def test_load_nonexistent_policy(self, temp_config_dir):
        """Test loading nonexistent policy returns default."""
        loaded = load_policy("exp-nonexistent")
        
        assert loaded.experiment_id == "exp-nonexistent"
        assert loaded.active_variant == "control"
        assert loaded.rollout_mode == RolloutMode.AUTO
    
    def test_list_active_policies(self, temp_config_dir):
        """Test listing active policies."""
        # Create multiple policies
        for i in range(3):
            policy = RolloutPolicy(experiment_id=f"exp-list-{i}")
            save_policy(policy)
        
        policies = list_active_policies()
        
        assert len(policies) == 3
        experiment_ids = [p.experiment_id for p in policies]
        assert "exp-list-0" in experiment_ids
        assert "exp-list-1" in experiment_ids
        assert "exp-list-2" in experiment_ids
    
    def test_list_empty_policies(self, temp_config_dir):
        """Test listing when no policies exist."""
        policies = list_active_policies()
        assert policies == []
    
    def test_delete_policy(self, temp_config_dir):
        """Test deleting a policy."""
        policy = RolloutPolicy(experiment_id="exp-delete")
        save_policy(policy)
        
        assert delete_policy("exp-delete") is True
        assert delete_policy("exp-delete") is False  # Already deleted
    
    def test_reset_policy(self, temp_config_dir):
        """Test resetting a policy."""
        # Create policy with custom values
        policy = RolloutPolicy(
            experiment_id="exp-reset",
            active_variant="variant-x",
            rollout_mode=RolloutMode.MANUAL,
            decision_reason="Custom",
        )
        save_policy(policy)
        
        # Reset
        reset = reset_policy("exp-reset")
        
        assert reset.active_variant == "control"
        assert reset.rollout_mode == RolloutMode.AUTO
        assert "reset to default" in reset.decision_reason.lower()


# =============================================================================
# TESTS: TELEMETRY
# =============================================================================

class TestTelemetry:
    """Test telemetry functions."""
    
    def test_log_promotion_decision_success(self):
        """Test logging successful promotion."""
        clear_telemetry_logs()
        
        result = PromotionResult(
            success=True,
            variant_id="variant-a",
            gates_passed=["gate1", "gate2"],
            gates_failed=[],
            reason="All passed",
        )
        log_promotion_decision(result)
        
        logs = get_telemetry_logs()
        assert len(logs) == 1
        assert logs[0]["type"] == "promotion"
        assert logs[0]["success"] is True
        assert logs[0]["variant_id"] == "variant-a"
    
    def test_log_promotion_decision_failure(self):
        """Test logging failed promotion."""
        clear_telemetry_logs()
        
        result = PromotionResult(
            success=False,
            variant_id="variant-b",
            gates_passed=[],
            gates_failed=["gate1"],
            reason="Failed",
        )
        log_promotion_decision(result)
        
        logs = get_telemetry_logs()
        assert len(logs) == 1
        assert logs[0]["success"] is False
    
    def test_log_rollback_decision(self):
        """Test logging rollback decision."""
        clear_telemetry_logs()
        
        log_rollback_decision("exp-001", "variant-a", "control", "Degradation detected")
        
        logs = get_telemetry_logs(log_type="rollback")
        assert len(logs) == 1
        assert logs[0]["type"] == "rollback"
        assert logs[0]["experiment_id"] == "exp-001"
        assert logs[0]["from_variant"] == "variant-a"
        assert logs[0]["to_variant"] == "control"
    
    def test_get_telemetry_logs_filtered(self):
        """Test filtering telemetry logs by type."""
        clear_telemetry_logs()
        
        # Add promotion log
        log_promotion_decision(PromotionResult(success=True, variant_id="v1"))
        # Add rollback log
        log_rollback_decision("exp-001", "v1", "control", "reason")
        
        promotion_logs = get_telemetry_logs(log_type="promotion")
        rollback_logs = get_telemetry_logs(log_type="rollback")
        
        assert len(promotion_logs) == 1
        assert len(rollback_logs) == 1
        assert promotion_logs[0]["type"] == "promotion"
        assert rollback_logs[0]["type"] == "rollback"
    
    def test_get_telemetry_logs_limit(self):
        """Test limiting telemetry logs."""
        clear_telemetry_logs()
        
        for i in range(10):
            log_promotion_decision(PromotionResult(success=True, variant_id=f"v{i}"))
        
        logs = get_telemetry_logs(limit=5)
        assert len(logs) == 5
    
    def test_clear_telemetry_logs(self):
        """Test clearing telemetry logs."""
        log_promotion_decision(PromotionResult(success=True, variant_id="v1"))
        
        clear_telemetry_logs()
        
        logs = get_telemetry_logs()
        assert len(logs) == 0


# =============================================================================
# TESTS: AUTO-ROLLOUT ORCHESTRATOR
# =============================================================================

class TestAutoRollout:
    """Test run_auto_rollout function."""
    
    def test_auto_rollout_promotion(self, temp_config_dir, sample_control_metrics, sample_variant_metrics):
        """Test auto-rollout promotes variant when on control."""
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": sample_variant_metrics,
        }
        
        promotion, rollback_dec = run_auto_rollout("exp-auto-001", benchmark)
        
        assert promotion is not None
        assert promotion.success is True
        assert rollback_dec is None
        
        # Check policy was updated
        policy = load_policy("exp-auto-001")
        assert policy.active_variant == "variant-a"
    
    def test_auto_rollout_rollback(self, temp_config_dir, sample_control_metrics):
        """Test auto-rollout triggers rollback when needed."""
        # Setup: policy with active variant
        policy = RolloutPolicy(
            experiment_id="exp-auto-002",
            active_variant="variant-a",
        )
        save_policy(policy)
        
        # Metrics showing degradation
        degraded_variant = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.60,  # 20% drop triggers rollback
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": degraded_variant,
        }
        
        promotion, rollback_dec = run_auto_rollout("exp-auto-002", benchmark)
        
        assert promotion is None
        assert rollback_dec is not None
        assert rollback_dec.should_rollback is True
        
        # Check policy was rolled back
        policy = load_policy("exp-auto-002")
        assert policy.active_variant == "control"
    
    def test_auto_rollout_no_action(self, temp_config_dir, sample_control_metrics):
        """Test auto-rollout when no action needed."""
        # Setup: policy with active variant but no degradation
        policy = RolloutPolicy(
            experiment_id="exp-auto-003",
            active_variant="variant-a",
        )
        save_policy(policy)
        
        # Good metrics
        good_variant = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.75,
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": good_variant,
        }
        
        promotion, rollback_dec = run_auto_rollout("exp-auto-003", benchmark)
        
        assert promotion is None
        assert rollback_dec is not None
        assert rollback_dec.should_rollback is False
        
        # Check policy unchanged
        policy = load_policy("exp-auto-003")
        assert policy.active_variant == "variant-a"
    
    def test_auto_rollout_blocked_promotion(self, temp_config_dir, sample_control_metrics):
        """Test auto-rollout when promotion is blocked."""
        bad_variant = BenchmarkMetrics(
            ttfv=200.0,  # Too high
            completion_rate=0.60,  # Too low
            abandonment_rate=0.30,  # Too high
            score=0.70,  # Too low
            sample_size=10,  # Too low
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": bad_variant,
        }
        
        promotion, rollback_dec = run_auto_rollout("exp-auto-004", benchmark)
        
        assert promotion is not None
        assert promotion.success is False
        
        # Check policy unchanged (still on control)
        policy = load_policy("exp-auto-004")
        assert policy.active_variant == "control"


# =============================================================================
# TESTS: FALLBACK SAFE
# =============================================================================

class TestFallbackSafe:
    """Test safe fallback behaviors."""
    
    def test_fallback_to_control_on_error(self, temp_config_dir):
        """Test fallback to control when errors occur."""
        # Load nonexistent policy should return control default
        policy = load_policy("nonexistent-exp")
        assert policy.active_variant == "control"
    
    def test_safe_rollback_target(self, temp_config_dir):
        """Test rollback target defaults to control."""
        policy = RolloutPolicy(experiment_id="exp-fallback")
        assert policy.rollback_target == "control"
    
    def test_rollback_uses_policy_target(self, temp_config_dir):
        """Test rollback respects policy rollback_target."""
        policy = RolloutPolicy(
            experiment_id="exp-target",
            active_variant="variant-b",
            rollback_target="variant-a",  # Custom target
        )
        save_policy(policy)
        
        # Manual rollback should use policy target if not specified
        result = rollback("exp-target")
        assert result.active_variant == "variant-a"


# =============================================================================
# TESTS: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_benchmark(self):
        """Test with empty benchmark."""
        result = evaluate_promotion("exp-empty", {})
        assert result.success is False
        assert "Missing control" in result.reason
    
    def test_negative_metrics(self):
        """Test with negative metric values."""
        control = BenchmarkMetrics(
            ttfv=-100.0,
            completion_rate=-0.5,
            abandonment_rate=-0.1,
            score=-0.8,
            sample_size=100,
        )
        variant = BenchmarkMetrics(
            ttfv=-90.0,
            completion_rate=-0.4,
            abandonment_rate=-0.05,
            score=-0.7,
            sample_size=50,
        )
        
        # Should not crash, though results may be weird
        gates = check_promotion_gates(control, variant)
        assert isinstance(gates, dict)
        assert len(gates) == 5
    
    def test_zero_sample_size(self, sample_control_metrics):
        """Test with zero sample size."""
        variant = BenchmarkMetrics(
            ttfv=110.0,
            completion_rate=0.78,
            abandonment_rate=0.14,
            score=0.85,
            sample_size=0,
        )
        
        gates = check_promotion_gates(sample_control_metrics, variant)
        assert gates[GateName.STABILITY] is False
    
    def test_very_large_numbers(self):
        """Test with very large metric values."""
        control = BenchmarkMetrics(
            ttfv=1e9,
            completion_rate=0.999999,
            abandonment_rate=0.000001,
            score=1e6,
            sample_size=1000000,
        )
        variant = BenchmarkMetrics(
            ttfv=1.1e9,
            completion_rate=0.999998,
            abandonment_rate=0.000002,
            score=1.01e6,
            sample_size=500000,
        )
        
        gates = check_promotion_gates(control, variant)
        assert isinstance(gates, dict)
    
    def test_concurrent_policy_access(self, temp_config_dir):
        """Test policy persistence with multiple saves."""
        policy = RolloutPolicy(experiment_id="exp-concurrent")
        
        # Multiple saves
        for i in range(5):
            policy.active_variant = f"variant-{i}"
            save_policy(policy)
        
        # Load should get last saved
        loaded = load_policy("exp-concurrent")
        assert loaded.active_variant == "variant-4"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for full workflows."""
    
    def test_full_promotion_workflow(self, temp_config_dir, sample_control_metrics, sample_variant_metrics):
        """Test complete promotion workflow."""
        # 1. Initial state: control
        policy = load_policy("exp-full-001")
        assert policy.active_variant == "control"
        
        # 2. Evaluate promotion
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": sample_variant_metrics,
        }
        result = evaluate_promotion("exp-full-001", benchmark)
        
        # 3. Apply promotion
        if result.success:
            policy.active_variant = result.variant_id
            policy.last_evaluation = datetime.now(timezone.utc).isoformat()
            policy.decision_reason = result.reason
            save_policy(policy)
        
        # 4. Verify
        updated = load_policy("exp-full-001")
        assert updated.active_variant == "variant-a"
        
        # 5. Check telemetry
        logs = get_telemetry_logs(log_type="promotion")
        assert len(logs) >= 1
    
    def test_full_rollback_workflow(self, temp_config_dir, sample_control_metrics):
        """Test complete rollback workflow."""
        # 1. Setup promoted state
        policy = RolloutPolicy(
            experiment_id="exp-full-002",
            active_variant="variant-a",
        )
        save_policy(policy)
        
        # 2. Detect degradation
        degraded = BenchmarkMetrics(
            ttfv=120.0,
            completion_rate=0.60,  # Triggers rollback
            abandonment_rate=0.15,
            score=0.80,
            sample_size=100,
        )
        benchmark = {
            "control": sample_control_metrics,
            "variant-a": degraded,
        }
        
        # 3. Evaluate rollback
        decision = evaluate_rollback(policy, benchmark)
        
        # 4. Execute rollback
        if decision.should_rollback:
            rollback("exp-full-002", reason=decision.reason)
        
        # 5. Verify
        updated = load_policy("exp-full-002")
        assert updated.active_variant == "control"
        
        # 6. Check telemetry
        logs = get_telemetry_logs(log_type="rollback")
        assert len(logs) >= 1


# Contagem de testes: 50+ testes implementados
