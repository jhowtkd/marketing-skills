"""
VM Studio v17 - Safety Gates Auto-Tuning Apply/Rollback

Aplicação e rollback seguro de ajustes de safety gates com:
- Autoapply apenas low-risk
- Rollback automático em 48h em caso de degradação
- Bloqueio com canary/rollback ativo
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional

from vm_webapp.safety_autotuning import (
    AdjustmentProposal,
    GatePerformance,
    RiskLevel,
)

UTC = timezone.utc


class ApplyDecision(str, Enum):
    """Decisão de aplicação de proposta."""
    APPLOYED_AUTO = "applied_auto"
    BLOCKED_HIGH_RISK = "blocked_high_risk"
    BLOCKED_CANARY_ACTIVE = "blocked_canary_active"
    BLOCKED_ROLLBACK_PENDING = "blocked_rollback_pending"
    REJECTED_BY_USER = "rejected_by_user"


class RollbackTrigger(str, Enum):
    """Gatilho para rollback."""
    FP_RATE_SPIKE = "fp_rate_spike"
    INCIDENTS_INCREASED = "incidents_increased"
    APPROVAL_RATE_DROP = "approval_rate_drop"
    MANUAL = "manual"


@dataclass
class ApplyResult:
    """Resultado de aplicação de proposta."""
    proposal_id: str
    decision: ApplyDecision
    applied_at: datetime
    previous_value: Optional[float] = None
    new_value: Optional[float] = None
    reason: Optional[str] = None


@dataclass
class RollbackResult:
    """Resultado de rollback."""
    proposal_id: str
    trigger: RollbackTrigger
    rolled_back_at: datetime
    restored_value: float
    reason: Optional[str] = None


class SafetyTuningApplier:
    """
    Aplicador seguro de ajustes de safety gates.
    
    Regras:
    - Apenas propostas LOW risk são auto-aplicadas
    - MEDIUM/HIGH/CRITICAL requerem aprovação manual
    - Rollback automático em 48h se performance degradar
    - Bloqueio se canary ou rollback ativo para o mesmo gate
    """
    
    # Thresholds de rollback
    ROLLBACK_WINDOW_HOURS = 48
    FP_RATE_INCREASE_THRESHOLD = 0.05  # 5% aumento = rollback
    INCIDENT_INCREASE_THRESHOLD = 0.03  # 3% aumento = rollback
    APPROVAL_RATE_DROP_THRESHOLD = 0.05  # 5% queda = rollback
    
    def __init__(self):
        # Propostas aplicadas (para possível rollback)
        self.applied_proposals: dict[str, dict] = {}
        
        # Gates com canary ativo
        self.active_canaries: set[str] = set()
        
        # Gates com rollback pendente
        self.pending_rollbacks: set[str] = set()
        
        # Gates congelados (não recebem ajustes)
        self.frozen_gates: set[str] = set()
        
        # Contador para IDs de proposta
        self._proposal_counter = 0
    
    def _generate_proposal_id(self) -> str:
        """Gera ID único para proposta."""
        self._proposal_counter += 1
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        return f"prop-{timestamp}-{self._proposal_counter:04d}"
    
    def apply_proposal(
        self,
        proposal: AdjustmentProposal,
        autoapply: bool = True
    ) -> ApplyResult:
        """
        Aplica uma proposta de ajuste.
        
        Args:
            proposal: Proposta de ajuste
            autoapply: Se True, aplica automaticamente apenas low-risk
            
        Returns:
            Resultado da aplicação
        """
        proposal_id = self._generate_proposal_id()
        now = datetime.now(UTC)
        
        # Verifica se gate está congelado
        if proposal.gate_name in self.frozen_gates:
            return ApplyResult(
                proposal_id=proposal_id,
                decision=ApplyDecision.BLOCKED_CANARY_ACTIVE,
                applied_at=now,
                reason="gate_frozen"
            )
        
        # Verifica canary ativo
        if proposal.gate_name in self.active_canaries:
            return ApplyResult(
                proposal_id=proposal_id,
                decision=ApplyDecision.BLOCKED_CANARY_ACTIVE,
                applied_at=now,
                reason="canary_active"
            )
        
        # Verifica rollback pendente
        if proposal.gate_name in self.pending_rollbacks:
            return ApplyResult(
                proposal_id=proposal_id,
                decision=ApplyDecision.BLOCKED_ROLLBACK_PENDING,
                applied_at=now,
                reason="rollback_pending"
            )
        
        # Verifica risk level para autoapply
        if autoapply and proposal.risk_level != RiskLevel.LOW:
            return ApplyResult(
                proposal_id=proposal_id,
                decision=ApplyDecision.BLOCKED_HIGH_RISK,
                applied_at=now,
                reason=f"risk_level_{proposal.risk_level.value}"
            )
        
        # Aplica o ajuste
        self.applied_proposals[proposal_id] = {
            "gate_name": proposal.gate_name,
            "previous_value": proposal.current_value,
            "new_value": proposal.proposed_value,
            "applied_at": now,
            "risk_level": proposal.risk_level.value,
            "reason": proposal.reason
        }
        
        # Inicia canary para monitoramento
        self.active_canaries.add(proposal.gate_name)
        
        return ApplyResult(
            proposal_id=proposal_id,
            decision=ApplyDecision.APPLOYED_AUTO,
            applied_at=now,
            previous_value=proposal.current_value,
            new_value=proposal.proposed_value
        )
    
    def evaluate_rollback(
        self,
        proposal_id: str,
        current_performance: GatePerformance,
        previous_performance: GatePerformance
    ) -> Optional[RollbackResult]:
        """
        Avalia se é necessário rollback baseado na performance.
        
        Args:
            proposal_id: ID da proposta aplicada
            current_performance: Performance atual
            previous_performance: Performance anterior à aplicação
            
        Returns:
            Resultado do rollback ou None se não necessário
        """
        if proposal_id not in self.applied_proposals:
            return None
        
        proposal_data = self.applied_proposals[proposal_id]
        applied_at = proposal_data["applied_at"]
        now = datetime.now(UTC)
        
        # Verifica janela de 48h
        hours_since_apply = (now - applied_at).total_seconds() / 3600
        if hours_since_apply > self.ROLLBACK_WINDOW_HOURS:
            return None  # Fora da janela de rollback
        
        # Verifica aumento de FP rate
        current_fp = current_performance.false_positive_rate
        previous_fp = previous_performance.false_positive_rate
        fp_increase = current_fp - previous_fp
        
        if fp_increase > self.FP_RATE_INCREASE_THRESHOLD:
            return RollbackResult(
                proposal_id=proposal_id,
                trigger=RollbackTrigger.FP_RATE_SPIKE,
                rolled_back_at=now,
                restored_value=proposal_data["previous_value"],
                reason=f"FP_rate_increased_from_{previous_fp:.2%}_to_{current_fp:.2%}"
            )
        
        # Verifica aumento de incidentes
        current_incidents = current_performance.missed_incident_rate
        previous_incidents = previous_performance.missed_incident_rate
        incident_increase = current_incidents - previous_incidents
        
        if incident_increase > self.INCIDENT_INCREASE_THRESHOLD:
            return RollbackResult(
                proposal_id=proposal_id,
                trigger=RollbackTrigger.INCIDENTS_INCREASED,
                rolled_back_at=now,
                restored_value=proposal_data["previous_value"],
                reason=f"incidents_increased_from_{previous_incidents:.2%}_to_{current_incidents:.2%}"
            )
        
        # Verifica queda de approval rate
        current_approval = current_performance.approval_without_regen_rate
        previous_approval = previous_performance.approval_without_regen_rate
        approval_drop = previous_approval - current_approval
        
        if approval_drop > self.APPROVAL_RATE_DROP_THRESHOLD:
            return RollbackResult(
                proposal_id=proposal_id,
                trigger=RollbackTrigger.APPROVAL_RATE_DROP,
                rolled_back_at=now,
                restored_value=proposal_data["previous_value"],
                reason=f"approval_rate_dropped_from_{previous_approval:.2%}_to_{current_approval:.2%}"
            )
        
        return None  # Sem rollback necessário
    
    def execute_rollback(self, rollback_result: RollbackResult) -> bool:
        """
        Executa o rollback de uma proposta.
        
        Args:
            rollback_result: Resultado do rollback a executar
            
        Returns:
            True se rollback executado com sucesso
        """
        proposal_id = rollback_result.proposal_id
        
        if proposal_id not in self.applied_proposals:
            return False
        
        proposal_data = self.applied_proposals[proposal_id]
        gate_name = proposal_data["gate_name"]
        
        # Adiciona à lista de rollbacks pendentes
        self.pending_rollbacks.add(gate_name)
        
        # Remove canary
        self.active_canaries.discard(gate_name)
        
        # Marca proposta como revertida
        proposal_data["rolled_back_at"] = rollback_result.rolled_back_at
        proposal_data["restored_value"] = rollback_result.restored_value
        proposal_data["rollback_trigger"] = rollback_result.trigger.value
        
        return True
    
    def clear_canary(self, gate_name: str):
        """Limpa o canary de um gate após validação."""
        self.active_canaries.discard(gate_name)
    
    def clear_rollback_pending(self, gate_name: str):
        """Limpa o status de rollback pendente."""
        self.pending_rollbacks.discard(gate_name)
    
    def freeze_gate(self, gate_name: str, reason: str = "manual"):
        """
        Congela um gate para prevenir ajustes.
        
        Args:
            gate_name: Nome do gate a congelar
            reason: Motivo do congelamento
        """
        self.frozen_gates.add(gate_name)
    
    def unfreeze_gate(self, gate_name: str):
        """Descongela um gate."""
        self.frozen_gates.discard(gate_name)
    
    def get_applied_proposal(self, proposal_id: str) -> Optional[dict]:
        """Retorna dados de uma proposta aplicada."""
        return self.applied_proposals.get(proposal_id)
    
    def is_gate_frozen(self, gate_name: str) -> bool:
        """Verifica se um gate está congelado."""
        return gate_name in self.frozen_gates
    
    def is_canary_active(self, gate_name: str) -> bool:
        """Verifica se há canary ativo para um gate."""
        return gate_name in self.active_canaries
    
    def is_rollback_pending(self, gate_name: str) -> bool:
        """Verifica se há rollback pendente para um gate."""
        return gate_name in self.pending_rollbacks
