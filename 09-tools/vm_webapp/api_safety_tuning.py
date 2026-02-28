"""
VM Studio v17 - Safety Gates Auto-Tuning API Endpoints

Endpoints:
- GET /v2/safety-tuning/status
- POST /v2/safety-tuning/run
- POST /v2/safety-tuning/{proposal_id}/apply
- POST /v2/safety-tuning/{proposal_id}/revert
- POST /v2/safety-tuning/gates/{gate_name}/freeze
- POST /v2/safety-tuning/gates/{gate_name}/unfreeze
- GET /v2/safety-tuning/audit
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vm_webapp.safety_autotuning import (
    GateConfig,
    GatePerformance,
    SafetyAutoTuner,
    AdjustmentProposal,
    RiskLevel,
)
from vm_webapp.safety_autotuning_apply import (
    SafetyTuningApplier,
    ApplyDecision,
    RollbackTrigger,
    RollbackResult,
)

router = APIRouter()

# Instâncias singleton (em produção, usar injeção de dependência)
_auto_tuner: Optional[SafetyAutoTuner] = None
_applier: Optional[SafetyTuningApplier] = None
_audit_log: list[dict] = []


def get_auto_tuner() -> SafetyAutoTuner:
    """Retorna instância do auto-tuner."""
    global _auto_tuner
    if _auto_tuner is None:
        _auto_tuner = SafetyAutoTuner()
    return _auto_tuner


def get_applier() -> SafetyTuningApplier:
    """Retorna instância do applier."""
    global _applier
    if _applier is None:
        _applier = SafetyTuningApplier()
    return _applier


# Schemas Pydantic

class SafetyTuningStatusResponse(BaseModel):
    status: str
    last_cycle_at: Optional[str]
    gates: list[dict]
    frozen_gates: list[str]
    active_canaries: list[str]


class SafetyTuningRunRequest(BaseModel):
    mode: str = "propose"  # "propose" ou "dry-run"


class SafetyTuningRunResponse(BaseModel):
    cycle_id: str
    proposals: list[dict]
    proposals_count: int
    timestamp: str


class SafetyTuningApplyRequest(BaseModel):
    auto: bool = False


class SafetyTuningApplyResponse(BaseModel):
    applied: bool
    proposal_id: str
    decision: str
    previous_value: Optional[float]
    new_value: Optional[float]
    reason: Optional[str]


class SafetyTuningRevertResponse(BaseModel):
    reverted: bool
    proposal_id: str
    restored_value: float
    timestamp: str


class SafetyTuningFreezeRequest(BaseModel):
    reason: str = "manual"


class SafetyTuningFreezeResponse(BaseModel):
    gate_name: str
    frozen: bool
    reason: Optional[str]


class SafetyTuningAuditResponse(BaseModel):
    cycles: list[dict]
    total_cycles: int
    applied_count: int
    rollback_count: int


# Dados simulados para demonstração (em produção, virariam do banco)
_DEFAULT_GATE_CONFIGS = [
    GateConfig(gate_name="sample_size", current_value=100, min_value=50, max_value=500),
    GateConfig(gate_name="confidence_threshold", current_value=0.8, min_value=0.5, max_value=0.95),
    GateConfig(gate_name="cooldown_hours", current_value=4, min_value=1, max_value=24),
    GateConfig(gate_name="max_actions_per_day", current_value=10, min_value=5, max_value=50),
]


@router.get("/v2/safety-tuning/status", response_model=SafetyTuningStatusResponse)
async def get_safety_tuning_status():
    """
    Retorna status atual do sistema de auto-tuning.
    
    Inclui configurações atuais, gates congelados e canaries ativos.
    """
    applier = get_applier()
    
    gates = []
    for config in _DEFAULT_GATE_CONFIGS:
        gates.append({
            "name": config.gate_name,
            "current_value": config.current_value,
            "min_value": config.min_value,
            "max_value": config.max_value,
            "is_frozen": config.gate_name in applier.frozen_gates,
            "is_canary_active": config.gate_name in applier.active_canaries,
        })
    
    # Busca último ciclo do audit log
    last_cycle_at = None
    if _audit_log:
        last_cycle_at = _audit_log[-1].get("timestamp")
    
    return SafetyTuningStatusResponse(
        status="active",
        last_cycle_at=last_cycle_at,
        gates=gates,
        frozen_gates=list(applier.frozen_gates),
        active_canaries=list(applier.active_canaries),
    )


@router.post("/v2/safety-tuning/run", response_model=SafetyTuningRunResponse)
async def run_safety_tuning_cycle(request: SafetyTuningRunRequest):
    """
    Executa um ciclo de análise e proposta de ajustes.
    
    Mode "propose": Analisa e retorna propostas sem aplicar.
    Mode "dry-run": Simula o ciclo sem persistir nada.
    """
    tuner = get_auto_tuner()
    
    # Gera dados de performance simulados para demonstração
    # Em produção, viriam do sistema de métricas
    import random
    performances = []
    for config in _DEFAULT_GATE_CONFIGS:
        performances.append(GatePerformance(
            gate_name=config.gate_name,
            false_positive_blocks=random.randint(5, 25),
            missed_incidents=random.randint(0, 5),
            total_decisions=100,
            approval_without_regen_count=random.randint(40, 60),
        ))
    
    cycle_id = f"cycle-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    
    # Executa análise
    result = tuner.run_cycle(cycle_id, _DEFAULT_GATE_CONFIGS, performances)
    
    # Converte propostas para dict
    proposals = []
    for p in result.proposals:
        proposals.append({
            "proposal_id": f"{cycle_id}-{p.gate_name}",
            "gate_name": p.gate_name,
            "current_value": p.current_value,
            "proposed_value": p.proposed_value,
            "adjustment_percent": p.adjustment_percent,
            "risk_level": p.risk_level.value,
            "reason": p.reason,
            "blocked_by_volume": p.blocked_by_volume,
        })
    
    # Registra no audit log
    _audit_log.append({
        "cycle_id": cycle_id,
        "timestamp": result.timestamp.isoformat(),
        "proposals": proposals,
        "mode": request.mode,
    })
    
    return SafetyTuningRunResponse(
        cycle_id=cycle_id,
        proposals=proposals,
        proposals_count=len(proposals),
        timestamp=result.timestamp.isoformat(),
    )


@router.post("/v2/safety-tuning/{proposal_id}/apply", response_model=SafetyTuningApplyResponse)
async def apply_safety_tuning_proposal(proposal_id: str, request: SafetyTuningApplyRequest):
    """
    Aplica uma proposta de ajuste específica.
    
    Se auto=True, aplica apenas se for low-risk.
    Se auto=False, permite aplicação manual de qualquer risk level.
    """
    applier = get_applier()
    
    # Busca a proposta no audit log
    proposal_data = None
    for entry in _audit_log:
        for p in entry.get("proposals", []):
            if p.get("proposal_id") == proposal_id:
                proposal_data = p
                break
        if proposal_data:
            break
    
    if not proposal_data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Recria o objeto AdjustmentProposal
    proposal = AdjustmentProposal(
        gate_name=proposal_data["gate_name"],
        current_value=proposal_data["current_value"],
        proposed_value=proposal_data["proposed_value"],
        adjustment_percent=proposal_data["adjustment_percent"],
        risk_level=RiskLevel(proposal_data["risk_level"]),
        reason=proposal_data["reason"],
        blocked_by_volume=proposal_data.get("blocked_by_volume", False),
    )
    
    # Aplica a proposta
    result = applier.apply_proposal(proposal, autoapply=request.auto)
    
    # Registra aplicação no audit log
    _audit_log.append({
        "type": "apply",
        "proposal_id": proposal_id,
        "timestamp": result.applied_at.isoformat(),
        "decision": result.decision.value,
        "previous_value": result.previous_value,
        "new_value": result.new_value,
    })
    
    return SafetyTuningApplyResponse(
        applied=result.decision == ApplyDecision.APPLOYED_AUTO,
        proposal_id=proposal_id,
        decision=result.decision.value,
        previous_value=result.previous_value,
        new_value=result.new_value,
        reason=result.reason,
    )


@router.post("/v2/safety-tuning/{proposal_id}/revert", response_model=SafetyTuningRevertResponse)
async def revert_safety_tuning_proposal(proposal_id: str):
    """
    Reverte uma proposta aplicada.
    
    Restaura o valor anterior do gate.
    """
    applier = get_applier()
    
    # Busca a proposta aplicada
    applied = None
    for entry in _audit_log:
        if entry.get("type") == "apply" and entry.get("proposal_id") == proposal_id:
            applied = entry
            break
    
    if not applied:
        raise HTTPException(status_code=404, detail="Applied proposal not found")
    
    previous_value = applied.get("previous_value")
    if previous_value is None:
        raise HTTPException(status_code=400, detail="Cannot revert: previous value not recorded")
    
    # Cria resultado de rollback
    rollback_result = RollbackResult(
        proposal_id=proposal_id,
        trigger=RollbackTrigger.MANUAL,
        rolled_back_at=datetime.now(timezone.utc),
        restored_value=previous_value,
        reason="manual_revert_api",
    )
    
    # Executa rollback
    success = applier.execute_rollback(rollback_result)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to execute rollback")
    
    # Registra no audit log
    _audit_log.append({
        "type": "rollback",
        "proposal_id": proposal_id,
        "timestamp": rollback_result.rolled_back_at.isoformat(),
        "restored_value": rollback_result.restored_value,
        "trigger": rollback_result.trigger.value,
    })
    
    return SafetyTuningRevertResponse(
        reverted=True,
        proposal_id=proposal_id,
        restored_value=rollback_result.restored_value,
        timestamp=rollback_result.rolled_back_at.isoformat(),
    )


@router.post("/v2/safety-tuning/gates/{gate_name}/freeze", response_model=SafetyTuningFreezeResponse)
async def freeze_safety_gate(gate_name: str, request: SafetyTuningFreezeRequest):
    """
    Congela um gate para prevenir ajustes automáticos.
    
    Gates congelados não recebem propostas de ajuste.
    """
    applier = get_applier()
    
    # Verifica se gate existe
    valid_gates = [g.gate_name for g in _DEFAULT_GATE_CONFIGS]
    if gate_name not in valid_gates:
        raise HTTPException(status_code=404, detail=f"Gate '{gate_name}' not found")
    
    applier.freeze_gate(gate_name, reason=request.reason)
    
    # Registra no audit log
    _audit_log.append({
        "type": "freeze",
        "gate_name": gate_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": request.reason,
    })
    
    return SafetyTuningFreezeResponse(
        gate_name=gate_name,
        frozen=True,
        reason=request.reason,
    )


@router.post("/v2/safety-tuning/gates/{gate_name}/unfreeze", response_model=SafetyTuningFreezeResponse)
async def unfreeze_safety_gate(gate_name: str):
    """
    Descongela um gate, permitindo ajustes automáticos novamente.
    """
    applier = get_applier()
    
    # Verifica se gate existe
    valid_gates = [g.gate_name for g in _DEFAULT_GATE_CONFIGS]
    if gate_name not in valid_gates:
        raise HTTPException(status_code=404, detail=f"Gate '{gate_name}' not found")
    
    was_frozen = gate_name in applier.frozen_gates
    applier.unfreeze_gate(gate_name)
    
    # Registra no audit log
    if was_frozen:
        _audit_log.append({
            "type": "unfreeze",
            "gate_name": gate_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    return SafetyTuningFreezeResponse(
        gate_name=gate_name,
        frozen=False,
        reason=None,
    )


@router.get("/v2/safety-tuning/audit", response_model=SafetyTuningAuditResponse)
async def get_safety_tuning_audit():
    """
    Retorna trilha de auditoria completa dos ciclos de tuning.
    
    Inclui todos os ciclos, aplicações, rollbacks e operações manuais.
    """
    applied_count = sum(1 for e in _audit_log if e.get("type") == "apply")
    rollback_count = sum(1 for e in _audit_log if e.get("type") == "rollback")
    
    return SafetyTuningAuditResponse(
        cycles=_audit_log,
        total_cycles=len(_audit_log),
        applied_count=applied_count,
        rollback_count=rollback_count,
    )
