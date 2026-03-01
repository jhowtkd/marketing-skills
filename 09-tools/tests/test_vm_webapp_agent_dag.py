"""
Testes para DAG planner e models - Task 1 v22
TDD: fail -> implement -> pass -> commit
"""

import pytest
from datetime import datetime, timezone


def test_dag_creation_valid():
    """Testa criação de DAG válida com nós e dependências."""
    from vm_webapp.agent_dag_models import DagNode, DagEdge, AgentDag
    from vm_webapp.agent_dag import DagPlanner
    
    planner = DagPlanner()
    
    # Cria nós
    node_a = DagNode(node_id="node_a", task_type="research", params={"topic": "AI"})
    node_b = DagNode(node_id="node_b", task_type="write", params={"format": "md"})
    node_c = DagNode(node_id="node_c", task_type="review", params={"strict": True})
    
    # Cria DAG
    dag = planner.create_dag(
        dag_id="dag_001",
        nodes=[node_a, node_b, node_c],
        edges=[
            DagEdge(from_node="node_a", to_node="node_b"),
            DagEdge(from_node="node_b", to_node="node_c"),
        ]
    )
    
    assert dag.dag_id == "dag_001"
    assert len(dag.nodes) == 3
    assert len(dag.edges) == 2
    assert dag.status == "pending"


def test_topological_sort():
    """Testa ordenação topológica dos nós."""
    from vm_webapp.agent_dag_models import DagNode, DagEdge, AgentDag
    from vm_webapp.agent_dag import DagPlanner
    
    planner = DagPlanner()
    
    # DAG: A -> B -> C, A -> C (diamond shape)
    node_a = DagNode(node_id="a", task_type="start", params={})
    node_b = DagNode(node_id="b", task_type="process", params={})
    node_c = DagNode(node_id="c", task_type="end", params={})
    
    dag = planner.create_dag(
        dag_id="dag_topo",
        nodes=[node_a, node_b, node_c],
        edges=[
            DagEdge(from_node="a", to_node="b"),
            DagEdge(from_node="b", to_node="c"),
        ]
    )
    
    order = planner.topological_sort(dag)
    
    # 'a' deve vir antes de 'b' e 'c'
    # 'b' deve vir antes de 'c'
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")


def test_cycle_detection():
    """Testa detecção de ciclo em DAG."""
    from vm_webapp.agent_dag_models import DagNode, DagEdge, AgentDag
    from vm_webapp.agent_dag import DagPlanner, DagValidationError
    
    planner = DagPlanner()
    
    # Cria ciclo: A -> B -> C -> A
    node_a = DagNode(node_id="a", task_type="start", params={})
    node_b = DagNode(node_id="b", task_type="process", params={})
    node_c = DagNode(node_id="c", task_type="end", params={})
    
    with pytest.raises(DagValidationError) as exc_info:
        planner.create_dag(
            dag_id="dag_cycle",
            nodes=[node_a, node_b, node_c],
            edges=[
                DagEdge(from_node="a", to_node="b"),
                DagEdge(from_node="b", to_node="c"),
                DagEdge(from_node="c", to_node="a"),  # Ciclo!
            ]
        )
    
    assert "cycle" in str(exc_info.value).lower()


def test_dag_node_dependencies():
    """Testa cálculo de dependências por nó."""
    from vm_webapp.agent_dag_models import DagNode, DagEdge, AgentDag
    from vm_webapp.agent_dag import DagPlanner
    
    planner = DagPlanner()
    
    node_a = DagNode(node_id="a", task_type="start", params={})
    node_b = DagNode(node_id="b", task_type="process", params={})
    node_c = DagNode(node_id="c", task_type="end", params={})
    
    dag = planner.create_dag(
        dag_id="dag_deps",
        nodes=[node_a, node_b, node_c],
        edges=[
            DagEdge(from_node="a", to_node="b"),
            DagEdge(from_node="a", to_node="c"),
        ]
    )
    
    deps = planner.get_dependencies(dag)
    
    assert deps["a"] == []  # Raiz
    assert deps["b"] == ["a"]
    assert deps["c"] == ["a"]


def test_dag_execution_plan():
    """Testa criação de plano de execução."""
    from vm_webapp.agent_dag_models import DagNode, DagEdge, AgentDag, DagRun
    from vm_webapp.agent_dag import DagPlanner
    
    planner = DagPlanner()
    
    node_a = DagNode(node_id="a", task_type="research", params={"topic": "AI"})
    node_b = DagNode(node_id="b", task_type="write", params={"format": "md"}, 
                     retry_policy={"max_retries": 3, "timeout_min": 15})
    
    dag = planner.create_dag(
        dag_id="dag_plan",
        nodes=[node_a, node_b],
        edges=[DagEdge(from_node="a", to_node="b")]
    )
    
    run = planner.create_run(dag, brand_id="b1", project_id="p1")
    
    assert run.run_id is not None
    assert run.dag_id == "dag_plan"
    assert run.brand_id == "b1"
    assert run.status == "pending"
    assert len(run.node_states) == 2


def test_parallel_nodes_execution_order():
    """Testa que nós paralelos podem executar em qualquer ordem."""
    from vm_webapp.agent_dag_models import DagNode, DagEdge, AgentDag
    from vm_webapp.agent_dag import DagPlanner
    
    planner = DagPlanner()
    
    # DAG: A -> [B, C] -> D (B e C são paralelos)
    node_a = DagNode(node_id="a", task_type="start", params={})
    node_b = DagNode(node_id="b", task_type="process1", params={})
    node_c = DagNode(node_id="c", task_type="process2", params={})
    node_d = DagNode(node_id="d", task_type="end", params={})
    
    dag = planner.create_dag(
        dag_id="dag_parallel",
        nodes=[node_a, node_b, node_c, node_d],
        edges=[
            DagEdge(from_node="a", to_node="b"),
            DagEdge(from_node="a", to_node="c"),
            DagEdge(from_node="b", to_node="d"),
            DagEdge(from_node="c", to_node="d"),
        ]
    )
    
    order = planner.topological_sort(dag)
    
    # a deve vir primeiro, d deve vir por último
    assert order[0] == "a"
    assert order[-1] == "d"
    
    # b e c devem estar entre a e d, mas ordem entre eles não importa
    assert "b" in order[1:-1]
    assert "c" in order[1:-1]
