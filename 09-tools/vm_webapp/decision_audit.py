"""
Task B: Decision Simulation + Audit Trail
Governança v16 - Auditabilidade completa de decisões automatizadas

Features:
- Dry-run simulation antes da execução real
- Persistência completa de auditoria
- Histórico paginado por segmento/brand
- Consistência e imutabilidade dos logs
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any, Callable
from enum import Enum
import uuid

from vm_webapp.safety_gates import (
    SafetyGateEngine, 
    SafetyGateResult, 
    RiskLevel, 
    GateType,
    evaluate_safety_gates
)

UTC = timezone.utc


@dataclass
class DecisionAuditLog:
    """
    Log completo de auditoria de uma decisão.
    
    Captura:
    - Input metrics snapshot
    - Decisão sugerida pelo sistema
    - Gates aplicados e seus resultados
    - Decisão final (pode diferir se override)
    - Actor (auto|manual)
    - Timestamp de execução
    """
    audit_id: str
    segment_key: str
    brand_id: str
    input_metrics: dict[str, Any]
    suggested_decision: str
    gates_applied: list[str]
    gate_results: list[dict[str, Any]]
    final_decision: str
    actor: str  # "auto" | "manual"
    executed_at: str
    # Optional fields
    override_reason: Optional[str] = None
    executed_by: Optional[str] = None  # User ID if manual
    rollback_triggered: bool = False
    rollback_reason: Optional[str] = None


@dataclass
class SimulationResult:
    """
    Resultado de uma simulação dry-run.
    
    Permite preview da decisão antes da execução real,
    incluindo quais gates bloqueariam e por quê.
    """
    dry_run: bool
    would_execute: bool
    safety_result: SafetyGateResult
    predicted_decision: str
    confidence: float
    warnings: list[str]
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)
    # Preview de override
    manual_override_preview: bool = False
    override_reason: Optional[str] = None


@dataclass
class AuditQuery:
    """Query parameters for audit log retrieval."""
    segment_key: Optional[str] = None
    brand_id: Optional[str] = None
    actor: Optional[str] = None
    final_decision: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class AuditPagination:
    """Pagination parameters for audit queries."""
    page: int = 1
    page_size: int = 20
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size."""
        return (self.page - 1) * self.page_size


class DecisionSimulator:
    """
    Simulador de decisões - dry-run antes da execução real.
    
    Permite:
    - Preview da decisão sem executar
    - Identificação de gates que bloqueariam
    - Validação de métricas antes da ação
    - Preview de override manual
    """
    
    def __init__(self, gate_engine: SafetyGateEngine = None):
        self.gate_engine = gate_engine or SafetyGateEngine()
    
    def simulate(self, context: dict[str, Any]) -> SimulationResult:
        """
        Executa simulação dry-run da decisão.
        
        Args:
            context: Contexto completo com métricas e configurações
            
        Returns:
            SimulationResult com preview da execução
        """
        # Captura snapshot completo das métricas
        metrics_snapshot = self._capture_snapshot(context)
        
        # Avalia safety gates
        safety_result = self.gate_engine.evaluate(context)
        
        # Determina decisão prevista
        predicted_decision = self._predict_decision(context, safety_result)
        
        # Verifica se executaria
        would_execute = safety_result.allowed
        
        # Gera warnings
        warnings = self._generate_warnings(context, safety_result)
        
        # Verifica preview de override
        manual_override = context.get("manual_override", False)
        override_reason = context.get("override_reason") if manual_override else None
        
        return SimulationResult(
            dry_run=True,
            would_execute=would_execute,
            safety_result=safety_result,
            predicted_decision=predicted_decision,
            confidence=context.get("confidence_score", 0.0),
            warnings=warnings,
            metrics_snapshot=metrics_snapshot,
            manual_override_preview=manual_override,
            override_reason=override_reason
        )
    
    def _capture_snapshot(self, context: dict[str, Any]) -> dict[str, Any]:
        """Captura snapshot completo das métricas."""
        snapshot = {
            "captured_at": datetime.now(UTC).isoformat(),
            "segment_key": context.get("segment_key"),
            "brand_id": context.get("brand_id"),
            "sample_size": context.get("sample_size"),
            "confidence_score": context.get("confidence_score"),
            "decision_type": context.get("decision_type"),
        }
        
        # Inclui KPI summary se disponível
        if "kpi_summary" in context:
            snapshot["kpi_summary"] = context["kpi_summary"]
        
        # Inclui alertas ativos
        if "active_alerts" in context:
            snapshot["active_alerts"] = context["active_alerts"]
        
        # Inclui regressões detectadas
        if "short_window_regression" in context:
            snapshot["short_window_regression"] = context["short_window_regression"]
        if "long_window_regression" in context:
            snapshot["long_window_regression"] = context["long_window_regression"]
        
        # Inclui contadores
        if "actions_today" in context:
            snapshot["actions_today"] = context["actions_today"]
        
        return snapshot
    
    def _predict_decision(
        self,
        context: dict[str, Any],
        safety_result: SafetyGateResult
    ) -> str:
        """Prediz qual decisão seria tomada."""
        requested = context.get("decision_type", "expand")
        
        if safety_result.allowed:
            return requested
        
        # Se bloqueado, sugere hold ou rollback baseado no risco
        if safety_result.risk_level == RiskLevel.CRITICAL:
            return "rollback"
        
        return "hold"
    
    def _generate_warnings(
        self,
        context: dict[str, Any],
        safety_result: SafetyGateResult
    ) -> list[str]:
        """Gera warnings baseado na avaliação."""
        warnings = []
        
        if not safety_result.allowed:
            for reason in safety_result.blocked_by:
                warning_map = {
                    "insufficient_sample_size": "Sample size below threshold",
                    "confidence_below_threshold": "Confidence score too low",
                    "short_window_regression": "Short-term regression detected",
                    "long_window_regression": "Long-term regression detected",
                    "critical_alert_active": "Critical alert active",
                    "cooldown_active": "Cooldown period active",
                    "max_actions_per_day_reached": "Daily action limit reached",
                }
                warnings.append(warning_map.get(reason, f"Blocked: {reason}"))
        
        # Warning se confidence está baixo mas passou
        confidence = context.get("confidence_score", 1.0)
        if confidence < 0.85 and safety_result.allowed:
            warnings.append("Confidence below recommended threshold")
        
        return warnings


