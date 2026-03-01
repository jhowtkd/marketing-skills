from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class QualityOptimizerMetrics:
    """v25 Quality-First Constrained Optimizer metrics."""
    # Counters
    cycles_total: int = 0
    proposals_generated_total: int = 0
    proposals_applied_total: int = 0
    proposals_blocked_total: int = 0
    proposals_rejected_total: int = 0
    rollbacks_total: int = 0
    
    # Impact expectations
    quality_gain_expected: float = 0.0  # Total expected V1 score improvement
    cost_impact_expected_pct: float = 0.0  # Expected cost impact %
    time_impact_expected_pct: float = 0.0  # Expected MTTC impact %
    
    # Constraint compliance
    constraint_violations_cost: int = 0
    constraint_violations_time: int = 0
    constraint_violations_incident: int = 0
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_proposal_applied_at: Optional[str] = None


@dataclass
class ApprovalLearningMetrics:
    """v24 Approval Learning Loop metrics."""
    # Counters
    learning_cycles_total: int = 0
    proposals_generated_total: int = 0
    proposals_applied_total: int = 0
    proposals_blocked_total: int = 0
    proposals_rejected_total: int = 0
    rollbacks_total: int = 0
    
    # Learning impact
    batch_precision_percent: float = 0.0
    human_minutes_saved: float = 0.0
    queue_reduction_percent: float = 0.0
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_proposal_applied_at: Optional[str] = None


@dataclass
class ControlLoopMetrics:
    """v26 Online Control Loop metrics."""
    # Counters
    cycles_total: int = 0
    regressions_detected_total: int = 0
    mitigations_applied_total: int = 0
    mitigations_blocked_total: int = 0
    rollbacks_total: int = 0
    
    # Time-based metrics (in seconds)
    time_to_detect_seconds: float = 0.0
    time_to_mitigate_seconds: float = 0.0
    time_to_detect_count: int = 0  # Number of measurements
    time_to_mitigate_count: int = 0
    
    # Active state
    active_cycles: int = 0
    frozen_brands: int = 0
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_regression_detected_at: Optional[str] = None
    last_mitigation_applied_at: Optional[str] = None
    last_rollback_at: Optional[str] = None


