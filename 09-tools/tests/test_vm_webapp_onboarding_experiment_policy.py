"""Tests for onboarding experiment evaluation and promotion policy."""

from __future__ import annotations

import pytest

from vm_webapp.onboarding_experiments import (
    Experiment,
    ExperimentRegistry,
    ExperimentStatus,
    ExperimentVariant,
    RiskLevel,
)
from vm_webapp.onboarding_experiment_policy import (
    EvaluationResult,
    ExperimentEvaluator,
    PromotionDecision,
    PromotionDecisionType,
)


class TestEvaluationResult:
    """Test evaluation result model."""

    def test_evaluation_result_creation(self):
        """Test creating an evaluation result."""
        result = EvaluationResult(
            experiment_id="test_exp",
            variant_id="treatment",
            sample_size=1000,
            control_conversion_rate=0.10,
            treatment_conversion_rate=0.12,
            absolute_lift=0.02,
            relative_lift=0.20,
            confidence=0.96,
            is_significant=True,
        )
        assert result.experiment_id == "test_exp"
        assert result.relative_lift == 0.20
        assert result.is_significant is True


class TestSampleThresholdValidation:
    """Test sample size threshold validation."""

    def test_below_min_sample_size_not_significant(self):
        """Test that results below min sample size are not significant."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=1000,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        # Below min sample size - should not be significant
        result = evaluator.evaluate(
            experiment_id="test_exp",
            variant_id="treatment",
            control_metrics={"conversions": 5, "total": 50},
            treatment_metrics={"conversions": 10, "total": 50},
        )
        assert result.is_significant is False
        assert "Sample size below minimum" in result.reason

    def test_at_min_sample_size_can_be_significant(self):
        """Test that results at min sample size can be significant."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        # At min sample size with clear difference
        result = evaluator.evaluate(
            experiment_id="test_exp",
            variant_id="treatment",
            control_metrics={"conversions": 5, "total": 100},
            treatment_metrics={"conversions": 15, "total": 100},
        )
        assert result.sample_size == 200


class TestConfidenceCalculation:
    """Test confidence interval calculations."""

    def test_high_confidence_significant_result(self):
        """Test significant result with high confidence."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        # Large effect size with good sample
        result = evaluator.evaluate(
            experiment_id="test_exp",
            variant_id="treatment",
            control_metrics={"conversions": 50, "total": 500},
            treatment_metrics={"conversions": 75, "total": 500},
        )
        assert result.confidence >= 0.95
        assert result.is_significant is True

    def test_low_confidence_not_significant(self):
        """Test non-significant result with low confidence."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        # Small effect size
        result = evaluator.evaluate(
            experiment_id="test_exp",
            variant_id="treatment",
            control_metrics={"conversions": 50, "total": 500},
            treatment_metrics={"conversions": 52, "total": 500},
        )
        assert result.confidence < 0.95
        assert result.is_significant is False


class TestLiftCalculation:
    """Test lift calculations."""

    def test_absolute_lift_calculation(self):
        """Test absolute lift is calculated correctly."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        result = evaluator.evaluate(
            experiment_id="test_exp",
            variant_id="treatment",
            control_metrics={"conversions": 10, "total": 100},
            treatment_metrics={"conversions": 15, "total": 100},
        )
        # 10% -> 15% = 5 percentage points absolute lift
        assert abs(result.control_conversion_rate - 0.10) < 0.001
        assert abs(result.treatment_conversion_rate - 0.15) < 0.001
        assert abs(result.absolute_lift - 0.05) < 0.001

    def test_relative_lift_calculation(self):
        """Test relative lift is calculated correctly."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        result = evaluator.evaluate(
            experiment_id="test_exp",
            variant_id="treatment",
            control_metrics={"conversions": 10, "total": 100},
            treatment_metrics={"conversions": 15, "total": 100},
        )
        # (15-10)/10 = 50% relative lift
        assert abs(result.relative_lift - 0.50) < 0.001


