"""Policy Operations Engine for v47.

Automated daily evaluation of experiment policies with promote/hold/rollback decisions.
Supports AUTO/SUPERVISED/MANUAL modes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from vm_webapp.onboarding_rollout_policy import (
    BenchmarkMetrics,
    RolloutMode,
    RolloutPolicy,
    check_promotion_gates,
    load_policy,
    save_policy,
    list_active_policies,
)

logger = logging.getLogger(__name__)


class RecommendationAction(str, Enum):
    """Possible recommendation actions from policy evaluation."""
    PROMOTE = "promote"
    HOLD = "hold"
    ROLLBACK = "rollback"


class RecommendationStatus(str, Enum):
    """Status of a recommendation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    APPLIED = "applied"


@dataclass
class PolicyRecommendation:
    """Recommendation from policy evaluation.
    
    Attributes:
        experiment_id: ID of the experiment
        action: Recommended action (promote/hold/rollback)
        confidence: Confidence score 0.0-1.0
        rationale: Human-readable explanation
        status: Current status of the recommendation
        created_at: When recommendation was created
        evaluated_at: When evaluation was performed
        expires_at: When recommendation expires (optional)
        operator_id: Who approved/rejected (if applicable)
        metrics_snapshot: Metrics used for decision
    """
    experiment_id: str
    action: RecommendationAction
    confidence: float = 0.0
    rationale: str = ""
    status: RecommendationStatus = RecommendationStatus.PENDING
    created_at: Optional[str] = None
    evaluated_at: Optional[str] = None
    expires_at: Optional[str] = None
    operator_id: Optional[str] = None
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class EvaluationResult:
    """Result of evaluating a single experiment policy."""
    experiment_id: str
    recommendation: PolicyRecommendation
    gates_passed: list[str] = field(default_factory=list)
    gates_failed: list[str] = field(default_factory=list)
    control_metrics: Optional[BenchmarkMetrics] = None
    variant_metrics: Optional[BenchmarkMetrics] = None


