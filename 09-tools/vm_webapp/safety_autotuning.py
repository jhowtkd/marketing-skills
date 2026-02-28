"""
VM Studio v17 - Safety Gates Auto-Tuning Engine

Auto-tuning semanal semi-automático dos safety gates com:
- Limites rígidos (±10% max adjustment)
- Guardas de volume mínimo
- Análise de performance
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

UTC = timezone.utc


class RiskLevel(str, Enum):
    """Níveis de risco para ajustes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GateConfig:
    """Configuração de um safety gate."""
    gate_name: str
    current_value: float
    min_value: float
    max_value: float


@dataclass
class GatePerformance:
    """Métricas de performance de um gate."""
    gate_name: str
    false_positive_blocks: int
    missed_incidents: int
    total_decisions: int
    approval_without_regen_count: int
    
    @property
    def false_positive_rate(self) -> float:
        """Taxa de falsos positivos."""
        if self.total_decisions == 0:
            return 0.0
        return self.false_positive_blocks / self.total_decisions
    
    @property
    def missed_incident_rate(self) -> float:
        """Taxa de incidentes perdidos."""
        if self.total_decisions == 0:
            return 0.0
        return self.missed_incidents / self.total_decisions
    
    @property
    def approval_without_regen_rate(self) -> float:
        """Taxa de aprovação sem regeneração."""
        if self.total_decisions == 0:
            return 0.0
        return self.approval_without_regen_count / self.total_decisions


@dataclass
class AdjustmentProposal:
    """Proposta de ajuste de gate."""
    gate_name: str
    current_value: float
    proposed_value: float
    adjustment_percent: float
    risk_level: RiskLevel
    reason: str
    blocked_by_volume: bool = False


@dataclass
class TuningCycleResult:
    """Resultado de um ciclo de tuning."""
    cycle_id: str
    timestamp: datetime
    proposals: list[AdjustmentProposal]
    applied_count: int = 0
    blocked_count: int = 0