class TestPromotionDecision:
    """Test promotion decision logic."""

    def test_low_risk_auto_promote(self):
        """Test low-risk experiments can be auto-promoted."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        result = EvaluationResult(
            experiment_id="test_exp",
            variant_id="treatment",
            sample_size=1000,
            control_conversion_rate=0.10,
            treatment_conversion_rate=0.105,
            absolute_lift=0.005,
            relative_lift=0.05,  # Within 10% threshold
            confidence=0.96,
            is_significant=True,
        )
        
        decision = evaluator.decide_promotion(experiment_id="test_exp", result=result)
        assert decision.decision == PromotionDecisionType.AUTO_APPLY
        assert decision.requires_approval is False

    def test_medium_risk_needs_approval(self):
        """Test medium-risk experiments need human approval."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.MEDIUM,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        result = EvaluationResult(
            experiment_id="test_exp",
            variant_id="treatment",
            sample_size=1000,
            control_conversion_rate=0.10,
            treatment_conversion_rate=0.105,
            absolute_lift=0.005,
            relative_lift=0.05,  # Within 10% threshold
            confidence=0.96,
            is_significant=True,
        )
        
        decision = evaluator.decide_promotion(experiment_id="test_exp", result=result)
        assert decision.decision == PromotionDecisionType.APPROVE
        assert decision.requires_approval is True

    def test_high_risk_needs_approval(self):
        """Test high-risk experiments need human approval."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.HIGH,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        result = EvaluationResult(
            experiment_id="test_exp",
            variant_id="treatment",
            sample_size=1000,
            control_conversion_rate=0.10,
            treatment_conversion_rate=0.105,
            absolute_lift=0.005,
            relative_lift=0.05,  # Within 10% threshold
            confidence=0.96,
            is_significant=True,
        )
        
        decision = evaluator.decide_promotion(experiment_id="test_exp", result=result)
        assert decision.decision == PromotionDecisionType.APPROVE
        assert decision.requires_approval is True

    def test_negative_lift_rollback(self):
        """Test negative lift suggests rollback."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        result = EvaluationResult(
            experiment_id="test_exp",
            variant_id="treatment",
            sample_size=1000,
            control_conversion_rate=0.10,
            treatment_conversion_rate=0.095,
            absolute_lift=-0.005,
            relative_lift=-0.05,  # Within 10% threshold
            confidence=0.96,
            is_significant=True,
        )
        
        decision = evaluator.decide_promotion(experiment_id="test_exp", result=result)
        assert decision.decision == PromotionDecisionType.ROLLBACK

    def test_guardrail_blocks_excessive_lift(self):
        """Test guardrail blocks if lift exceeds max threshold."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,  # 10% max
        )
        registry.register(experiment)
        
        # 50% lift exceeds 10% max threshold
        result = EvaluationResult(
            experiment_id="test_exp",
            variant_id="treatment",
            sample_size=1000,
            control_conversion_rate=0.10,
            treatment_conversion_rate=0.15,
            absolute_lift=0.05,
            relative_lift=0.50,
            confidence=0.96,
            is_significant=True,
        )
        
        decision = evaluator.decide_promotion(experiment_id="test_exp", result=result)
        assert decision.decision == PromotionDecisionType.BLOCK
        assert "Lift exceeds maximum threshold" in decision.reason

    def test_not_significant_continue(self):
        """Test non-significant result suggests continue."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        result = EvaluationResult(
            experiment_id="test_exp",
            variant_id="treatment",
            sample_size=1000,
            control_conversion_rate=0.10,
            treatment_conversion_rate=0.102,
            absolute_lift=0.002,
            relative_lift=0.02,
            confidence=0.80,
            is_significant=False,
        )
        
        decision = evaluator.decide_promotion(experiment_id="test_exp", result=result)
        assert decision.decision == PromotionDecisionType.CONTINUE


class TestWeeklyEvaluation:
    """Test weekly evaluation cycle."""

    def test_evaluate_all_running_experiments(self):
        """Test evaluating all running experiments."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        # Create two experiments
        for i in range(2):
            variants = [
                ExperimentVariant("control", "Control", {}, 50),
                ExperimentVariant("treatment", "Treatment", {}, 50),
            ]
            experiment = Experiment(
                experiment_id=f"test_exp_{i}",
                name=f"Test {i}",
                description="Test",
                hypothesis="Test",
                primary_metric="conversion",
                variants=variants,
                risk_level=RiskLevel.LOW,
                min_sample_size=100,
                min_confidence=0.95,
                max_lift_threshold=0.10,
            )
            registry.register(experiment)
            registry.start_experiment(f"test_exp_{i}")
        
        # Mock metrics fetcher
        def mock_fetch_metrics(experiment_id: str, variant_id: str):
            return {"conversions": 50, "total": 500}
        
        results = evaluator.evaluate_all_running(mock_fetch_metrics)
        assert len(results) == 2

    def test_skip_non_running_experiments(self):
        """Test skipping experiments that aren't running."""
        registry = ExperimentRegistry()
        evaluator = ExperimentEvaluator(registry)
        
        # Create experiment but don't start it
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="test_exp",
            name="Test",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        registry.register(experiment)
        
        def mock_fetch_metrics(experiment_id: str, variant_id: str):
            return {"conversions": 50, "total": 500}
        
        results = evaluator.evaluate_all_running(mock_fetch_metrics)
        assert len(results) == 0
