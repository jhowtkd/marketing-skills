"""
Task A: Safety Gates Policy Engine
Governança v16 - Safety gates fortes para automação de decisões

Principles:
- Safety-first
- Determinístico
- Auditável
- Reversível
- Sem automação cega

Gates implementados:
1. Sample Size - minimum sample size por segmento
2. Confidence Threshold - confidence mínimo para executar
3. Regression Guard - janela curta vs longa
4. Cooldown - período de espera entre ações
5. Max Actions Per Day - limite de ações por brand
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Any

UTC = timezone.utc


class RiskLevel(str, Enum):
    """Níveis de risco para decisões."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GateType(str, Enum):
    """Tipos de safety gates."""
    SAMPLE_SIZE = "sample_size"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    REGRESSION_GUARD = "regression_guard"
    COOLDOWN = "cooldown"
    MAX_ACTIONS_PER_DAY = "max_actions_per_day"


@dataclass
class SafetyGateResult:
    """Resultado da avaliação de um safety gate."""
    gate_type: GateType
    allowed: bool
    risk_level: RiskLevel
    blocked_by: list[str] = field(default_factory=list)
    recommended_action: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)


class SafetyGate:
    """Base class para todos os safety gates."""
    
    def __init__(self, gate_type: GateType):
        self.gate_type = gate_type
    
    def evaluate(self, context: dict[str, Any]) -> SafetyGateResult:
        """Avalia o gate e retorna o resultado."""
        raise NotImplementedError("Subclasses must implement evaluate()")


class SampleSizeGate(SafetyGate):
    """
    Gate 1: Minimum sample size por segmento.
    
    Bloqueia se não houver dados suficientes para tomar
    uma decisão estatisticamente significativa.
    """
    
    def __init__(self, min_samples: int = 100):
        super().__init__(GateType.SAMPLE_SIZE)
        self.min_samples = min_samples
    
    def evaluate(self, context: dict[str, Any]) -> SafetyGateResult:
        sample_size = context.get("sample_size")
        decision_type = context.get("decision_type", "expand")
        
        # Ajusta requisitos baseado no tipo de decisão
        required_samples = self._get_required_samples(decision_type)
        
        # Valida sample size
        if sample_size is None:
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=["missing_sample_size"],
                risk_level=RiskLevel.CRITICAL,
                recommended_action="collect_segment_data",
                details={"required": required_samples, "actual": None}
            )
        
        if sample_size == 0:
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=["zero_sample_size"],
                risk_level=RiskLevel.CRITICAL,
                recommended_action="collect_segment_data",
                details={"required": required_samples, "actual": 0}
            )
        
        if sample_size < required_samples:
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=["insufficient_sample_size"],
                risk_level=RiskLevel.HIGH,
                recommended_action=f"collect_more_data_need_{required_samples - sample_size}_more",
                details={"required": required_samples, "actual": sample_size}
            )
        
        return SafetyGateResult(
            gate_type=self.gate_type,
            allowed=True,
            risk_level=RiskLevel.LOW,
            details={"required": required_samples, "actual": sample_size}
        )
    
    def _get_required_samples(self, decision_type: str) -> int:
        """Retorna o número mínimo de amostras baseado no tipo de decisão."""
        # ROLLBACK pode ser mais urgente, aceita menos dados
        # EXPAND requer mais dados por ser uma ação expansiva
        multipliers = {
            "rollback": 0.5,   # 50% do mínimo para rollback
            "hold": 0.75,      # 75% para hold
            "expand": 1.0      # 100% para expand
        }
        multiplier = multipliers.get(decision_type, 1.0)
        return int(self.min_samples * multiplier)


