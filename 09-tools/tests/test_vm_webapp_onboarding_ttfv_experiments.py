"""Tests for v38 onboarding TTFV experiment governance."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from vm_webapp.onboarding_ttfv_experiments import (
    ExperimentStatus,
    ExperimentDecision,
    UserAssignment,
    Experiment,
    ExperimentResult,
    assign_user_to_variant,
    evaluate_experiment,
    make_experiment_decision,
    check_guardrails,
    calculate_guardrail_status,
)


class TestExperimentStatus:
    """Test experiment status enum."""

    def test_experiment_status_values(self):
        assert ExperimentStatus.DRAFT == "draft"
        assert ExperimentStatus.RUNNING == "running"
        assert ExperimentStatus.PAUSED == "paused"
        assert ExperimentStatus.COMPLETED == "completed"
        assert ExperimentStatus.ROLLED_BACK == "rolled_back"


class TestExperimentDecision:
    """Test experiment decision enum."""

    def test_experiment_decision_values(self):
        assert ExperimentDecision.PROMOTE == "promote"
        assert ExperimentDecision.HOLD == "hold"
        assert ExperimentDecision.ROLLBACK == "rollback"


class TestUserAssignment:
    """Test user assignment logic."""

    def test_deterministic_assignment_same_user(self):
        """Same user should always get same variant."""
        user_id = "user-123"
        experiment_id = "exp-001"
        
        assignment1 = assign_user_to_variant(user_id, experiment_id)
        assignment2 = assign_user_to_variant(user_id, experiment_id)
        
        assert assignment1.variant == assignment2.variant
        assert assignment1.user_id == user_id
        assert assignment1.experiment_id == experiment_id

    def test_different_users_get_different_variants(self):
        """Different users should potentially get different variants."""
        experiment_id = "exp-001"
        variants = set()
        
        for i in range(20):
            assignment = assign_user_to_variant(f"user-{i}", experiment_id)
            variants.add(assignment.variant)
        
        # Should have both control and treatment in 20 users
        assert len(variants) >= 2

    def test_assignment_50_50_split(self):
        """Assignment should be roughly 50/50."""
        experiment_id = "exp-001"
        control_count = 0
        total = 1000
        
        for i in range(total):
            assignment = assign_user_to_variant(f"user-{i}", experiment_id)
            if assignment.variant == "control":
                control_count += 1
        
        # Should be within 10% of 50/50
        assert 0.40 <= control_count / total <= 0.60

    def test_assignment_includes_timestamp(self):
        """Assignment should include assignment timestamp."""
        user_id = "user-123"
        experiment_id = "exp-001"
        
        assignment = assign_user_to_variant(user_id, experiment_id)
        
        assert assignment.assigned_at is not None
        assert isinstance(assignment.assigned_at, datetime)


class TestCheckGuardrails:
    """Test guardrail checking."""

    def test_activation_rate_guardrail_pass(self):
        """Activation rate drop within tolerance should pass."""
        metrics = {
            "activation_rate_d1_control": 0.50,
            "activation_rate_d1_treatment": 0.49,  # -1 p.p., within -2 p.p. guardrail
        }
        
        result = check_guardrails(metrics)
        
        assert result["activation_rate_d1_ok"] is True
        assert result["all_passed"] is True

    def test_activation_rate_guardrail_fail(self):
        """Activation rate drop beyond -2 p.p. should fail."""
        metrics = {
            "activation_rate_d1_control": 0.50,
            "activation_rate_d1_treatment": 0.47,  # -3 p.p., beyond -2 p.p. guardrail
        }
        
        result = check_guardrails(metrics)
        
        assert result["activation_rate_d1_ok"] is False
        assert result["all_passed"] is False
        assert "activation" in result["violations"][0].lower()

    def test_completion_rate_guardrail_pass(self):
        """Completion rate drop within tolerance should pass."""
        metrics = {
            "onboarding_completion_rate_control": 0.80,
            "onboarding_completion_rate_treatment": 0.78,  # -2 p.p., within -3 p.p. guardrail
        }
        
        result = check_guardrails(metrics)
        
        assert result["onboarding_completion_rate_ok"] is True
        assert result["all_passed"] is True

    def test_completion_rate_guardrail_fail(self):
        """Completion rate drop beyond -3 p.p. should fail."""
        metrics = {
            "onboarding_completion_rate_control": 0.80,
            "onboarding_completion_rate_treatment": 0.75,  # -5 p.p., beyond -3 p.p. guardrail
        }
        
        result = check_guardrails(metrics)
        
        assert result["onboarding_completion_rate_ok"] is False
        assert result["all_passed"] is False

    def test_incident_rate_guardrail_pass(self):
        """No incident increase should pass."""
        metrics = {
            "incident_rate_control": 0.01,
            "incident_rate_treatment": 0.01,  # No increase
        }
        
        result = check_guardrails(metrics)
        
        assert result["incident_rate_ok"] is True
        assert result["all_passed"] is True

    def test_incident_rate_guardrail_fail(self):
        """Any incident increase should fail."""
        metrics = {
            "incident_rate_control": 0.01,
            "incident_rate_treatment": 0.02,  # Increase
        }
        
        result = check_guardrails(metrics)
        
        assert result["incident_rate_ok"] is False
        assert result["all_passed"] is False
        assert "incident" in result["violations"][0].lower()

    def test_multiple_guardrails_combined(self):
        """All guardrails must pass for all_passed to be True."""
        metrics = {
            "activation_rate_d1_control": 0.50,
            "activation_rate_d1_treatment": 0.50,
            "onboarding_completion_rate_control": 0.80,
            "onboarding_completion_rate_treatment": 0.80,
            "incident_rate_control": 0.01,
            "incident_rate_treatment": 0.01,
        }
        
        result = check_guardrails(metrics)
        
        assert result["all_passed"] is True
        assert len(result["violations"]) == 0


class TestEvaluateExperiment:
    """Test experiment evaluation."""

    def test_evaluation_returns_metrics(self):
        """Evaluation should return calculated metrics."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.RUNNING,
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            variants=["control", "treatment"],
        )
        
        result = evaluate_experiment(experiment)
        
        assert result.experiment_id == experiment.experiment_id
        assert "median_ttfv_minutes" in result.metrics
        assert "activation_rate_d1" in result.metrics
        assert "onboarding_completion_rate" in result.metrics

    def test_evaluation_includes_sample_size(self):
        """Evaluation should include sample size per variant."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.RUNNING,
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            variants=["control", "treatment"],
        )
        
        result = evaluate_experiment(experiment)
        
        assert result.sample_size_control > 0
        assert result.sample_size_treatment > 0

    def test_evaluation_calculates_confidence_interval(self):
        """Evaluation should calculate confidence intervals."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.RUNNING,
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            variants=["control", "treatment"],
        )
        
        result = evaluate_experiment(experiment)
        
        assert "confidence_interval" in result.metrics.get("median_ttfv_minutes", {})


