"""Predictive Resilience Engine - v27.

Implementa engine preditivo de resiliência com score composto e mitigação automática low-risk,
mantendo governança de segurança para medium/high risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class CycleState(Enum):
    """Estados do ciclo de resiliência."""
    
    OBSERVING = "observing"
    DETECTING = "detecting"
    PROPOSING = "proposing"
    MITIGATING = "mitigating"
    COMPLETED = "completed"


class RiskClassification(Enum):
    """Classificação de risco baseada no score composto."""
    
    LOW = "low"           # Score >= 0.85
    MEDIUM = "medium"     # Score 0.60 - 0.85
    HIGH = "high"         # Score 0.30 - 0.60
    CRITICAL = "critical" # Score < 0.30


class MitigationType(Enum):
    """Tipos de mitigação suportados."""
    
    AUTO_ADJUST = "auto_adjust"
    ADJUST_WITH_APPROVAL = "adjust_with_approval"
    FREEZE = "freeze"
    ROLLBACK = "rollback"


class MitigationSeverity(Enum):
    """Severidade da mitigação (determina auto-apply vs approval)."""
    
    LOW = "low"       # Auto-apply permitido
    MEDIUM = "medium" # Requer aprovação
    HIGH = "high"     # Requer aprovação + possível escalação
    CRITICAL = "critical"  # Requer aprovação + escalação imediata


@dataclass
class ResilienceScore:
    """Score composto de resiliência."""
    
    incident_component: float
    handoff_component: float
    approval_component: float
    composite_score: float = field(default=0.0)
    risk_class: RiskClassification = field(default=None)
    timestamp: Optional[str] = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def __post_init__(self):
        if self.composite_score == 0.0:
            # Calcular média ponderada (pode ser ajustado para pesos diferentes)
            self.composite_score = round(
                (self.incident_component + self.handoff_component + self.approval_component) / 3,
                4
            )
        
        if self.risk_class is None:
            self.risk_class = self._classify_risk(self.composite_score)
    
    @staticmethod
    def _classify_risk(score: float) -> RiskClassification:
        """Classifica o risco baseado no score."""
        if score >= 0.85:
            return RiskClassification.LOW
        elif score >= 0.60:
            return RiskClassification.MEDIUM
        elif score >= 0.30:
            return RiskClassification.HIGH
        else:
            return RiskClassification.CRITICAL
    
    def to_dict(self) -> dict[str, Any]:
        """Converte score para dict."""
        return {
            "incident_component": self.incident_component,
            "handoff_component": self.handoff_component,
            "approval_component": self.approval_component,
            "composite_score": self.composite_score,
            "risk_class": self.risk_class.value,
            "timestamp": self.timestamp,
        }


@dataclass
class PredictiveSignal:
    """Sinal preditivo de degradação."""
    
    signal_id: str
    metric_name: str
    current_value: float
    predicted_value: float
    confidence: float
    forecast_horizon_hours: int = 4
    severity: Optional[MitigationSeverity] = None
    timestamp: Optional[str] = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def __post_init__(self):
        if self.severity is None:
            self.severity = self._calculate_severity()
    
    @property
    def delta(self) -> float:
        """Calcula delta absoluto."""
        return self.predicted_value - self.current_value
    
    @property
    def delta_pct(self) -> float:
        """Calcula delta percentual."""
        if self.current_value == 0:
            return 0.0
        return abs(self.delta / self.current_value)
    
    def _calculate_severity(self) -> MitigationSeverity:
        """Calcula severidade baseada na degradação predita."""
        delta_pct = self.delta_pct
        
        if delta_pct < 0.10:
            return MitigationSeverity.LOW
        elif delta_pct < 0.30:
            return MitigationSeverity.MEDIUM
        elif delta_pct < 0.50:
            return MitigationSeverity.HIGH
        else:
            return MitigationSeverity.CRITICAL


@dataclass
class MitigationProposal:
    """Proposta de mitigação para um sinal."""
    
    proposal_id: str
    signal_id: str
    mitigation_type: MitigationType
    severity: MitigationSeverity
    description: str = ""
    estimated_impact: dict[str, float] = field(default_factory=dict)
    state: str = "pending"  # pending, applied, rejected, rolled_back
    created_at: Optional[str] = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    @property
    def can_auto_apply(self) -> bool:
        """Verifica se pode ser auto-aplicada."""
        return self.severity == MitigationSeverity.LOW
    
    @property
    def requires_escalation(self) -> bool:
        """Verifica se requer escalação."""
        return self.severity == MitigationSeverity.HIGH


@dataclass
class ResilienceCycle:
    """Ciclo de execução do engine de resiliência."""
    
    cycle_id: str
    brand_id: str
    state: CycleState = field(default_factory=lambda: CycleState.OBSERVING)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    score: Optional[ResilienceScore] = None
    signals: list[PredictiveSignal] = field(default_factory=list)
    proposals: list[MitigationProposal] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Converte ciclo para dict."""
        return {
            "cycle_id": self.cycle_id,
            "brand_id": self.brand_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "score": self.score.to_dict() if self.score else None,
            "signals_count": len(self.signals),
            "proposals_count": len(self.proposals),
        }