class ConfidenceThresholdGate(SafetyGate):
    """
    Gate 2: Confidence threshold mínimo.
    
    Bloqueia se a confiança na decisão for insuficiente.
    """
    
    def __init__(self, min_confidence: float = 0.8):
        super().__init__(GateType.CONFIDENCE_THRESHOLD)
        self.min_confidence = min_confidence
    
    def evaluate(self, context: dict[str, Any]) -> SafetyGateResult:
        confidence_score = context.get("confidence_score")
        
        if confidence_score is None:
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=["missing_confidence_score"],
                risk_level=RiskLevel.HIGH,
                recommended_action="recalculate_confidence",
                details={"required": self.min_confidence, "actual": None}
            )
        
        if confidence_score < self.min_confidence:
            risk_level = RiskLevel.MEDIUM if confidence_score >= 0.7 else RiskLevel.HIGH
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=["confidence_below_threshold"],
                risk_level=risk_level,
                recommended_action="improve_model_confidence",
                details={"required": self.min_confidence, "actual": confidence_score}
            )
        
        return SafetyGateResult(
            gate_type=self.gate_type,
            allowed=True,
            risk_level=RiskLevel.LOW,
            details={"required": self.min_confidence, "actual": confidence_score}
        )


class RegressionGuardGate(SafetyGate):
    """
    Gate 3: Regression guard (janela curta vs longa).
    
    Bloqueia se detectar regressão em janelas curtas ou longas,
    ou se houver alertas críticos ativos.
    """
    
    def __init__(
        self,
        short_window_hours: int = 1,
        long_window_hours: int = 24
    ):
        super().__init__(GateType.REGRESSION_GUARD)
        self.short_window_hours = short_window_hours
        self.long_window_hours = long_window_hours
    
    def evaluate(self, context: dict[str, Any]) -> SafetyGateResult:
        short_regression = context.get("short_window_regression", False)
        long_regression = context.get("long_window_regression", False)
        active_alerts = context.get("active_alerts", [])
        
        blocked_by = []
        risk_level = RiskLevel.LOW
        
        # Verifica alertas críticos primeiro
        critical_alerts = [
            a for a in active_alerts
            if isinstance(a, dict) and a.get("severity") == "critical"
        ]
        
        if critical_alerts:
            blocked_by.append("critical_alert_active")
            risk_level = RiskLevel.CRITICAL
        
        # Verifica regressão em janela longa (mais grave)
        if long_regression:
            blocked_by.append("long_window_regression")
            risk_level = RiskLevel.CRITICAL
        
        # Verifica regressão em janela curta
        if short_regression:
            blocked_by.append("short_window_regression")
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.HIGH
        
        if blocked_by:
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=blocked_by,
                risk_level=risk_level,
                recommended_action="investigate_regression",
                details={
                    "short_window_hours": self.short_window_hours,
                    "long_window_hours": self.long_window_hours,
                    "critical_alerts_count": len(critical_alerts)
                }
            )
        
        return SafetyGateResult(
            gate_type=self.gate_type,
            allowed=True,
            risk_level=RiskLevel.LOW,
            details={
                "short_window_hours": self.short_window_hours,
                "long_window_hours": self.long_window_hours
            }
        )


class CooldownGate(SafetyGate):
    """
    Gate 4: Cooldown por segmento.
    
    Impede ações frequentes no mesmo segmento para evitar
    flapping e permitir observação do efeito das decisões.
    
    ROLLBACK ignora cooldown (emergência).
    """
    
    def __init__(self, cooldown_hours: int = 4):
        super().__init__(GateType.COOLDOWN)
        self.cooldown_hours = cooldown_hours
    
    def evaluate(self, context: dict[str, Any]) -> SafetyGateResult:
        last_action_at = context.get("last_action_at")
        decision_type = context.get("decision_type", "expand")
        
        # ROLLBACK sempre pode passar (emergência)
        if decision_type == "rollback":
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=True,
                risk_level=RiskLevel.LOW,
                details={"emergency_override": True, "reason": "rollback_bypasses_cooldown"}
            )
        
        # Sem ação anterior = pode executar
        if last_action_at is None:
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=True,
                risk_level=RiskLevel.LOW,
                details={"last_action": None}
            )
        
        # Calcula tempo desde última ação
        try:
            if isinstance(last_action_at, str):
                last_action_time = datetime.fromisoformat(last_action_at.replace('Z', '+00:00'))
            else:
                last_action_time = last_action_at
            
            time_since = datetime.now(UTC) - last_action_time
            hours_since = time_since.total_seconds() / 3600
            
            if hours_since < self.cooldown_hours:
                remaining = self.cooldown_hours - hours_since
                return SafetyGateResult(
                    gate_type=self.gate_type,
                    allowed=False,
                    blocked_by=["cooldown_active"],
                    risk_level=RiskLevel.MEDIUM,
                    recommended_action=f"wait_{remaining:.1f}_hours",
                    details={
                        "cooldown_hours": self.cooldown_hours,
                        "hours_since_last": hours_since,
                        "hours_remaining": remaining
                    }
                )
            
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=True,
                risk_level=RiskLevel.LOW,
                details={
                    "cooldown_hours": self.cooldown_hours,
                    "hours_since_last": hours_since
                }
            )
        
        except (ValueError, TypeError):
            # Erro ao parsear data = bloqueia por segurança
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=["invalid_last_action_timestamp"],
                risk_level=RiskLevel.HIGH,
                recommended_action="verify_system_clock"
            )


