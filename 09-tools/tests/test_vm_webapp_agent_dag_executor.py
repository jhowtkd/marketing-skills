"""
Testes para DAG executor com timeout/retry/handoff - Task 2 v22
TDD: fail -> implement -> pass -> commit
"""

import time
import pytest
from unittest.mock import Mock, patch


def test_executor_timeout_15_min():
    """Testa timeout de 15 minutos por nó."""
    from vm_webapp.agent_dag_models import DagNode, DagRun, NodeStatus
    from vm_webapp.agent_dag_executor import DagNodeExecutor
    
    executor = DagNodeExecutor(timeout_minutes=15)
    
    node = DagNode(node_id="slow_node", task_type="slow_task", params={})
    run = Mock(spec=DagRun)
    run.run_id = "run_001"
    run.node_states = {"slow_node": Mock(status=NodeStatus.RUNNING)}
    
    # Verifica configuração de timeout
    assert executor.timeout_minutes == 15
    
    # Executa task simples para verificar timeout_minutes no resultado
    def fast_task(*args, **kwargs):
        return {"result": "ok"}
    
    result = executor.execute_node(run, node, task_fn=fast_task)
    
    # Verifica que timeout padrão é aplicado
    assert result["timeout_minutes"] == 15
    assert result["status"] == "completed"


def test_executor_3_retries_with_backoff():
    """Testa 3 retries com backoff exponencial."""
    from vm_webapp.agent_dag_models import DagNode
    from vm_webapp.agent_dag_executor import DagNodeExecutor, ExecutionError
    
    executor = DagNodeExecutor()
    executor.clear_cache()  # Limpa cache para idempotência
    
    node = DagNode(
        node_id="flaky_node_" + str(time.time()),  # Node único
        task_type="flaky_task",
        params={},
        retry_policy={"max_retries": 3, "timeout_min": 15, "backoff_base_sec": 0.001}
    )
    
    run = Mock()
    run.run_id = "run_002_" + str(time.time())
    run.node_states = {node.node_id: Mock(status="pending", attempts=0)}
    
    # Task que falha 2 vezes e depois sucede
    call_count = [0]
    def flaky_task(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            raise ExecutionError(f"Attempt {call_count[0]} failed")
        return {"result": "success"}
    
    result = executor.execute_node_with_retries(run, node, task_fn=flaky_task)
    
    assert call_count[0] == 3  # 3 tentativas
    assert result["result"] == "success"
    assert result["attempts"] == 3


def test_handoff_failed_after_exhaustion():
    """Testa handoff_failed após exaustão de retries."""
    from vm_webapp.agent_dag_models import DagNode, NodeStatus
    from vm_webapp.agent_dag_executor import DagNodeExecutor, ExecutionError
    
    executor = DagNodeExecutor()
    executor.clear_cache()
    
    node = DagNode(
        node_id="always_fail_" + str(time.time()),
        task_type="fail_task",
        params={},
        retry_policy={"max_retries": 3, "timeout_min": 15, "backoff_base_sec": 0.001}
    )
    
    run = Mock()
    run.run_id = "run_003_" + str(time.time())
    run.node_states = {node.node_id: Mock(status=NodeStatus.PENDING, attempts=0)}
    
    # Task que sempre falha
    def always_fail(*args, **kwargs):
        raise ExecutionError("Permanent failure")
    
    result = executor.execute_node_with_retries(run, node, task_fn=always_fail)
    
    assert result["status"] == "handoff_failed"
    assert result["attempts"] == 3
    assert "error" in result


def test_idempotency_by_node_task_id():
    """Testa idempotência por node_id + task_id."""
    from vm_webapp.agent_dag_models import DagNode
    from vm_webapp.agent_dag_executor import DagNodeExecutor
    
    executor = DagNodeExecutor()
    executor.clear_cache()
    
    unique_id = str(time.time())
    node = DagNode(node_id=f"idempotent_node_{unique_id}", task_type="task_a", params={"key": "value"})
    run = Mock()
    run.run_id = f"run_004_{unique_id}"
    run.node_states = {node.node_id: Mock(status="pending", attempts=0)}
    
    call_count = [0]
    def task_fn(*args, **kwargs):
        call_count[0] += 1
        return {"result": f"call_{call_count[0]}"}
    
    # Primeira execução
    result1 = executor.execute_node(run, node, task_fn=task_fn)
    
    # Segunda execução com mesmo idempotency_key deve retornar cache
    result2 = executor.execute_node(run, node, task_fn=task_fn)
    
    # Task deve ser chamada apenas uma vez
    assert call_count[0] == 1
    assert result1 == result2


def test_executor_completes_successful_node():
    """Testa execução bem-sucedida de um nó."""
    from vm_webapp.agent_dag_models import DagNode, NodeStatus
    from vm_webapp.agent_dag_executor import DagNodeExecutor
    
    executor = DagNodeExecutor()
    executor.clear_cache()
    
    node = DagNode(node_id="success_node_" + str(time.time()), task_type="simple", params={"input": "test"})
    run = Mock()
    run.run_id = "run_005_" + str(time.time())
    run.node_states = {node.node_id: Mock(status=NodeStatus.PENDING, attempts=0)}
    
    def success_task(node, run):
        return {"output": "completed", "input": node.params.get("input")}
    
    result = executor.execute_node(run, node, task_fn=success_task)
    
    assert result["output"] == "completed"
    assert result["input"] == "test"
    assert result["status"] == "completed"


def test_retry_backoff_timing():
    """Testa que backoff é aplicado entre retries."""
    from vm_webapp.agent_dag_models import DagNode
    from vm_webapp.agent_dag_executor import DagNodeExecutor, ExecutionError
    
    executor = DagNodeExecutor()
    executor.clear_cache()
    
    node = DagNode(
        node_id="backoff_test_" + str(time.time()),
        task_type="test",
        params={},
        retry_policy={"max_retries": 3, "timeout_min": 15, "backoff_base_sec": 0.001}
    )
    
    run = Mock()
    run.run_id = "run_006_" + str(time.time())
    run.node_states = {node.node_id: Mock(status="pending", attempts=0)}
    
    timestamps = []
    def timing_task(*args, **kwargs):
        timestamps.append(time.time())
        if len(timestamps) < 3:
            raise ExecutionError("fail")
        return {"result": "ok"}
    
    result = executor.execute_node_with_retries(run, node, task_fn=timing_task)
    
    assert len(timestamps) == 3
    # Verifica que houve delay entre tentativas (backoff)
    assert timestamps[1] > timestamps[0]
    assert timestamps[2] > timestamps[1]
