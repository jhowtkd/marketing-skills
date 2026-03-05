"""Motor de decisão/promote/rollback para Auto-Rollout.

v45: Implementa o motor de decisão automática para rollout de experimentos
de onboarding com gates de qualidade, rollback automático e persistência.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# Configuração de logging
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class RolloutMode(str, Enum):
    """Modos de operação do rollout."""
    AUTO = "auto"
    SUPERVISED = "supervised"
    MANUAL = "manual"


class GateName(str, Enum):
    """Nomes dos gates de promoção."""
    GAIN = "gain_gate"
    STABILITY = "stability_gate"
    RISK = "risk_gate"
    ABANDONMENT = "abandonment_gate"
    REGRESSION = "regression_gate"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class BenchmarkMetrics:
    """Métricas de benchmark para avaliação de variantes.
    
    Attributes:
        ttfv: Time To First Value (em segundos)
        completion_rate: Taxa de conclusão (0-1)
        abandonment_rate: Taxa de abandono (0-1)
        score: Score composto da variante
        sample_size: Tamanho da amostra
    """
    ttfv: float
    completion_rate: float
    abandonment_rate: float
    score: float
    sample_size: int


@dataclass
class PromotionResult:
    """Resultado de uma avaliação de promoção.
    
    Attributes:
        success: Se a promoção foi aprovada
        variant_id: ID da variante avaliada
        gates_passed: Lista de gates que passaram
        gates_failed: Lista de gates que falharam
        reason: Razão da decisão
    """
    success: bool
    variant_id: str
    gates_passed: list[str] = field(default_factory=list)
    gates_failed: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class RolloutPolicy:
    """Política de rollout para um experimento.
    
    Attributes:
        experiment_id: ID do experimento
        active_variant: Variante ativa atualmente
        rollout_mode: Modo de operação do rollout
        last_evaluation: Timestamp da última avaliação
        decision_reason: Razão da última decisão
        rollback_target: Variante de fallback para rollback
    """
    experiment_id: str
    active_variant: str = "control"
    rollout_mode: RolloutMode = RolloutMode.AUTO
    last_evaluation: Optional[str] = None
    decision_reason: str = ""
    rollback_target: str = "control"


@dataclass
class RollbackDecision:
    """Resultado de uma avaliação de rollback.
    
    Attributes:
        should_rollback: Se deve executar rollback
        reason: Razão do rollback
        from_variant: Variante atual
        to_variant: Variante de destino
    """
    should_rollback: bool
    reason: str
    from_variant: str
    to_variant: str


# =============================================================================
# GATE THRESHOLDS
# =============================================================================

# Thresholds configuráveis para os gates
GATE_THRESHOLDS = {
    GateName.GAIN: 1.005,        # 0.5% de ganho mínimo
    GateName.STABILITY: 30,      # Mínimo 30 amostras
    GateName.RISK: 0.95,         # 95% do completion do controle
    GateName.ABANDONMENT: 1.10,  # 10% acima do abandono do controle
    GateName.REGRESSION: 1.10,   # 10% acima do TTFV do controle
}


# =============================================================================
# PROMOTION ENGINE
# =============================================================================

def check_promotion_gates(
    control_metrics: BenchmarkMetrics,
    variant_metrics: BenchmarkMetrics,
    thresholds: Optional[dict[str, float]] = None,
) -> dict[str, bool]:
    """Verifica todos os gates de promoção.
    
    Args:
        control_metrics: Métricas do grupo controle
        variant_metrics: Métricas da variante candidata
        thresholds: Thresholds customizados (opcional)
        
    Returns:
        Dict com resultado de cada gate
        
    Gates:
        * gain_gate: variant.score > control.score * 1.005
        * stability_gate: variant.sample_size >= 30
        * risk_gate: variant.completion >= control.completion * 0.95
        * abandonment_gate: variant.abandonment <= control.abandonment * 1.10
        * regression_gate: variant.ttfv <= control.ttfv * 1.10
    """
    if thresholds is None:
        thresholds = GATE_THRESHOLDS
    
    gates = {}
    
    # Gain gate: variante deve ter score pelo menos 0.5% maior
    gates[GateName.GAIN] = (
        variant_metrics.score > control_metrics.score * thresholds[GateName.GAIN]
    )
    
    # Stability gate: amostra suficiente para confiança estatística
    gates[GateName.STABILITY] = (
        variant_metrics.sample_size >= thresholds[GateName.STABILITY]
    )
    
    # Risk gate: completion rate não deve cair mais que 5%
    gates[GateName.RISK] = (
        variant_metrics.completion_rate >= control_metrics.completion_rate * thresholds[GateName.RISK]
    )
    
    # Abandonment gate: abandono não deve subir mais que 10%
    gates[GateName.ABANDONMENT] = (
        variant_metrics.abandonment_rate <= control_metrics.abandonment_rate * thresholds[GateName.ABANDONMENT]
    )
    
    # Regression gate: TTFV não deve subir mais que 10%
    gates[GateName.REGRESSION] = (
        variant_metrics.ttfv <= control_metrics.ttfv * thresholds[GateName.REGRESSION]
    )
    
    return gates


def evaluate_promotion(
    experiment_id: str,
    benchmark_results: dict[str, BenchmarkMetrics],
    variant_id: Optional[str] = None,
    thresholds: Optional[dict[str, float]] = None,
) -> PromotionResult:
    """Avalia se uma variante pode ser promovida.
    
    Args:
        experiment_id: ID do experimento
        benchmark_results: Dict com métricas de cada variante
        variant_id: ID da variante a avaliar (default: procura a não-control)
        thresholds: Thresholds customizados (opcional)
        
    Returns:
        PromotionResult com resultado da avaliação
    """
    # Validação de entrada
    if "control" not in benchmark_results:
        return PromotionResult(
            success=False,
            variant_id=variant_id or "unknown",
            reason="Missing control metrics in benchmark results",
        )
    
    control_metrics = benchmark_results["control"]
    
    # Determina variante candidata
    if variant_id is None:
        candidates = [v for v in benchmark_results.keys() if v != "control"]
        if not candidates:
            return PromotionResult(
                success=False,
                variant_id="unknown",
                reason="No variant candidates found (only control present)",
            )
        variant_id = candidates[0]
    
    if variant_id not in benchmark_results:
        return PromotionResult(
            success=False,
            variant_id=variant_id,
            reason=f"Variant '{variant_id}' not found in benchmark results",
        )
    
    variant_metrics = benchmark_results[variant_id]
    
    # Verifica gates
    gates = check_promotion_gates(control_metrics, variant_metrics, thresholds)
    
    gates_passed = [name for name, passed in gates.items() if passed]
    gates_failed = [name for name, passed in gates.items() if not passed]
    
    # Sucesso se todos os gates passarem
    success = len(gates_failed) == 0
    
    # Constrói razão da decisão
    if success:
        reason = f"All {len(gates_passed)} gates passed for variant '{variant_id}'"
    else:
        reason = f"Failed gates: {', '.join(gates_failed)}"
    
    result = PromotionResult(
        success=success,
        variant_id=variant_id,
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        reason=reason,
    )
    
    # Log da decisão
    log_promotion_decision(result)
    
    return result


# =============================================================================
# ROLLBACK ENGINE
# =============================================================================

def check_rollback_conditions(
    current_metrics: BenchmarkMetrics,
    new_metrics: BenchmarkMetrics,
    current_policy: Optional[RolloutPolicy] = None,
) -> bool:
    """Verifica se condições de rollback foram atingidas.
    
    Args:
        current_metrics: Métricas baselines (quando foi promovida)
        new_metrics: Métricas atuais
        current_policy: Política atual (para contexto adicional)
        
    Returns:
        True se deve executar rollback
        
    Condições de rollback:
        * Score caiu mais que 10%
        * Completion rate caiu mais que 15%
        * Abandonment subiu mais que 20%
        * TTFV subiu mais que 25%
    """
    # Score degradation > 10%
    if new_metrics.score < current_metrics.score * 0.90:
        return True
    
    # Completion rate degradation > 15%
    if new_metrics.completion_rate < current_metrics.completion_rate * 0.85:
        return True
    
    # Abandonment spike > 20%
    if new_metrics.abandonment_rate > current_metrics.abandonment_rate * 1.20:
        return True
    
    # TTFV regression > 25%
    if new_metrics.ttfv > current_metrics.ttfv * 1.25:
        return True
    
    return False


def evaluate_rollback(
    current_policy: RolloutPolicy,
    new_benchmark: dict[str, BenchmarkMetrics],
) -> RollbackDecision:
    """Avalia se deve executar rollback.
    
    Args:
        current_policy: Política de rollout atual
        new_benchmark: Novas métricas de benchmark
        
    Returns:
        RollbackDecision com decisão e razão
    """
    active_variant = current_policy.active_variant
    
    # Se já está no control, não há rollback necessário
    if active_variant == "control":
        return RollbackDecision(
            should_rollback=False,
            reason="Already on control variant, no rollback needed",
            from_variant="control",
            to_variant="control",
        )
    
    # Precisa de métricas da variante ativa
    if active_variant not in new_benchmark:
        return RollbackDecision(
            should_rollback=False,
            reason=f"No metrics available for active variant '{active_variant}'",
            from_variant=active_variant,
            to_variant=current_policy.rollback_target,
        )
    
    # Para comparar, precisamos das métricas do momento da promoção
    # Em produção, isso viria do histórico de políticas
    # Aqui usamos uma heurística: se control existe no benchmark, usamos como baseline
    if "control" in new_benchmark:
        baseline_metrics = new_benchmark["control"]
        current_metrics = new_benchmark[active_variant]
        
        if check_rollback_conditions(baseline_metrics, current_metrics, current_policy):
            return RollbackDecision(
                should_rollback=True,
                reason=f"Degradation detected in variant '{active_variant}'",
                from_variant=active_variant,
                to_variant=current_policy.rollback_target,
            )
    
    return RollbackDecision(
        should_rollback=False,
        reason=f"No degradation detected, keeping variant '{active_variant}'",
        from_variant=active_variant,
        to_variant=current_policy.rollback_target,
    )


def rollback(
    experiment_id: str,
    target_variant: Optional[str] = None,
    reason: str = "Manual rollback",
) -> RolloutPolicy:
    """Executa rollback para uma variante segura.
    
    Args:
        experiment_id: ID do experimento
        target_variant: Variante de destino (default: control)
        reason: Razão do rollback
        
    Returns:
        RolloutPolicy atualizada
    """
    policy = load_policy(experiment_id)
    
    from_variant = policy.active_variant
    to_variant = target_variant or policy.rollback_target or "control"
    
    # Executa rollback
    policy.active_variant = to_variant
    policy.last_evaluation = datetime.now(timezone.utc).isoformat()
    policy.decision_reason = reason
    
    # Salva política atualizada
    save_policy(policy)
    
    # Log do rollback
    log_rollback_decision(experiment_id, from_variant, to_variant, reason)
    
    logger.info(f"Rollback executed: {from_variant} -> {to_variant} for {experiment_id}")
    
    return policy


# =============================================================================
# POLICY PERSISTENCE
# =============================================================================

def _get_config_dir() -> Path:
    """Retorna diretório de configuração das políticas."""
    base_dir = Path(__file__).parent.parent
    config_dir = base_dir / "config" / "rollout_policies"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _policy_file_path(experiment_id: str) -> Path:
    """Retorna path do arquivo de política."""
    return _get_config_dir() / f"{experiment_id}.json"


def load_policy(experiment_id: str) -> RolloutPolicy:
    """Carrega política de rollout do disco.
    
    Args:
        experiment_id: ID do experimento
        
    Returns:
        RolloutPolicy (cria default se não existir)
    """
    policy_file = _policy_file_path(experiment_id)
    
    if policy_file.exists():
        try:
            with open(policy_file, "r") as f:
                data = json.load(f)
            
            # Converte string para enum
            if "rollout_mode" in data and isinstance(data["rollout_mode"], str):
                data["rollout_mode"] = RolloutMode(data["rollout_mode"])
            
            return RolloutPolicy(**data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Failed to load policy for {experiment_id}: {e}")
    
    # Retorna política padrão
    return RolloutPolicy(
        experiment_id=experiment_id,
        active_variant="control",
        rollout_mode=RolloutMode.AUTO,
        rollback_target="control",
    )


def save_policy(policy: RolloutPolicy) -> None:
    """Salva política de rollout no disco.
    
    Args:
        policy: Política a salvar
    """
    policy_file = _policy_file_path(policy.experiment_id)
    
    data = asdict(policy)
    # Converte enum para string
    if isinstance(data["rollout_mode"], RolloutMode):
        data["rollout_mode"] = data["rollout_mode"].value
    
    with open(policy_file, "w") as f:
        json.dump(data, f, indent=2)
    
    logger.debug(f"Policy saved for {policy.experiment_id}")


def list_active_policies() -> list[RolloutPolicy]:
    """Lista todas as políticas ativas.
    
    Returns:
        Lista de políticas ativas
    """
    config_dir = _get_config_dir()
    policies = []
    
    if not config_dir.exists():
        return policies
    
    for policy_file in config_dir.glob("*.json"):
        experiment_id = policy_file.stem
        try:
            policy = load_policy(experiment_id)
            policies.append(policy)
        except Exception as e:
            logger.warning(f"Failed to load policy from {policy_file}: {e}")
    
    return policies


def delete_policy(experiment_id: str) -> bool:
    """Remove uma política.
    
    Args:
        experiment_id: ID do experimento
        
    Returns:
        True se foi removida com sucesso
    """
    policy_file = _policy_file_path(experiment_id)
    
    if policy_file.exists():
        policy_file.unlink()
        logger.info(f"Policy deleted for {experiment_id}")
        return True
    
    return False


# =============================================================================
# TELEMETRY
# =============================================================================

# Métricas em memória para telemetria
_telemetry_logs: list[dict[str, Any]] = []
_telemetry_enabled = True


def log_promotion_decision(result: PromotionResult) -> None:
    """Loga uma decisão de promoção.
    
    Args:
        result: Resultado da promoção
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "promotion",
        "success": result.success,
        "variant_id": result.variant_id,
        "gates_passed": result.gates_passed,
        "gates_failed": result.gates_failed,
        "reason": result.reason,
    }
    
    _telemetry_logs.append(log_entry)
    
    if result.success:
        logger.info(f"Promotion approved for {result.variant_id}: {result.reason}")
    else:
        logger.warning(f"Promotion blocked for {result.variant_id}: {result.reason}")