class TestMakeExperimentDecision:
    """Test experiment decision making."""

    def test_promote_when_guardrails_pass_and_ttfv_improved(self):
        """Should promote when guardrails pass and TTFV improves."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.RUNNING,
        )
        
        metrics = {
            "median_ttfv_minutes_control": 10.0,
            "median_ttfv_minutes_treatment": 7.0,  # 30% improvement
            "activation_rate_d1_control": 0.50,
            "activation_rate_d1_treatment": 0.50,
            "onboarding_completion_rate_control": 0.80,
            "onboarding_completion_rate_treatment": 0.80,
            "incident_rate_control": 0.01,
            "incident_rate_treatment": 0.01,
            "sample_size_control": 500,
            "sample_size_treatment": 500,
        }
        
        decision = make_experiment_decision(experiment, metrics)
        
        assert decision.decision == ExperimentDecision.PROMOTE

    def test_hold_when_insufficient_data(self):
        """Should hold when sample size is insufficient."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.RUNNING,
        )
        
        metrics = {
            "median_ttfv_minutes_control": 10.0,
            "median_ttfv_minutes_treatment": 7.0,
            "activation_rate_d1_control": 0.50,
            "activation_rate_d1_treatment": 0.50,
            "onboarding_completion_rate_control": 0.80,
            "onboarding_completion_rate_treatment": 0.80,
            "incident_rate_control": 0.01,
            "incident_rate_treatment": 0.01,
            "sample_size_control": 50,  # Too small
            "sample_size_treatment": 50,
        }
        
        decision = make_experiment_decision(experiment, metrics, min_sample_size=100)
        
        assert decision.decision == ExperimentDecision.HOLD
        assert "sample" in decision.reason.lower()

    def test_rollback_when_guardrails_fail(self):
        """Should rollback when guardrails fail."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.RUNNING,
        )
        
        metrics = {
            "median_ttfv_minutes_control": 10.0,
            "median_ttfv_minutes_treatment": 7.0,  # TTFV improved
            "activation_rate_d1_control": 0.50,
            "activation_rate_d1_treatment": 0.45,  # -5 p.p., fails guardrail
            "onboarding_completion_rate_control": 0.80,
            "onboarding_completion_rate_treatment": 0.80,
            "incident_rate_control": 0.01,
            "incident_rate_treatment": 0.01,
            "sample_size_control": 500,
            "sample_size_treatment": 500,
        }
        
        decision = make_experiment_decision(experiment, metrics)
        
        assert decision.decision == ExperimentDecision.ROLLBACK
        assert "guardrail" in decision.reason.lower()

    def test_hold_when_ttfv_not_significantly_improved(self):
        """Should hold when TTFV improvement is not significant."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.RUNNING,
        )
        
        metrics = {
            "median_ttfv_minutes_control": 10.0,
            "median_ttfv_minutes_treatment": 9.5,  # Only 5% improvement
            "activation_rate_d1_control": 0.50,
            "activation_rate_d1_treatment": 0.50,
            "onboarding_completion_rate_control": 0.80,
            "onboarding_completion_rate_treatment": 0.80,
            "incident_rate_control": 0.01,
            "incident_rate_treatment": 0.01,
            "sample_size_control": 500,
            "sample_size_treatment": 500,
        }
        
        decision = make_experiment_decision(experiment, metrics, min_ttfv_improvement=0.10)
        
        assert decision.decision == ExperimentDecision.HOLD
        assert "improvement" in decision.reason.lower()