class DecisionAuditStore:
    """
    Store para persistência de logs de auditoria.
    
    Fornece:
    - Storage e retrieval por ID
    - Query por segmento, brand, data
    - Paginação
    - Filtragem múltipla
    
    Nota: Implementação em memória. Para produção,
    substituir por storage persistente (DB).
    """
    
    def __init__(self):
        # In-memory storage: audit_id -> DecisionAuditLog
        self._logs: dict[str, DecisionAuditLog] = {}
        # Índices para queries eficientes
        self._by_segment: dict[str, list[str]] = {}
        self._by_brand: dict[str, list[str]] = {}
    
    def store(self, log: DecisionAuditLog) -> str:
        """
        Armazena um log de auditoria.
        
        Args:
            log: DecisionAuditLog a ser armazenado
            
        Returns:
            audit_id do log armazenado
        """
        # Atualiza índices
        if log.segment_key not in self._by_segment:
            self._by_segment[log.segment_key] = []
        if log.audit_id not in self._by_segment[log.segment_key]:
            self._by_segment[log.segment_key].append(log.audit_id)
        
        if log.brand_id not in self._by_brand:
            self._by_brand[log.brand_id] = []
        if log.audit_id not in self._by_brand[log.brand_id]:
            self._by_brand[log.brand_id].append(log.audit_id)
        
        # Armazena log
        self._logs[log.audit_id] = log
        
        return log.audit_id
    
    def get(self, audit_id: str) -> Optional[DecisionAuditLog]:
        """Recupera log por ID."""
        return self._logs.get(audit_id)
    
    def query_by_segment(self, segment_key: str) -> list[DecisionAuditLog]:
        """Query todos os logs de um segmento."""
        audit_ids = self._by_segment.get(segment_key, [])
        return [self._logs[aid] for aid in audit_ids if aid in self._logs]
    
    def query_by_brand(self, brand_id: str) -> list[DecisionAuditLog]:
        """Query todos os logs de um brand."""
        audit_ids = self._by_brand.get(brand_id, [])
        return [self._logs[aid] for aid in audit_ids if aid in self._logs]
    
    def query_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> list[DecisionAuditLog]:
        """Query logs em um range de datas."""
        results = []
        for log in self._logs.values():
            if start_date <= log.executed_at <= end_date:
                results.append(log)
        return results
    
    def query_paginated(
        self,
        segment_key: Optional[str] = None,
        brand_id: Optional[str] = None,
        pagination: AuditPagination = None
    ) -> tuple[list[DecisionAuditLog], int]:
        """
        Query paginada de logs.
        
        Returns:
            Tuple de (logs da página, total de logs)
        """
        pagination = pagination or AuditPagination()
        
        # Filtra por segmento ou brand
        if segment_key:
            all_logs = self.query_by_segment(segment_key)
        elif brand_id:
            all_logs = self.query_by_brand(brand_id)
        else:
            all_logs = list(self._logs.values())
        
        # Ordena por data (mais recente primeiro)
        all_logs.sort(key=lambda x: x.executed_at, reverse=True)
        
        total = len(all_logs)
        
        # Aplica paginação
        offset = pagination.offset
        end = offset + pagination.page_size
        paginated_logs = all_logs[offset:end]
        
        return paginated_logs, total
    
    def query(self, query_params: AuditQuery) -> list[DecisionAuditLog]:
        """
        Query flexível com múltiplos filtros.
        
        Args:
            query_params: AuditQuery com filtros
            
        Returns:
            Lista de logs matching os filtros
        """
        results = list(self._logs.values())
        
        # Aplica filtros
        if query_params.segment_key:
            results = [r for r in results if r.segment_key == query_params.segment_key]
        
        if query_params.brand_id:
            results = [r for r in results if r.brand_id == query_params.brand_id]
        
        if query_params.actor:
            results = [r for r in results if r.actor == query_params.actor]
        
        if query_params.final_decision:
            results = [r for r in results if r.final_decision == query_params.final_decision]
        
        if query_params.start_date:
            results = [r for r in results if r.executed_at >= query_params.start_date]
        
        if query_params.end_date:
            results = [r for r in results if r.executed_at <= query_params.end_date]
        
        # Ordena por data (mais recente primeiro)
        results.sort(key=lambda x: x.executed_at, reverse=True)
        
        return results


