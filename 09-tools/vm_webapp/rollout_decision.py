"""
Task C: Rollout Decision Assistant
Governança operacional v15 - Decisão assistida de expand/hold/rollback
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
UTC = timezone.utc
from enum import Enum
from typing import Optional


class RolloutDecision(str, Enum):
    """Decisões possíveis para rollout."""
    EXPAND = "expand"
    HOLD = "hold"
    ROLLBACK = "rollback"


class DecisionConfidence(str, Enum):
    """Níveis de confiança na decisão."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DecisionReason:
    """Razão para a decisão."""
    code: str
    description: str
    severity: str  # "info", "warning", "critical"


@dataclass
class RequiredAction:
    """Ação necessária baseada na decisão."""
    action_id: str
    description: str
    priority: str  # "low", "medium", "high", "critical"
    due_hours: int
    auto_applicable: bool = False


@dataclass
class DecisionResult:
    """Resultado completo da decisão."""
    segment_key: str
    decision: RolloutDecision
    confidence: DecisionConfidence
    reasons: list[DecisionReason]
    required_actions: list[RequiredAction]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    overridden: bool = False
    original_decision: Optional[RolloutDecision] = None
    override_reason: Optional[str] = None


class RolloutDecisionEngine:
    """
    Motor de decisão para rollout de segmentos.
    
    Regras:
    - EXPAND: Todos KPIs on_track, sem alertas, >= 7 dias de dados
    - HOLD: KPIs mistos, ou alertas ativos, ou < 7 dias
    - ROLLBACK: KPIs off_track ou alertas críticos
    """
    
    # Pesos para cálculo de confiança
    KPI_WEIGHTS = {
        "approval_without_regen_24h": 0.4,
        "v1_score_avg": 0.35,
        "regenerations_per_job": 0.25,
    }
    
    def recommend(
        self,
        segment_key: str,
        kpi_summary: dict,
        active_alerts: list[dict],
        days_in_current_phase: int
    ) -> dict:
        """
        Recomenda decisão de rollout baseado em dados do segmento.
        
        Args:
            segment_key: Identificador do segmento
            kpi_summary: Resumo de KPIs do segmento
            active_alerts: Lista de alertas ativos
            days_in_current_phase: Dias na fase atual
        
        Returns:
            Dict com decision, confidence, reasons, required_actions
        """
        reasons = []
        
        # Verifica alertas primeiro
        critical_alerts = [a for a in active_alerts if a.get("severity") == "critical"]
        warning_alerts = [a for a in active_alerts if a.get("severity") == "warning"]
        
        # Analisa KPIs (necessário para decisões e razões, mesmo com alertas críticos)
        kpi_statuses = []
        off_track_count = 0
        attention_count = 0
        for metric_name, data in kpi_summary.items():
            status = data.get("status", "unknown")
            kpi_statuses.append((metric_name, status))
            
            if status == "off_track":
                off_track_count += 1
                reasons.append(DecisionReason(
                    code=f"{metric_name}_off_track",
                    description=f"{metric_name} is off track",
                    severity="critical"
                ))
            elif status == "attention":
                attention_count += 1
                reasons.append(DecisionReason(
                    code=f"{metric_name}_attention",
                    description=f"{metric_name} requires attention",
                    severity="warning"
                ))
        
        # Se tem alertas críticos, prioriza ROLLBACK independente de dados
        if critical_alerts:
            for alert in critical_alerts:
                reasons.append(DecisionReason(
                    code=f"critical_alert_{alert.get('reason_code', 'unknown')}",
                    description=f"Critical alert: {alert.get('reason_code', 'unknown')}",
                    severity="critical"
                ))
            return self._build_result(
                segment_key=segment_key,
                decision=RolloutDecision.ROLLBACK,
                confidence=DecisionConfidence.HIGH,
                reasons=reasons,
                days_in_phase=days_in_current_phase
            )
        
        # Verifica se tem dados suficientes
        if days_in_current_phase < 7 or not kpi_summary:
            reasons.append(DecisionReason(
                code="insufficient_data",
                description=f"Insufficient data: only {days_in_current_phase} days in phase (minimum 7)",
                severity="warning"
            ))
            return self._build_result(
                segment_key=segment_key,
                decision=RolloutDecision.HOLD,
                confidence=DecisionConfidence.LOW,
                reasons=reasons,
                days_in_phase=days_in_current_phase
            )
        
        # Adiciona razões para alertas de warning (critical já tratado acima)
        for alert in warning_alerts:
            reasons.append(DecisionReason(
                code=f"warning_alert_{alert.get('reason_code', 'unknown')}",
                description=f"Warning alert: {alert.get('reason_code', 'unknown')}",
                severity="warning"
            ))
        
        # Determina decisão
        decision, confidence = self._determine_decision(
            kpi_statuses=kpi_statuses,
            critical_alerts=len(critical_alerts),
            warning_alerts=len(warning_alerts),
            days_in_phase=days_in_current_phase
        )
        
        # Adiciona razões positivas se apropriado
        if decision == RolloutDecision.EXPAND:
            reasons.append(DecisionReason(
                code="kpi_on_track",
                description="All KPIs are meeting targets",
                severity="info"
            ))
        
        return self._build_result(
            segment_key=segment_key,
            decision=decision,
            confidence=confidence,
            reasons=reasons,
            days_in_phase=days_in_current_phase
        )
    
    def _determine_decision(
        self,
        kpi_statuses: list[tuple[str, str]],
        critical_alerts: int,
        warning_alerts: int,
        days_in_phase: int
    ) -> tuple[RolloutDecision, DecisionConfidence]:
        """
        Determina decisão baseada em sinais.
        
        Returns:
            Tuple de (decision, confidence)
        """
        off_track_count = sum(1 for _, s in kpi_statuses if s == "off_track")
        attention_count = sum(1 for _, s in kpi_statuses if s == "attention")
        on_track_count = sum(1 for _, s in kpi_statuses if s == "on_track")
        total_kpis = len(kpi_statuses)
        
        # Regra: ROLLBACK se crítico
        if critical_alerts > 0 or off_track_count >= 2:
            return RolloutDecision.ROLLBACK, DecisionConfidence.HIGH
        
        if off_track_count == 1:
            return RolloutDecision.ROLLBACK, DecisionConfidence.MEDIUM
        
        # Regra: HOLD se atenção ou alertas
        if attention_count > 0 or warning_alerts > 0:
            confidence = DecisionConfidence.MEDIUM if (warning_alerts > 0 or attention_count > 0) else DecisionConfidence.LOW
            return RolloutDecision.HOLD, confidence
        
        # Regra: EXPAND se tudo verde e dados suficientes
        if on_track_count == total_kpis and days_in_phase >= 7:
            confidence = DecisionConfidence.HIGH if days_in_phase >= 14 else DecisionConfidence.MEDIUM
            return RolloutDecision.EXPAND, confidence
        
        # Default: HOLD
        return RolloutDecision.HOLD, DecisionConfidence.LOW
    
    def _build_result(
        self,
        segment_key: str,
        decision: RolloutDecision,
        confidence: DecisionConfidence,
        reasons: list[DecisionReason],
        days_in_phase: int
    ) -> dict:
        """Constrói resultado com ações necessárias."""
        
        required_actions = self._generate_actions(decision, confidence, segment_key, days_in_phase)
        
        return {
            "segment_key": segment_key,
            "decision": decision,
            "confidence": confidence,
            "reasons": reasons,
            "required_actions": required_actions,
            "generated_at": datetime.now(UTC)
        }
    
    def _generate_actions(
        self,
        decision: RolloutDecision,
        confidence: DecisionConfidence,
        segment_key: str,
        days_in_phase: int
    ) -> list[RequiredAction]:
        """Gera ações necessárias baseado na decisão."""
        
        actions = []
        import uuid
        
        if decision == RolloutDecision.EXPAND:
            actions.append(RequiredAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                description="Increase rollout coverage to 50% of eligible segments",
                priority="medium",
                due_hours=48,
                auto_applicable=confidence == DecisionConfidence.HIGH
            ))
            actions.append(RequiredAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                description="Monitor KPIs daily for next 7 days",
                priority="medium",
                due_hours=24,
                auto_applicable=False
            ))
        
        elif decision == RolloutDecision.HOLD:
            actions.append(RequiredAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                description="Continue monitoring current rollout scope",
                priority="medium",
                due_hours=24,
                auto_applicable=False
            ))
            actions.append(RequiredAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                description="Investigate attention items before next decision",
                priority="high" if confidence == DecisionConfidence.LOW else "medium",
                due_hours=72,
                auto_applicable=False
            ))
        
        elif decision == RolloutDecision.ROLLBACK:
            actions.append(RequiredAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                description="Initiate immediate rollback to v13 baseline",
                priority="critical",
                due_hours=4,
                auto_applicable=False
            ))
            actions.append(RequiredAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                description="Notify engineering team and document incident",
                priority="critical",
                due_hours=2,
                auto_applicable=False
            ))
            actions.append(RequiredAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                description="Preserve segment data for root cause analysis",
                priority="high",
                due_hours=8,
                auto_applicable=True
            ))
        
        return actions


