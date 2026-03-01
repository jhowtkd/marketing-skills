"""
DAG Supervisor com risco e approvals - v22 Multi-Agent Orchestrator
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from vm_webapp.agent_dag_models import (
    DagNode,
    DagRun,
    RiskLevel,
)


class DagSupervisor:
    """Supervisor para gestão de risco e aprovações em DAGs."""
    
    def __init__(
        self,
        auto_execute_risk_levels: Optional[set[RiskLevel]] = None,
        approval_timeout_minutes: float = 60.0,
    ):
        # Por padrão, low risk executa automaticamente
        self.auto_execute_risk_levels = auto_execute_risk_levels or {RiskLevel.LOW}
        self.approval_timeout_minutes = approval_timeout_minutes
        
        # Mapeamento de task_type para risk_level (sobrescreve node.risk_level)
        self._task_risk_mapping: dict[str, RiskLevel] = {}
        
        # Storage para approval requests
        self._approval_requests: dict[str, dict[str, Any]] = {}
        self._requests_lock = threading.Lock()
    
    def set_task_risk_mapping(self, mapping: dict[str, RiskLevel]) -> None:
        """Configura mapeamento de task_type para risk_level."""
        self._task_risk_mapping.update(mapping)
    
    def evaluate_node(self, run: DagRun, node: DagNode) -> dict[str, Any]:
        """
        Avalia risco de um nó e determina ação necessária.
        
        Args:
            run: Execução do DAG
            node: Nó a ser avaliado
            
        Returns:
            Decisão de execução
        """
        # Determina risk level (do mapeamento ou do nó)
        risk_level = self._task_risk_mapping.get(node.task_type, node.risk_level)
        
        # Decide ação baseada no risk level
        requires_approval = risk_level not in self.auto_execute_risk_levels
        
        if requires_approval:
            return {
                "action": "await_approval",
                "risk_level": risk_level.value,
                "requires_approval": True,
                "node_id": node.node_id,
                "run_id": run.run_id,
                "reason": f"Risk level '{risk_level.value}' requires approval",
            }
        else:
            return {
                "action": "auto_execute",
                "risk_level": risk_level.value,
                "requires_approval": False,
                "node_id": node.node_id,
                "run_id": run.run_id,
            }
    
    def request_approval(
        self,
        run: DagRun,
        node: DagNode,
        requested_by: str = "system",
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Cria pedido de aprovação para um nó.
        
        Args:
            run: Execução do DAG
            node: Nó que precisa de aprovação
            requested_by: Quem solicitou a aprovação
            reason: Motivo da solicitação
            
        Returns:
            Dados da solicitação
        """
        request_id = uuid4().hex[:16]
        risk_level = self._task_risk_mapping.get(node.task_type, node.risk_level)
        
        request = {
            "request_id": request_id,
            "run_id": run.run_id,
            "node_id": node.node_id,
            "brand_id": run.brand_id,
            "risk_level": risk_level.value,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "requested_by": requested_by,
            "reason": reason or f"Approval required for {node.task_type} task",
            "granted_by": None,
            "granted_at": None,
        }
        
        with self._requests_lock:
            self._approval_requests[request_id] = request
        
        return request
    
    def grant_approval(
        self,
        request_id: str,
        granted_by: str,
    ) -> dict[str, Any]:
        """
        Aprova uma solicitação.
        
        Args:
            request_id: ID da solicitação
            granted_by: Quem aprovou
            
        Returns:
            Dados da aprovação atualizada
        """
        with self._requests_lock:
            if request_id not in self._approval_requests:
                raise ValueError(f"Approval request not found: {request_id}")
            
            request = self._approval_requests[request_id]
            
            if request["status"] != "pending":
                raise ValueError(f"Request already {request['status']}")
            
            request["status"] = "granted"
            request["granted_by"] = granted_by
            request["granted_at"] = datetime.now(timezone.utc).isoformat()
            
            return request.copy()
    
    def reject_approval(
        self,
        request_id: str,
        rejected_by: str,
        reason: str,
    ) -> dict[str, Any]:
        """
        Rejeita uma solicitação.
        
        Args:
            request_id: ID da solicitação
            rejected_by: Quem rejeitou
            reason: Motivo da rejeição
            
        Returns:
            Dados da solicitação atualizada
        """
        with self._requests_lock:
            if request_id not in self._approval_requests:
                raise ValueError(f"Approval request not found: {request_id}")
            
            request = self._approval_requests[request_id]
            
            if request["status"] != "pending":
                raise ValueError(f"Request already {request['status']}")
            
            request["status"] = "rejected"
            request["rejected_by"] = rejected_by
            request["rejected_at"] = datetime.now(timezone.utc).isoformat()
            request["reason"] = reason
            
            return request.copy()
    
    def check_escalation(self, request_id: str) -> dict[str, Any]:
        """
        Verifica se solicitação deve ser escalonada por timeout.
        
        Args:
            request_id: ID da solicitação
            
        Returns:
            Dados da solicitação (possivelmente escalonada)
        """
        with self._requests_lock:
            if request_id not in self._approval_requests:
                raise ValueError(f"Approval request not found: {request_id}")
            
            request = self._approval_requests[request_id]
            
            # Só verifica timeout para requests pendentes
            if request["status"] != "pending":
                return request.copy()
            
            # Verifica timeout
            requested_at = datetime.fromisoformat(request["requested_at"])
            timeout_delta = self.approval_timeout_minutes * 60
            elapsed = (datetime.now(timezone.utc) - requested_at).total_seconds()
            
            if elapsed > timeout_delta:
                request["status"] = "escalated"
                request["escalated_at"] = datetime.now(timezone.utc).isoformat()
                request["reason"] = f"Approval timeout after {self.approval_timeout_minutes} minutes"
            
            return request.copy()
    
    def get_approval_request(self, request_id: str) -> Optional[dict[str, Any]]:
        """Retorna uma solicitação pelo ID."""
        with self._requests_lock:
            request = self._approval_requests.get(request_id)
            return request.copy() if request else None
    
    def list_pending_approvals(
        self,
        run_id: Optional[str] = None,
        brand_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Lista solicitações pendentes.
        
        Args:
            run_id: Filtrar por run específica
            brand_id: Filtrar por brand específica
            
        Returns:
            Lista de solicitações pendentes
        """
        with self._requests_lock:
            pending = []
            for request in self._approval_requests.values():
                if request["status"] != "pending":
                    continue
                if run_id and request["run_id"] != run_id:
                    continue
                if brand_id and request.get("brand_id") != brand_id:
                    continue
                pending.append(request.copy())
            return pending
    
    def list_all_approvals(
        self,
        run_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Lista todas as solicitações.
        
        Args:
            run_id: Filtrar por run específica
            status: Filtrar por status
            
        Returns:
            Lista de solicitações
        """
        with self._requests_lock:
            results = []
            for request in self._approval_requests.values():
                if run_id and request["run_id"] != run_id:
                    continue
                if status and request["status"] != status:
                    continue
                results.append(request.copy())
            return results
