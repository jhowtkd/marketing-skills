"""Recovery Chain Executor - v28 Auto-Recovery Orchestration.

Executor de cadeia de recuperação com suporte a:
- Sequência de steps com dependências
- Timeout e retry
- Idempotência
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import time


class StepStatus(Enum):
    """Status de execução de um step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Resultado da execução de um step."""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    attempt_number: int = 1


@dataclass
class ExecutionContext:
    """Contexto de execução para idempotência."""
    execution_id: str
    brand_id: str
    incident_id: str
    plan_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecoveryStepExecutor:
    """Executor de steps individuais com timeout e retry."""
    
    def __init__(self):
        self._action_handlers: Dict[str, Callable] = {}
    
    def register_action(self, action_name: str, handler: Callable) -> None:
        """Registra um handler para uma ação."""
        self._action_handlers[action_name] = handler
    
    def execute(
        self,
        step_id: str,
        action: str,
        timeout_seconds: int,
        context: ExecutionContext,
        max_retries: int = 0
    ) -> StepResult:
        """Executa um step com timeout e retry."""
        started_at = datetime.now(timezone.utc).isoformat()
        attempt = 0
        last_error = None
        
        handler = self._action_handlers.get(action)
        if not handler:
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                error=f"No handler registered for action: {action}",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        
        while attempt <= max_retries:
            attempt += 1
            try:
                # Execute with timeout simulation
                start_time = time.time()
                result = handler(context)
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                return StepResult(
                    step_id=step_id,
                    status=StepStatus.SUCCESS,
                    output=result,
                    execution_time_ms=execution_time_ms,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    attempt_number=attempt,
                )
            except TimeoutError:
                last_error = "Timeout"
                if attempt > max_retries:
                    return StepResult(
                        step_id=step_id,
                        status=StepStatus.TIMEOUT,
                        error="Execution timed out",
                        started_at=started_at,
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        attempt_number=attempt,
                    )
            except Exception as e:
                last_error = str(e)
                if attempt > max_retries:
                    return StepResult(
                        step_id=step_id,
                        status=StepStatus.FAILED,
                        error=last_error,
                        started_at=started_at,
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        attempt_number=attempt,
                    )
        
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=last_error or "Unknown error",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            attempt_number=attempt,
        )


class IdempotencyStore:
    """Store para garantir idempotência de execuções."""
    
    def __init__(self):
        self._executions: Dict[str, Dict[str, Any]] = {}
    
    def get_execution_key(
        self,
        brand_id: str,
        incident_id: str,
        plan_id: str
    ) -> str:
        """Gera chave única para execução."""
        return f"{brand_id}:{incident_id}:{plan_id}"
    
    def is_executed(self, execution_key: str) -> bool:
        """Verifica se execução já foi realizada."""
        return execution_key in self._executions
    
    def get_result(self, execution_key: str) -> Optional[Dict[str, Any]]:
        """Recupera resultado de execução anterior."""
        return self._executions.get(execution_key)
    
    def store_result(
        self,
        execution_key: str,
        result: Dict[str, Any],
        ttl_hours: int = 24
    ) -> None:
        """Armazena resultado de execução."""
        self._executions[execution_key] = {
            "result": result,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "ttl_hours": ttl_hours,
        }
    
    def clear(self, execution_key: str) -> None:
        """Limpa registro de execução."""
        if execution_key in self._executions:
            del self._executions[execution_key]


@dataclass
class ChainStep:
    """Step na cadeia de recuperação."""
    step_id: str
    name: str
    action: str
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    max_retries: int = 0


@dataclass
class ChainExecutionResult:
    """Resultado da execução de uma cadeia."""
    execution_id: str
    plan_id: str
    status: StepStatus
    step_results: List[StepResult] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    total_execution_time_ms: int = 0


class RecoveryChainExecutor:
    """Executor de cadeia de recuperação com idempotência."""
    
    def __init__(self):
        self._step_executor = RecoveryStepExecutor()
        self._idempotency_store = IdempotencyStore()
    
    def register_action(self, action_name: str, handler: Callable) -> None:
        """Registra um handler para uma ação."""
        self._step_executor.register_action(action_name, handler)
    
    def _build_dependency_graph(self, steps: List[ChainStep]) -> Dict[str, List[str]]:
        """Constroi grafo de dependências."""
        graph = {step.step_id: [] for step in steps}
        for step in steps:
            for dep in step.depends_on:
                if dep in graph:
                    graph[step.step_id].append(dep)
        return graph
    
    def _get_execution_order(self, steps: List[ChainStep]) -> List[str]:
        """Determina ordem de execução respeitando dependências."""
        graph = self._build_dependency_graph(steps)
        visited = set()
        order = []
        
        def visit(step_id: str, path: set):
            if step_id in path:
                raise ValueError(f"Circular dependency detected at {step_id}")
            if step_id in visited:
                return
            path.add(step_id)
            for dep in graph.get(step_id, []):
                visit(dep, path)
            path.remove(step_id)
            visited.add(step_id)
            order.append(step_id)
        
        for step in steps:
            visit(step.step_id, set())
        
        return order
    
    def execute_chain(
        self,
        plan_id: str,
        brand_id: str,
        incident_id: str,
        steps: List[ChainStep],
        skip_if_executed: bool = True
    ) -> ChainExecutionResult:
        """Executa uma cadeia de steps com idempotência."""
        execution_id = f"exec-{incident_id}-{plan_id}"
        execution_key = self._idempotency_store.get_execution_key(
            brand_id, incident_id, plan_id
        )
        
        # Check idempotency
        if skip_if_executed and self._idempotency_store.is_executed(execution_key):
            stored = self._idempotency_store.get_result(execution_key)
            if stored:
                return ChainExecutionResult(
                    execution_id=execution_id,
                    plan_id=plan_id,
                    status=StepStatus.SUCCESS,
                    step_results=stored["result"].get("step_results", []),
                    started_at=stored["result"].get("started_at", ""),
                    completed_at=stored["result"].get("completed_at", ""),
                    total_execution_time_ms=stored["result"].get("total_execution_time_ms", 0),
                )
        
        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.time()
        
        context = ExecutionContext(
            execution_id=execution_id,
            brand_id=brand_id,
            incident_id=incident_id,
            plan_id=plan_id,
        )
        
        # Build step lookup
        step_map = {step.step_id: step for step in steps}
        
        # Get execution order
        try:
            execution_order = self._get_execution_order(steps)
        except ValueError as e:
            return ChainExecutionResult(
                execution_id=execution_id,
                plan_id=plan_id,
                status=StepStatus.FAILED,
                step_results=[],
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        
        step_results: List[StepResult] = []
        failed_steps: set = set()
        
        for step_id in execution_order:
            step = step_map[step_id]
            
            # Check if dependencies failed
            if any(dep in failed_steps for dep in step.depends_on):
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.SKIPPED,
                    error="Dependency failed",
                )
                failed_steps.add(step_id)
            else:
                result = self._step_executor.execute(
                    step_id=step_id,
                    action=step.action,
                    timeout_seconds=step.timeout_seconds,
                    context=context,
                    max_retries=step.max_retries,
                )
                if result.status != StepStatus.SUCCESS:
                    failed_steps.add(step_id)
            
            step_results.append(result)
        
        total_time_ms = int((time.time() - start_time) * 1000)
        completed_at = datetime.now(timezone.utc).isoformat()
        
        final_status = StepStatus.SUCCESS if not failed_steps else StepStatus.FAILED
        
        result = ChainExecutionResult(
            execution_id=execution_id,
            plan_id=plan_id,
            status=final_status,
            step_results=step_results,
            started_at=started_at,
            completed_at=completed_at,
            total_execution_time_ms=total_time_ms,
        )
        
        # Store for idempotency
        self._idempotency_store.store_result(
            execution_key,
            {
                "step_results": [
                    {
                        "step_id": r.step_id,
                        "status": r.status.value,
                        "output": r.output,
                        "error": r.error,
                    }
                    for r in step_results
                ],
                "started_at": started_at,
                "completed_at": completed_at,
                "total_execution_time_ms": total_time_ms,
            }
        )
        
        return result
    
    def reset_execution(self, brand_id: str, incident_id: str, plan_id: str) -> None:
        """Reseta execução para permitir reexecução."""
        execution_key = self._idempotency_store.get_execution_key(
            brand_id, incident_id, plan_id
        )
        self._idempotency_store.clear(execution_key)