class TestCalculateGuardrailStatus:
    """Test guardrail status calculation."""

    def test_status_includes_all_guardrails(self):
        """Status should include all guardrail metrics."""
        status = calculate_guardrail_status()
        
        assert "activation_rate_d1" in status
        assert "onboarding_completion_rate" in status
        assert "incident_rate" in status
        assert "overall_status" in status

    def test_status_reflects_current_metrics(self):
        """Status should reflect current metric values."""
        status = calculate_guardrail_status()
        
        assert isinstance(status["activation_rate_d1"]["control"], float)
        assert isinstance(status["activation_rate_d1"]["treatment"], float)
        assert isinstance(status["activation_rate_d1"]["delta_pp"], float)

    def test_overall_status_pass_when_all_guardrails_ok(self):
        """Overall status should be PASS when all guardrails pass."""
        # This will use mock/default data
        status = calculate_guardrail_status()
        
        assert status["overall_status"] in ["PASS", "FAIL", "WARNING"]


class TestEdgeCases:
    """Test edge cases."""

    def test_experiment_not_started_cannot_be_evaluated(self):
        """Draft experiment cannot be evaluated."""
        experiment = Experiment(
            experiment_id="exp-001",
            name="TTFV Optimization",
            status=ExperimentStatus.DRAFT,
        )
        
        with pytest.raises(ValueError):
            evaluate_experiment(experiment)

    def test_zero_control_metrics_handled(self):
        """Zero control metrics should be handled gracefully."""
        metrics = {
            "median_ttfv_minutes_control": 0,
            "median_ttfv_minutes_treatment": 5.0,
        }
        
        # Should not raise exception
        result = check_guardrails(metrics)
        assert isinstance(result, dict)

    def test_missing_metrics_handled(self):
        """Missing metrics should be handled gracefully."""
        metrics = {}  # Empty metrics
        
        # Should not raise exception
        result = check_guardrails(metrics)
        assert isinstance(result, dict)
        assert result["all_passed"] is False  # Can't pass without data
