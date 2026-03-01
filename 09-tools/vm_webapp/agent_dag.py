"""
DAG Planner - v22 Multi-Agent Orchestrator
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Any, Optional
from uuid import uuid4

from vm_webapp.agent_dag_models import (
    AgentDag,
    DagApprovalRequest,
    DagEdge,
    DagNode,
    DagNodeState,
    DagRun,
    DagStatus,
    NodeStatus,
    RiskLevel,
)


class DagValidationError(ValueError):
    """Erro de validação de DAG."""
    pass


class DagPlanner:
    """Planner para criação e validação de DAGs."""
    
    def create_dag(
        self,
        dag_id: str,
        nodes: list[DagNode],
        edges: list[DagEdge],
        metadata: Optional[dict[str, Any]] = None
    ) -> AgentDag:
        """Cria um novo DAG validado."""
        # Valida que todos os nós referenciados em edges existem
        node_ids = {n.node_id for n in nodes}
        for edge in edges:
            if edge.from_node not in node_ids:
                raise DagValidationError(f"Edge references unknown node: {edge.from_node}")
            if edge.to_node not in node_ids:
                raise DagValidationError(f"Edge references unknown node: {edge.to_node}")
        
        # Valida que não há ciclos
        if self._has_cycle(nodes, edges):
            raise DagValidationError("Cycle detected in DAG")
        
        # Preenche depends_on baseado nas edges
        node_map = {n.node_id: n for n in nodes}
        for edge in edges:
            if edge.from_node not in node_map[edge.to_node].depends_on:
                node_map[edge.to_node].depends_on.append(edge.from_node)
        
        return AgentDag(
            dag_id=dag_id,
            nodes=nodes,
            edges=edges,
            metadata=metadata or {},
        )
    
    def topological_sort(self, dag: AgentDag) -> list[str]:
        """Retorna ordem topológica dos nós."""
        # Constrói grafo
        in_degree = defaultdict(int)
        adj = defaultdict(list)
        
        for node in dag.nodes:
            in_degree[node.node_id] = 0
        
        for edge in dag.edges:
            adj[edge.from_node].append(edge.to_node)
            in_degree[edge.to_node] += 1
        
        # Kahn's algorithm
        queue = deque([n for n in in_degree if in_degree[n] == 0])
        result = []
        
        while queue:
            # Ordena para estabilidade em testes
            queue = deque(sorted(queue))
            node_id = queue.popleft()
            result.append(node_id)
            
            for neighbor in sorted(adj[node_id]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(dag.nodes):
            raise DagValidationError("Cycle detected during topological sort")
        
        return result
    
    def get_dependencies(self, dag: AgentDag) -> dict[str, list[str]]:
        """Retorna mapa de dependências por nó."""
        deps = {n.node_id: [] for n in dag.nodes}
        for edge in dag.edges:
            deps[edge.to_node].append(edge.from_node)
        return deps
    
    def get_dependents(self, dag: AgentDag) -> dict[str, list[str]]:
        """Retorna mapa de nós que dependem de cada nó."""
        deps = {n.node_id: [] for n in dag.nodes}
        for edge in dag.edges:
            deps[edge.from_node].append(edge.to_node)
        return deps
    
    def create_run(
        self,
        dag: AgentDag,
        brand_id: str,
        project_id: str,
        run_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> DagRun:
        """Cria uma nova execução do DAG."""
        run_id = run_id or uuid4().hex[:16]
        
        # Inicializa estados dos nós
        node_states = {
            node.node_id: DagNodeState(node_id=node.node_id)
            for node in dag.nodes
        }
        
        return DagRun(
            run_id=run_id,
            dag_id=dag.dag_id,
            brand_id=brand_id,
            project_id=project_id,
            status=DagStatus.PENDING,
            node_states=node_states,
            metadata=metadata or {},
        )
    
    def create_approval_request(
        self,
        run: DagRun,
        node_id: str,
        risk_level: RiskLevel
    ) -> DagApprovalRequest:
        """Cria um pedido de aprovação para um nó."""
        return DagApprovalRequest(
            request_id=uuid4().hex[:16],
            run_id=run.run_id,
            node_id=node_id,
            risk_level=risk_level,
        )
    
    def get_ready_nodes(self, dag: AgentDag, run: DagRun) -> list[str]:
        """Retorna nós prontos para execução (dependências satisfeitas)."""
        deps = self.get_dependencies(dag)
        ready = []
        
        for node_id, node_state in run.node_states.items():
            if node_state.status != NodeStatus.PENDING:
                continue
            
            # Verifica se todas as dependências estão completas
            all_deps_completed = all(
                run.node_states[dep].status == NodeStatus.COMPLETED
                for dep in deps.get(node_id, [])
            )
            
            if all_deps_completed:
                ready.append(node_id)
        
        return ready
    
    def _has_cycle(self, nodes: list[DagNode], edges: list[DagEdge]) -> bool:
        """Verifica se há ciclo no grafo usando DFS."""
        # Constrói grafo
        graph = defaultdict(list)
        for edge in edges:
            graph[edge.from_node].append(edge.to_node)
        
        # Estados: 0 = unvisited, 1 = visiting, 2 = visited
        state = {n.node_id: 0 for n in nodes}
        
        def has_cycle_from(node_id: str) -> bool:
            state[node_id] = 1  # visiting
            
            for neighbor in graph[node_id]:
                if state[neighbor] == 1:  # back edge -> cycle
                    return True
                if state[neighbor] == 0 and has_cycle_from(neighbor):
                    return True
            
            state[node_id] = 2  # visited
            return False
        
        for node in nodes:
            if state[node.node_id] == 0:
                if has_cycle_from(node.node_id):
                    return True
        
        return False