# Global store instance (substituir por injeção de dependência em produção)
_default_store: Optional[DecisionAuditStore] = None


def get_default_store() -> DecisionAuditStore:
    """Retorna instância padrão do store."""
    global _default_store
    if _default_store is None:
        _default_store = DecisionAuditStore()
    return _default_store


def simulate_decision(context: dict[str, Any]) -> SimulationResult:
    """
    Função utilitária para simular decisão.
    
    Args:
        context: Contexto completo da decisão
        
    Returns:
        SimulationResult com preview
    """
    simulator = DecisionSimulator()
    return simulator.simulate(context)


def record_decision_execution(
    execution_data: dict[str, Any],
    store: DecisionAuditStore = None
) -> str:
    """
    Registra execução de decisão no audit trail.
    
    Args:
        execution_data: Dados da execução
        store: Store opcional (usa default se não fornecido)
        
    Returns:
        audit_id gerado
    """
    store = store or get_default_store()
    
    audit_id = f"audit_{uuid.uuid4().hex[:12]}"
    
    log = DecisionAuditLog(
        audit_id=audit_id,
        segment_key=execution_data["segment_key"],
        brand_id=execution_data["brand_id"],
        input_metrics=execution_data["input_metrics"],
        suggested_decision=execution_data["suggested_decision"],
        gates_applied=execution_data.get("gates_applied", []),
        gate_results=execution_data.get("gate_results", []),
        final_decision=execution_data["final_decision"],
        actor=execution_data.get("actor", "auto"),
        executed_at=datetime.now(UTC).isoformat(),
        override_reason=execution_data.get("override_reason"),
        executed_by=execution_data.get("executed_by"),
        rollback_triggered=execution_data.get("rollback_triggered", False),
        rollback_reason=execution_data.get("rollback_reason")
    )
    
    store.store(log)
    return audit_id


def get_decision_history(
    segment_key: str,
    store: DecisionAuditStore = None
) -> list[DecisionAuditLog]:
    """
    Recupera histórico de decisões de um segmento.
    
    Args:
        segment_key: Chave do segmento
        store: Store opcional
        
    Returns:
        Lista de logs ordenados por data (mais recente primeiro)
    """
    store = store or get_default_store()
    return store.query_by_segment(segment_key)


def get_audit_summary(
    brand_id: str,
    store: DecisionAuditStore = None
) -> dict[str, Any]:
    """
    Gera resumo de auditoria para um brand.
    
    Args:
        brand_id: ID do brand
        store: Store opcional
        
    Returns:
        Dicionário com estatísticas de decisões
    """
    store = store or get_default_store()
    logs = store.query_by_brand(brand_id)
    
    total = len(logs)
    auto_count = sum(1 for l in logs if l.actor == "auto")
    manual_count = sum(1 for l in logs if l.actor == "manual")
    
    expand_count = sum(1 for l in logs if l.final_decision == "expand")
    hold_count = sum(1 for l in logs if l.final_decision == "hold")
    rollback_count = sum(1 for l in logs if l.final_decision == "rollback")
    
    rollback_triggered_count = sum(1 for l in logs if l.rollback_triggered)
    
    return {
        "brand_id": brand_id,
        "total_decisions": total,
        "by_actor": {
            "auto": auto_count,
            "manual": manual_count
        },
        "by_decision": {
            "expand": expand_count,
            "hold": hold_count,
            "rollback": rollback_count
        },
        "rollbacks_triggered": rollback_triggered_count
    }