class PolicyOpsEngine:
    """Engine for daily policy operations and automated recommendations.
    
    Evaluates active experiment policies daily and generates recommendations
    for promote/hold/rollback actions based on configured gates.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the policy ops engine.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> dict[str, Any]:
        """Load engine configuration."""
        default_config = {
            "min_confidence_for_auto": 0.8,
            "min_sample_size": 30,
            "default_expiry_hours": 24,
            "confidence_weights": {
                "sample_size": 0.4,
                "metric_stability": 0.3,
                "gate_clearance": 0.3,
            },
        }
        
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config: {e}, using defaults")
        
        return default_config
    
    def evaluate_daily(
        self,
        experiment_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> list[EvaluationResult]:
        """Run daily evaluation of experiment policies.
        
        Args:
            experiment_id: Specific experiment to evaluate (optional, all if None)
            dry_run: If True, don't persist any changes
            
        Returns:
            List of evaluation results
        """
        results = []
        
        # Load policies to evaluate
        if experiment_id:
            policy = load_policy(experiment_id)
            policies = [policy] if policy else []
        else:
            policies = list_active_policies()
        
        logger.info(f"Evaluating {len(policies)} policies (dry_run={dry_run})")
        
        for policy in policies:
            try:
                result = self._evaluate_single_policy(policy, dry_run)
                results.append(result)
                logger.info(f"Evaluated {policy.experiment_id}: {result.recommendation.action} "
                           f"(confidence={result.recommendation.confidence:.2f})")
            except Exception as e:
                logger.error(f"Failed to evaluate {policy.experiment_id}: {e}")
                # Continue with other policies
        
        return results
    
    def _evaluate_single_policy(
        self,
        policy: RolloutPolicy,
        dry_run: bool,
    ) -> EvaluationResult:
        """Evaluate a single policy and generate recommendation."""
        # Fetch metrics (placeholder - would integrate with actual metrics system)
        control_metrics, variant_metrics = self._fetch_metrics(policy.experiment_id)
        
        # Check promotion gates
        if control_metrics and variant_metrics:
            gates_result = check_promotion_gates(control_metrics, variant_metrics)
            gates_passed = [k for k, v in gates_result.items() if v]
            gates_failed = [k for k, v in gates_result.items() if not v]
        else:
            gates_passed = []
            gates_failed = ["metrics_unavailable"]
        
        # Determine recommendation
        action, confidence, rationale = self._recommend_action(
            policy=policy,
            control_metrics=control_metrics,
            variant_metrics=variant_metrics,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )
        
        # Create recommendation
        recommendation = PolicyRecommendation(
            experiment_id=policy.experiment_id,
            action=action,
            confidence=confidence,
            rationale=rationale,
            status=RecommendationStatus.PENDING,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            metrics_snapshot={
                "control_sample": control_metrics.sample_size if control_metrics else 0,
                "variant_sample": variant_metrics.sample_size if variant_metrics else 0,
                "gates_passed": len(gates_passed),
                "gates_failed": len(gates_failed),
            },
        )
        
        # Set expiry
        expiry_hours = self._config.get("default_expiry_hours", 24)
        expiry = datetime.now(timezone.utc)
        expiry = expiry.replace(hour=expiry.hour + expiry_hours)
        recommendation.expires_at = expiry.isoformat()
        
        # Persist recommendation (unless dry_run)
        if not dry_run:
            self._save_recommendation(recommendation)
        
        return EvaluationResult(
            experiment_id=policy.experiment_id,
            recommendation=recommendation,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            control_metrics=control_metrics,
            variant_metrics=variant_metrics,
        )
    
    def _fetch_metrics(
        self,
        experiment_id: str,
    ) -> tuple[Optional[BenchmarkMetrics], Optional[BenchmarkMetrics]]:
        """Fetch metrics for an experiment.
        
        In production, this would query actual metrics from analytics.
        For now, returns placeholder data.
        """
        # TODO: Integrate with actual metrics system
        # This is a placeholder implementation
        import random
        
        # Generate synthetic metrics for testing
        control = BenchmarkMetrics(
            ttfv=25.0 + random.uniform(-2, 2),
            completion_rate=0.85 + random.uniform(-0.05, 0.05),
            abandonment_rate=0.15 + random.uniform(-0.03, 0.03),
            score=1.0,
            sample_size=random.randint(40, 60),
        )
        
        variant = BenchmarkMetrics(
            ttfv=22.0 + random.uniform(-2, 2),
            completion_rate=0.88 + random.uniform(-0.05, 0.05),
            abandonment_rate=0.12 + random.uniform(-0.03, 0.03),
            score=1.02 + random.uniform(-0.02, 0.05),
            sample_size=random.randint(35, 55),
        )
        
        return control, variant
    
    def _recommend_action(
        self,
        policy: RolloutPolicy,
        control_metrics: Optional[BenchmarkMetrics],
        variant_metrics: Optional[BenchmarkMetrics],
        gates_passed: list[str],
        gates_failed: list[str],
    ) -> tuple[RecommendationAction, float, str]:
        """Determine recommended action based on evaluation.
        
        Returns:
            Tuple of (action, confidence, rationale)
        """
        # Calculate confidence
        confidence = self._calculate_confidence(
            control_metrics, variant_metrics, gates_passed, gates_failed
        )
        
        # Build rationale
        rationale_parts = []
        
        # Check mode
        if policy.rollout_mode == RolloutMode.MANUAL:
            return (
                RecommendationAction.HOLD,
                confidence,
                "Manual mode: automated promotion disabled. Review metrics and promote manually if desired.",
            )
        
        # Check if we have metrics
        if not control_metrics or not variant_metrics:
            return (
                RecommendationAction.HOLD,
                0.0,
                "Insufficient metrics data for evaluation. Waiting for more samples.",
            )
        
        # Check sample size
        min_sample = self._config.get("min_sample_size", 30)
        if variant_metrics.sample_size < min_sample:
            return (
                RecommendationAction.HOLD,
                confidence * 0.5,
                f"Insufficient sample size ({variant_metrics.sample_size} < {min_sample}). "
                "Continue monitoring for statistical significance.",
            )
        
        # Check for degradation (rollback condition)
        if control_metrics and variant_metrics:
            if variant_metrics.score < control_metrics.score * 0.9:
                return (
                    RecommendationAction.ROLLBACK,
                    confidence,
                    f"Variant score degraded ({variant_metrics.score:.3f} vs control {control_metrics.score:.3f}). "
                    f"Rollback recommended to protect user experience.",
                )
        
        # Check gates
        if len(gates_failed) == 0:
            # All gates passed
            if policy.rollout_mode == RolloutMode.SUPERVISED:
                rationale = (
                    f"All {len(gates_passed)} promotion gates passed. "
                    f"SUPERVISED mode: awaiting manual approval before promotion."
                )
            else:
                rationale = (
                    f"All {len(gates_passed)} promotion gates passed. "
                    f"AUTO mode: ready for automatic promotion."
                )
            return RecommendationAction.PROMOTE, confidence, rationale
        else:
            # Some gates failed
            return (
                RecommendationAction.HOLD,
                confidence,
                f"{len(gates_failed)} gate(s) failed: {', '.join(gates_failed)}. "
                f"Continue monitoring or adjust experiment configuration.",
            )
    
    def _calculate_confidence(
        self,
        control_metrics: Optional[BenchmarkMetrics],
        variant_metrics: Optional[BenchmarkMetrics],
        gates_passed: list[str],
        gates_failed: list[str],
    ) -> float:
        """Calculate confidence score for recommendation.
        
        Returns score between 0.0 and 1.0 based on:
        - Sample size (more samples = higher confidence)
        - Metric stability
        - Gate clearance
        """
        weights = self._config.get("confidence_weights", {})
        sample_weight = weights.get("sample_size", 0.4)
        stability_weight = weights.get("metric_stability", 0.3)
        gate_weight = weights.get("gate_clearance", 0.3)
        
        # Sample size score (sigmoid-like curve)
        if variant_metrics:
            sample_score = min(variant_metrics.sample_size / 50.0, 1.0)
        else:
            sample_score = 0.0
        
        # Stability score (placeholder)
        stability_score = 0.8  # Would calculate from metric variance
        
        # Gate clearance score
        total_gates = len(gates_passed) + len(gates_failed)
        if total_gates > 0:
            gate_score = len(gates_passed) / total_gates
        else:
            gate_score = 0.5
        
        # Weighted sum
        confidence = (
            sample_weight * sample_score +
            stability_weight * stability_score +
            gate_weight * gate_score
        )
        
        return round(confidence, 3)
    
    def _save_recommendation(self, recommendation: PolicyRecommendation) -> None:
        """Save recommendation to persistence layer."""
        # Use JSON storage in config directory (v45 pattern)
        config_dir = Path("09-tools/config/policy_ops")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = config_dir / f"{recommendation.experiment_id}_recommendation.json"
        
        data = {
            "experiment_id": recommendation.experiment_id,
            "action": recommendation.action.value,
            "confidence": recommendation.confidence,
            "rationale": recommendation.rationale,
            "status": recommendation.status.value,
            "created_at": recommendation.created_at,
            "evaluated_at": recommendation.evaluated_at,
            "expires_at": recommendation.expires_at,
            "operator_id": recommendation.operator_id,
            "metrics_snapshot": recommendation.metrics_snapshot,
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Saved recommendation to {filepath}")


def get_pending_recommendations() -> list[PolicyRecommendation]:
    """Get all pending recommendations.
    
    Returns:
        List of recommendations with status=PENDING
    """
    config_dir = Path("09-tools/config/policy_ops")
    if not config_dir.exists():
        return []
    
    recommendations = []
    for filepath in config_dir.glob("*_recommendation.json"):
        try:
            with open(filepath) as f:
                data = json.load(f)
            
            if data.get("status") == RecommendationStatus.PENDING.value:
                rec = PolicyRecommendation(
                    experiment_id=data["experiment_id"],
                    action=RecommendationAction(data["action"]),
                    confidence=data["confidence"],
                    rationale=data["rationale"],
                    status=RecommendationStatus(data["status"]),
                    created_at=data.get("created_at"),
                    evaluated_at=data.get("evaluated_at"),
                    expires_at=data.get("expires_at"),
                    operator_id=data.get("operator_id"),
                    metrics_snapshot=data.get("metrics_snapshot", {}),
                )
                recommendations.append(rec)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load recommendation from {filepath}: {e}")
    
    # Sort by created_at (newest first)
    recommendations.sort(key=lambda r: r.created_at or "", reverse=True)
    return recommendations


def update_recommendation_status(
    experiment_id: str,
    status: RecommendationStatus,
    operator_id: Optional[str] = None,
) -> Optional[PolicyRecommendation]:
    """Update the status of a recommendation.
    
    Args:
        experiment_id: ID of the experiment
        status: New status
        operator_id: ID of operator making the change (optional)
        
    Returns:
        Updated recommendation or None if not found
    """
    config_dir = Path("09-tools/config/policy_ops")
    filepath = config_dir / f"{experiment_id}_recommendation.json"
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath) as f:
            data = json.load(f)
        
        data["status"] = status.value
        if operator_id:
            data["operator_id"] = operator_id
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        return PolicyRecommendation(
            experiment_id=data["experiment_id"],
            action=RecommendationAction(data["action"]),
            confidence=data["confidence"],
            rationale=data["rationale"],
            status=status,
            created_at=data.get("created_at"),
            evaluated_at=data.get("evaluated_at"),
            expires_at=data.get("expires_at"),
            operator_id=data.get("operator_id"),
            metrics_snapshot=data.get("metrics_snapshot", {}),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to update recommendation: {e}")
        return None
