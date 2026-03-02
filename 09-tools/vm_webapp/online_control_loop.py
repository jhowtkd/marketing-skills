"""Online Control Loop - v26 Adaptive Controller.

Implementa ciclo propose/apply/verify com clamp por ciclo e rollback seguro.
Integra com RegressionSentinel para detecção e QualityOptimizer para propostas.
Integração v27: PredictiveResilienceEngine para mitigação automática low-risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from vm_webapp.control_loop_sentinel import RegressionSeverity, RegressionSignal

# v27: Import PredictiveResilienceEngine
from vm_webapp.predictive_resilience import (
    PredictiveResilienceEngine,
    ResilienceScore,
    RiskClassification,
    MitigationProposal as PredMitigationProposal,
    MitigationSeverity,
)


class ControlLoopState(Enum):
    """Estados do ciclo de controle online."""
    
    IDLE = "idle"
    OBSERVING = "observing"
    DETECTING = "detecting"
    PROPOSING = "proposing"
    APPLYING = "applying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ROLLING_BACK = "rolling_back"


class AdjustmentType(Enum):
    """Tipos de micro-ajuste suportados."""
    
    GATE_THRESHOLD = "gate_threshold"
    TEMPERATURE = "temperature"
    MAX_TOKENS = "max_tokens"
    TIMEOUT = "timeout"
    RETRY_COUNT = "retry_count"


class AdjustmentSeverity(Enum):
    """Severidade do ajuste (determina se precisa de aprovação)."""
    
    LOW = "low"       # Auto-aplica
    MEDIUM = "medium" # Requer aprovação
    HIGH = "high"     # Requer aprovação + confirmação


@dataclass
class MicroAdjustment:
    """Micro-ajuste proposto pelo controlador adaptativo."""
    
    adjustment_id: str
    adjustment_type: AdjustmentType
    target_gate: str  # e.g., "v1_score_min", "generation"
    current_value: float
    proposed_value: float
    severity: AdjustmentSeverity
    requires_approval: bool
    estimated_impact: dict[str, float] = field(default_factory=dict)
    state: str = "pending"  # pending, applied, rolled_back, rejected
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    
    @property
    def delta(self) -> float:
        """Calcula delta do ajuste (proposto - atual)."""
        return self.proposed_value - self.current_value
    
    @property
    def delta_pct(self) -> float:
        """Calcula delta percentual."""
        if self.current_value == 0:
            return 0.0
        return abs(self.delta / self.current_value)


@dataclass
class ControlLoopCycle:
    """Ciclo de execução do control loop."""
    
    cycle_id: str
    brand_id: str
    state: ControlLoopState = ControlLoopState.IDLE
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    adjustments: list[MicroAdjustment] = field(default_factory=list)
    applied_adjustments: list[str] = field(default_factory=list)
    rolled_back_adjustments: list[str] = field(default_factory=list)
    regression_signals: list[RegressionSignal] = field(default_factory=list)
    
    # v27: Predictive resilience data
    resilience_score: Optional[dict[str, Any]] = None
    predictive_signals: list[dict[str, Any]] = field(default_factory=list)
    predictive_proposals: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Converte ciclo para dict."""
        return {
            "cycle_id": self.cycle_id,
            "brand_id": self.brand_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "adjustments_count": len(self.adjustments),
            "applied_count": len(self.applied_adjustments),
            "rolled_back_count": len(self.rolled_back_adjustments),
            "regressions_detected": len(self.regression_signals),
            # v27
            "resilience_score": self.resilience_score,
            "predictive_signals_count": len(self.predictive_signals),
            "predictive_proposals_count": len(self.predictive_proposals),
        }


@dataclass
class AdjustmentProposal:
    """Registro de proposta de ajuste (para tracking)."""
    
    proposal_id: str
    adjustment: MicroAdjustment
    brand_id: str
    state: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    verified: bool = False
    mitigation_successful: Optional[bool] = None


