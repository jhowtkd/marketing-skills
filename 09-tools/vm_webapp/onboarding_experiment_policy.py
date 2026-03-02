"""Onboarding experiment evaluation and promotion policy with guardrails.

This module provides weekly evaluation cycles and promotion decisions
based on lift, confidence, and risk levels with guardrails.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from vm_webapp.onboarding_experiments import (
    ExperimentRegistry,
    ExperimentStatus,
    RiskLevel,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PromotionDecisionType(str, Enum):
    """Type of promotion decision."""
    AUTO_APPLY = "auto_apply"  # Automatically promote (low risk only)
    APPROVE = "approve"  # Ready for human approval
    CONTINUE = "continue"  # Keep running, not enough data
    BLOCK = "block"  # Block due to guardrail violation
    ROLLBACK = "rollback"  # Rollback due to negative lift


@dataclass
class EvaluationResult:
    """Result of evaluating an experiment variant."""
    experiment_id: str
    variant_id: str
    sample_size: int
    control_conversion_rate: float
    treatment_conversion_rate: float
    absolute_lift: float
    relative_lift: float
    confidence: float
    is_significant: bool
    evaluated_at: str = field(default_factory=_now_iso)
    reason: str = ""


@dataclass
class PromotionDecision:
    """Decision on whether to promote a variant."""
    experiment_id: str
    variant_id: str
    decision: PromotionDecisionType
    result: EvaluationResult
    requires_approval: bool
    reason: str
    decided_at: str = field(default_factory=_now_iso)


class ExperimentEvaluator:
    """Evaluator for experiment results with promotion policy."""

    def __init__(self, registry: ExperimentRegistry):
        self._registry = registry

    def evaluate(
        self,
        experiment_id: str,
        variant_id: str,
        control_metrics: dict,
        treatment_metrics: dict,
    ) -> EvaluationResult:
        """Evaluate a variant against control.
        
        Args:
            experiment_id: The experiment ID
            variant_id: The variant being evaluated
            control_metrics: Dict with 'conversions' and 'total' for control
            treatment_metrics: Dict with 'conversions' and 'total' for treatment
        """
        experiment = self._registry.get_experiment(experiment_id)
        
        control_conversions = control_metrics.get("conversions", 0)
        control_total = control_metrics.get("total", 0)
        treatment_conversions = treatment_metrics.get("conversions", 0)
        treatment_total = treatment_metrics.get("total", 0)
        
        # Calculate rates
        control_rate = control_conversions / control_total if control_total > 0 else 0
        treatment_rate = treatment_conversions / treatment_total if treatment_total > 0 else 0
        
        # Calculate lifts
        absolute_lift = treatment_rate - control_rate
        relative_lift = (treatment_rate - control_rate) / control_rate if control_rate > 0 else 0
        
        # Sample size
        sample_size = control_total + treatment_total
        
        # Check minimum sample size
        if sample_size < experiment.min_sample_size:
            return EvaluationResult(
                experiment_id=experiment_id,
                variant_id=variant_id,
                sample_size=sample_size,
                control_conversion_rate=control_rate,
                treatment_conversion_rate=treatment_rate,
                absolute_lift=absolute_lift,
                relative_lift=relative_lift,
                confidence=0.0,
                is_significant=False,
                reason=f"Sample size below minimum: {sample_size} < {experiment.min_sample_size}",
            )
        
        # Calculate confidence using normal approximation
        confidence = self._calculate_confidence(
            control_conversions, control_total,
            treatment_conversions, treatment_total
        )
        
        # Determine significance
        is_significant = confidence >= experiment.min_confidence
        
        reason = ""
        if not is_significant:
            reason = f"Confidence {confidence:.2%} below threshold {experiment.min_confidence:.2%}"
        
        return EvaluationResult(
            experiment_id=experiment_id,
            variant_id=variant_id,
            sample_size=sample_size,
            control_conversion_rate=control_rate,
            treatment_conversion_rate=treatment_rate,
            absolute_lift=absolute_lift,
            relative_lift=relative_lift,
            confidence=confidence,
            is_significant=is_significant,
            reason=reason,
        )

    def _calculate_confidence(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
    ) -> float:
        """Calculate confidence level using z-test for proportions.
        
        Returns confidence as a value between 0 and 1.
        """
        if control_total == 0 or treatment_total == 0:
            return 0.0
        
        p1 = control_conversions / control_total
        p2 = treatment_conversions / treatment_total
        
        # Pooled probability
        p_pool = (control_conversions + treatment_conversions) / (control_total + treatment_total)
        
        # Standard error
        se = math.sqrt(
            p_pool * (1 - p_pool) * (1 / control_total + 1 / treatment_total)
        )
        
        if se == 0:
            return 0.0
        
        # Z-score
        z = (p2 - p1) / se
        
        # Convert z-score to confidence (two-tailed)
        # Using error function approximation for normal CDF
        confidence = 1 - 2 * (1 - self._normal_cdf(abs(z)))
        
        return max(0.0, min(1.0, confidence))

    def _normal_cdf(self, x: float) -> float:
        """Cumulative distribution function for standard normal distribution."""
        # Abramowitz and Stegun approximation
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911
        
        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2.0)
        
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return 0.5 * (1.0 + sign * y)

    def decide_promotion(
        self,
        experiment_id: str,
        result: EvaluationResult,
    ) -> PromotionDecision:
        """Decide whether to promote a variant based on evaluation result.
        
        Implements the promotion policy with guardrails:
        - Low risk + significant positive lift = auto-apply
        - Medium/High risk + significant positive lift = needs approval
        - Guardrail violation = block
        - Negative lift = rollback
        - Not significant = continue
        """
        experiment = self._registry.get_experiment(experiment_id)
        
        # Check for guardrail violation (excessive lift)
        if abs(result.relative_lift) > experiment.max_lift_threshold:
            return PromotionDecision(
                experiment_id=experiment_id,
                variant_id=result.variant_id,
                decision=PromotionDecisionType.BLOCK,
                result=result,
                requires_approval=True,
                reason=f"Lift exceeds maximum threshold: {result.relative_lift:.1%} > {experiment.max_lift_threshold:.1%}",
            )
        
        # Not significant - continue running
        if not result.is_significant:
            return PromotionDecision(
                experiment_id=experiment_id,
                variant_id=result.variant_id,
                decision=PromotionDecisionType.CONTINUE,
                result=result,
                requires_approval=False,
                reason="Results not statistically significant",
            )
        
        # Negative lift - rollback
        if result.relative_lift < 0:
            return PromotionDecision(
                experiment_id=experiment_id,
                variant_id=result.variant_id,
                decision=PromotionDecisionType.ROLLBACK,
                result=result,
                requires_approval=experiment.risk_level != RiskLevel.LOW,
                reason=f"Negative lift: {result.relative_lift:.1%}",
            )
        
        # Positive lift - promotion decision based on risk
        if experiment.risk_level == RiskLevel.LOW:
            return PromotionDecision(
                experiment_id=experiment_id,
                variant_id=result.variant_id,
                decision=PromotionDecisionType.AUTO_APPLY,
                result=result,
                requires_approval=False,
                reason=f"Low risk, significant positive lift: {result.relative_lift:.1%} at {result.confidence:.1%} confidence",
            )
        else:
            return PromotionDecision(
                experiment_id=experiment_id,
                variant_id=result.variant_id,
                decision=PromotionDecisionType.APPROVE,
                result=result,
                requires_approval=True,
                reason=f"{experiment.risk_level.value} risk, significant positive lift: {result.relative_lift:.1%} at {result.confidence:.1%} confidence - requires approval",
            )

    def evaluate_all_running(
        self,
        metrics_fetcher: Callable[[str, str], dict],
    ) -> list[tuple[EvaluationResult, PromotionDecision]]:
        """Evaluate all running experiments.
        
        Args:
            metrics_fetcher: Callable that takes (experiment_id, variant_id) and returns metrics dict
        
        Returns:
            List of (evaluation_result, promotion_decision) tuples
        """
        results = []
        
        for experiment in self._registry.list_experiments():
            if experiment.status != ExperimentStatus.RUNNING:
                continue
            
            # Get control variant (first variant)
            control_variant = experiment.variants[0]
            control_metrics = metrics_fetcher(experiment.experiment_id, control_variant.variant_id)
            
            # Evaluate each treatment variant
            for variant in experiment.variants[1:]:
                treatment_metrics = metrics_fetcher(experiment.experiment_id, variant.variant_id)
                
                evaluation = self.evaluate(
                    experiment_id=experiment.experiment_id,
                    variant_id=variant.variant_id,
                    control_metrics=control_metrics,
                    treatment_metrics=treatment_metrics,
                )
                
                decision = self.decide_promotion(experiment.experiment_id, evaluation)
                results.append((evaluation, decision))
        
        return results

    def apply_decision(self, decision: PromotionDecision) -> bool:
        """Apply a promotion decision to the experiment.
        
        Returns True if the decision was applied, False otherwise.
        """
        if decision.requires_approval:
            # Cannot auto-apply decisions that require approval
            return False
        
        if decision.decision == PromotionDecisionType.AUTO_APPLY:
            self._registry.complete_experiment(decision.experiment_id)
            return True
        elif decision.decision == PromotionDecisionType.ROLLBACK:
            self._registry.rollback_experiment(decision.experiment_id)
            return True
        
        return False
