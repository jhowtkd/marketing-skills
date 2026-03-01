"""
DAG Executor com timeout/retry/handoff - v22 Multi-Agent Orchestrator

P0 Fix: Instrumentação estruturada de logs e métricas por node_type
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from vm_webapp.agent_dag_models import (
    DagNode,
    DagRun,
    NodeStatus,
    RiskLevel,
)

# Logger estruturado para DAG operations
logger = logging.getLogger("vm_webapp.dag_executor")


class ExecutionError(Exception):
    """Erro durante execução de um nó."""
    pass


class TimeoutError(ExecutionError):
    """Erro de timeout durante execução."""
    pass


@dataclass
class FailureMetrics:
    """Métricas de falha por tipo de nó."""
    node_type: str
    handoff_failed_total: int = 0
    timeout_total: int = 0
    retry_exhausted_total: int = 0
    last_failure_at: Optional[str] = None
    
    def record_failure(self, failure_type: str) -> None:
        """Registra uma falha do tipo especificado."""
        if failure_type == "handoff_failed":
            self.handoff_failed_total += 1
        elif failure_type == "timeout":
            self.timeout_total += 1
        elif failure_type == "retry_exhausted":
            self.retry_exhausted_total += 1
        self.last_failure_at = datetime.now(timezone.utc).isoformat()


class DagNodeExecutor:
    """Executor resiliente para nós de DAG."""
    
    # Configuração de timeout segura (P0 fix): baseline 15min, ajustável por workload
    DEFAULT_TIMEOUT_MINUTES = 15.0
    MIN_TIMEOUT_MINUTES = 5.0
    MAX_TIMEOUT_MINUTES = 60.0
    
    def __init__(
        self,
        timeout_minutes: float = None,
        default_max_retries: int = 3,
        default_backoff_base_sec: float = 5.0,
        enable_structured_logging: bool = True,
    ):
        # Valida e ajusta timeout dentro de limites seguros
        if timeout_minutes is None:
            timeout_minutes = self.DEFAULT_TIMEOUT_MINUTES
        self.timeout_minutes = max(
            self.MIN_TIMEOUT_MINUTES,
            min(timeout_minutes, self.MAX_TIMEOUT_MINUTES)
        )
        self.default_max_retries = default_max_retries
        self.default_backoff_base_sec = default_backoff_base_sec
        self.enable_structured_logging = enable_structured_logging
        
        # Cache para idempotência: {(run_id, node_id): result}
        self._execution_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._cache_lock = threading.Lock()
        
        # Métricas por node_type para diagnóstico P0
        self._failure_metrics: dict[str, FailureMetrics] = {}
        self._metrics_lock = threading.Lock()
    
    def _log_structured(
        self,
        level: str,
        event: str,
        run_id: str,
        node: DagNode,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log estruturado com contexto do nó."""
        if not self.enable_structured_logging:
            return
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "run_id": run_id,
            "node_id": node.node_id,
            "node_type": node.task_type,
            "risk_level": node.risk_level.value,
        }
        if extra:
            log_entry.update(extra)
        
        log_msg = json.dumps(log_entry, default=str)
        
        if level == "error":
            logger.error(log_msg)
        elif level == "warning":
            logger.warning(log_msg)
        elif level == "info":
            logger.info(log_msg)
        else:
            logger.debug(log_msg)
    
    def _record_failure_metric(self, node: DagNode, failure_type: str) -> None:
        """Registra métrica de falha por node_type."""
        with self._metrics_lock:
            if node.task_type not in self._failure_metrics:
                self._failure_metrics[node.task_type] = FailureMetrics(node_type=node.task_type)
            self._failure_metrics[node.task_type].record_failure(failure_type)
    
    def get_failure_metrics(self, node_type: Optional[str] = None) -> dict[str, Any]:
        """Retorna métricas de falha por tipo de nó."""
        with self._metrics_lock:
            if node_type:
                metrics = self._failure_metrics.get(node_type)
                return {
                    "node_type": node_type,
                    "handoff_failed_total": metrics.handoff_failed_total if metrics else 0,
                    "timeout_total": metrics.timeout_total if metrics else 0,
                    "retry_exhausted_total": metrics.retry_exhausted_total if metrics else 0,
                }
            return {
                node_type: {
                    "handoff_failed_total": m.handoff_failed_total,
                    "timeout_total": m.timeout_total,
                    "retry_exhausted_total": m.retry_exhausted_total,
                    "last_failure_at": m.last_failure_at,
                }
                for node_type, m in self._failure_metrics.items()
            }
    
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
                self._log_structured(
                    "debug", "cache_hit", run.run_id, node,
                    {"cached_at": self._execution_cache[cache_key].get("completed_at")}
                )
                return self._execution_cache[cache_key].copy()
        
        # Determina timeout (do nó ou default) - P0: respeita limites seguros
        timeout_min = node.retry_policy.get("timeout_min", self.timeout_minutes)
        timeout_min = max(self.MIN_TIMEOUT_MINUTES, min(timeout_min, self.MAX_TIMEOUT_MINUTES))
        timeout_sec = timeout_min * 60
        
        self._log_structured(
            "info", "node_execution_started", run.run_id, node,
            {"timeout_min": timeout_min, "timeout_sec": timeout_sec}
        )
        
        # Executa com timeout
        start_time = time.time()
        try:
            result = self._execute_with_timeout(task_fn, node, run, timeout_sec)
            result["status"] = "completed"
            result["duration_sec"] = time.time() - start_time
            result["timeout_minutes"] = timeout_min
            result["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            self._log_structured(
                "info", "node_execution_completed", run.run_id, node,
                {"duration_sec": result["duration_sec"], "attempts": result.get("attempts", 1)}
            )
            
        except TimeoutError as e:
            duration = time.time() - start_time
            self._record_failure_metric(node, "timeout")
            self._log_structured(
                "error", "node_execution_timeout", run.run_id, node,
                {
                    "duration_sec": duration,
                    "timeout_sec": timeout_sec,
                    "error": str(e),
                }
            )
            result = {
                "status": "timeout",
                "error": str(e),
                "duration_sec": duration,
                "timeout_minutes": timeout_min,
            }
        except ExecutionError as e:
            duration = time.time() - start_time
            self._log_structured(
                "error", "node_execution_failed", run.run_id, node,
                {"duration_sec": duration, "error": str(e)}
            )
            result = {
                "status": "failed",
                "error": str(e),
                "duration_sec": duration,
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
        
        self._log_structured(
            "info", "retry_loop_started", run.run_id, node,
            {"max_retries": max_retries, "backoff_base_sec": backoff_base}
        )
        
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = self.execute_node(run, node, task_fn)
                result["attempts"] = attempt
                
                # Se completou com sucesso, retorna
                if result["status"] == "completed":
                    if attempt > 1:
                        self._log_structured(
                            "info", "retry_success", run.run_id, node,
                            {"success_on_attempt": attempt}
                        )
                    return result
                
                # Se deu timeout, tenta novamente (se ainda houver retries)
                if result["status"] == "timeout":
                    last_error = result.get("error", "Timeout")
                    if attempt < max_retries:
                        sleep_time = backoff_base * (2 ** (attempt - 1))
                        self._log_structured(
                            "warning", "retry_after_timeout", run.run_id, node,
                            {"attempt": attempt, "sleep_sec": sleep_time, "next_attempt": attempt + 1}
                        )
                        time.sleep(sleep_time)
                    continue
                
                # Outro erro
                last_error = result.get("error", "Unknown error")
                if attempt < max_retries:
                    sleep_time = backoff_base * (2 ** (attempt - 1))
                    self._log_structured(
                        "warning", "retry_after_error", run.run_id, node,
                        {"attempt": attempt, "sleep_sec": sleep_time, "error": last_error}
                    )
                    time.sleep(sleep_time)
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    sleep_time = backoff_base * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
        
        # Todas as tentativas falharam -> handoff_failed
        self._record_failure_metric(node, "handoff_failed")
        self._log_structured(
            "error", "handoff_failed", run.run_id, node,
            {
                "attempts": max_retries,
                "last_error": last_error,
                "mitigation": "Check failure_metrics for node_type patterns"
            }
        )
        
        return {
            "status": "handoff_failed",
            "attempts": max_retries,
            "error": last_error or "All retries exhausted",
            "node_id": node.node_id,
            "run_id": run.run_id,
            "node_type": node.task_type,
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
    
    def get_executor_config(self) -> dict[str, Any]:
        """Retorna configuração atual do executor."""
        return {
            "timeout_minutes": self.timeout_minutes,
            "min_timeout_minutes": self.MIN_TIMEOUT_MINUTES,
            "max_timeout_minutes": self.MAX_TIMEOUT_MINUTES,
            "default_max_retries": self.default_max_retries,
            "default_backoff_base_sec": self.default_backoff_base_sec,
            "enable_structured_logging": self.enable_structured_logging,
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
                    self.on_node_complete(run.run_id, node_id, result)
        
        return {
            "run_id": run.run_id,
            "dag_id": dag.dag_id,
            "completed_nodes": completed_nodes,
            "failed_nodes": failed_nodes,
            "success": len(failed_nodes) == 0,
        }