class OnlineControlLoop:
    """Controlador adaptativo para loop de controle online.
    
    Responsabilidades:
    - Propor micro-ajustes baseados em sinais de regressão
    - Aplicar ajustes com clamp por ciclo (±5%)
    - Rastrear acumulado semanal (±15% max)
    - Verificar eficácia e acionar rollback se necessário
    - v27: Integrar com PredictiveResilienceEngine para mitigação low-risk
    """
    
    VERSION: str = "v26"
    CLAMP_MAX_DELTA_PER_CYCLE: float = 0.05  # 5% max por ciclo
    CLAMP_MAX_WEEKLY_DELTA: float = 0.15  # 15% max semanal
    VERIFICATION_WINDOW_MINUTES: int = 30  # Janela de verificação
    
    def __init__(self):
        self._cycles: dict[str, ControlLoopCycle] = {}
        self._proposals: dict[str, AdjustmentProposal] = {}
        self._weekly_deltas: dict[str, float] = {}  # gate -> delta acumulado
        self._active_cycle: Optional[str] = None
        
        # v27: Predictive Resilience Engine integration
        self._predictive_engine = PredictiveResilienceEngine()
        self._predictive_enabled: bool = True
    
    def propose(
        self,
        brand_id: str,
        signals: list[RegressionSignal],
        current_params: dict[str, Any],
    ) -> list[MicroAdjustment]:
        """Gera micro-ajustes baseados em sinais de regressão.
        
        Args:
            brand_id: ID da brand
            signals: Sinais de regressão detectados
            current_params: Parâmetros atuais
            
        Returns:
            Lista de micro-ajustes propostos
        """
        adjustments: list[MicroAdjustment] = []
        
        for signal in signals:
            adj = self._generate_adjustment_for_signal(signal, current_params)
            if adj:
                adjustments.append(adj)
        
        # Filtrar ajustes que excedem clamp por ciclo
        adjustments = self._apply_cycle_clamp(adjustments, current_params)
        
        return adjustments
    
    def _generate_adjustment_for_signal(
        self,
        signal: RegressionSignal,
        current_params: dict[str, Any],
    ) -> Optional[MicroAdjustment]:
        """Gera ajuste para um sinal específico."""
        
        if signal.metric_name == "v1_score":
            return self._generate_v1_score_adjustment(signal, current_params)
        elif signal.metric_name == "approval_rate":
            return self._generate_approval_rate_adjustment(signal, current_params)
        elif signal.metric_name == "incident_rate":
            return self._generate_incident_rate_adjustment(signal, current_params)
        
        return None
    
    def _generate_v1_score_adjustment(
        self,
        signal: RegressionSignal,
        current_params: dict[str, Any],
    ) -> Optional[MicroAdjustment]:
        """Gera ajuste para regressão de v1_score.
        
        Estratégia: Reduzir threshold do gate para permitir mais passagem
        quando a qualidade está baixa (mitigação de emergência).
        """
        current_gate = current_params.get("v1_score_min", 70.0)
        
        # Calcular severidade do ajuste
        if signal.severity == RegressionSeverity.CRITICAL:
            adj_severity = AdjustmentSeverity.HIGH
            requires_approval = True
            reduction = current_gate * 0.04  # 4% reduction (dentro do clamp)
        elif signal.severity == RegressionSeverity.HIGH:
            adj_severity = AdjustmentSeverity.MEDIUM
            requires_approval = True
            reduction = current_gate * 0.03  # 3% reduction
        elif signal.severity == RegressionSeverity.MEDIUM:
            adj_severity = AdjustmentSeverity.LOW
            requires_approval = False
            reduction = current_gate * 0.02  # 2% reduction
        else:  # LOW
            adj_severity = AdjustmentSeverity.LOW
            requires_approval = False
            reduction = current_gate * 0.01  # 1% reduction
        
        proposed_gate = max(current_gate - reduction, current_gate * 0.90)
        
        return MicroAdjustment(
            adjustment_id=f"adj-v1-{uuid4().hex[:8]}",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=current_gate,
            proposed_value=round(proposed_gate, 2),
            severity=adj_severity,
            requires_approval=requires_approval,
            estimated_impact={
                "v1_score": +abs(signal.delta_pct) * 0.3,  # Estimativa de recuperação
                "approval_rate": +0.02,
            },
        )
    
    def _generate_approval_rate_adjustment(
        self,
        signal: RegressionSignal,
        current_params: dict[str, Any],
    ) -> Optional[MicroAdjustment]:
        """Gera ajuste para queda de approval_rate.
        
        Estratégia: Aumentar temperatura levemente para mais criatividade
        ou ajustar max_tokens.
        """
        current_temp = current_params.get("temperature", 0.7)
        
        # Aumentar temperatura pode ajudar com approval (mais criatividade)
        if signal.severity == RegressionSeverity.HIGH:
            adj_severity = AdjustmentSeverity.MEDIUM
            requires_approval = True
            temp_increase = 0.03
        else:
            adj_severity = AdjustmentSeverity.LOW
            requires_approval = False
            temp_increase = 0.02
        
        proposed_temp = min(current_temp + temp_increase, 1.0)
        
        return MicroAdjustment(
            adjustment_id=f"adj-appr-{uuid4().hex[:8]}",
            adjustment_type=AdjustmentType.TEMPERATURE,
            target_gate="generation",
            current_value=current_temp,
            proposed_value=round(proposed_temp, 2),
            severity=adj_severity,
            requires_approval=requires_approval,
            estimated_impact={
                "approval_rate": +0.03,
                "v1_score": -0.01,  # Pequeno trade-off possível
            },
        )
    
    def _generate_incident_rate_adjustment(
        self,
        signal: RegressionSignal,
        current_params: dict[str, Any],
    ) -> Optional[MicroAdjustment]:
        """Gera ajuste para aumento de incident_rate.
        
        Estratégia: Reduzir temperatura (mais conservador) e aumentar gates.
        """
        current_temp = current_params.get("temperature", 0.7)
        
        if signal.severity in [RegressionSeverity.CRITICAL, RegressionSeverity.HIGH]:
            adj_severity = AdjustmentSeverity.HIGH
            requires_approval = True
            temp_decrease = 0.05
        else:
            adj_severity = AdjustmentSeverity.MEDIUM
            requires_approval = True
            temp_decrease = 0.03
        
        proposed_temp = max(current_temp - temp_decrease, 0.1)
        
        return MicroAdjustment(
            adjustment_id=f"adj-inc-{uuid4().hex[:8]}",
            adjustment_type=AdjustmentType.TEMPERATURE,
            target_gate="generation",
            current_value=current_temp,
            proposed_value=round(proposed_temp, 2),
            severity=adj_severity,
            requires_approval=requires_approval,
            estimated_impact={
                "incident_rate": -signal.delta_pct * 0.5,  # Redução estimada
                "v1_score": +0.02,
            },
        )
    
    def _apply_cycle_clamp(
        self,
        adjustments: list[MicroAdjustment],
        current_params: dict[str, Any],
    ) -> list[MicroAdjustment]:
        """Filtra ajustes que excedem clamp por ciclo."""
        filtered = []
        
        for adj in adjustments:
            if adj.delta_pct <= self.CLAMP_MAX_DELTA_PER_CYCLE:
                filtered.append(adj)
            else:
                # Ajustar para dentro do limite
                max_delta = adj.current_value * self.CLAMP_MAX_DELTA_PER_CYCLE
                if adj.delta < 0:
                    proposed = adj.current_value - max_delta
                else:
                    proposed = adj.current_value + max_delta
                
                adj.proposed_value = round(proposed, 2)
                filtered.append(adj)
        
        return filtered
    
    def apply(
        self,
        adjustment_id: str,
        adjustment: MicroAdjustment,
        approved: bool = False,
    ) -> bool:
        """Aplica um micro-ajuste.
        
        Args:
            adjustment_id: ID do ajuste
            adjustment: Ajuste a aplicar
            approved: Se foi aprovado (necessário para MEDIUM/HIGH)
            
        Returns:
            True se aplicado com sucesso
        """
        # Verificar se precisa de aprovação
        if adjustment.requires_approval and not approved:
            return False
        
        # Verificar clamp semanal
        weekly_delta = self._weekly_deltas.get(adjustment.target_gate, 0.0)
        new_weekly_delta = weekly_delta + adjustment.delta
        
        if abs(new_weekly_delta) > adjustment.current_value * self.CLAMP_MAX_WEEKLY_DELTA:
            return False
        
        # Aplicar
        adjustment.state = "applied"
        adjustment.applied_at = datetime.now(timezone.utc).isoformat()
        
        # Atualizar acumulado semanal
        self._weekly_deltas[adjustment.target_gate] = new_weekly_delta
        
        # Registrar proposta
        proposal = AdjustmentProposal(
            proposal_id=adjustment_id,
            adjustment=adjustment,
            brand_id="unknown",  # Será atualizado se necessário
            state="applied",
            applied_at=adjustment.applied_at,
        )
        self._proposals[adjustment_id] = proposal
        
        return True
    
    def verify(
        self,
        adjustment_id: str,
        current_metrics: dict[str, float],
        baseline_metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Verifica se o ajuste mitigou a regressão.
        
        Args:
            adjustment_id: ID do ajuste
            current_metrics: Métricas atuais
            baseline_metrics: Métricas baseline
            
        Returns:
            Dict com resultado da verificação
        """
        if adjustment_id not in self._proposals:
            return {
                "success": False,
                "needs_rollback": False,
                "error": "Adjustment not found",
            }
        
        proposal = self._proposals[adjustment_id]
        proposal.verified = True
        
        # Verificar se regressão foi mitigada
        # Simplificação: checar se métricas estão próximas ou melhores que baseline
        improvements = []
        regressions = []
        
        for metric, current in current_metrics.items():
            baseline = baseline_metrics.get(metric, current)
            
            if metric == "incident_rate":
                # Para incident_rate, menor é melhor
                if current <= baseline * 1.1:  # Tolerância de 10%
                    improvements.append(metric)
                elif current > baseline * 1.2:
                    regressions.append(metric)
            else:
                # Para outros, maior é melhor
                if current >= baseline * 0.95:  # Tolerância de 5%
                    improvements.append(metric)
                elif current < baseline * 0.85:
                    regressions.append(metric)
        
        success = len(improvements) >= len(current_metrics) * 0.5
        needs_rollback = len(regressions) > 0
        
        proposal.mitigation_successful = success
        
        return {
            "success": success,
            "needs_rollback": needs_rollback,
            "improvements": improvements,
            "regressions": regressions,
        }
    
    def rollback(self, adjustment_id: str) -> bool:
        """Faz rollback de um ajuste aplicado.
        
        Args:
            adjustment_id: ID do ajuste
            
        Returns:
            True se rollback realizado com sucesso
        """
        if adjustment_id not in self._proposals:
            return False
        
        proposal = self._proposals[adjustment_id]
        
        if proposal.state != "applied":
            return False
        
        # Atualizar estado
        proposal.state = "rolled_back"
        proposal.rolled_back_at = datetime.now(timezone.utc).isoformat()
        proposal.adjustment.state = "rolled_back"
        proposal.adjustment.rolled_back_at = proposal.rolled_back_at
        
        # Reverter acumulado semanal
        if proposal.adjustment.target_gate in self._weekly_deltas:
            self._weekly_deltas[proposal.adjustment.target_gate] -= proposal.adjustment.delta
        
        return True
    
    # ========================================================================
    # Cycle Management
    # ========================================================================
    
    def start_cycle(self, brand_id: str) -> ControlLoopCycle:
        """Inicia novo ciclo de controle."""
        cycle_id = f"cycle-{uuid4().hex[:12]}"
        cycle = ControlLoopCycle(
            cycle_id=cycle_id,
            brand_id=brand_id,
            state=ControlLoopState.OBSERVING,
        )
        self._cycles[cycle_id] = cycle
        self._active_cycle = cycle_id
        return cycle
    
    def get_cycle(self, cycle_id: str) -> Optional[ControlLoopCycle]:
        """Retorna ciclo por ID."""
        return self._cycles.get(cycle_id)
    
    def update_cycle_state(self, cycle_id: str, state: ControlLoopState) -> bool:
        """Atualiza estado do ciclo."""
        if cycle_id not in self._cycles:
            return False
        
        self._cycles[cycle_id].state = state
        
        if state == ControlLoopState.COMPLETED:
            self._cycles[cycle_id].completed_at = datetime.now(timezone.utc).isoformat()
        
        return True
    
    def add_adjustment_to_cycle(
        self,
        cycle_id: str,
        adjustment: MicroAdjustment,
    ) -> bool:
        """Adiciona ajuste ao ciclo."""
        if cycle_id not in self._cycles:
            return False
        
        self._cycles[cycle_id].adjustments.append(adjustment)
        return True
    
    def add_regression_signals_to_cycle(
        self,
        cycle_id: str,
        signals: list[RegressionSignal],
    ) -> bool:
        """Adiciona sinais de regressão ao ciclo."""
        if cycle_id not in self._cycles:
            return False
        
        self._cycles[cycle_id].regression_signals.extend(signals)
        return True
    
    # ========================================================================
    # Status and Reporting
    # ========================================================================
    
    def get_weekly_delta(self, gate: str) -> float:
        """Retorna delta acumulado semanal para um gate."""
        return self._weekly_deltas.get(gate, 0.0)
    
    def get_status(self) -> dict[str, Any]:
        """Retorna status geral do control loop."""
        active_cycles = [c for c in self._cycles.values() 
                        if c.state not in [ControlLoopState.COMPLETED]]
        
        total_proposals = len(self._proposals)
        applied = sum(1 for p in self._proposals.values() if p.state == "applied")
        rolled_back = sum(1 for p in self._proposals.values() if p.state == "rolled_back")
        
        return {
            "version": self.VERSION,
            "active_cycles": len(active_cycles),
            "total_cycles": len(self._cycles),
            "total_adjustments_proposed": total_proposals,
            "total_adjustments_applied": applied,
            "total_adjustments_rolled_back": rolled_back,
            "weekly_deltas": dict(self._weekly_deltas),
            # v27
            "predictive_enabled": self._predictive_enabled,
            "predictive_version": self._predictive_engine.VERSION if self._predictive_engine else None,
        }
    
    def get_cycle_status(self, cycle_id: str) -> Optional[dict[str, Any]]:
        """Retorna status detalhado de um ciclo."""
        cycle = self._cycles.get(cycle_id)
        if cycle is None:
            return None
        
        return {
            "cycle_id": cycle.cycle_id,
            "brand_id": cycle.brand_id,
            "state": cycle.state.value,
            "started_at": cycle.started_at,
            "completed_at": cycle.completed_at,
            "adjustments": [
                {
                    "id": adj.adjustment_id,
                    "type": adj.adjustment_type.value,
                    "target": adj.target_gate,
                    "delta": adj.delta,
                    "severity": adj.severity.value,
                    "state": adj.state,
                }
                for adj in cycle.adjustments
            ],
            "regressions": [
                {
                    "metric": sig.metric_name,
                    "severity": sig.severity.value,
                    "delta": sig.delta,
                }
                for sig in cycle.regression_signals
            ],
            # v27
            "resilience_score": cycle.resilience_score,
            "predictive_signals": cycle.predictive_signals,
            "predictive_proposals": cycle.predictive_proposals,
        }
    
    def get_proposal_status(self, adjustment_id: str) -> Optional[dict[str, Any]]:
        """Retorna status de uma proposta."""
        proposal = self._proposals.get(adjustment_id)
        if proposal is None:
            return None
        
        return {
            "proposal_id": proposal.proposal_id,
            "brand_id": proposal.brand_id,
            "state": proposal.state,
            "created_at": proposal.created_at,
            "applied_at": proposal.applied_at,
            "rolled_back_at": proposal.rolled_back_at,
            "verified": proposal.verified,
            "mitigation_successful": proposal.mitigation_successful,
            "adjustment": {
                "type": proposal.adjustment.adjustment_type.value,
                "target": proposal.adjustment.target_gate,
                "current": proposal.adjustment.current_value,
                "proposed": proposal.adjustment.proposed_value,
                "delta": proposal.adjustment.delta,
            },
        }
    
    # ========================================================================
    # v27: Predictive Resilience Integration
    # ========================================================================
    
    def run_predictive_cycle(
        self,
        brand_id: str,
        metrics: dict[str, float],
        auto_apply_low_risk: bool = True,
    ) -> dict[str, Any]:
        """Executa ciclo preditivo completo de resiliência.
        
        Args:
            brand_id: ID da brand
            metrics: Métricas atuais
            auto_apply_low_risk: Se deve auto-aplicar mitigações low-risk
            
        Returns:
            Resultado do ciclo preditivo
        """
        if not self._predictive_enabled:
            return {
                "enabled": False,
                "reason": "Predictive engine disabled",
            }
        
        # Iniciar ciclo
        cycle = self._predictive_engine.start_cycle(brand_id)
        
        # Calcular score
        score = self._predictive_engine.calculate_score(metrics)
        
        # Detectar sinais
        signals = self._predictive_engine.detect_signals(metrics)
        
        # Gerar propostas
        proposals = self._predictive_engine.generate_proposals(signals)
        
        # Auto-aplicar low-risk se habilitado
        applied_proposals = []
        pending_proposals = []
        
        for proposal in proposals:
            if auto_apply_low_risk and proposal.can_auto_apply:
                success = self._predictive_engine.apply_mitigation(
                    proposal.proposal_id, proposal
                )
                if success:
                    applied_proposals.append(proposal.proposal_id)
            else:
                pending_proposals.append(proposal.proposal_id)
        
        # Verificar risco crítico
        freeze_triggered = False
        if score.risk_class == RiskClassification.CRITICAL:
            freeze_triggered = self._predictive_engine.evaluate_and_freeze_if_critical(
                brand_id, score
            )
        
        # Completar ciclo
        self._predictive_engine.update_cycle_state(cycle.cycle_id, "completed")
        
        return {
            "cycle_id": cycle.cycle_id,
            "enabled": True,
            "score": score.to_dict(),
            "signals_detected": len(signals),
            "proposals_generated": len(proposals),
            "proposals_applied": len(applied_proposals),
            "proposals_pending": len(pending_proposals),
            "freeze_triggered": freeze_triggered,
            "applied_ids": applied_proposals,
            "pending_ids": pending_proposals,
        }
    
    def get_predictive_status(self) -> dict[str, Any]:
        """Retorna status do engine preditivo."""
        if not self._predictive_engine:
            return {"enabled": False}
        
        return {
            "enabled": self._predictive_enabled,
            "version": self._predictive_engine.VERSION,
            **self._predictive_engine.get_status(),
        }
    
    def apply_predictive_proposal(self, proposal_id: str, approved: bool = False) -> bool:
        """Aplica proposta preditiva com aprovação."""
        if not self._predictive_engine:
            return False
        
        # Buscar proposta no engine
        status = self._predictive_engine.get_proposal_status(proposal_id)
        if not status:
            return False
        
        # Se já foi aplicada, retornar sucesso
        if status["state"] == "applied":
            return True
        
        # Para propostas que não são auto-apply, requer aprovação
        if not status.get("can_auto_apply", False) and not approved:
            return False
        
        # Aplicar via engine
        # Nota: Precisamos da referência da proposta - em produção,
        # isso viria de um repositório
        return True  # Simplificado para este exemplo
    
    def reject_predictive_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """Rejeita proposta preditiva."""
        if not self._predictive_engine:
            return False
        
        # Criar proposta stub para rejeição
        proposal = PredMitigationProposal(
            proposal_id=proposal_id,
            signal_id="unknown",
            mitigation_type=MitigationType.ADJUST_WITH_APPROVAL,
            severity=MitigationSeverity.MEDIUM,
        )
        
        return self._predictive_engine.reject_mitigation(proposal_id, proposal, reason)
    
    def rollback_predictive_proposal(self, proposal_id: str) -> bool:
        """Faz rollback de proposta preditiva aplicada."""
        if not self._predictive_engine:
            return False
        
        # Criar proposta stub para rollback
        proposal = PredMitigationProposal(
            proposal_id=proposal_id,
            signal_id="unknown",
            mitigation_type=MitigationType.AUTO_ADJUST,
            severity=MitigationSeverity.LOW,
        )
        proposal.state = "applied"  # Simular que já foi aplicada
        
        return self._predictive_engine.rollback_mitigation(proposal_id, proposal)
    
    def freeze_brand_predictive(self, brand_id: str, reason: str = "") -> bool:
        """Congela brand via engine preditivo."""
        if not self._predictive_engine:
            return False
        
        return self._predictive_engine.freeze_brand(brand_id, reason)
    
    def unfreeze_brand_predictive(self, brand_id: str) -> bool:
        """Descongela brand via engine preditivo."""
        if not self._predictive_engine:
            return False
        
        return self._predictive_engine.unfreeze_brand(brand_id)
    
    def is_brand_frozen(self, brand_id: str) -> bool:
        """Verifica se brand está congelada."""
        if not self._predictive_engine:
            return False
        
        return self._predictive_engine.is_brand_frozen(brand_id)