class MaxActionsPerDayGate(SafetyGate):
    """
    Gate 5: Max actions per day por brand.
    
    Limita o número de ações automatizadas por dia para
    prevenir cascata de erros e permitir supervisão humana.
    """
    
    def __init__(self, max_actions: int = 10):
        super().__init__(GateType.MAX_ACTIONS_PER_DAY)
        self.max_actions = max_actions
    
    def evaluate(self, context: dict[str, Any]) -> SafetyGateResult:
        actions_today = context.get("actions_today", 0)
        
        if actions_today >= self.max_actions:
            risk_level = RiskLevel.HIGH if actions_today > self.max_actions else RiskLevel.MEDIUM
            return SafetyGateResult(
                gate_type=self.gate_type,
                allowed=False,
                blocked_by=["max_actions_per_day_reached"],
                risk_level=risk_level,
                recommended_action="wait_until_tomorrow_or_manual_override",
                details={
                    "max_actions": self.max_actions,
                    "actions_today": actions_today,
                    "overage": max(0, actions_today - self.max_actions)
                }
            )
        
        return SafetyGateResult(
            gate_type=self.gate_type,
            allowed=True,
            risk_level=RiskLevel.LOW,
            details={
                "max_actions": self.max_actions,
                "actions_today": actions_today,
                "remaining": self.max_actions - actions_today
            }
        )


