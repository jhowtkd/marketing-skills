"""Quality-First Constrained Optimizer - v25.

Otimizador com prioridade em qualidade e restrições explícitas de custo/tempo.
Implementa ciclo evaluate/optimize/constrain/apply com feasibility check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class ProposalState(Enum):
    """Estados possíveis de uma proposta."""
    
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    FROZEN = "frozen"
    ROLLED_BACK = "rolled_back"


@dataclass
class QualityScore:
    """Score de qualidade calculado."""
    
    overall: float  # 0-100
    v1_score: float
    approval_rate: float
    incident_rate: float
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConstraintBounds:
    """Limites de restrição para otimização."""
    
    max_cost_increase_pct: float = 10.0  # +10% max
    max_mttc_increase_pct: float = 10.0  # +10% max
    max_incident_rate: float = 0.05  # 5% max


@dataclass
class OptimizationProposal:
    """Proposta de otimização gerada."""
    
    proposal_id: str
    run_id: str
    recommended_params: dict[str, Any]
    estimated_v1_improvement: float  # pontos
    estimated_cost_delta_pct: float  # percentual
    estimated_mttc_delta_pct: float  # percentual
    estimated_incident_rate: float
    quality_score: QualityScore
    feasibility_check_passed: bool = False
    state: ProposalState = field(default=ProposalState.PENDING)
    original_params: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None


@dataclass
class ProposalSnapshot:
    """Snapshot do estado anterior à aplicação."""
    
    proposal_id: str
    previous_params: dict[str, Any]
    applied_params: dict[str, Any]
    applied_at: str


class QualityOptimizer:
    """Otimizador quality-first com restrições."""
    
    version: str = "v25"
    
    def __init__(self):
        self._proposal_history: dict[str, list[OptimizationProposal]] = {}
        self._proposal_states: dict[str, ProposalState] = {}
        self._proposal_snapshots: dict[str, ProposalSnapshot] = {}
        self._quality_weights = {
            "v1_score": 0.40,
            "approval_rate": 0.35,
            "incident_penalty": 0.25,
        }
    
    def calculate_quality_score(
        self,
        v1_score: float,
        approval_rate: float,
        incident_rate: float,
    ) -> QualityScore:
        """Calcula score de qualidade ponderado.
        
        Args:
            v1_score: Score V1 (0-100)
            approval_rate: Taxa de aprovação (0-1)
            incident_rate: Taxa de incidentes (0-1)
        
        Returns:
            QualityScore calculado
        """
        # Normalizar componentes para 0-100
        approval_component = approval_rate * 100
        
        # Penalidade por incidentes (quadratica)
        incident_penalty = min(incident_rate * 100 * 2, 50)  # max 50 pontos penalty
        
        # Calcular score ponderado
        overall = (
            self._quality_weights["v1_score"] * v1_score +
            self._quality_weights["approval_rate"] * approval_component -
            self._quality_weights["incident_penalty"] * incident_penalty
        )
        
        # Garantir range 0-100
        overall = max(0.0, min(100.0, overall))
        
        return QualityScore(
            overall=overall,
            v1_score=v1_score,
            approval_rate=approval_rate,
            incident_rate=incident_rate,
        )
    
    def generate_proposal(
        self,
        current_run: dict[str, Any],
        historical_runs: list[dict[str, Any]],
        constraints: ConstraintBounds,
    ) -> OptimizationProposal:
        """Gera proposta de otimização.
        
        Args:
            current_run: Dados do run atual
            historical_runs: Runs históricos para análise
            constraints: Restrições a respeitar
        
        Returns:
            OptimizationProposal com recomendações
        """
        run_id = current_run.get("run_id", str(uuid4()))
        
        # Extrair métricas atuais
        current_v1 = current_run.get("v1_score", 60.0)
        current_cost = current_run.get("cost_per_job", 100.0)
        current_mttc = current_run.get("mttc", 300.0)
        current_incidents = current_run.get("incident_rate", 0.05)
        current_approval = current_run.get("approval_without_regen_24h", 0.70)
        
        # Calcular score atual
        quality_score = self.calculate_quality_score(
            v1_score=current_v1,
            approval_rate=current_approval,
            incident_rate=current_incidents,
        )
        
        # Gerar parâmetros recomendados (lógica simplificada)
        current_params = current_run.get("params", {})
        recommended_params = self._optimize_params(
            current_params=current_params,
            quality_score=quality_score,
            constraints=constraints,
        )
        
        # Estimar impacto
        estimated_v1_improvement = self._estimate_v1_improvement(
            current_v1=current_v1,
            recommended_params=recommended_params,
            historical_runs=historical_runs,
        )
        
        estimated_cost_delta_pct = self._estimate_cost_delta(
            current_cost=current_cost,
            recommended_params=recommended_params,
        )
        
        estimated_mttc_delta_pct = self._estimate_mttc_delta(
            current_mttc=current_mttc,
            recommended_params=recommended_params,
        )
        
        estimated_incident_rate = self._estimate_incident_rate(
            current_incidents=current_incidents,
            recommended_params=recommended_params,
        )
        
        # Verificar feasibilidade
        feasibility_check_passed = self._check_feasibility(
            cost_delta_pct=estimated_cost_delta_pct,
            mttc_delta_pct=estimated_mttc_delta_pct,
            incident_rate=estimated_incident_rate,
            constraints=constraints,
        )
        
        proposal_id = str(uuid4())
        proposal = OptimizationProposal(
            proposal_id=proposal_id,
            run_id=run_id,
            recommended_params=recommended_params,
            estimated_v1_improvement=estimated_v1_improvement,
            estimated_cost_delta_pct=estimated_cost_delta_pct,
            estimated_mttc_delta_pct=estimated_mttc_delta_pct,
            estimated_incident_rate=estimated_incident_rate,
            quality_score=quality_score,
            feasibility_check_passed=feasibility_check_passed,
            state=ProposalState.PENDING,
            original_params=dict(current_params),
        )
        
        # Registrar no histórico
        if run_id not in self._proposal_history:
            self._proposal_history[run_id] = []
        self._proposal_history[run_id].append(proposal)
        
        # Registrar estado inicial
        self._proposal_states[proposal_id] = ProposalState.PENDING
        
        return proposal
    
    def _optimize_params(
        self,
        current_params: dict[str, Any],
        quality_score: QualityScore,
        constraints: ConstraintBounds,
    ) -> dict[str, Any]:
        """Otimiza parâmetros baseado no score de qualidade."""
        params = dict(current_params)
        
        # Se qualidade está baixa, ajustar parâmetros
        if quality_score.overall < 70:
            # Aumentar temperatura levemente para mais criatividade
            params["temperature"] = min(params.get("temperature", 0.7) + 0.1, 1.0)
            # Aumentar tokens se necessário
            params["max_tokens"] = int(params.get("max_tokens", 2000) * 1.1)
        elif quality_score.overall > 85:
            # Qualidade boa, otimizar para custo
            params["temperature"] = max(params.get("temperature", 0.7) - 0.05, 0.1)
        
        # Garantir modelo definido
        if "model" not in params:
            params["model"] = "gpt-4"
        
        return params
    
    def _estimate_v1_improvement(
        self,
        current_v1: float,
        recommended_params: dict[str, Any],
        historical_runs: list[dict[str, Any]],
    ) -> float:
        """Estima melhoria no V1 score."""
        # Lógica simplificada: se temperatura aumentou, potencial melhoria
        temp = recommended_params.get("temperature", 0.7)
        base_improvement = max(0, (temp - 0.5) * 10)  # até ~5 pontos
        
        # Boost se histórico mostrar melhorias similares
        if historical_runs:
            recent_v1s = [r.get("v1_score", current_v1) for r in historical_runs[-5:]]
            if recent_v1s:
                trend = (recent_v1s[-1] - recent_v1s[0]) / len(recent_v1s)
                if trend > 0:
                    base_improvement += 2
        
        return round(min(base_improvement, 15.0), 2)  # max 15 pontos
    
    def _estimate_cost_delta(
        self,
        current_cost: float,
        recommended_params: dict[str, Any],
    ) -> float:
        """Estima delta de custo (%)."""
        tokens = recommended_params.get("max_tokens", 2000)
        # Aumento proporcional aos tokens
        delta = ((tokens - 2000) / 2000) * 100
        return round(max(delta, -5.0), 2)  # min -5%, max conforme tokens
    
    def _estimate_mttc_delta(
        self,
        current_mttc: float,
        recommended_params: dict[str, Any],
    ) -> float:
        """Estima delta de MTTC (%)."""
        tokens = recommended_params.get("max_tokens", 2000)
        # MTTC aumenta com mais tokens
        delta = ((tokens - 2000) / 2000) * 50  # 50% do delta de tokens
        return round(max(delta, -2.0), 2)  # min -2%
    
    def _estimate_incident_rate(
        self,
        current_incidents: float,
        recommended_params: dict[str, Any],
    ) -> float:
        """Estima taxa de incidentes."""
        temp = recommended_params.get("temperature", 0.7)
        # Temperatura alta pode aumentar incidentes
        if temp > 0.8:
            return round(min(current_incidents * 1.1, 0.08), 4)
        return round(current_incidents, 4)
    
    def _check_feasibility(
        self,
        cost_delta_pct: float,
        mttc_delta_pct: float,
        incident_rate: float,
        constraints: ConstraintBounds,
    ) -> bool:
        """Verifica se proposta respeita restrições."""
        if cost_delta_pct > constraints.max_cost_increase_pct:
            return False
        if mttc_delta_pct > constraints.max_mttc_increase_pct:
            return False
        if incident_rate > constraints.max_incident_rate:
            return False
        return True
    
    def get_proposal_history(self, run_id: str) -> list[OptimizationProposal]:
        """Retorna histórico de propostas para um run."""
        return list(self._proposal_history.get(run_id, []))
    
    def compare_proposals(
        self,
        proposals: list[OptimizationProposal],
    ) -> dict[str, Any]:
        """Compara múltiplas propostas.
        
        Returns:
            Dict com análise comparativa
        """
        if not proposals:
            return {"error": "no proposals to compare"}
        
        best_quality = max(proposals, key=lambda p: p.quality_score.overall)
        best_feasible = [p for p in proposals if p.feasibility_check_passed]
        
        return {
            "total_proposals": len(proposals),
            "feasible_proposals": len(best_feasible),
            "best_quality_proposal_id": best_quality.proposal_id,
            "best_quality_score": best_quality.quality_score.overall,
            "proposals": [
                {
                    "id": p.proposal_id,
                    "v1_improvement": p.estimated_v1_improvement,
                    "cost_delta_pct": p.estimated_cost_delta_pct,
                    "mttc_delta_pct": p.estimated_mttc_delta_pct,
                    "feasible": p.feasibility_check_passed,
                }
                for p in proposals
            ],
        }
    
    # =========================================================================
    # Proposal State Management (Task 2)
    # =========================================================================
    
    def get_proposal_state(self, proposal_id: str) -> Optional[ProposalState]:
        """Retorna o estado atual de uma proposta."""
        return self._proposal_states.get(proposal_id)
    
    def apply_proposal(
        self,
        proposal_id: str,
        enforce_feasibility: bool = True,
    ) -> bool:
        """Aplica uma proposta.
        
        Args:
            proposal_id: ID da proposta
            enforce_feasibility: Se True, bloqueia aplicação de propostas não viáveis
        
        Returns:
            True se aplicada com sucesso, False caso contrário
        """
        # Encontrar a proposta
        proposal = self._find_proposal_by_id(proposal_id)
        if proposal is None:
            return False
        
        # Verificar estado atual
        current_state = self._proposal_states.get(proposal_id)
        if current_state != ProposalState.PENDING:
            return False
        
        # Verificar feasibilidade se necessário
        if enforce_feasibility and not proposal.feasibility_check_passed:
            return False
        
        # Criar snapshot antes de aplicar
        self._create_snapshot(proposal)
        
        # Atualizar estado
        self._proposal_states[proposal_id] = ProposalState.APPLIED
        proposal.state = ProposalState.APPLIED
        proposal.applied_at = datetime.now(timezone.utc).isoformat()
        
        return True
    
    def reject_proposal(self, proposal_id: str) -> bool:
        """Rejeita uma proposta.
        
        Args:
            proposal_id: ID da proposta
        
        Returns:
            True se rejeitada com sucesso, False caso contrário
        """
        current_state = self._proposal_states.get(proposal_id)
        if current_state != ProposalState.PENDING:
            return False
        
        self._proposal_states[proposal_id] = ProposalState.REJECTED
        
        # Atualizar também no objeto proposta
        proposal = self._find_proposal_by_id(proposal_id)
        if proposal:
            proposal.state = ProposalState.REJECTED
        
        return True
    
    def freeze_proposal(self, proposal_id: str) -> bool:
        """Congela uma proposta (impede qualquer transição).
        
        Args:
            proposal_id: ID da proposta
        
        Returns:
            True se congelada com sucesso, False caso contrário
        """
        current_state = self._proposal_states.get(proposal_id)
        if current_state is None:
            return False
        
        # Só pode congelar se estiver PENDING
        if current_state != ProposalState.PENDING:
            return False
        
        self._proposal_states[proposal_id] = ProposalState.FROZEN
        
        proposal = self._find_proposal_by_id(proposal_id)
        if proposal:
            proposal.state = ProposalState.FROZEN
        
        return True
    
    def rollback_proposal(self, proposal_id: str) -> bool:
        """Faz rollback de uma proposta aplicada.
        
        Args:
            proposal_id: ID da proposta
        
        Returns:
            True se rollback realizado com sucesso, False caso contrário
        """
        current_state = self._proposal_states.get(proposal_id)
        if current_state != ProposalState.APPLIED:
            return False
        
        # Verificar se existe snapshot
        if proposal_id not in self._proposal_snapshots:
            return False
        
        # Atualizar estado
        self._proposal_states[proposal_id] = ProposalState.ROLLED_BACK
        
        proposal = self._find_proposal_by_id(proposal_id)
        if proposal:
            proposal.state = ProposalState.ROLLED_BACK
            proposal.rolled_back_at = datetime.now(timezone.utc).isoformat()
        
        return True
    
    def get_proposal_snapshot(self, proposal_id: str) -> Optional[dict[str, Any]]:
        """Retorna o snapshot de uma proposta aplicada.
        
        Returns:
            Dict com snapshot ou None se não existir
        """
        snapshot = self._proposal_snapshots.get(proposal_id)
        if snapshot is None:
            return None
        
        return {
            "proposal_id": snapshot.proposal_id,
            "previous_params": snapshot.previous_params,
            "applied_params": snapshot.applied_params,
            "applied_at": snapshot.applied_at,
        }
    
    def get_proposal_status(self, proposal_id: str) -> Optional[dict[str, Any]]:
        """Retorna o status completo de uma proposta.
        
        Returns:
            Dict com status ou None se não encontrada
        """
        proposal = self._find_proposal_by_id(proposal_id)
        if proposal is None:
            return None
        
        return {
            "proposal_id": proposal_id,
            "run_id": proposal.run_id,
            "state": proposal.state.value,
            "feasibility_check_passed": proposal.feasibility_check_passed,
            "estimated_v1_improvement": proposal.estimated_v1_improvement,
            "estimated_cost_delta_pct": proposal.estimated_cost_delta_pct,
            "estimated_mttc_delta_pct": proposal.estimated_mttc_delta_pct,
            "estimated_incident_rate": proposal.estimated_incident_rate,
            "quality_score": proposal.quality_score.overall,
            "created_at": proposal.created_at,
            "applied_at": proposal.applied_at,
            "rolled_back_at": proposal.rolled_back_at,
        }
    
    def _find_proposal_by_id(self, proposal_id: str) -> Optional[OptimizationProposal]:
        """Busca uma proposta por ID em todo o histórico."""
        for proposals in self._proposal_history.values():
            for proposal in proposals:
                if proposal.proposal_id == proposal_id:
                    return proposal
        return None
    
    def _create_snapshot(self, proposal: OptimizationProposal) -> None:
        """Cria um snapshot do estado antes da aplicação."""
        snapshot = ProposalSnapshot(
            proposal_id=proposal.proposal_id,
            previous_params=proposal.original_params,
            applied_params=proposal.recommended_params,
            applied_at=datetime.now(timezone.utc).isoformat(),
        )
        self._proposal_snapshots[proposal.proposal_id] = snapshot
