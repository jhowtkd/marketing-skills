"""
VM Studio v17 - Safety Tuning Audit Trail

Persistência e auditoria completa dos ciclos de auto-tuning.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional
import json

UTC = timezone.utc


@dataclass
class TuningCycleAuditRecord:
    """Registro de auditoria de um ciclo de tuning."""
    cycle_id: str
    timestamp: str
    mode: str
    proposals: list[dict]
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "TuningCycleAuditRecord":
        """Cria a partir de dicionário."""
        return cls(**data)


@dataclass
class TuningApplyAuditRecord:
    """Registro de auditoria de aplicação de proposta."""
    type: str = "apply"
    proposal_id: Optional[str] = None
    timestamp: Optional[str] = None
    decision: Optional[str] = None
    previous_value: Optional[float] = None
    new_value: Optional[float] = None
    gate_name: Optional[str] = None
    applied_by: Optional[str] = None  # "auto" ou user_id
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return asdict(self)


@dataclass
class TuningRollbackAuditRecord:
    """Registro de auditoria de rollback."""
    type: str = "rollback"
    proposal_id: Optional[str] = None
    timestamp: Optional[str] = None
    restored_value: Optional[float] = None
    trigger: Optional[str] = None  # fp_rate_spike, incidents_increased, manual
    reason: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return asdict(self)


@dataclass
class TuningFreezeAuditRecord:
    """Registro de auditoria de freeze/unfreeze."""
    type: str = "freeze"  # ou "unfreeze"
    gate_name: Optional[str] = None
    timestamp: Optional[str] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return asdict(self)


class SafetyTuningAuditStore:
    """
    Store para auditoria de tuning.
    
    Em produção, persistiria em banco de dados.
    Para MVP, usa armazenamento em memória com opção de export.
    """
    
    def __init__(self):
        self._records: list[dict] = []
    
    def record_cycle(self, cycle_id: str, mode: str, proposals: list[dict]):
        """Registra um ciclo de tuning."""
        record = TuningCycleAuditRecord(
            cycle_id=cycle_id,
            timestamp=datetime.now(UTC).isoformat(),
            mode=mode,
            proposals=proposals
        )
        self._records.append(record.to_dict())
    
    def record_apply(
        self,
        proposal_id: str,
        decision: str,
        previous_value: Optional[float],
        new_value: Optional[float],
        gate_name: Optional[str] = None,
        applied_by: str = "auto"
    ):
        """Registra uma aplicação de proposta."""
        record = TuningApplyAuditRecord(
            proposal_id=proposal_id,
            timestamp=datetime.now(UTC).isoformat(),
            decision=decision,
            previous_value=previous_value,
            new_value=new_value,
            gate_name=gate_name,
            applied_by=applied_by
        )
        self._records.append(record.to_dict())
    
    def record_rollback(
        self,
        proposal_id: str,
        restored_value: float,
        trigger: str,
        reason: Optional[str] = None
    ):
        """Registra um rollback."""
        record = TuningRollbackAuditRecord(
            proposal_id=proposal_id,
            timestamp=datetime.now(UTC).isoformat(),
            restored_value=restored_value,
            trigger=trigger,
            reason=reason
        )
        self._records.append(record.to_dict())
    
    def record_freeze(self, gate_name: str, reason: str):
        """Registra congelamento de gate."""
        record = TuningFreezeAuditRecord(
            type="freeze",
            gate_name=gate_name,
            timestamp=datetime.now(UTC).isoformat(),
            reason=reason
        )
        self._records.append(record.to_dict())
    
    def record_unfreeze(self, gate_name: str):
        """Registra descongelamento de gate."""
        record = TuningFreezeAuditRecord(
            type="unfreeze",
            gate_name=gate_name,
            timestamp=datetime.now(UTC).isoformat(),
            reason=None
        )
        self._records.append(record.to_dict())
    
    def get_all_records(self) -> list[dict]:
        """Retorna todos os registros."""
        return self._records.copy()
    
    def get_cycles(self) -> list[dict]:
        """Retorna apenas registros de ciclos."""
        return [r for r in self._records if "cycle_id" in r and "mode" in r]
    
    def get_applications(self) -> list[dict]:
        """Retorna apenas registros de aplicação."""
        return [r for r in self._records if r.get("type") == "apply"]
    
    def get_rollbacks(self) -> list[dict]:
        """Retorna apenas registros de rollback."""
        return [r for r in self._records if r.get("type") == "rollback"]
    
    def get_by_gate(self, gate_name: str) -> list[dict]:
        """Retorna registros relacionados a um gate específico."""
        return [
            r for r in self._records
            if r.get("gate_name") == gate_name
            or any(p.get("gate_name") == gate_name for p in r.get("proposals", []))
        ]
    
    def export_to_json(self, filepath: str):
        """Exporta todos os registros para JSON."""
        with open(filepath, 'w') as f:
            json.dump(self._records, f, indent=2)
    
    def get_summary(self) -> dict:
        """Retorna resumo das operações."""
        cycles = self.get_cycles()
        applications = self.get_applications()
        rollbacks = self.get_rollbacks()
        
        applied_count = len(applications)
        rollback_count = len(rollbacks)
        
        return {
            "total_cycles": len(cycles),
            "applied_count": applied_count,
            "rollback_count": rollback_count,
            "success_rate": (applied_count - rollback_count) / applied_count if applied_count > 0 else 0.0,
        }


# Instância global (em produção, usar injeção de dependência)
_audit_store: Optional[SafetyTuningAuditStore] = None


def get_audit_store() -> SafetyTuningAuditStore:
    """Retorna instância do audit store."""
    global _audit_store
    if _audit_store is None:
        _audit_store = SafetyTuningAuditStore()
    return _audit_store