def _fetch_kpi_summary(segment_key: str) -> dict:
    """Busca resumo de KPIs do segmento (stub)."""
    return {}


def _fetch_active_alerts(segment_key: str) -> list[dict]:
    """Busca alertas ativos do segmento (stub)."""
    return []


def _fetch_segment_phase_info(segment_key: str) -> dict:
    """Busca informações da fase atual do segmento (stub)."""
    return {"days_in_phase": 0, "current_phase": "unknown"}


def get_rollout_decision(segment_key: str) -> dict:
    """
    API pública para obter decisão de rollout.
    
    Args:
        segment_key: Identificador do segmento
    
    Returns:
        Dict com decision, confidence, reasons, required_actions
    """
    engine = RolloutDecisionEngine()
    
    kpi_summary = _fetch_kpi_summary(segment_key)
    active_alerts = _fetch_active_alerts(segment_key)
    phase_info = _fetch_segment_phase_info(segment_key)
    
    result = engine.recommend(
        segment_key=segment_key,
        kpi_summary=kpi_summary,
        active_alerts=active_alerts,
        days_in_current_phase=phase_info.get("days_in_phase", 0)
    )
    
    return result


def _store_decision_override(override_data: dict):
    """Armazena override de decisão (stub)."""
    pass


def _fetch_original_decision(segment_key: str) -> Optional[dict]:
    """Busca decisão original (stub)."""
    return None


def override_decision(
    segment_key: str,
    new_decision: RolloutDecision,
    reason: str,
    overridden_by: str
) -> dict:
    """
    Permite override manual da decisão do sistema.
    
    Args:
        segment_key: Identificador do segmento
        new_decision: Nova decisão (expand/hold/rollback)
        reason: Razão do override
        overridden_by: Quem está fazendo o override
    
    Returns:
        Dict com status do override
    """
    original = _fetch_original_decision(segment_key)
    original_decision = original.get("decision") if original else None
    
    override_data = {
        "segment_key": segment_key,
        "original_decision": original_decision,
        "new_decision": new_decision,
        "reason": reason,
        "overridden_by": overridden_by,
        "overridden_at": datetime.now(UTC),
        "requires_notification": new_decision == RolloutDecision.ROLLBACK
    }
    
    _store_decision_override(override_data)
    
    return {
        "overridden": True,
        "segment_key": segment_key,
        "original_decision": original_decision,
        "new_decision": new_decision,
        "override_reason": reason,
        "requires_notification": new_decision == RolloutDecision.ROLLBACK,
        "overridden_by": overridden_by,
        "overridden_at": datetime.now(UTC).isoformat()
    }
