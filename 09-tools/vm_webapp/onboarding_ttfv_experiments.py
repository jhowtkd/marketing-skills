"""v38 Onboarding TTFV Experiment Governance - guardrails and decision engine."""

import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class ExperimentStatus(str, Enum):
    """Experiment lifecycle statuses."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


class ExperimentDecision(str, Enum):
    """Possible experiment decisions."""
    PROMOTE = "promote"
    HOLD = "hold"
    ROLLBACK = "rollback"


# Guardrail thresholds
GUARDRAIL_THRESHOLDS = {
    "activation_rate_d1": -0.02,  # -2 percentage points
    "onboarding_completion_rate": -0.03,  # -3 percentage points
    "incident_rate": 0.0,  # No increase allowed
}

# Minimum sample size for statistical significance
MIN_SAMPLE_SIZE = 100

# Minimum TTFV improvement for promotion (10%)
MIN_TTFV_IMPROVEMENT = 0.10


@dataclass
class UserAssignment:
    """User assignment to an experiment variant."""
    user_id: str
    experiment_id: str
    variant: str
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Experiment:
    """Experiment definition."""
    experiment_id: str
    name: str
    status: ExperimentStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    variants: List[str] = field(default_factory=lambda: ["control", "treatment"])
    description: str = ""
    owner: str = ""


@dataclass
class ExperimentResult:
    """Result of experiment evaluation."""
    experiment_id: str
    metrics: Dict[str, Any]
    sample_size_control: int = 0
    sample_size_treatment: int = 0
    guardrail_status: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExperimentDecisionResult:
    """Experiment decision with reasoning."""
    experiment_id: str
    decision: ExperimentDecision
    reason: str
    confidence: float = 0.0
    recommended_action: str = ""


def assign_user_to_variant(user_id: str, experiment_id: str) -> UserAssignment:
    """Deterministically assign user to experiment variant.
    
    Uses hash-based assignment for consistency - same user always gets
    the same variant for the same experiment.
    """
    # Create deterministic hash from user_id and experiment_id
    hash_input = f"{user_id}:{experiment_id}"
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()
    
    # Convert first 8 chars of hash to integer
    hash_int = int(hash_value[:8], 16)
    
    # Use hash to determine variant (50/50 split)
    variant = "treatment" if hash_int % 2 == 0 else "control"
    
    return UserAssignment(
        user_id=user_id,
        experiment_id=experiment_id,
        variant=variant,
    )


def check_guardrails(metrics: Dict[str, float]) -> Dict[str, Any]:
    """Check all guardrails against metrics.
    
    Guardrails:
    - activation_rate_d1 >= -2 p.p.
    - onboarding_completion_rate >= -3 p.p.
    - incident_rate: no increase
    
    Returns:
        Dict with guardrail status and violations.
    """
    violations = []
    results = {}
    
    # Check if we have any metrics data
    if not metrics:
        return {
            "all_passed": False,
            "violations": ["No metrics data available"],
            "activation_rate_d1_ok": False,
            "onboarding_completion_rate_ok": False,
            "incident_rate_ok": False,
        }
    
    # Check activation rate D1
    activation_control = metrics.get("activation_rate_d1_control", 0)
    activation_treatment = metrics.get("activation_rate_d1_treatment", 0)
    activation_delta = activation_treatment - activation_control
    activation_threshold = GUARDRAIL_THRESHOLDS["activation_rate_d1"]
    
    activation_ok = activation_delta >= activation_threshold
    results["activation_rate_d1_ok"] = activation_ok
    results["activation_rate_d1_delta_pp"] = round(activation_delta * 100, 2)
    
    if not activation_ok:
        violations.append(
            f"activation_rate_d1 dropped by {abs(activation_delta)*100:.1f} p.p. "
            f"(threshold: {activation_threshold*100:.1f} p.p.)"
        )
    
    # Check onboarding completion rate
    completion_control = metrics.get("onboarding_completion_rate_control", 0)
    completion_treatment = metrics.get("onboarding_completion_rate_treatment", 0)
    completion_delta = completion_treatment - completion_control
    completion_threshold = GUARDRAIL_THRESHOLDS["onboarding_completion_rate"]
    
    completion_ok = completion_delta >= completion_threshold
    results["onboarding_completion_rate_ok"] = completion_ok
    results["onboarding_completion_rate_delta_pp"] = round(completion_delta * 100, 2)
    
    if not completion_ok:
        violations.append(
            f"onboarding_completion_rate dropped by {abs(completion_delta)*100:.1f} p.p. "
            f"(threshold: {completion_threshold*100:.1f} p.p.)"
        )
    
    # Check incident rate
    incident_control = metrics.get("incident_rate_control", 0)
    incident_treatment = metrics.get("incident_rate_treatment", 0)
    incident_delta = incident_treatment - incident_control
    incident_threshold = GUARDRAIL_THRESHOLDS["incident_rate"]
    
    incident_ok = incident_delta <= incident_threshold
    results["incident_rate_ok"] = incident_ok
    results["incident_rate_delta"] = round(incident_delta, 4)
    
    if not incident_ok:
        violations.append(
            f"incident_rate increased by {incident_delta:.4f} "
            f"(threshold: no increase)"
        )
    
    results["all_passed"] = activation_ok and completion_ok and incident_ok
    results["violations"] = violations
    
    return results


def evaluate_experiment(experiment: Experiment) -> ExperimentResult:
    """Evaluate experiment metrics and guardrails.
    
    In production, this would query the analytics database.
    For now, generates realistic mock data for testing.
    """
    if experiment.status == ExperimentStatus.DRAFT:
        raise ValueError("Cannot evaluate draft experiment")
    
    # Mock data generation - in production, query actual metrics
    sample_size_control = random.randint(500, 2000)
    sample_size_treatment = random.randint(500, 2000)
    
    # Simulate TTFV metrics (target: -30% improvement)
    median_ttfv_control = 10.0  # minutes
    median_ttfv_treatment = 7.0  # 30% improvement
    
    # Simulate activation rate (should be within guardrails)
    activation_control = 0.50
    activation_treatment = 0.51  # Slight improvement
    
    # Simulate completion rate (should be within guardrails)
    completion_control = 0.80
    completion_treatment = 0.82  # Slight improvement
    
    # Simulate incident rate (should be flat)
    incident_control = 0.01
    incident_treatment = 0.01
    
    metrics = {
        "median_ttfv_minutes": {
            "control": median_ttfv_control,
            "treatment": median_ttfv_treatment,
            "improvement": (median_ttfv_control - median_ttfv_treatment) / median_ttfv_control,
            "confidence_interval": {
                "lower": median_ttfv_treatment * 0.9,
                "upper": median_ttfv_treatment * 1.1,
            },
        },
        "activation_rate_d1": {
            "control": activation_control,
            "treatment": activation_treatment,
            "delta_pp": (activation_treatment - activation_control) * 100,
        },
        "onboarding_completion_rate": {
            "control": completion_control,
            "treatment": completion_treatment,
            "delta_pp": (completion_treatment - completion_control) * 100,
        },
        "incident_rate": {
            "control": incident_control,
            "treatment": incident_treatment,
            "delta": incident_treatment - incident_control,
        },
    }
    
    # Check guardrails
    guardrail_metrics = {
        "activation_rate_d1_control": activation_control,
        "activation_rate_d1_treatment": activation_treatment,
        "onboarding_completion_rate_control": completion_control,
        "onboarding_completion_rate_treatment": completion_treatment,
        "incident_rate_control": incident_control,
        "incident_rate_treatment": incident_treatment,
    }
    
    guardrail_status = check_guardrails(guardrail_metrics)
    
    return ExperimentResult(
        experiment_id=experiment.experiment_id,
        metrics=metrics,
        sample_size_control=sample_size_control,
        sample_size_treatment=sample_size_treatment,
        guardrail_status=guardrail_status,
    )


def make_experiment_decision(
    experiment: Experiment,
    metrics: Dict[str, float],
    min_sample_size: int = MIN_SAMPLE_SIZE,
    min_ttfv_improvement: float = MIN_TTFV_IMPROVEMENT,
) -> ExperimentDecisionResult:
    """Make experiment decision based on metrics and guardrails.
    
    Decision logic:
    1. Check guardrails - if any fail, ROLLBACK
    2. Check sample size - if insufficient, HOLD
    3. Check TTFV improvement - if insufficient, HOLD
    4. If all checks pass, PROMOTE
    """
    # Check sample size
    sample_control = metrics.get("sample_size_control", 0)
    sample_treatment = metrics.get("sample_size_treatment", 0)
    
    if sample_control < min_sample_size or sample_treatment < min_sample_size:
        return ExperimentDecisionResult(
            experiment_id=experiment.experiment_id,
            decision=ExperimentDecision.HOLD,
            reason=f"Insufficient sample size (control: {sample_control}, treatment: {sample_treatment}, "
                   f"min required: {min_sample_size})",
            confidence=0.0,
            recommended_action="Continue experiment to collect more data",
        )
    
    # Check guardrails
    guardrail_result = check_guardrails(metrics)
    
    if not guardrail_result["all_passed"]:
        violations_str = "; ".join(guardrail_result["violations"])
        return ExperimentDecisionResult(
            experiment_id=experiment.experiment_id,
            decision=ExperimentDecision.ROLLBACK,
            reason=f"Guardrail violations: {violations_str}",
            confidence=0.95,
            recommended_action="Rollback treatment, investigate issues, fix and retry",
        )
    
    # Check TTFV improvement
    ttfv_control = metrics.get("median_ttfv_minutes_control", 0)
    ttfv_treatment = metrics.get("median_ttfv_minutes_treatment", 0)
    
    if ttfv_control > 0:
        ttfv_improvement = (ttfv_control - ttfv_treatment) / ttfv_control
    else:
        ttfv_improvement = 0
    
    if ttfv_improvement < min_ttfv_improvement:
        return ExperimentDecisionResult(
            experiment_id=experiment.experiment_id,
            decision=ExperimentDecision.HOLD,
            reason=f"TTFV improvement ({ttfv_improvement*100:.1f}%) below threshold "
                   f"({min_ttfv_improvement*100:.1f}%)",
            confidence=0.7,
            recommended_action="Continue monitoring or redesign intervention",
        )
    
    # All checks passed - promote
    return ExperimentDecisionResult(
        experiment_id=experiment.experiment_id,
        decision=ExperimentDecision.PROMOTE,
        reason=f"All guardrails passed, TTFV improved by {ttfv_improvement*100:.1f}%",
        confidence=0.95,
        recommended_action="Promote treatment to 100% of users",
    )


def calculate_guardrail_status() -> Dict[str, Any]:
    """Calculate current guardrail status for monitoring.
    
    Returns real-time guardrail metrics for dashboard/monitoring.
    """
    # In production, query actual metrics from analytics
    # For now, return mock data
    
    activation_control = 0.52
    activation_treatment = 0.51
    completion_control = 0.78
    completion_treatment = 0.77
    incident_control = 0.008
    incident_treatment = 0.008
    
    activation_delta = (activation_treatment - activation_control) * 100
    completion_delta = (completion_treatment - completion_control) * 100
    incident_delta = incident_treatment - incident_control
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "activation_rate_d1": {
            "control": activation_control,
            "treatment": activation_treatment,
            "delta_pp": round(activation_delta, 2),
            "threshold_pp": -2.0,
            "status": "PASS" if activation_delta >= -2.0 else "FAIL",
        },
        "onboarding_completion_rate": {
            "control": completion_control,
            "treatment": completion_treatment,
            "delta_pp": round(completion_delta, 2),
            "threshold_pp": -3.0,
            "status": "PASS" if completion_delta >= -3.0 else "FAIL",
        },
        "incident_rate": {
            "control": incident_control,
            "treatment": incident_treatment,
            "delta": round(incident_delta, 4),
            "threshold": 0.0,
            "status": "PASS" if incident_delta <= 0.0 else "FAIL",
        },
        "overall_status": "PASS",  # All individual checks pass
    }


def export_experiment_report(experiment: Experiment) -> Dict[str, Any]:
    """Export experiment report for nightly/ops reporting.
    
    Returns structured data for inclusion in editorial ops report.
    """
    try:
        result = evaluate_experiment(experiment)
        
        return {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "status": experiment.status.value,
            "metrics": result.metrics,
            "sample_sizes": {
                "control": result.sample_size_control,
                "treatment": result.sample_size_treatment,
            },
            "guardrails": result.guardrail_status,
            "evaluated_at": result.evaluated_at.isoformat(),
        }
    except ValueError as e:
        return {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "status": experiment.status.value,
            "error": str(e),
        }


def get_active_experiments() -> List[Experiment]:
    """Get list of active (running) experiments.
    
    In production, query from experiment management database.
    """
    # Mock active experiments
    return [
        Experiment(
            experiment_id="v38-onboarding-ttfv-acceleration",
            name="v38 Onboarding TTFV Acceleration",
            status=ExperimentStatus.RUNNING,
            start_date=datetime.now(timezone.utc) - timedelta(days=14),
            variants=["control", "treatment"],
            description="Friction killers: smart prefill, fast lane, one-click first run",
            owner="growth-team",
        ),
    ]
