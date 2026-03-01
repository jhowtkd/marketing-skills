"""
DAG Audit Trail e Metrics - v22 Multi-Agent Orchestrator
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class DagAuditEvent:
    """Evento de auditoria para operações DAG."""
    event_id: str
    event_type: str  # run_started, node_started, node_completed, node_failed, approval_requested, etc.
    run_id: str
    dag_id: str
    node_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict[str, Any] = field(default_factory=dict)
    actor: str = "system"  # system, user:<id>, agent:<id>


class DagAuditTrail:
    """Registro de auditoria para operações DAG."""
    
    def __init__(self, max_events: int = 10000):
        self._events: list[DagAuditEvent] = []
        self._max_events = max_events
        self._lock = threading.Lock()
    
    def log_event(
        self,
        event_type: str,
        run_id: str,
        dag_id: str,
        node_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        actor: str = "system",
    ) -> DagAuditEvent:
        """Registra um evento de auditoria."""
        from uuid import uuid4
        
        event = DagAuditEvent(
            event_id=uuid4().hex[:16],
            event_type=event_type,
            run_id=run_id,
            dag_id=dag_id,
            node_id=node_id,
            details=details or {},
            actor=actor,
        )
        
        with self._lock:
            self._events.append(event)
            # Trim se necessário
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
        
        return event
    
    def get_events(
        self,
        run_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[DagAuditEvent]:
        """Retorna eventos filtrados."""
        with self._lock:
            events = self._events.copy()
        
        if run_id:
            events = [e for e in events if e.run_id == run_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def get_run_timeline(self, run_id: str) -> list[DagAuditEvent]:
        """Retorna timeline completa de uma run."""
        return self.get_events(run_id=run_id, limit=1000)


class DagMetricsCollector:
    """Coletor de métricas Prometheus para DAG."""
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Contadores
        self._runs_total = {"completed": 0, "failed": 0, "aborted": 0, "timeout": 0}
        self._nodes_total = {"completed": 0, "failed": 0, "timeout": 0, "skipped": 0}
        self._retries_total = 0
        self._handoff_failures_total = 0
        self._approvals_total = {"pending": 0, "granted": 0, "rejected": 0, "escalated": 0}
        
        # Gauges
        self._approval_wait_times: list[float] = []
        self._node_execution_times: list[float] = []
        
        # P0: Métricas de falha por node_type
        self._handoff_failures_by_node_type: dict[str, int] = {}
        self._timeouts_by_node_type: dict[str, int] = {}
        self._retries_by_node_type: dict[str, int] = {}
    
    def record_run(self, status: str) -> None:
        """Registra conclusão de uma run."""
        with self._lock:
            if status in self._runs_total:
                self._runs_total[status] += 1
    
    def record_node_execution(self, status: str, duration_sec: Optional[float] = None) -> None:
        """Registra execução de um nó."""
        with self._lock:
            if status in self._nodes_total:
                self._nodes_total[status] += 1
            if duration_sec is not None:
                self._node_execution_times.append(duration_sec)
    
    def record_retry(self) -> None:
        """Registra um retry."""
        with self._lock:
            self._retries_total += 1
    
    def record_handoff_failure(self, node_type: Optional[str] = None) -> None:
        """Registra uma falha de handoff."""
        with self._lock:
            self._handoff_failures_total += 1
            if node_type:
                self._handoff_failures_by_node_type[node_type] = \
                    self._handoff_failures_by_node_type.get(node_type, 0) + 1
    
    def record_approval(self, status: str, wait_sec: Optional[float] = None) -> None:
        """Registra uma aprovação."""
        with self._lock:
            if status in self._approvals_total:
                self._approvals_total[status] += 1
            if wait_sec is not None:
                self._approval_wait_times.append(wait_sec)
    
    def get_snapshot(self) -> dict[str, Any]:
        """Retorna snapshot das métricas."""
        with self._lock:
            avg_approval_wait = (
                sum(self._approval_wait_times) / len(self._approval_wait_times)
                if self._approval_wait_times else 0.0
            )
            avg_node_execution = (
                sum(self._node_execution_times) / len(self._node_execution_times)
                if self._node_execution_times else 0.0
            )
            
            return {
                "runs": self._runs_total.copy(),
                "nodes": self._nodes_total.copy(),
                "retries_total": self._retries_total,
                "handoff_failures_total": self._handoff_failures_total,
                "handoff_failures_by_node_type": self._handoff_failures_by_node_type.copy(),
                "timeouts_by_node_type": self._timeouts_by_node_type.copy(),
                "approvals": self._approvals_total.copy(),
                "avg_approval_wait_sec": avg_approval_wait,
                "avg_node_execution_sec": avg_node_execution,
            }
    
    def render_prometheus(self) -> str:
        """Renderiza métricas no formato Prometheus."""
        snapshot = self.get_snapshot()
        lines = []
        
        # Runs
        lines.append("# HELP dag_runs_total Total DAG runs")
        lines.append("# TYPE dag_runs_total counter")
        for status, count in snapshot["runs"].items():
            lines.append(f'dag_runs_total{{status="{status}"}} {count}')
        
        # Nodes
        lines.append("# HELP dag_node_executions_total Total node executions")
        lines.append("# TYPE dag_node_executions_total counter")
        for status, count in snapshot["nodes"].items():
            lines.append(f'dag_node_executions_total{{status="{status}"}} {count}')
        
        # Retries
        lines.append("# HELP dag_retries_total Total node retries")
        lines.append("# TYPE dag_retries_total counter")
        lines.append(f'dag_retries_total {snapshot["retries_total"]}')
        
        # Timeouts
        lines.append("# HELP dag_timeouts_total Total timeouts")
        lines.append("# TYPE dag_timeouts_total counter")
        lines.append(f'dag_timeouts_total {snapshot["nodes"]["timeout"]}')
        
        # Handoff failures
        lines.append("# HELP dag_handoff_failed_total Total handoff failures")
        lines.append("# TYPE dag_handoff_failed_total counter")
        lines.append(f'dag_handoff_failed_total {snapshot["handoff_failures_total"]}')
        
        # P0: Handoff failures by node_type
        lines.append("# HELP dag_handoff_failed_total_by_node_type Handoff failures by node type")
        lines.append("# TYPE dag_handoff_failed_total_by_node_type counter")
        for node_type, count in snapshot.get("handoff_failures_by_node_type", {}).items():
            lines.append(f'dag_handoff_failed_total_by_node_type{{node_type="{node_type}"}} {count}')
        
        # Approvals
        lines.append("# HELP dag_approvals_total Total approval requests")
        lines.append("# TYPE dag_approvals_total counter")
        for status, count in snapshot["approvals"].items():
            lines.append(f'dag_approvals_total{{status="{status}"}} {count}')
        
        # Gauges
        lines.append("# HELP dag_approval_wait_seconds Average approval wait time")
        lines.append("# TYPE dag_approval_wait_seconds gauge")
        lines.append(f'dag_approval_wait_seconds {snapshot["avg_approval_wait_sec"]}')
        
        lines.append("# HELP dag_node_execution_seconds Average node execution time")
        lines.append("# TYPE dag_node_execution_seconds gauge")
        lines.append(f'dag_node_execution_seconds {snapshot["avg_node_execution_sec"]}')
        
        return "\n".join(lines) + "\n"
    
    def get_bottlenecks(self) -> list[dict[str, Any]]:
        """Identifica gargalos baseado nas métricas."""
        snapshot = self.get_snapshot()
        bottlenecks = []
        
        total_nodes = sum(snapshot["nodes"].values())
        if total_nodes == 0:
            return bottlenecks
        
        # Identifica tipos de nó com alta taxa de falha
        for status, count in snapshot["nodes"].items():
            if status == "failed":
                failure_rate = count / total_nodes if total_nodes > 0 else 0
                if failure_rate > 0.1:  # Mais de 10% falha
                    bottlenecks.append({
                        "node_type": "general",
                        "failure_rate": failure_rate,
                        "avg_wait_sec": snapshot["avg_approval_wait_sec"],
                    })
        
        return bottlenecks


# Instância global para coleta de métricas
_dag_metrics = DagMetricsCollector()


def get_dag_metrics() -> DagMetricsCollector:
    """Retorna coletor de métricas global."""
    return _dag_metrics
