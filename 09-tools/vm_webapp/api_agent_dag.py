"""
API v2 DAG Operations Endpoints - v22 Multi-Agent Orchestrator
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from vm_webapp.agent_dag import DagPlanner
from vm_webapp.agent_dag_models import (
    AgentDag,
    DagEdge,
    DagNode,
    DagRun,
    DagStatus,
    NodeStatus,
    RiskLevel,
)
from vm_webapp.agent_dag_supervisor import DagSupervisor


router = APIRouter()

# In-memory storage para testes (em produção, seria no banco)
_dag_store: dict[str, AgentDag] = {}
_run_store: dict[str, DagRun] = {}
_supervisor = DagSupervisor()


# Pydantic models para requests/responses

class DagNodeInput(BaseModel):
    node_id: str
    task_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    retry_policy: dict[str, Any] = Field(default_factory=dict)


class DagEdgeInput(BaseModel):
    from_node: str
    to_node: str


class CreateDagRunRequest(BaseModel):
    dag_id: str
    brand_id: str
    project_id: str
    nodes: list[DagNodeInput]
    edges: list[DagEdgeInput]
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateDagRunResponse(BaseModel):
    run_id: str
    dag_id: str
    brand_id: str
    project_id: str
    status: str
    node_states: dict[str, dict[str, Any]]


class DagRunResponse(BaseModel):
    run_id: str
    dag_id: str
    brand_id: str
    project_id: str
    status: str
    node_states: dict[str, dict[str, Any]]
    started_at: str
    completed_at: Optional[str] = None


class StatusResponse(BaseModel):
    run_id: str
    status: str


class RetryNodeResponse(BaseModel):
    run_id: str
    node_id: str
    status: str
    message: str


class ApprovalRequestResponse(BaseModel):
    request_id: str
    run_id: str
    node_id: str
    status: str
    risk_level: str


class GrantApprovalRequest(BaseModel):
    granted_by: str


class RejectApprovalRequest(BaseModel):
    rejected_by: str
    reason: str


class GrantApprovalResponse(BaseModel):
    request_id: str
    status: str
    granted_by: str
    granted_at: str


class RejectApprovalResponse(BaseModel):
    request_id: str
    status: str
    rejected_by: str
    reason: str


# Helper functions

def _node_input_to_model(node: DagNodeInput) -> DagNode:
    """Converte input Pydantic para modelo."""
    retry_policy = node.retry_policy or {
        "max_retries": 3,
        "timeout_min": 15,
        "backoff_base_sec": 5,
    }
    return DagNode(
        node_id=node.node_id,
        task_type=node.task_type,
        params=node.params,
        risk_level=RiskLevel(node.risk_level),
        retry_policy=retry_policy,
    )


def _run_to_response(run: DagRun) -> dict[str, Any]:
    """Converte DagRun para resposta dict."""
    return {
        "run_id": run.run_id,
        "dag_id": run.dag_id,
        "brand_id": run.brand_id,
        "project_id": run.project_id,
        "status": run.status.value if isinstance(run.status, DagStatus) else run.status,
        "node_states": {
            node_id: {
                "node_id": state.node_id,
                "status": state.status.value if isinstance(state.status, NodeStatus) else state.status,
                "attempts": state.attempts,
                "started_at": state.started_at,
                "completed_at": state.completed_at,
                "error": state.error,
            }
            for node_id, state in run.node_states.items()
        },
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


# API Endpoints

@router.post("/api/v2/dag/run", response_model=CreateDagRunResponse)
def create_dag_run(request: CreateDagRunRequest) -> dict[str, Any]:
    """Cria uma nova execução de DAG."""
    planner = DagPlanner()
    
    # Converte inputs para modelos
    nodes = [_node_input_to_model(n) for n in request.nodes]
    edges = [DagEdge(from_node=e.from_node, to_node=e.to_node) for e in request.edges]
    
    # Cria o DAG
    dag = planner.create_dag(
        dag_id=request.dag_id,
        nodes=nodes,
        edges=edges,
        metadata=request.metadata,
    )
    
    # Armazena o DAG
    _dag_store[request.dag_id] = dag
    
    # Cria a run
    run = planner.create_run(
        dag=dag,
        brand_id=request.brand_id,
        project_id=request.project_id,
    )
    
    # Armazena a run
    _run_store[run.run_id] = run
    
    return _run_to_response(run)


@router.get("/api/v2/dag/run/{run_id}", response_model=DagRunResponse)
def get_dag_run(run_id: str) -> dict[str, Any]:
    """Retorna detalhes de uma execução de DAG."""
    if run_id not in _run_store:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    return _run_to_response(_run_store[run_id])


@router.post("/api/v2/dag/run/{run_id}/pause", response_model=StatusResponse)
def pause_dag_run(run_id: str) -> dict[str, Any]:
    """Pausa uma execução de DAG."""
    if run_id not in _run_store:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    run = _run_store[run_id]
    
    if run.status == DagStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot pause completed run")
    
    run.status = DagStatus.PAUSED
    
    return {"run_id": run_id, "status": "paused"}


@router.post("/api/v2/dag/run/{run_id}/resume", response_model=StatusResponse)
def resume_dag_run(run_id: str) -> dict[str, Any]:
    """Retoma uma execução de DAG pausada."""
    if run_id not in _run_store:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    run = _run_store[run_id]
    
    if run.status != DagStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Run is not paused")
    
    run.status = DagStatus.RUNNING
    
    return {"run_id": run_id, "status": "running"}


@router.post("/api/v2/dag/run/{run_id}/abort", response_model=StatusResponse)
def abort_dag_run(run_id: str) -> dict[str, Any]:
    """Aborta uma execução de DAG."""
    if run_id not in _run_store:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    run = _run_store[run_id]
    
    if run.status == DagStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot abort completed run")
    
    run.status = DagStatus.ABORTED
    
    return {"run_id": run_id, "status": "aborted"}


@router.post("/api/v2/dag/run/{run_id}/node/{node_id}/retry", response_model=RetryNodeResponse)
def retry_node(run_id: str, node_id: str) -> dict[str, Any]:
    """Reexecuta um nó específico."""
    if run_id not in _run_store:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    run = _run_store[run_id]
    
    if node_id not in run.node_states:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    
    node_state = run.node_states[node_id]
    node_state.attempts = 0
    node_state.status = NodeStatus.PENDING
    node_state.error = None
    
    return {
        "run_id": run_id,
        "node_id": node_id,
        "status": "pending",
        "message": "Node queued for retry",
    }


@router.post("/api/v2/dag/run/{run_id}/node/{node_id}/approve-request", response_model=ApprovalRequestResponse)
def request_node_approval(run_id: str, node_id: str) -> dict[str, Any]:
    """Solicita aprovação para um nó."""
    if run_id not in _run_store:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    run = _run_store[run_id]
    dag = _dag_store.get(run.dag_id)
    
    if not dag:
        raise HTTPException(status_code=404, detail=f"DAG not found: {run.dag_id}")
    
    # Encontra o nó
    node = next((n for n in dag.nodes if n.node_id == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    
    # Cria solicitação de aprovação
    request = _supervisor.request_approval(run, node, requested_by="system")
    
    return {
        "request_id": request["request_id"],
        "run_id": run_id,
        "node_id": node_id,
        "status": "pending",
        "risk_level": request["risk_level"],
    }


@router.post("/api/v2/dag/approval/{request_id}/grant", response_model=GrantApprovalResponse)
def grant_approval(request_id: str, req: GrantApprovalRequest) -> dict[str, Any]:
    """Aprova uma solicitação."""
    try:
        result = _supervisor.grant_approval(request_id, granted_by=req.granted_by)
        return {
            "request_id": request_id,
            "status": "granted",
            "granted_by": result["granted_by"],
            "granted_at": result["granted_at"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v2/dag/approval/{request_id}/reject", response_model=RejectApprovalResponse)
def reject_approval(request_id: str, req: RejectApprovalRequest) -> dict[str, Any]:
    """Rejeita uma solicitação."""
    try:
        result = _supervisor.reject_approval(
            request_id,
            rejected_by=req.rejected_by,
            reason=req.reason,
        )
        return {
            "request_id": request_id,
            "status": "rejected",
            "rejected_by": result["rejected_by"],
            "reason": result["reason"],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/v2/dag/approvals/pending")
def list_pending_approvals(run_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Lista aprovações pendentes."""
    return _supervisor.list_pending_approvals(run_id=run_id)