def log_rollback_decision(
    experiment_id: str,
    from_variant: str,
    to_variant: str,
    reason: str,
) -> None:
    """Loga uma decisão de rollback.
    
    Args:
        experiment_id: ID do experimento
        from_variant: Variante de origem
        to_variant: Variante de destino
        reason: Razão do rollback
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "rollback",
        "experiment_id": experiment_id,
        "from_variant": from_variant,
        "to_variant": to_variant,
        "reason": reason,
    }
    
    _telemetry_logs.append(log_entry)
    
    logger.warning(f"Rollback for {experiment_id}: {from_variant} -> {to_variant}, reason: {reason}")


def get_telemetry_logs(
    log_type: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Retorna logs de telemetria.
    
    Args:
        log_type: Filtrar por tipo ('promotion' ou 'rollback')
        limit: Limite de logs a retornar
        
    Returns:
        Lista de logs
    """
    logs = _telemetry_logs
    
    if log_type:
        logs = [log for log in logs if log.get("type") == log_type]
    
    return logs[-limit:]


def clear_telemetry_logs() -> None:
    """Limpa todos os logs de telemetria."""
    global _telemetry_logs
    _telemetry_logs = []


# =============================================================================
# AUTO-ROLLOUT ORCHESTRATOR
# =============================================================================

def run_auto_rollout(
    experiment_id: str,
    benchmark_results: dict[str, BenchmarkMetrics],
) -> tuple[PromotionResult | None, RollbackDecision | None]:
    """Executa ciclo completo de auto-rollout.
    
    Args:
        experiment_id: ID do experimento
        benchmark_results: Métricas de benchmark
        
    Returns:
        Tupla com (PromotionResult, RollbackDecision) - um pode ser None
    """
    policy = load_policy(experiment_id)
    
    promotion_result = None
    rollback_decision = None
    
    # Se estamos no control, avalia promoção
    if policy.active_variant == "control":
        promotion_result = evaluate_promotion(experiment_id, benchmark_results)
        
        if promotion_result.success:
            # Promove variante
            new_variant = promotion_result.variant_id
            policy.active_variant = new_variant
            policy.last_evaluation = datetime.now(timezone.utc).isoformat()
            policy.decision_reason = promotion_result.reason
            save_policy(policy)
    else:
        # Já temos uma variante ativa, avalia rollback
        rollback_decision = evaluate_rollback(policy, benchmark_results)
        
        if rollback_decision.should_rollback:
            rollback(
                experiment_id,
                rollback_decision.to_variant,
                rollback_decision.reason,
            )
    
    return promotion_result, rollback_decision