class PredictiveResilienceEngine:
    """Engine preditivo de resiliência - v27.
    
    Responsabilidades:
    - Calcular score composto de resiliência
    - Detectar sinais preditivos de degradação
    - Gerar propostas de mitigação
    - Auto-aplicar mitigações low-risk
    - Bloquear medium/high até aprovação
    - Suportar freeze e rollback
    """
    
    VERSION: str = "v27"
    
    # Thresholds para detecção de sinais
    INCIDENT_THRESHOLD: float = 0.10
    HANDOFF_THRESHOLD: float = 0.08
    APPROVAL_THRESHOLD: float = 0.05
    
    def __init__(self):
        self._cycles: dict[str, ResilienceCycle] = {}
        self._proposals: dict[str, MitigationProposal] = {}
        self._frozen_brands: set[str] = set()
        self._metric_history: list[dict[str, Any]] = []
        self._false_positives: list[dict[str, Any]] = []
        self._active_cycle: Optional[str] = None
    
    def calculate_score(self, metrics: dict[str, float]) -> ResilienceScore:
        """Calcula score composto de resiliência.
        
        Args:
            metrics: Dict com métricas atuais
            
        Returns:
            ResilienceScore calculado
        """
        # Componente de incidente (inverso - menor é melhor)
        incident_rate = metrics.get("incident_rate", 0.0)
        incident_component = max(0.0, 1.0 - (incident_rate * 5))  # 0.20 rate = 0 score
        
        # Componente de handoff (inverso - menor é melhor)
        handoff_rate = metrics.get("handoff_timeout_rate", 0.0)
        handoff_component = max(0.0, 1.0 - (handoff_rate * 6))  # ~0.17 rate = 0 score
        
        # Componente de approval (inverso - menor é melhor)
        approval_rate = metrics.get("approval_sla_breach_rate", 0.0)
        approval_component = max(0.0, 1.0 - (approval_rate * 10))  # 0.10 rate = 0 score
        
        return ResilienceScore(
            incident_component=round(incident_component, 4),
            handoff_component=round(handoff_component, 4),
            approval_component=round(approval_component, 4),
        )
    
    def detect_signals(self, metrics: dict[str, float]) -> list[PredictiveSignal]:
        """Detecta sinais preditivos de degradação.
        
        Args:
            metrics: Dict com métricas atuais
            
        Returns:
            Lista de sinais detectados
        """
        signals: list[PredictiveSignal] = []
        
        # Detectar incident_rate elevado ou crescente
        incident_rate = metrics.get("incident_rate", 0.0)
        if incident_rate > self.INCIDENT_THRESHOLD:
            # Predição simples: tendência continuará por 4h
            predicted = incident_rate * 1.2  # 20% increase projection
            signals.append(PredictiveSignal(
                signal_id=f"sig-inc-{uuid4().hex[:8]}",
                metric_name="incident_rate",
                current_value=incident_rate,
                predicted_value=predicted,
                confidence=0.75,
                forecast_horizon_hours=4,
            ))
        
        # Detectar handoff_timeout elevado
        handoff_rate = metrics.get("handoff_timeout_rate", 0.0)
        if handoff_rate > self.HANDOFF_THRESHOLD:
            predicted = handoff_rate * 1.25
            signals.append(PredictiveSignal(
                signal_id=f"sig-hand-{uuid4().hex[:8]}",
                metric_name="handoff_timeout_rate",
                current_value=handoff_rate,
                predicted_value=predicted,
                confidence=0.70,
                forecast_horizon_hours=4,
            ))
        
        # Detectar approval_sla_breach elevado
        approval_rate = metrics.get("approval_sla_breach_rate", 0.0)
        if approval_rate > self.APPROVAL_THRESHOLD:
            predicted = approval_rate * 1.3
            signals.append(PredictiveSignal(
                signal_id=f"sig-appr-{uuid4().hex[:8]}",
                metric_name="approval_sla_breach_rate",
                current_value=approval_rate,
                predicted_value=predicted,
                confidence=0.80,
                forecast_horizon_hours=4,
            ))
        
        return signals
    
    def generate_proposals(self, signals: list[PredictiveSignal]) -> list[MitigationProposal]:
        """Gera propostas de mitigação para sinais detectados.
        
        Args:
            signals: Lista de sinais detectados
            
        Returns:
            Lista de propostas de mitigação
        """
        proposals: list[MitigationProposal] = []
        
        for signal in signals:
            proposal = self._generate_proposal_for_signal(signal)
            if proposal:
                proposals.append(proposal)
        
        return proposals
    
    def _generate_proposal_for_signal(self, signal: PredictiveSignal) -> Optional[MitigationProposal]:
        """Gera proposta específica para um sinal."""
        
        if signal.metric_name == "incident_rate":
            return MitigationProposal(
                proposal_id=f"prop-inc-{uuid4().hex[:8]}",
                signal_id=signal.signal_id,
                mitigation_type=MitigationType.ADJUST_WITH_APPROVAL,
                severity=signal.severity,
                description=f"Reduce temperature and increase safety gates for incident_rate={signal.current_value:.2f}",
                estimated_impact={"incident_rate": -0.05, "v1_score": +0.02},
            )
        
        elif signal.metric_name == "handoff_timeout_rate":
            return MitigationProposal(
                proposal_id=f"prop-hand-{uuid4().hex[:8]}",
                signal_id=signal.signal_id,
                mitigation_type=MitigationType.AUTO_ADJUST if signal.severity == MitigationSeverity.LOW else MitigationType.ADJUST_WITH_APPROVAL,
                severity=signal.severity,
                description=f"Increase timeout buffer for handoff_rate={signal.current_value:.2f}",
                estimated_impact={"handoff_timeout_rate": -0.03},
            )
        
        elif signal.metric_name == "approval_sla_breach_rate":
            return MitigationProposal(
                proposal_id=f"prop-appr-{uuid4().hex[:8]}",
                signal_id=signal.signal_id,
                mitigation_type=MitigationType.AUTO_ADJUST if signal.severity == MitigationSeverity.LOW else MitigationType.ADJUST_WITH_APPROVAL,
                severity=signal.severity,
                description=f"Optimize approval queue for breach_rate={signal.current_value:.2f}",
                estimated_impact={"approval_sla_breach_rate": -0.04},
            )
        
        return None
    
    def apply_mitigation(
        self,
        proposal_id: str,
        proposal: MitigationProposal,
        approved: bool = False,
    ) -> bool:
        """Aplica uma mitigação.
        
        Args:
            proposal_id: ID da proposta
            proposal: Proposta a aplicar
            approved: Se foi aprovada (necessário para MEDIUM/HIGH)
            
        Returns:
            True se aplicada com sucesso
        """
        # Verificar se precisa de aprovação
        if not proposal.can_auto_apply and not approved:
            return False
        
        # Aplicar
        proposal.state = "applied"
        proposal.applied_at = datetime.now(timezone.utc).isoformat()
        
        # Registrar proposta
        self._proposals[proposal_id] = proposal
        
        return True
    
    def reject_mitigation(
        self,
        proposal_id: str,
        proposal: MitigationProposal,
        reason: str = "",
    ) -> bool:
        """Rejeita uma proposta de mitigação.
        
        Args:
            proposal_id: ID da proposta
            proposal: Proposta a rejeitar
            reason: Motivo da rejeição
            
        Returns:
            True se rejeitada com sucesso
        """
        proposal.state = "rejected"
        proposal.rejection_reason = reason
        
        self._proposals[proposal_id] = proposal
        
        return True
    
    def rollback_mitigation(self, proposal_id: str, proposal: MitigationProposal) -> bool:
        """Faz rollback de uma mitigação aplicada.
        
        Args:
            proposal_id: ID da proposta
            proposal: Proposta a fazer rollback
            
        Returns:
            True se rollback realizado com sucesso
        """
        if proposal.state != "applied":
            return False
        
        proposal.state = "rolled_back"
        proposal.rolled_back_at = datetime.now(timezone.utc).isoformat()
        
        self._proposals[proposal_id] = proposal
        
        return True
    
    def freeze_brand(self, brand_id: str, reason: str = "") -> bool:
        """Congela uma brand (prevenir novas operações).
        
        Args:
            brand_id: ID da brand
            reason: Motivo do freeze
            
        Returns:
            True se congelada com sucesso
        """
        self._frozen_brands.add(brand_id)
        return True
    
    def unfreeze_brand(self, brand_id: str) -> bool:
        """Descongela uma brand.
        
        Args:
            brand_id: ID da brand
            
        Returns:
            True se descongelada com sucesso
        """
        if brand_id in self._frozen_brands:
            self._frozen_brands.remove(brand_id)
            return True
        return False
    
    def record_false_positive(self, signal_id: str, reason: str = "") -> None:
        """Registra um falso positivo.
        
        Args:
            signal_id: ID do sinal
            reason: Motivo do falso positivo
        """
        self._false_positives.append({
            "signal_id": signal_id,
            "reason": reason,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
    
    # ========================================================================
    # Cycle Management
    # ========================================================================
    
    def start_cycle(self, brand_id: str) -> ResilienceCycle:
        """Inicia novo ciclo de resiliência."""
        cycle_id = f"cycle-res-{uuid4().hex[:12]}"
        cycle = ResilienceCycle(
            cycle_id=cycle_id,
            brand_id=brand_id,
            state=CycleState.OBSERVING,
        )
        self._cycles[cycle_id] = cycle
        self._active_cycle = cycle_id
        return cycle
    
    def get_cycle(self, cycle_id: str) -> Optional[ResilienceCycle]:
        """Retorna ciclo por ID."""
        return self._cycles.get(cycle_id)
    
    def update_cycle_state(self, cycle_id: str, state: str) -> bool:
        """Atualiza estado do ciclo."""
        if cycle_id not in self._cycles:
            return False
        
        try:
            cycle_state = CycleState(state)
        except ValueError:
            return False
        
        self._cycles[cycle_id].state = cycle_state
        
        if state == "completed":
            self._cycles[cycle_id].completed_at = datetime.now(timezone.utc).isoformat()
        
        return True
    
    # ========================================================================
    # Status and Reporting
    # ========================================================================
    
    def get_proposal_status(self, proposal_id: str) -> Optional[dict[str, Any]]:
        """Retorna status de uma proposta."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None
        
        return {
            "proposal_id": proposal.proposal_id,
            "signal_id": proposal.signal_id,
            "state": proposal.state,
            "created_at": proposal.created_at,
            "applied_at": proposal.applied_at,
            "rolled_back_at": proposal.rolled_back_at,
            "mitigation_type": proposal.mitigation_type.value,
            "severity": proposal.severity.value,
            "can_auto_apply": proposal.can_auto_apply,
            "requires_escalation": proposal.requires_escalation,
        }
    
    def get_status(self) -> dict[str, Any]:
        """Retorna status geral do engine."""
        active_cycles = [c for c in self._cycles.values() if c.state != CycleState.COMPLETED]
        
        total_proposals = len(self._proposals)
        applied = sum(1 for p in self._proposals.values() if p.state == "applied")
        rejected = sum(1 for p in self._proposals.values() if p.state == "rejected")
        rolled_back = sum(1 for p in self._proposals.values() if p.state == "rolled_back")
        
        return {
            "version": self.VERSION,
            "active_cycles": len(active_cycles),
            "cycles_total": len(self._cycles),
            "total_cycles": len(self._cycles),
            "frozen_brands": len(self._frozen_brands),
            "total_proposals": total_proposals,
            "proposals_applied": applied,
            "proposals_rejected": rejected,
            "proposals_rolled_back": rolled_back,
            "false_positives_total": len(self._false_positives),
        }
