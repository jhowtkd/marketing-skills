"""v45 Simulation Models - Data structures for rollout simulation.

This module provides deterministic data structures for simulating
promotion and rollback scenarios in onboarding experiments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class ExperimentPhase(str, Enum):
    """Phases of the rollout experiment lifecycle."""
    CONTROL_BASELINE = "control_baseline"
    TREATMENT_EVALUATION = "treatment_evaluation"
    TREATMENT_PROMOTED = "treatment_promoted"
    TREATMENT_DEGRADED = "treatment_degraded"
    ROLLED_BACK = "rolled_back"


class RolloutDecisionType(str, Enum):
    """Types of rollout decisions."""
    PROMOTE = "promote"
    CONTINUE = "continue"
    ROLLBACK = "rollback"
    BLOCK = "block"


@dataclass
class JourneyMetrics:
    """Metrics for a single onboarding journey."""
    user_id: str
    variant_id: str
    completed: bool
    time_to_first_value_ms: int
    steps_completed: int
    total_steps: int
    abandonment_step: Optional[str] = None
    prefill_used: bool = False
    fast_lane_used: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "variant_id": self.variant_id,
            "completed": self.completed,
            "time_to_first_value_ms": self.time_to_first_value_ms,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "abandonment_step": self.abandonment_step,
            "prefill_used": self.prefill_used,
            "fast_lane_used": self.fast_lane_used,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class VariantMetrics:
    """Aggregated metrics for a variant."""
    variant_id: str
    sample_size: int
    conversions: int
    total_time_to_value_ms: int
    avg_time_to_value_ms: float
    completion_rate: float
    abandonment_rate: float
    prefill_adoption: float
    fast_lane_adoption: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "variant_id": self.variant_id,
            "sample_size": self.sample_size,
            "conversions": self.conversions,
            "total_time_to_value_ms": self.total_time_to_value_ms,
            "avg_time_to_value_ms": self.avg_time_to_value_ms,
            "completion_rate": self.completion_rate,
            "abandonment_rate": self.abandonment_rate,
            "prefill_adoption": self.prefill_adoption,
            "fast_lane_adoption": self.fast_lane_adoption,
        }


@dataclass
class ExperimentMetrics:
    """Metrics for an entire experiment with multiple variants."""
    experiment_id: str
    variant_metrics: Dict[str, VariantMetrics]
    control_variant_id: str = "control"
    
    def get_control_metrics(self) -> Optional[VariantMetrics]:
        """Get metrics for control variant."""
        return self.variant_metrics.get(self.control_variant_id)
    
    def get_treatment_metrics(self, treatment_id: str = "treatment") -> Optional[VariantMetrics]:
        """Get metrics for treatment variant."""
        return self.variant_metrics.get(treatment_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "control_variant_id": self.control_variant_id,
            "variant_metrics": {
                k: v.to_dict() for k, v in self.variant_metrics.items()
            },
        }


@dataclass
class PromotionPolicyConfig:
    """Configuration for promotion policy."""
    min_sample_size: int = 100
    min_confidence: float = 0.95
    min_relative_lift: float = 0.05
    max_degradation_threshold: float = 0.10
    ttfv_efficiency_weight: float = 0.50
    completion_rate_weight: float = 0.35
    abandonment_rate_weight: float = 0.15
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "min_sample_size": self.min_sample_size,
            "min_confidence": self.min_confidence,
            "min_relative_lift": self.min_relative_lift,
            "max_degradation_threshold": self.max_degradation_threshold,
            "ttfv_efficiency_weight": self.ttfv_efficiency_weight,
            "completion_rate_weight": self.completion_rate_weight,
            "abandonment_rate_weight": self.abandonment_rate_weight,
        }


@dataclass
class RollbackPolicyConfig:
    """Configuration for rollback policy."""
    max_completion_rate_drop: float = 0.15
    max_ttfv_increase_ratio: float = 1.30
    min_sample_size_for_rollback: int = 50
    consecutive_failures_threshold: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_completion_rate_drop": self.max_completion_rate_drop,
            "max_ttfv_increase_ratio": self.max_ttfv_increase_ratio,
            "min_sample_size_for_rollback": self.min_sample_size_for_rollback,
            "consecutive_failures_threshold": self.consecutive_failures_threshold,
        }


@dataclass
class GateCheck:
    """Result of a gate check."""
    gate_name: str
    passed: bool
    value: float
    threshold: float
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gate_name": self.gate_name,
            "passed": self.passed,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }


@dataclass
class PhaseResult:
    """Result of a phase in the rollout simulation."""
    phase: ExperimentPhase
    experiment_id: str
    variant_id: str
    metrics: VariantMetrics
    gate_checks: List[GateCheck]
    decision: RolloutDecisionType
    decision_reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "phase": self.phase.value,
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "metrics": self.metrics.to_dict(),
            "gate_checks": [g.to_dict() for g in self.gate_checks],
            "decision": self.decision.value,
            "decision_reason": self.decision_reason,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SimulationReport:
    """Complete report of a rollout simulation."""
    simulation_id: str
    experiment_id: str
    phases: List[PhaseResult]
    final_decision: RolloutDecisionType
    final_state: ExperimentPhase
    promotion_policy: PromotionPolicyConfig
    rollback_policy: RollbackPolicyConfig
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def add_phase(self, phase: PhaseResult) -> None:
        """Add a phase result."""
        self.phases.append(phase)
    
    def complete(self) -> None:
        """Mark simulation as complete."""
        self.completed_at = datetime.utcnow()
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate simulation duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "simulation_id": self.simulation_id,
            "experiment_id": self.experiment_id,
            "phases": [p.to_dict() for p in self.phases],
            "final_decision": self.final_decision.value,
            "final_state": self.final_state.value,
            "promotion_policy": self.promotion_policy.to_dict(),
            "rollback_policy": self.rollback_policy.to_dict(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }
