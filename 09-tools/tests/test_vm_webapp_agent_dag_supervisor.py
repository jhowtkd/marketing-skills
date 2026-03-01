"""
Testes para DAG supervisor com risco e approvals - Task 3 v22
TDD: fail -> implement -> pass -> commit
"""

import time
import pytest
from unittest.mock import Mock


def test_low_risk_auto_execute():
    """Testa que low-risk executa automaticamente."""
    from vm_webapp.agent_dag_models import DagNode, DagRun, RiskLevel, NodeStatus
    from vm_webapp.agent_dag_supervisor import DagSupervisor
    
    supervisor = DagSupervisor()
    
    node = DagNode(
        node_id="low_risk_node",
        task_type="simple",
        params={},
        risk_level=RiskLevel.LOW
    )
    run = Mock()
    run.run_id = "run_001"
    run.brand_id = "b1"
    
    decision = supervisor.evaluate_node(run, node)
    
    assert decision["action"] == "auto_execute"
    assert decision["risk_level"] == "low"
    assert decision["requires_approval"] == False


def test_medium_high_risk_waiting_approval():
    """Testa que medium/high risk aguarda aprovação."""
    from vm_webapp.agent_dag_models import DagNode, DagRun, RiskLevel
    from vm_webapp.agent_dag_supervisor import DagSupervisor
    
    supervisor = DagSupervisor()
    
    # Medium risk
    node_medium = DagNode(
        node_id="medium_risk_node",
        task_type="important",
        params={},
        risk_level=RiskLevel.MEDIUM
    )
    run = Mock()
    run.run_id = "run_002"
    run.brand_id = "b1"
    
    decision = supervisor.evaluate_node(run, node_medium)
    
    assert decision["action"] == "await_approval"
    assert decision["risk_level"] == "medium"
    assert decision["requires_approval"] == True
    
    # High risk
    node_high = DagNode(
        node_id="high_risk_node",
        task_type="critical",
        params={},
        risk_level=RiskLevel.HIGH
    )
    
    decision = supervisor.evaluate_node(run, node_high)
    
    assert decision["action"] == "await_approval"
    assert decision["risk_level"] == "high"
    assert decision["requires_approval"] == True


def test_grant_reject_by_node():
    """Testa grant/reject por nó específico."""
    from vm_webapp.agent_dag_models import DagNode, DagRun, RiskLevel
    from vm_webapp.agent_dag_supervisor import DagSupervisor
    
    supervisor = DagSupervisor()
    
    node = DagNode(
        node_id="approval_node",
        task_type="important",
        params={},
        risk_level=RiskLevel.HIGH
    )
    run = Mock()
    run.run_id = "run_003"
    run.brand_id = "b1"
    
    # Solicita aprovação
    request = supervisor.request_approval(run, node, requested_by="system")
    
    assert request["run_id"] == "run_003"
    assert request["node_id"] == "approval_node"
    assert request["status"] == "pending"
    
    # Grant approval
    granted = supervisor.grant_approval(request["request_id"], granted_by="admin_001")
    
    assert granted["status"] == "granted"
    assert granted["granted_by"] == "admin_001"
    assert granted["granted_at"] is not None
    
    # Testa rejeição em outro request
    request2 = supervisor.request_approval(run, node, requested_by="system")
    rejected = supervisor.reject_approval(request2["request_id"], rejected_by="admin_002", reason="Risk too high")
    
    assert rejected["status"] == "rejected"
    assert rejected["rejected_by"] == "admin_002"
    assert rejected["reason"] == "Risk too high"


def test_escalation_by_timeout():
    """Testa escalonamento por timeout de aprovação."""
    from vm_webapp.agent_dag_models import DagNode, DagRun, RiskLevel
    from vm_webapp.agent_dag_supervisor import DagSupervisor
    
    # Supervisor com timeout curto para teste
    supervisor = DagSupervisor(approval_timeout_minutes=0.001)  # ~60ms
    
    node = DagNode(
        node_id="timeout_node",
        task_type="important",
        params={},
        risk_level=RiskLevel.HIGH
    )
    run = Mock()
    run.run_id = "run_004"
    run.brand_id = "b1"
    
    # Solicita aprovação
    request = supervisor.request_approval(run, node, requested_by="system")
    
    # Aguarda o timeout
    time.sleep(0.1)
    
    # Verifica escalonamento
    escalated = supervisor.check_escalation(request["request_id"])
    
    assert escalated["status"] == "escalated"
    assert "timeout" in escalated["reason"].lower()


def test_list_pending_approvals():
    """Testa listagem de aprovações pendentes."""
    from vm_webapp.agent_dag_models import DagNode, DagRun, RiskLevel
    from vm_webapp.agent_dag_supervisor import DagSupervisor
    
    supervisor = DagSupervisor()
    
    node1 = DagNode(node_id="node_a", task_type="t1", params={}, risk_level=RiskLevel.HIGH)
    node2 = DagNode(node_id="node_b", task_type="t2", params={}, risk_level=RiskLevel.MEDIUM)
    
    run = Mock()
    run.run_id = "run_005"
    run.brand_id = "b1"
    
    # Cria aprovações
    supervisor.request_approval(run, node1, requested_by="system")
    supervisor.request_approval(run, node2, requested_by="system")
    
    pending = supervisor.list_pending_approvals(run_id="run_005")
    
    assert len(pending) == 2


def test_risk_level_by_task_type():
    """Testa que risk level pode ser inferido do task_type."""
    from vm_webapp.agent_dag_models import DagNode, DagRun, RiskLevel
    from vm_webapp.agent_dag_supervisor import DagSupervisor
    
    supervisor = DagSupervisor()
    
    # Configura mapeamento de task_type para risk_level
    supervisor.set_task_risk_mapping({
        "research": RiskLevel.LOW,
        "write": RiskLevel.MEDIUM,
        "publish": RiskLevel.HIGH,
    })
    
    run = Mock()
    run.run_id = "run_006"
    run.brand_id = "b1"
    
    # Testa research -> low
    node_research = DagNode(node_id="n1", task_type="research", params={})
    decision = supervisor.evaluate_node(run, node_research)
    assert decision["risk_level"] == "low"
    
    # Testa write -> medium
    node_write = DagNode(node_id="n2", task_type="write", params={})
    decision = supervisor.evaluate_node(run, node_write)
    assert decision["risk_level"] == "medium"
    
    # Testa publish -> high
    node_publish = DagNode(node_id="n3", task_type="publish", params={})
    decision = supervisor.evaluate_node(run, node_publish)
    assert decision["risk_level"] == "high"