@dataclass
class RoiOptimizerMetrics:
    """v19 ROI Optimizer metrics snapshot."""
    # Counters
    cycles_total: int = 0
    proposals_generated_total: int = 0
    proposals_applied_total: int = 0
    proposals_blocked_total: int = 0
    proposals_rejected_total: int = 0
    rollbacks_total: int = 0
    
    # Gauges - ROI composite
    roi_composite_score: float = 0.0
    roi_business_contribution: float = 0.0
    roi_quality_contribution: float = 0.0
    roi_efficiency_contribution: float = 0.0
    
    # Pillar scores
    business_pillar_score: float = 0.0
    quality_pillar_score: float = 0.0
    efficiency_pillar_score: float = 0.0
    
    # Timestamps
    last_run_at: Optional[str] = None
    last_applied_at: Optional[str] = None


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._latencies: dict[str, list[float]] = {}
        self._costs: dict[str, float] = {}
        self._roi_metrics = RoiOptimizerMetrics()
        self._learning_metrics = ApprovalLearningMetrics()
        self._quality_metrics = QualityOptimizerMetrics()
        self._control_loop_metrics = ControlLoopMetrics()
    
    # v24: Approval Learning Loop metrics
    def record_learning_cycle(self) -> None:
        """v24: Record a learning cycle run."""
        with self._lock:
            self._learning_metrics.learning_cycles_total += 1
            self._learning_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()
    
    def record_learning_proposal(self, status: str = "generated") -> None:
        """v24: Record a learning proposal."""
        with self._lock:
            self._learning_metrics.proposals_generated_total += 1
            if status == "blocked":
                self._learning_metrics.proposals_blocked_total += 1
            elif status == "rejected":
                self._learning_metrics.proposals_rejected_total += 1
    
    def record_learning_proposal_applied(self) -> None:
        """v24: Record a learning proposal being applied."""
        with self._lock:
            self._learning_metrics.proposals_applied_total += 1
            self._learning_metrics.last_proposal_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_learning_rollback(self) -> None:
        """v24: Record a learning rollback operation."""
        with self._lock:
            self._learning_metrics.rollbacks_total += 1
    
    def update_learning_impact(
        self,
        batch_precision: float,
        minutes_saved: float,
        queue_reduction: float,
    ) -> None:
        """v24: Update learning impact gauges."""
        with self._lock:
            self._learning_metrics.batch_precision_percent = batch_precision
            self._learning_metrics.human_minutes_saved = minutes_saved
            self._learning_metrics.queue_reduction_percent = queue_reduction
    
    def get_learning_metrics(self) -> ApprovalLearningMetrics:
        """v24: Get current learning metrics snapshot."""
        with self._lock:
            return ApprovalLearningMetrics(
                learning_cycles_total=self._learning_metrics.learning_cycles_total,
                proposals_generated_total=self._learning_metrics.proposals_generated_total,
                proposals_applied_total=self._learning_metrics.proposals_applied_total,
                proposals_blocked_total=self._learning_metrics.proposals_blocked_total,
                proposals_rejected_total=self._learning_metrics.proposals_rejected_total,
                rollbacks_total=self._learning_metrics.rollbacks_total,
                batch_precision_percent=self._learning_metrics.batch_precision_percent,
                human_minutes_saved=self._learning_metrics.human_minutes_saved,
                queue_reduction_percent=self._learning_metrics.queue_reduction_percent,
                last_cycle_at=self._learning_metrics.last_cycle_at,
                last_proposal_applied_at=self._learning_metrics.last_proposal_applied_at,
            )
    
    # v25: Quality-First Optimizer metrics
    def record_quality_cycle(self) -> None:
        """v25: Record a quality optimizer cycle run."""
        with self._lock:
            self._quality_metrics.cycles_total += 1
            self._quality_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()
    
    def record_quality_proposal(self, status: str) -> None:
        """v25: Record a proposal generated with given status."""
        with self._lock:
            self._quality_metrics.proposals_generated_total += 1
            if status == "blocked":
                self._quality_metrics.proposals_blocked_total += 1
            elif status == "rejected":
                self._quality_metrics.proposals_rejected_total += 1
    
    def record_quality_proposal_applied(self) -> None:
        """v25: Record a proposal being applied."""
        with self._lock:
            self._quality_metrics.proposals_applied_total += 1
            self._quality_metrics.last_proposal_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_quality_rollback(self) -> None:
        """v25: Record a rollback operation."""
        with self._lock:
            self._quality_metrics.rollbacks_total += 1
    
    def record_quality_impact(
        self,
        quality_gain: float,
        cost_impact_pct: float,
        time_impact_pct: float,
    ) -> None:
        """v25: Record expected impact metrics."""
        with self._lock:
            self._quality_metrics.quality_gain_expected += quality_gain
            self._quality_metrics.cost_impact_expected_pct = cost_impact_pct
            self._quality_metrics.time_impact_expected_pct = time_impact_pct
    
    def record_constraint_violation(self, violation_type: str) -> None:
        """v25: Record a constraint violation."""
        with self._lock:
            if violation_type == "cost":
                self._quality_metrics.constraint_violations_cost += 1
            elif violation_type == "time":
                self._quality_metrics.constraint_violations_time += 1
            elif violation_type == "incident":
                self._quality_metrics.constraint_violations_incident += 1
    
    def get_quality_metrics(self) -> QualityOptimizerMetrics:
        """v25: Get current quality optimizer metrics snapshot."""
        with self._lock:
            return QualityOptimizerMetrics(
                cycles_total=self._quality_metrics.cycles_total,
                proposals_generated_total=self._quality_metrics.proposals_generated_total,
                proposals_applied_total=self._quality_metrics.proposals_applied_total,
                proposals_blocked_total=self._quality_metrics.proposals_blocked_total,
                proposals_rejected_total=self._quality_metrics.proposals_rejected_total,
                rollbacks_total=self._quality_metrics.rollbacks_total,
                quality_gain_expected=self._quality_metrics.quality_gain_expected,
                cost_impact_expected_pct=self._quality_metrics.cost_impact_expected_pct,
                time_impact_expected_pct=self._quality_metrics.time_impact_expected_pct,
                constraint_violations_cost=self._quality_metrics.constraint_violations_cost,
                constraint_violations_time=self._quality_metrics.constraint_violations_time,
                constraint_violations_incident=self._quality_metrics.constraint_violations_incident,
                last_cycle_at=self._quality_metrics.last_cycle_at,
                last_proposal_applied_at=self._quality_metrics.last_proposal_applied_at,
            )
    
    # v26: Online Control Loop metrics
    def record_control_loop_cycle(self) -> None:
        """v26: Record a control loop cycle run."""
        with self._lock:
            self._control_loop_metrics.cycles_total += 1
            self._control_loop_metrics.active_cycles += 1
            self._control_loop_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()
    
    def record_regression_detected(self) -> None:
        """v26: Record a regression detection."""
        with self._lock:
            self._control_loop_metrics.regressions_detected_total += 1
            self._control_loop_metrics.last_regression_detected_at = datetime.now(timezone.utc).isoformat()
    
    def record_mitigation_applied(self) -> None:
        """v26: Record a mitigation being applied."""
        with self._lock:
            self._control_loop_metrics.mitigations_applied_total += 1
            self._control_loop_metrics.last_mitigation_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_mitigation_blocked(self) -> None:
        """v26: Record a mitigation being blocked."""
        with self._lock:
            self._control_loop_metrics.mitigations_blocked_total += 1
    
    def record_control_loop_rollback(self) -> None:
        """v26: Record a rollback operation."""
        with self._lock:
            self._control_loop_metrics.rollbacks_total += 1
            self._control_loop_metrics.last_rollback_at = datetime.now(timezone.utc).isoformat()
    
    def record_time_to_detect(self, seconds: float) -> None:
        """v26: Record time to detect regression (seconds)."""
        with self._lock:
            # Running average
            current = self._control_loop_metrics.time_to_detect_seconds
            count = self._control_loop_metrics.time_to_detect_count
            new_count = count + 1
            new_avg = (current * count + seconds) / new_count
            self._control_loop_metrics.time_to_detect_seconds = new_avg
            self._control_loop_metrics.time_to_detect_count = new_count
    
    def record_time_to_mitigate(self, seconds: float) -> None:
        """v26: Record time to mitigate regression (seconds)."""
        with self._lock:
            current = self._control_loop_metrics.time_to_mitigate_seconds
            count = self._control_loop_metrics.time_to_mitigate_count
            new_count = count + 1
            new_avg = (current * count + seconds) / new_count
            self._control_loop_metrics.time_to_mitigate_seconds = new_avg
            self._control_loop_metrics.time_to_mitigate_count = new_count
    
    def update_active_cycles(self, count: int) -> None:
        """v26: Update active cycles count."""
        with self._lock:
            self._control_loop_metrics.active_cycles = count
    
    def update_frozen_brands(self, count: int) -> None:
        """v26: Update frozen brands count."""
        with self._lock:
            self._control_loop_metrics.frozen_brands = count
    
    def get_control_loop_metrics(self) -> ControlLoopMetrics:
        """v26: Get current control loop metrics snapshot."""
        with self._lock:
            return ControlLoopMetrics(
                cycles_total=self._control_loop_metrics.cycles_total,
                regressions_detected_total=self._control_loop_metrics.regressions_detected_total,
                mitigations_applied_total=self._control_loop_metrics.mitigations_applied_total,
                mitigations_blocked_total=self._control_loop_metrics.mitigations_blocked_total,
                rollbacks_total=self._control_loop_metrics.rollbacks_total,
                time_to_detect_seconds=self._control_loop_metrics.time_to_detect_seconds,
                time_to_mitigate_seconds=self._control_loop_metrics.time_to_mitigate_seconds,
                time_to_detect_count=self._control_loop_metrics.time_to_detect_count,
                time_to_mitigate_count=self._control_loop_metrics.time_to_mitigate_count,
                active_cycles=self._control_loop_metrics.active_cycles,
                frozen_brands=self._control_loop_metrics.frozen_brands,
                last_cycle_at=self._control_loop_metrics.last_cycle_at,
                last_regression_detected_at=self._control_loop_metrics.last_regression_detected_at,
                last_mitigation_applied_at=self._control_loop_metrics.last_mitigation_applied_at,
                last_rollback_at=self._control_loop_metrics.last_rollback_at,
            )
    
    # v19: ROI Optimizer metrics
    def record_roi_cycle(self) -> None:
        """v19: Record an ROI optimizer cycle run."""
        with self._lock:
            self._roi_metrics.cycles_total += 1
            self._roi_metrics.last_run_at = datetime.now(timezone.utc).isoformat()
    
    def record_roi_proposal(self, status: str) -> None:
        """v19: Record a proposal generated with given status."""
        with self._lock:
            self._roi_metrics.proposals_generated_total += 1
            if status == "blocked":
                self._roi_metrics.proposals_blocked_total += 1
            elif status == "rejected":
                self._roi_metrics.proposals_rejected_total += 1
    
    def record_roi_proposal_applied(self) -> None:
        """v19: Record a proposal being applied."""
        with self._lock:
            self._roi_metrics.proposals_applied_total += 1
            self._roi_metrics.last_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_roi_rollback(self) -> None:
        """v19: Record a rollback operation."""
        with self._lock:
            self._roi_metrics.rollbacks_total += 1
    
    def update_roi_scores(
        self,
        composite_score: float,
        business_contrib: float,
        quality_contrib: float,
        efficiency_contrib: float,
        business_pillar: float,
        quality_pillar: float,
        efficiency_pillar: float,
    ) -> None:
        """v19: Update ROI score gauges."""
        with self._lock:
            self._roi_metrics.roi_composite_score = composite_score
            self._roi_metrics.roi_business_contribution = business_contrib
            self._roi_metrics.roi_quality_contribution = quality_contrib
            self._roi_metrics.roi_efficiency_contribution = efficiency_contrib
            self._roi_metrics.business_pillar_score = business_pillar
            self._roi_metrics.quality_pillar_score = quality_pillar
            self._roi_metrics.efficiency_pillar_score = efficiency_pillar
    
    def get_roi_metrics(self) -> RoiOptimizerMetrics:
        """v19: Get current ROI metrics snapshot."""
        with self._lock:
            return RoiOptimizerMetrics(
                cycles_total=self._roi_metrics.cycles_total,
                proposals_generated_total=self._roi_metrics.proposals_generated_total,
                proposals_applied_total=self._roi_metrics.proposals_applied_total,
                proposals_blocked_total=self._roi_metrics.proposals_blocked_total,
                proposals_rejected_total=self._roi_metrics.proposals_rejected_total,
                rollbacks_total=self._roi_metrics.rollbacks_total,
                roi_composite_score=self._roi_metrics.roi_composite_score,
                roi_business_contribution=self._roi_metrics.roi_business_contribution,
                roi_quality_contribution=self._roi_metrics.roi_quality_contribution,
                roi_efficiency_contribution=self._roi_metrics.roi_efficiency_contribution,
                business_pillar_score=self._roi_metrics.business_pillar_score,
                quality_pillar_score=self._roi_metrics.quality_pillar_score,
                efficiency_pillar_score=self._roi_metrics.efficiency_pillar_score,
                last_run_at=self._roi_metrics.last_run_at,
                last_applied_at=self._roi_metrics.last_applied_at,
            )

    def record_count(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counts[name] = self._counts.get(name, 0) + value

    def record_latency(self, name: str, seconds: float) -> None:
        with self._lock:
            self._latencies.setdefault(name, []).append(seconds)

    def record_cost(self, name: str, amount: float) -> None:
        with self._lock:
            self._costs[name] = self._costs.get(name, 0.0) + amount

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_latencies = {
                key: sum(values) / len(values) if values else 0.0
                for key, values in self._latencies.items()
            }
            return {
                "counts": dict(self._counts),
                "avg_latencies": avg_latencies,
                "total_costs": dict(self._costs),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # v25 Quality Optimizer metrics
                "quality_optimizer_v25": {
                    "cycles_total": self._quality_metrics.cycles_total,
                    "proposals_generated_total": self._quality_metrics.proposals_generated_total,
                    "proposals_applied_total": self._quality_metrics.proposals_applied_total,
                    "proposals_blocked_total": self._quality_metrics.proposals_blocked_total,
                    "proposals_rejected_total": self._quality_metrics.proposals_rejected_total,
                    "rollbacks_total": self._quality_metrics.rollbacks_total,
                    "quality_gain_expected": self._quality_metrics.quality_gain_expected,
                    "cost_impact_expected_pct": self._quality_metrics.cost_impact_expected_pct,
                    "time_impact_expected_pct": self._quality_metrics.time_impact_expected_pct,
                    "constraint_violations_cost": self._quality_metrics.constraint_violations_cost,
                    "constraint_violations_time": self._quality_metrics.constraint_violations_time,
                    "constraint_violations_incident": self._quality_metrics.constraint_violations_incident,
                },
                # v26 Online Control Loop metrics
                "control_loop_v26": {
                    "cycles_total": self._control_loop_metrics.cycles_total,
                    "regressions_detected_total": self._control_loop_metrics.regressions_detected_total,
                    "mitigations_applied_total": self._control_loop_metrics.mitigations_applied_total,
                    "mitigations_blocked_total": self._control_loop_metrics.mitigations_blocked_total,
                    "rollbacks_total": self._control_loop_metrics.rollbacks_total,
                    "time_to_detect_seconds": self._control_loop_metrics.time_to_detect_seconds,
                    "time_to_mitigate_seconds": self._control_loop_metrics.time_to_mitigate_seconds,
                    "active_cycles": self._control_loop_metrics.active_cycles,
                    "frozen_brands": self._control_loop_metrics.frozen_brands,
                    "last_cycle_at": self._control_loop_metrics.last_cycle_at,
                    "last_regression_detected_at": self._control_loop_metrics.last_regression_detected_at,
                },
            }


def _normalize_metric_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.replace(":", "_"))
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if not sanitized:
        return "metric"
    if sanitized[0].isdigit():
        sanitized = f"m_{sanitized}"
    return sanitized.lower()


def render_prometheus(snapshot: dict[str, Any], *, prefix: str = "vm") -> str:
    lines: list[str] = []

    counts = snapshot.get("counts")
    if isinstance(counts, dict):
        for name in sorted(counts):
            metric_name = f"{prefix}_{_normalize_metric_name(str(name))}"
            value = int(counts[name])
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{metric_name} {value}")

    avg_latencies = snapshot.get("avg_latencies")
    if isinstance(avg_latencies, dict):
        for name in sorted(avg_latencies):
            metric_name = f"{prefix}_{_normalize_metric_name(str(name))}"
            value = float(avg_latencies[name])
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{metric_name} {value:.6f}")

    total_costs = snapshot.get("total_costs")
    if isinstance(total_costs, dict):
        for name in sorted(total_costs):
            metric_name = f"{prefix}_{_normalize_metric_name(str(name))}"
            value = float(total_costs[name])
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{metric_name} {value:.6f}")

    if not lines:
        lines.append("# no metrics recorded")
    return "\n".join(lines) + "\n"
