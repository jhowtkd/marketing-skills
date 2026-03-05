"""v45 Rollout Engines - Promotion and Rollback engines for onboarding experiments.

This module provides deterministic engines for:
- PromotionEngine: Deciding when to promote treatment to production
- RollbackEngine: Detecting degradation and triggering rollback
- PolicyPersistence: Storing and retrieving policy configurations
- Individual Gates: Validating specific criteria
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from tests.simulations.simulation_models import (
    ExperimentMetrics,
    GateCheck,
    PromotionPolicyConfig,
    RollbackPolicyConfig,
    RolloutDecisionType,
    VariantMetrics,
)
from vm_webapp.onboarding_personalization import (
    PersonalizationPolicy,
    PolicyStatus,
    RiskLevel,
    SegmentKey,
)


# =============================================================================
# INDIVIDUAL GATES
# =============================================================================

@dataclass
class ConfidenceGate:
    """Gate for checking statistical confidence."""
    min_confidence: float = 0.95
    
    def check(self, confidence: float) -> GateCheck:
        """Check if confidence meets threshold."""
        passed = confidence >= self.min_confidence
        return GateCheck(
            gate_name="confidence",
            passed=passed,
            value=confidence,
            threshold=self.min_confidence,
            message=f"Confidence {confidence:.2%} {'meets' if passed else 'below'} threshold {self.min_confidence:.2%}",
        )


@dataclass
class DegradationGate:
    """Gate for checking degradation against baseline."""
    max_degradation: float = 0.10
    
    def check(self, current_value: float, baseline_value: float) -> GateCheck:
        """Check if degradation is within acceptable limits."""
        if baseline_value == 0:
            return GateCheck(
                gate_name="degradation",
                passed=True,
                value=0.0,
                threshold=self.max_degradation,
                message="No baseline available for degradation check",
            )
        
        degradation = (baseline_value - current_value) / baseline_value
        passed = degradation <= self.max_degradation
        
        return GateCheck(
            gate_name="degradation",
            passed=passed,
            value=degradation,
            threshold=self.max_degradation,
            message=f"Degradation {degradation:.1%} {'within' if passed else 'exceeds'} limit {self.max_degradation:.1%}",
        )


@dataclass
class SampleSizeGate:
    """Gate for checking minimum sample size."""
    min_sample_size: int = 100
    
    def check(self, sample_size: int) -> GateCheck:
        """Check if sample size meets minimum."""
        passed = sample_size >= self.min_sample_size
        return GateCheck(
            gate_name="sample_size",
            passed=passed,
            value=float(sample_size),
            threshold=float(self.min_sample_size),
            message=f"Sample size {sample_size} {'meets' if passed else 'below'} minimum {self.min_sample_size}",
        )


@dataclass
class LiftGate:
    """Gate for checking relative lift."""
    min_lift: float = 0.05
    
    def check(self, relative_lift: float) -> GateCheck:
        """Check if relative lift meets minimum."""
        passed = relative_lift >= self.min_lift
        return GateCheck(
            gate_name="relative_lift",
            passed=passed,
            value=relative_lift,
            threshold=self.min_lift,
            message=f"Lift {relative_lift:.1%} {'meets' if passed else 'below'} minimum {self.min_lift:.1%}",
        )


@dataclass
class TTFVGate:
    """Gate for checking Time to First Value increase."""
    max_increase_ratio: float = 1.30
    
    def check(self, current_ttfv: float, baseline_ttfv: float) -> GateCheck:
        """Check if TTFV increase is within limits."""
        if baseline_ttfv == 0:
            return GateCheck(
                gate_name="ttfv_increase",
                passed=True,
                value=0.0,
                threshold=self.max_increase_ratio,
                message="No baseline TTFV available",
            )
        
        ratio = current_ttfv / baseline_ttfv
        passed = ratio <= self.max_increase_ratio
        
        return GateCheck(
            gate_name="ttfv_increase",
            passed=passed,
            value=ratio,
            threshold=self.max_increase_ratio,
            message=f"TTFV ratio {ratio:.2f}x {'within' if passed else 'exceeds'} limit {self.max_increase_ratio:.2f}x",
        )


@dataclass
class CompletionRateDropGate:
    """Gate for checking completion rate drop."""
    max_drop: float = 0.15
    
    def check(self, current_rate: float, baseline_rate: float) -> GateCheck:
        """Check if completion rate drop is within limits."""
        if baseline_rate == 0:
            return GateCheck(
                gate_name="completion_rate_drop",
                passed=True,
                value=0.0,
                threshold=self.max_drop,
                message="No baseline rate available",
            )
        
        drop = baseline_rate - current_rate
        passed = drop <= self.max_drop
        
        return GateCheck(
            gate_name="completion_rate_drop",
            passed=passed,
            value=drop,
            threshold=self.max_drop,
            message=f"Completion rate drop {drop:.1%} {'within' if passed else 'exceeds'} limit {self.max_drop:.1%}",
        )


# =============================================================================
# PROMOTION ENGINE
# =============================================================================

@dataclass
class PromotionEngine:
    """Engine for deciding when to promote treatment variants."""
    
    config: PromotionPolicyConfig = field(default_factory=PromotionPolicyConfig)
    decision_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def calculate_lift(self, metrics: ExperimentMetrics, variant_id: str) -> float:
        """Calculate relative lift of variant vs control."""
        control = metrics.get_control_metrics()
        variant = metrics.variant_metrics.get(variant_id)
        
        if not control or not variant:
            return 0.0
        
        if control.completion_rate == 0:
            return 0.0
        
        return (variant.completion_rate - control.completion_rate) / control.completion_rate
    
    def calculate_ttfv_efficiency(self, metrics: ExperimentMetrics, variant_id: str) -> float:
        """Calculate TTFV efficiency (lower is better)."""
        control = metrics.get_control_metrics()
        variant = metrics.variant_metrics.get(variant_id)
        
        if not control or not variant:
            return 1.0
        
        if variant.avg_time_to_value_ms == 0:
            return 1.0
        
        return control.avg_time_to_value_ms / variant.avg_time_to_value_ms
    
    def calculate_score(self, metrics: ExperimentMetrics, variant_id: str) -> float:
        """Calculate weighted score for variant."""
        variant = metrics.variant_metrics.get(variant_id)
        if not variant:
            return 0.0
        
        ttfv_efficiency = self.calculate_ttfv_efficiency(metrics, variant_id)
        completion_rate = variant.completion_rate
        abandonment_rate = 1.0 - completion_rate
        
        score = (
            self.config.ttfv_efficiency_weight * ttfv_efficiency +
            self.config.completion_rate_weight * completion_rate +
            self.config.abandonment_rate_weight * (1.0 - abandonment_rate)
        )
        
        return score
    
    def check_sample_size_gate(self, metrics: ExperimentMetrics, variant_id: str) -> GateCheck:
        """Check if variant has sufficient sample size."""
        variant = metrics.variant_metrics.get(variant_id)
        if not variant:
            return GateCheck(
                gate_name="sample_size",
                passed=False,
                value=0.0,
                threshold=float(self.config.min_sample_size),
                message="Variant not found",
            )
        
        gate = SampleSizeGate(min_sample_size=self.config.min_sample_size)
        return gate.check(variant.sample_size)
    
    def check_lift_gate(self, metrics: ExperimentMetrics, variant_id: str) -> GateCheck:
        """Check if variant meets lift requirements."""
        lift = self.calculate_lift(metrics, variant_id)
        gate = LiftGate(min_lift=self.config.min_relative_lift)
        return gate.check(lift)
    
    def decide(self, metrics: ExperimentMetrics, variant_id: str) -> Tuple[RolloutDecisionType, str]:
        """Decide whether to promote variant."""
        variant = metrics.variant_metrics.get(variant_id)
        if not variant:
            return RolloutDecisionType.BLOCK, "Variant not found"
        
        # Check sample size
        sample_check = self.check_sample_size_gate(metrics, variant_id)
        if not sample_check.passed:
            self._record_decision(metrics.experiment_id, variant_id, RolloutDecisionType.CONTINUE, sample_check.message)
            return RolloutDecisionType.CONTINUE, sample_check.message
        
        # Check lift
        lift_check = self.check_lift_gate(metrics, variant_id)
        if not lift_check.passed:
            self._record_decision(metrics.experiment_id, variant_id, RolloutDecisionType.CONTINUE, lift_check.message)
            return RolloutDecisionType.CONTINUE, lift_check.message
        
        # All checks passed - promote
        reason = f"Sufficient lift ({lift_check.value:.1%}) with adequate sample size ({variant.sample_size})"
        self._record_decision(metrics.experiment_id, variant_id, RolloutDecisionType.PROMOTE, reason)
        return RolloutDecisionType.PROMOTE, reason
    
    def _record_decision(self, experiment_id: str, variant_id: str, decision: RolloutDecisionType, reason: str) -> None:
        """Record decision in history."""
        self.decision_history.append({
            "experiment_id": experiment_id,
            "variant_id": variant_id,
            "decision": decision.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })


# =============================================================================
# ROLLBACK ENGINE
# =============================================================================

@dataclass
class RollbackEngine:
    """Engine for detecting degradation and triggering rollback."""
    
    config: RollbackPolicyConfig = field(default_factory=RollbackPolicyConfig)
    violation_history: List[Dict[str, Any]] = field(default_factory=list)
    consecutive_violations: int = 0
    
    def check_completion_rate(self, metrics: ExperimentMetrics, variant_id: str) -> GateCheck:
        """Check if completion rate drop is within limits."""
        control = metrics.get_control_metrics()
        variant = metrics.variant_metrics.get(variant_id)
        
        if not control or not variant:
            return GateCheck(
                gate_name="completion_rate_drop",
                passed=True,
                value=0.0,
                threshold=self.config.max_completion_rate_drop,
                message="Missing metrics for comparison",
            )
        
        gate = CompletionRateDropGate(max_drop=self.config.max_completion_rate_drop)
        return gate.check(variant.completion_rate, control.completion_rate)
    
    def check_ttfv_increase(self, metrics: ExperimentMetrics, variant_id: str) -> GateCheck:
        """Check if TTFV increase is within limits."""
        control = metrics.get_control_metrics()
        variant = metrics.variant_metrics.get(variant_id)
        
        if not control or not variant:
            return GateCheck(
                gate_name="ttfv_increase",
                passed=True,
                value=0.0,
                threshold=self.config.max_ttfv_increase_ratio,
                message="Missing metrics for comparison",
            )
        
        gate = TTFVGate(max_increase_ratio=self.config.max_ttfv_increase_ratio)
        return gate.check(variant.avg_time_to_value_ms, control.avg_time_to_value_ms)
    
    def check_sample_size(self, metrics: ExperimentMetrics, variant_id: str) -> GateCheck:
        """Check if sample size is sufficient for rollback decision."""
        variant = metrics.variant_metrics.get(variant_id)
        if not variant:
            return GateCheck(
                gate_name="sample_size_rollback",
                passed=False,
                value=0.0,
                threshold=float(self.config.min_sample_size_for_rollback),
                message="Variant not found",
            )
        
        gate = SampleSizeGate(min_sample_size=self.config.min_sample_size_for_rollback)
        return gate.check(variant.sample_size)
    
    def decide(self, metrics: ExperimentMetrics, variant_id: str) -> Tuple[RolloutDecisionType, str]:
        """Decide whether to rollback variant."""
        variant = metrics.variant_metrics.get(variant_id)
        if not variant:
            return RolloutDecisionType.BLOCK, "Variant not found"
        
        # Check sample size first
        sample_check = self.check_sample_size(metrics, variant_id)
        if not sample_check.passed:
            return RolloutDecisionType.CONTINUE, f"Insufficient sample size for rollback decision: {variant.sample_size}"
        
        # Check degradation metrics
        completion_check = self.check_completion_rate(metrics, variant_id)
        ttfv_check = self.check_ttfv_increase(metrics, variant_id)
        
        violations = []
        if not completion_check.passed:
            violations.append(completion_check.message)
        if not ttfv_check.passed:
            violations.append(ttfv_check.message)
        
        if violations:
            self.consecutive_violations += 1
            self._record_violation(metrics.experiment_id, variant_id, violations)
            
            if self.consecutive_violations >= self.config.consecutive_failures_threshold:
                reason = f"Rollback triggered after {self.consecutive_violations} consecutive violations: {'; '.join(violations)}"
                return RolloutDecisionType.ROLLBACK, reason
            else:
                reason = f"Degradation detected ({self.consecutive_violations}/{self.config.consecutive_failures_threshold}): {'; '.join(violations)}"
                return RolloutDecisionType.CONTINUE, reason
        else:
            # Reset consecutive violations on healthy check
            self.consecutive_violations = 0
            return RolloutDecisionType.CONTINUE, "All metrics healthy"
    
    def _record_violation(self, experiment_id: str, variant_id: str, violations: List[str]) -> None:
        """Record violation in history."""
        self.violation_history.append({
            "experiment_id": experiment_id,
            "variant_id": variant_id,
            "violations": violations,
            "consecutive_count": self.consecutive_violations,
            "timestamp": datetime.utcnow().isoformat(),
        })


# =============================================================================
# POLICY PERSISTENCE
# =============================================================================

class PolicyPersistence:
    """Persistence layer for personalization policies."""
    
    def __init__(self, storage_path: str = ".policies"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _policy_to_dict(self, policy: PersonalizationPolicy) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "policy_id": policy.policy_id,
            "segment_key": {
                "company_size": policy.segment_key.company_size if policy.segment_key else "*",
                "industry": policy.segment_key.industry if policy.segment_key else "*",
                "experience_level": policy.segment_key.experience_level if policy.segment_key else "*",
                "traffic_source": policy.segment_key.traffic_source if policy.segment_key else "*",
            } if policy.segment_key else None,
            "nudge_delay_ms": policy.nudge_delay_ms,
            "template_order": policy.template_order,
            "welcome_message": policy.welcome_message,
            "show_video_tutorial": policy.show_video_tutorial,
            "max_steps": policy.max_steps,
            "risk_level": policy.risk_level.value,
            "status": policy.status.value,
            "created_at": policy.created_at,
            "activated_at": policy.activated_at,
            "frozen_at": policy.frozen_at,
            "rolled_back_at": policy.rolled_back_at,
        }
    
    def _dict_to_policy(self, data: Dict[str, Any]) -> PersonalizationPolicy:
        """Convert dictionary to policy."""
        segment_key = None
        if data.get("segment_key"):
            segment_key = SegmentKey(
                company_size=data["segment_key"]["company_size"],
                industry=data["segment_key"]["industry"],
                experience_level=data["segment_key"]["experience_level"],
                traffic_source=data["segment_key"]["traffic_source"],
            )
        
        policy = PersonalizationPolicy(
            policy_id=data["policy_id"],
            segment_key=segment_key,
            nudge_delay_ms=data["nudge_delay_ms"],
            template_order=data["template_order"],
            welcome_message=data["welcome_message"],
            show_video_tutorial=data["show_video_tutorial"],
            max_steps=data["max_steps"],
            risk_level=RiskLevel(data["risk_level"]),
        )
        
        # Restore status and timestamps
        policy.status = PolicyStatus(data["status"])
        policy.created_at = data["created_at"]
        policy.activated_at = data.get("activated_at")
        policy.frozen_at = data.get("frozen_at")
        policy.rolled_back_at = data.get("rolled_back_at")
        
        return policy
    
    def save_policy(self, policy: PersonalizationPolicy) -> None:
        """Save policy to storage."""
        policy_file = self.storage_path / f"{policy.policy_id}.json"
        with open(policy_file, "w") as f:
            json.dump(self._policy_to_dict(policy), f, indent=2)
    
    def load_policy(self, policy_id: str) -> Optional[PersonalizationPolicy]:
        """Load policy from storage."""
        policy_file = self.storage_path / f"{policy_id}.json"
        if not policy_file.exists():
            return None
        
        with open(policy_file, "r") as f:
            data = json.load(f)
        
        return self._dict_to_policy(data)
    
    def list_policies(self) -> List[PersonalizationPolicy]:
        """List all saved policies."""
        policies = []
        for policy_file in self.storage_path.glob("*.json"):
            policy_id = policy_file.stem
            policy = self.load_policy(policy_id)
            if policy:
                policies.append(policy)
        return policies
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete policy from storage."""
        policy_file = self.storage_path / f"{policy_id}.json"
        if policy_file.exists():
            policy_file.unlink()
            return True
        return False


if __name__ == "__main__":
    # Quick test
    print("Rollout Engines - v45")
    print("=" * 50)
    
    # Test gates
    gate = ConfidenceGate(min_confidence=0.95)
    result = gate.check(0.97)
    print(f"Confidence gate (0.97 >= 0.95): {result.passed}")
    
    # Test promotion engine
    promo_engine = PromotionEngine()
    print(f"Promotion engine initialized: {promo_engine.config.min_sample_size}")