def reset_policy(experiment_id: str) -> RolloutPolicy:
    """Reseta política para estado inicial.
    
    Args:
        experiment_id: ID do experimento
        
    Returns:
        Nova política padrão
    """
    policy = RolloutPolicy(
        experiment_id=experiment_id,
        active_variant="control",
        rollout_mode=RolloutMode.AUTO,
        rollback_target="control",
        last_evaluation=datetime.now(timezone.utc).isoformat(),
        decision_reason="Policy reset to default",
    )
    save_policy(policy)
    return policy


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "RolloutMode",
    "GateName",
    # Data structures
    "BenchmarkMetrics",
    "PromotionResult",
    "RolloutPolicy",
    "RollbackDecision",
    # Promotion Engine
    "check_promotion_gates",
    "evaluate_promotion",
    # Rollback Engine
    "check_rollback_conditions",
    "evaluate_rollback",
    "rollback",
    # Policy Persistence
    "load_policy",
    "save_policy",
    "list_active_policies",
    "delete_policy",
    "reset_policy",
    # Telemetry
    "log_promotion_decision",
    "log_rollback_decision",
    "get_telemetry_logs",
    "clear_telemetry_logs",
    # Orchestrator
    "run_auto_rollout",
    # Constants
    "GATE_THRESHOLDS",
]
