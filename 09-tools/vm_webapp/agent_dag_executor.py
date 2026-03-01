"""
DAG Executor com timeout/retry/handoff - v22 Multi-Agent Orchestrator
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from vm_webapp.agent_dag_models import (
    DagNode,
    DagRun,
    NodeStatus,
    RiskLevel,
)


class ExecutionError(Exception):
    """Erro durante execução de um nó."""
    pass


class TimeoutError(ExecutionError):
    """Erro de timeout durante execução."""
    pass


class DagNodeExecutor:
    """Executor resiliente para nós de DAG."""
    
    def __init__(
        self,
        timeout_minutes: float = 15.0,
        default_max_retries: int = 3,
        default_backoff_base_sec: float = 5.0,
    ):
        self.timeout_minutes = timeout_minutes
        self.default_max_retries = default_max_retries
        self.default_backoff_base_sec = default_backoff_base_sec
        
        # Cache para idempotência: {(run_id, node_id): result}
        self._execution_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._cache_lock = threading.Lock()
    
    def execute_node(
        self,
        run: DagRun,
        node: DagNode,
        task_fn: Callable[[DagNode, DagRun], dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Executa um nó com timeout e idempotência.
        
        Args:
            run: A execução do DAG
            node: O nó a ser executado
            task_fn: Função que executa a tarefa
            
        Returns:
            Resultado da execução
        """
        cache_key = (run.run_id, node.node_id)
        
        # Verifica cache (idempotência)
        with self._cache_lock:
            if cache_key in self._execution_cache:
                return self._execution_cache[cache_key].copy()
        
        # Determina timeout (do nó ou default)
        timeout_min = node.retry_policy.get("timeout_min", self.timeout_minutes)
        timeout_sec = timeout_min * 60
        
        # Executa com timeout
        start_time = time.time()
        try:
            result = self._execute_with_timeout(task_fn, node, run, timeout_sec)
            result["status"] = "completed"
            result["duration_sec"] = time.time() - start_time
            result["timeout_minutes"] = timeout_min
        except TimeoutError as e:
            result = {
                "status": "timeout",
                "error": str(e),
                "duration_sec": time.time() - start_time,
                "timeout_minutes": timeout_min,
            }
        except ExecutionError as e:
            result = {
                "status": "failed",
                "error": str(e),
                "duration_sec": time.time() - start_time,
                "timeout_minutes": timeout_min,
            }
        
        # Armazena no cache apenas resultados bem-sucedidos (idempotência)
        if result.get("status") == "completed":
            with self._cache_lock:
                self._execution_cache[cache_key] = result.copy()
        
        return result
    
    def execute_node_with_retries(
        self,
        run: DagRun,
        node: DagNode,
        task_fn: Callable[[DagNode, DagRun], dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Executa um nó com retry e backoff.
        
        Args:
            run: A execução do DAG
            node: O nó a ser executado
            task_fn: Função que executa a tarefa
            
        Returns:
            Resultado da execução (pode ser handoff_failed)
        """
        max_retries = node.retry_policy.get("max_retries", self.default_max_retries)
        backoff_base = node.retry_policy.get("backoff_base_sec", self.default_backoff_base_sec)
        
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = self.execute_node(run, node, task_fn)
                result["attempts"] = attempt
                
                # Se completou com sucesso, retorna
                if result["status"] == "completed":
                    return result
                
                # Se deu timeout, tenta novamente (se ainda houver retries)
                if result["status"] == "timeout":
                    last_error = result.get("error", "Timeout")
                    if attempt < max_retries:
                        # Backoff exponencial
                        sleep_time = backoff_base * (2 ** (attempt - 1))
                        time.sleep(sleep_time)
                    continue
                
                # Outro erro
                last_error = result.get("error", "Unknown error")
                if attempt < max_retries:
                    sleep_time = backoff_base * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    sleep_time = backoff_base * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
        
        # Todas as tentativas falharam -> handoff_failed
        return {
            "status": "handoff_failed",
            "attempts": max_retries,
            "error": last_error or "All retries exhausted",
            "node_id": node.node_id,
            "run_id": run.run_id,
        }
    
    def _execute_with_timeout(
        self,
        task_fn: Callable,
        node: DagNode,
        run: DagRun,
        timeout_sec: float,
    ) -> dict[str, Any]:
        """Executa task com timeout usando threading."""
        result_container = {}
        exception_container = {}
        
        def target():
            try:
                result_container["result"] = task_fn(node, run)
            except Exception as e:
                exception_container["error"] = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout_sec)
        
        if thread.is_alive():
            # Timeout - não podemos matar a thread em Python,
            # mas marcamos como timeout
            raise TimeoutError(f"Task exceeded timeout of {timeout_sec}s")
        
        if "error" in exception_container:
            raise ExecutionError(str(exception_container["error"]))
        
        return result_container.get("result", {})
    
    def clear_cache(self, run_id: Optional[str] = None) -> None:
        """Limpa cache de idempotência."""
        with self._cache_lock:
            if run_id is None:
                self._execution_cache.clear()
            else:
                keys_to_remove = [k for k in self._execution_cache if k[0] == run_id]
                for key in keys_to_remove:
                    del self._execution_cache[key]
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do cache."""
        with self._cache_lock:
            return {
                "cached_entries": len(self._execution_cache),
                "cached_runs": len(set(k[0] for k in self._execution_cache)),
            }


class DagOrchestrator:
    """Orquestrador de execução de DAG completo."""
    
    def __init__(
        self,
        executor: Optional[DagNodeExecutor] = None,
        on_node_complete: Optional[Callable[[str, str, dict], None]] = None,
        on_node_failed: Optional[Callable[[str, str, dict], None]] = None,
    ):
        self.executor = executor or DagNodeExecutor()
        self.on_node_complete = on_node_complete
        self.on_node_failed = on_node_failed
    
    def execute_dag(
        self,
        dag: Any,  # AgentDag
        run: DagRun,
        task_registry: dict[str, Callable[[DagNode, DagRun], dict[str, Any]]],
    ) -> dict[str, Any]:
        """
        Executa um DAG completo.
        
        Args:
            dag: O DAG a ser executado
            run: A execução do DAG
            task_registry: Mapeia task_type para função executora
            
        Returns:
            Resumo da execução
        """
        from vm_webapp.agent_dag import DagPlanner
        
        planner = DagPlanner()
        execution_order = planner.topological_sort(dag)
        
        completed_nodes = []
        failed_nodes = []
        
        for node_id in execution_order:
            node = next(n for n in dag.nodes if n.node_id == node_id)
            task_fn = task_registry.get(node.task_type)
            
            if task_fn is None:
                failed_nodes.append({
                    "node_id": node_id,
                    "error": f"No task handler for type: {node.task_type}",
                })
                continue
            
            result = self.executor.execute_node_with_retries(run, node, task_fn)
            
            if result["status"] == "completed":
                completed_nodes.append({
                    "node_id": node_id,
                    "result": result,
                })
                if self.on_node_complete:
                    self.on_node_complete(run.run_id, node_id, result)
            else:
                failed_nodes.append({
                    "node_id": node_id,
                    "result": result,
                })
                if self.on_node_failed:
                    self.on_node_failed(run.run_id, node_id, result)
        
        return {
            "run_id": run.run_id,
            "dag_id": dag.dag_id,
            "completed_nodes": completed_nodes,
            "failed_nodes": failed_nodes,
            "success": len(failed_nodes) == 0,
        }