class SafetyAutoTuner:
    """
    Engine de auto-tuning para safety gates.
    
    Regras:
    - Ajuste máximo: ±10% por ciclo
    - Volume mínimo: 50 decisões para análise
    - Baixa taxa FP (>15%): reduzir threshold
    - Alta taxa de incidentes perdidos (>3%): aumentar threshold
    """
    
    # Thresholds de performance
    FP_RATE_HIGH_THRESHOLD = 0.15  # 15% - considerado alto
    MISSED_INCIDENT_HIGH_THRESHOLD = 0.03  # 3% - considerado alto
    MAX_ADJUSTMENT_PERCENT = 10.0  # ±10% max
    DEFAULT_MIN_VOLUME = 50  # Mínimo de decisões para análise
    
    def __init__(self, min_volume_threshold: int = None):
        self.min_volume_threshold = min_volume_threshold or self.DEFAULT_MIN_VOLUME
    
    def analyze_cycle(
        self,
        configs: list[GateConfig],
        performances: list[GatePerformance]
    ) -> list[AdjustmentProposal]:
        """
        Analisa um ciclo e retorna propostas de ajuste.
        
        Args:
            configs: Lista de configurações de gates
            performances: Lista de métricas de performance
            
        Returns:
            Lista de propostas de ajuste
        """
        proposals = []
        
        # Cria mapa de performance por nome
        perf_map = {p.gate_name: p for p in performances}
        
        for config in configs:
            perf = perf_map.get(config.gate_name)
            if perf:
                proposal = self.propose_adjustment(config, perf)
                if proposal:
                    proposals.append(proposal)
        
        return proposals
    
    def propose_adjustment(
        self,
        config: GateConfig,
        performance: GatePerformance
    ) -> Optional[AdjustmentProposal]:
        """
        Proporciona ajuste para um gate baseado em performance.
        
        Args:
            config: Configuração do gate
            performance: Métricas de performance
            
        Returns:
            Proposta de ajuste ou None se nenhum ajuste necessário
        """
        # Verifica volume mínimo
        if performance.total_decisions < self.min_volume_threshold:
            return AdjustmentProposal(
                gate_name=config.gate_name,
                current_value=config.current_value,
                proposed_value=config.current_value,
                adjustment_percent=0.0,
                risk_level=RiskLevel.LOW,
                reason="INSUFFICIENT_VOLUME",
                blocked_by_volume=True
            )
        
        fp_rate = performance.false_positive_rate
        missed_rate = performance.missed_incident_rate
        
        # Determina direção do ajuste
        adjustment_percent = 0.0
        reason = None
        risk_level = RiskLevel.LOW
        
        # Alto FP rate -> diminuir threshold (ajuste negativo)
        if fp_rate > self.FP_RATE_HIGH_THRESHOLD and missed_rate <= self.MISSED_INCIDENT_HIGH_THRESHOLD:
            # Calcular ajuste baseado na severidade do FP
            suggested_adjustment = -min(fp_rate * 100, self.MAX_ADJUSTMENT_PERCENT)
            adjustment_percent = max(suggested_adjustment, -self.MAX_ADJUSTMENT_PERCENT)
            reason = "HIGH_FP_RATE"
            risk_level = RiskLevel.MEDIUM if fp_rate > 0.25 else RiskLevel.LOW
        
        # Alto missed incident rate -> aumentar threshold (ajuste positivo)
        elif missed_rate > self.MISSED_INCIDENT_HIGH_THRESHOLD and fp_rate <= self.FP_RATE_HIGH_THRESHOLD:
            suggested_adjustment = min(missed_rate * 100 * 2, self.MAX_ADJUSTMENT_PERCENT)
            adjustment_percent = min(suggested_adjustment, self.MAX_ADJUSTMENT_PERCENT)
            reason = "HIGH_MISSED_INCIDENTS"
            risk_level = RiskLevel.HIGH if missed_rate > 0.05 else RiskLevel.MEDIUM
        
        # Ambos altos -> conflito, prioriza segurança (aumentar threshold)
        elif fp_rate > self.FP_RATE_HIGH_THRESHOLD and missed_rate > self.MISSED_INCIDENT_HIGH_THRESHOLD:
            # Prioriza segurança: aumenta threshold moderadamente
            adjustment_percent = min(missed_rate * 50, self.MAX_ADJUSTMENT_PERCENT / 2)
            adjustment_percent = max(adjustment_percent, 2.0)  # Mínimo 2%
            reason = "BOTH_METRICS_HIGH_PRIORITIZE_SAFETY"
            risk_level = RiskLevel.HIGH
        
        # Se não há necessidade de ajuste
        if adjustment_percent == 0.0:
            return None
        
        # Calcula valor proposto com clamp aos bounds
        adjustment_factor = 1 + (adjustment_percent / 100)
        proposed_value = config.current_value * adjustment_factor
        
        # Clamp aos bounds min/max
        proposed_value = max(config.min_value, min(config.max_value, proposed_value))
        
        # Recalcula percentual real após clamp
        actual_adjustment = ((proposed_value - config.current_value) / config.current_value) * 100
        
        return AdjustmentProposal(
            gate_name=config.gate_name,
            current_value=config.current_value,
            proposed_value=proposed_value,
            adjustment_percent=round(actual_adjustment, 2),
            risk_level=risk_level,
            reason=reason
        )
    
    def run_cycle(
        self,
        cycle_id: str,
        configs: list[GateConfig],
        performances: list[GatePerformance]
    ) -> TuningCycleResult:
        """
        Executa um ciclo completo de tuning.
        
        Args:
            cycle_id: Identificador do ciclo
            configs: Lista de configurações de gates
            performances: Lista de métricas de performance
            
        Returns:
            Resultado do ciclo de tuning
        """
        proposals = self.analyze_cycle(configs, performances)
        
        blocked_count = sum(1 for p in proposals if p.blocked_by_volume)
        
        return TuningCycleResult(
            cycle_id=cycle_id,
            timestamp=datetime.now(UTC),
            proposals=proposals,
            applied_count=0,
            blocked_count=blocked_count
        )
