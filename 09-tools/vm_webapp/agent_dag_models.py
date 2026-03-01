"""
Models for Agent DAG - v22 Multi-Agent Orchestrator
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DagStatus(str, Enum):
    """Status do DAG."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class NodeStatus(str, Enum):
    """Status de um nó no DAG."""
    PENDING = "pending"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    HANDOFF_FAILED = "handoff_failed"


class RiskLevel(str, Enum):
    """Nível de risco para aprovação."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DagNode:
    """Um nó no DAG representa uma tarefa de agente."""
    node_id: str
    task_type: str  # e.g., "research", "write", "review", "execute"
    params: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    retry_policy: dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 3,
        "timeout_min": 15,
        "backoff_base_sec": 5,
    })
    depends_on: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.node_id:
            raise ValueError("node_id is required")
        if not self.task_type:
            raise ValueError("task_type is required")


@dataclass
class DagEdge:
    """Uma aresta no DAG representa dependência entre nós."""
    from_node: str
    to_node: str
    condition: Optional[str] = None  # Condição opcional para seguir esta aresta


@dataclass
class AgentDag:
    """Representação de um DAG de agentes."""
    dag_id: str
    nodes: list[DagNode]
    edges: list[DagEdge]
    status: DagStatus = DagStatus.PENDING
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.dag_id:
            raise ValueError("dag_id is required")


@dataclass
class DagNodeState:
    """Estado de execução de um nó em uma run."""
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    output: Optional[dict[str, Any]] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


@dataclass
class DagRun:
    """Uma execução instanciada de um DAG."""
    run_id: str
    dag_id: str
    brand_id: str
    project_id: str
    status: DagStatus = DagStatus.PENDING
    node_states: dict[str, DagNodeState] = field(default_factory=dict)
    started_at: str = field(default_factory=_now_iso)
    completed_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.run_id:
            raise ValueError("run_id is required")


@dataclass
class DagApprovalRequest:
    """Pedido de aprovação para um nó."""
    request_id: str
    run_id: str
    node_id: str
    risk_level: RiskLevel
    requested_at: str = field(default_factory=_now_iso)
    status: str = "pending"  # pending, granted, rejected, escalated
    granted_by: Optional[str] = None
    granted_at: Optional[str] = None
    reason: Optional[str] = None
