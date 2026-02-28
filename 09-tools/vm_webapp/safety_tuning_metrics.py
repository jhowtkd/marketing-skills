"""
VM Studio v17 - Safety Tuning Metrics

Métricas Prometheus para auto-tuning:
- Cycles completed
- Proposals generated
- Adjustments applied/blocked
- Rollbacks triggered
- FP rate deltas
- Incidents deltas
"""

import re
import threading
from datetime import datetime, timezone
from typing import Any, Optional


class SafetyTuningMetricsCollector:
    """
    Coletor de métricas para safety auto-tuning.
    
    Métricas:
    - cycles_completed: Número de ciclos de tuning completados
    - proposals_generated: Total de propostas geradas
    - adjustments_applied: Ajustes aplicados com sucesso
    - adjustments_blocked: Ajustes bloqueados por segurança
    - rollbacks_triggered: Rollbacks acionados
    - frozen_gates: Gates atualmente congelados
    - fp_rate_deltas: Delta de FP rate por gate
    - incidents_deltas: Delta de incidentes por gate
    """
    
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cycles_completed = 0
        self._proposals_generated = 0
        self._adjustments_applied = 0
        self._adjustments_applied_by_risk: dict[str, int] = {}
        self._adjustments_blocked = 0
        self._rollbacks_triggered = 0
        self._frozen_gates: set[str] = set()
        self._fp_rate_deltas: dict[str, float] = {}
        self._incidents_deltas: dict[str, float] = {}
    
    def record_cycle_completed(
        self,
        cycle_id: str,
        proposals_count: int,
        adjustments_count: int
    ) -> None:
        """Registra ciclo de tuning completado."""
        with self._lock:
            self._cycles_completed += 1
            self._proposals_generated += proposals_count
    
    def record_adjustment_applied(
        self,
        gate_name: str,
        adjustment_percent: float,
        risk_level: str
    ) -> None:
        """Registra ajuste aplicado."""
        with self._lock:
            self._adjustments_applied += 1
            risk_key = f"adjustments_applied_{risk_level}_risk"
            self._adjustments_applied_by_risk[risk_key] = \
                self._adjustments_applied_by_risk.get(risk_key, 0) + 1
    
    def record_adjustment_blocked(
        self,
        gate_name: str,
        reason: str
    ) -> None:
        """Registra ajuste bloqueado."""
        with self._lock:
            self._adjustments_blocked += 1
    
    def record_rollback_triggered(
        self,
        gate_name: str,
        trigger: str
    ) -> None:
        """Registra rollback acionado."""
        with self._lock:
            self._rollbacks_triggered += 1
    
    def record_gate_frozen(self, gate_name: str) -> None:
        """Registra gate congelado."""
        with self._lock:
            self._frozen_gates.add(gate_name)
    
    def record_gate_unfrozen(self, gate_name: str) -> None:
        """Registra gate descongelado."""
        with self._lock:
            self._frozen_gates.discard(gate_name)
    
    def record_fp_rate_delta(
        self,
        gate_name: str,
        previous_rate: float,
        current_rate: float
    ) -> None:
        """Registra delta de FP rate."""
        with self._lock:
            self._fp_rate_deltas[gate_name] = current_rate - previous_rate
    
    def record_incidents_delta(
        self,
        gate_name: str,
        previous_rate: float,
        current_rate: float
    ) -> None:
        """Registra delta de incidentes."""
        with self._lock:
            self._incidents_deltas[gate_name] = current_rate - previous_rate
    
    def snapshot(self) -> dict[str, Any]:
        """Retorna snapshot das métricas."""
        with self._lock:
            return {
                "cycles_completed": self._cycles_completed,
                "proposals_generated": self._proposals_generated,
                "adjustments_applied": self._adjustments_applied,
                "adjustments_applied_by_risk": dict(self._adjustments_applied_by_risk),
                "adjustments_blocked": self._adjustments_blocked,
                "rollbacks_triggered": self._rollbacks_triggered,
                "frozen_gates": list(self._frozen_gates),
                "fp_rate_deltas": dict(self._fp_rate_deltas),
                "incidents_deltas": dict(self._incidents_deltas),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


def _normalize_metric_name(name: str) -> str:
    """Normaliza nome de métrica para Prometheus."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.replace(":", "_"))
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if not sanitized:
        return "metric"
    if sanitized[0].isdigit():
        sanitized = f"m_{sanitized}"
    return sanitized.lower()


def render_tuning_prometheus(snapshot: dict[str, Any], *, prefix: str = "vm") -> str:
    """
    Renderiza métricas de tuning no formato Prometheus.
    
    Args:
        snapshot: Snapshot do coletor de métricas
        prefix: Prefixo das métricas
        
    Returns:
        String no formato Prometheus
    """
    lines: list[str] = []
    
    # Contadores principais
    counters = {
        "safety_tuning_cycles_completed": snapshot.get("cycles_completed", 0),
        "safety_tuning_proposals_generated": snapshot.get("proposals_generated", 0),
        "safety_tuning_adjustments_applied": snapshot.get("adjustments_applied", 0),
        "safety_tuning_adjustments_blocked": snapshot.get("adjustments_blocked", 0),
        "safety_tuning_rollbacks_triggered": snapshot.get("rollbacks_triggered", 0),
    }
    
    for name, value in counters.items():
        metric_name = f"{prefix}_{name}"
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(f"{metric_name} {int(value)}")
    
    # Ajustes por nível de risco
    by_risk = snapshot.get("adjustments_applied_by_risk", {})
    for risk_key, value in by_risk.items():
        metric_name = f"{prefix}_{_normalize_metric_name(risk_key)}"
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(f"{metric_name} {int(value)}")
    
    # Gates congelados (gauge)
    frozen_gates = snapshot.get("frozen_gates", [])
    if frozen_gates:
        metric_name = f"{prefix}_safety_tuning_frozen_gates"
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {len(frozen_gates)}")
        
        # Labels para cada gate congelado
        for gate in frozen_gates:
            lines.append(f'{metric_name}{{gate="{gate}"}} 1')
    
    # Deltas de FP rate (gauge)
    fp_deltas = snapshot.get("fp_rate_deltas", {})
    if fp_deltas:
        metric_name = f"{prefix}_safety_tuning_fp_rate_delta"
        lines.append(f"# TYPE {metric_name} gauge")
        for gate, delta in fp_deltas.items():
            lines.append(f'{metric_name}{{gate="{gate}"}} {delta:.6f}')
    
    # Deltas de incidentes (gauge)
    incidents_deltas = snapshot.get("incidents_deltas", {})
    if incidents_deltas:
        metric_name = f"{prefix}_safety_tuning_incidents_delta"
        lines.append(f"# TYPE {metric_name} gauge")
        for gate, delta in incidents_deltas.items():
            lines.append(f'{metric_name}{{gate="{gate}"}} {delta:.6f}')
    
    if not lines:
        lines.append("# no metrics recorded")
    
    return "\n".join(lines) + "\n"


# Instância global (em produção, usar injeção de dependência)
_metrics_collector: Optional[SafetyTuningMetricsCollector] = None


def get_metrics_collector() -> SafetyTuningMetricsCollector:
    """Retorna instância do coletor de métricas."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = SafetyTuningMetricsCollector()
    return _metrics_collector
