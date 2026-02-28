from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


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
