from __future__ import annotations

import re
import threading
from datetime import datetime, timezone
from typing import Any


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._latencies: dict[str, list[float]] = {}
        self._costs: dict[str, float] = {}

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