class SafetyGateEngine:
    """
    Engine principal que orquestra todos os safety gates.
    
    Avalia todos os gates e retorna uma decisão consolidada.
    A decisão só é aprovada se TODOS os gates passarem.
    """
    
    # Configurações padrão
    DEFAULT_MIN_SAMPLES = 100
    DEFAULT_MIN_CONFIDENCE = 0.8
    DEFAULT_COOLDOWN_HOURS = 4
    DEFAULT_MAX_ACTIONS_PER_DAY = 10
    
    def __init__(
        self,
        min_samples: int = None,
        min_confidence: float = None,
        cooldown_hours: int = None,
        max_actions_per_day: int = None
    ):
        # Inicializa gates com configurações
        self.gates: list[SafetyGate] = [
            SampleSizeGate(min_samples or self.DEFAULT_MIN_SAMPLES),
            ConfidenceThresholdGate(min_confidence or self.DEFAULT_MIN_CONFIDENCE),
            RegressionGuardGate(),
            CooldownGate(cooldown_hours or self.DEFAULT_COOLDOWN_HOURS),
            MaxActionsPerDayGate(max_actions_per_day or self.DEFAULT_MAX_ACTIONS_PER_DAY)
        ]
    
    def evaluate(self, context: dict[str, Any]) -> SafetyGateResult:
        """
        Avalia todos os gates e retorna resultado consolidado.
        
        Returns:
            SafetyGateResult com:
            - allowed: True se TODOS os gates passaram
            - blocked_by: lista de todos os reason codes de falha
            - risk_level: nível agregado de risco
            - recommended_action: ação sugerida para resolver bloqueios
        """
        # Validações básicas de contexto
        if not context:
            return SafetyGateResult(
                gate_type=GateType.SAMPLE_SIZE,  # Default
                allowed=False,
                blocked_by=["empty_context"],
                risk_level=RiskLevel.CRITICAL,
                recommended_action="provide_execution_context"
            )
        
        if "segment_key" not in context:
            return SafetyGateResult(
                gate_type=GateType.SAMPLE_SIZE,
                allowed=False,
                blocked_by=["missing_segment_key"],
                risk_level=RiskLevel.CRITICAL,
                recommended_action="specify_target_segment"
            )
        
        # Aplica configurações customizadas se fornecidas
        custom_config = context.get("custom_config", {})
        if custom_config:
            self._apply_custom_config(custom_config)
        
        # Avalia todos os gates
        results: list[SafetyGateResult] = []
        for gate in self.gates:
            result = gate.evaluate(context)
            results.append(result)
        
        # Consolida resultados
        all_allowed = all(r.allowed for r in results)
        all_blocked = []
        max_risk = RiskLevel.LOW
        
        for r in results:
            all_blocked.extend(r.blocked_by)
            # Atualiza risk level para o mais grave
            if r.risk_level == RiskLevel.CRITICAL:
                max_risk = RiskLevel.CRITICAL
            elif r.risk_level == RiskLevel.HIGH:
                if max_risk not in [RiskLevel.CRITICAL]:
                    max_risk = RiskLevel.HIGH
            elif r.risk_level == RiskLevel.MEDIUM and max_risk == RiskLevel.LOW:
                max_risk = RiskLevel.MEDIUM
        
        # Determina ação recomendada
        recommended_action = None
        if not all_allowed:
            recommended_action = self._generate_recommendation(all_blocked, results)
        
        return SafetyGateResult(
            gate_type=GateType.SAMPLE_SIZE,  # Representativo
            allowed=all_allowed,
            blocked_by=all_blocked,
            risk_level=max_risk,
            recommended_action=recommended_action,
            details={"individual_results": results}
        )
    
    def _apply_custom_config(self, config: dict[str, Any]):
        """Aplica configurações customizadas aos gates."""
        for gate in self.gates:
            if isinstance(gate, SampleSizeGate) and "min_samples" in config:
                gate.min_samples = config["min_samples"]
            elif isinstance(gate, ConfidenceThresholdGate) and "min_confidence" in config:
                gate.min_confidence = config["min_confidence"]
            elif isinstance(gate, CooldownGate) and "cooldown_hours" in config:
                gate.cooldown_hours = config["cooldown_hours"]
            elif isinstance(gate, MaxActionsPerDayGate) and "max_actions_per_day" in config:
                gate.max_actions = config["max_actions_per_day"]
    
    def _generate_recommendation(
        self,
        blocked_by: list[str],
        results: list[SafetyGateResult]
    ) -> str:
        """Gera recomendação baseada nos bloqueios."""
        if "critical_alert_active" in blocked_by or "long_window_regression" in blocked_by:
            return "immediate_manual_review_required"
        
        if "insufficient_sample_size" in blocked_by:
            return "collect_more_data"
        
        if "confidence_below_threshold" in blocked_by:
            return "improve_model_confidence"
        
        if "cooldown_active" in blocked_by:
            # Encontra o resultado do cooldown para tempo restante
            for r in results:
                if r.gate_type == GateType.COOLDOWN and r.details:
                    remaining = r.details.get("hours_remaining")
                    if remaining:
                        return f"wait_{remaining:.1f}_hours"
            return "wait_cooldown_period"
        
        if "max_actions_per_day_reached" in blocked_by:
            return "wait_until_tomorrow_or_manual_override"
        
        return "review_block_conditions"


def evaluate_safety_gates(context: dict[str, Any]) -> SafetyGateResult:
    """
    Função utilitária para avaliar safety gates.
    
    Args:
        context: Dicionário com informações do segmento e decisão
        
    Returns:
        SafetyGateResult com a decisão consolidada
    """
    engine = SafetyGateEngine()
    return engine.evaluate(context)
