from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading

@dataclass
class MetricSnapshot:
    counts: dict[str, int] = field(default_factory=dict)
    latencies: dict[str, float] = field(default_factory=dict)
    costs: dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._latencies: dict[str, list[float]] = {}
        self._costs: dict[str, float] = {}

    def record_count(self, name: str, value: int = 1):
        with self._lock:
            self._counts[name] = self._counts.get(name, 0) + value

    def record_latency(self, name: str, seconds: float):
        with self._lock:
            if name not in self._latencies:
                self._latencies[name] = []
            self._latencies[name].append(seconds)

    def record_cost(self, name: str, amount: float):
        with self._lock:
            self._costs[name] = self._costs.get(name, 0.0) + amount

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_latencies = {
                k: sum(v) / len(v) if v else 0.0
                for k, v in self._latencies.items()
            }
            return {
                "counts": dict(self._counts),
                "avg_latencies": avg_latencies,
                "total_costs": dict(self._costs),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
