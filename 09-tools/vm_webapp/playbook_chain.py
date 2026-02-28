"""Playbook Chain - execução segura de cadeia de ações editoriais.

Fornece:
- Ordem definida das ações
- Idempotência (mesma execução = mesmo resultado)
- Kill-switch (capacidade de parar execução)
- Rate-limit entre steps
- Retorno detalhado por step
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal


ChainStatus = Literal["completed", "partial", "failed"]


@dataclass
class ChainStepResult:
    """Resultado de execução de um step da cadeia.
    
    Attributes:
        action: Identificador da ação executada
        executed: Se a ação foi efetivamente executada
        skipped: Se a ação foi pulada
        error: Mensagem de erro (se houver)
        motivo: Descrição do resultado em português
    """
    action: str
    executed: bool
    skipped: bool
    error: str | None
    motivo: str


@dataclass
class ChainExecutionResult:
    """Resultado completo da execução de uma cadeia.
    
    Attributes:
        execution_id: ID único da execução
        steps: Lista de resultados por step
        status: Status geral da execução
    """
    execution_id: str
    steps: list[ChainStepResult]
    status: ChainStatus


@dataclass
class ChainOptions:
    """Opções de configuração para execução da cadeia.
    
    Attributes:
        steps: Lista de steps a executar (cada step é um dict com 'action' e opcionalmente 'suppress_when')
        stop_on_error: Se deve parar execução quando um step falha
        kill_switch: Se kill-switch está ativo (bloqueia execução)
        rate_limit_delay_ms: Delay em ms entre steps
        cooldown_seconds: Cooldown mínimo entre execuções do mesmo playbook
    """
    steps: list[dict[str, Any]]
    stop_on_error: bool = True
    kill_switch: bool = False
    rate_limit_delay_ms: int = 0
    cooldown_seconds: int = 0


class PlaybookChainExecutor:
    """Executor de cadeia de playbooks com segurança e controle.
    
    Features:
    - Execução ordenada de steps
    - Kill-switch para parada emergencial
    - Rate limiting entre steps
    - Cooldown entre execuções
    - Suppression de ações baseada em condições
    """
    
    def __init__(
        self,
        execution_history: list[dict[str, Any]] | None = None,
        execution_cache: dict[str, ChainExecutionResult] | None = None,
    ):
        self.execution_history = execution_history or []
        self._cache = execution_cache or {}
        self._kill_switch_active = False
    
    def execute(
        self,
        playbook_id: str,
        thread_id: str,
        idempotency_key: str,
        chain_options: ChainOptions,
        context: dict[str, Any] | None = None,
    ) -> ChainExecutionResult:
        """Executa uma cadeia de ações com segurança.
        
        Args:
            playbook_id: ID do playbook
            thread_id: ID do thread
            idempotency_key: Chave de idempotência
            chain_options: Opções da cadeia
            context: Contexto para avaliação de suppressions
            
        Returns:
            ChainExecutionResult com resultado detalhado
            
        Raises:
            RuntimeError: Se kill-switch está ativo
            RuntimeError: Se cooldown não foi respeitado
        """
        context = context or {}
        
        # Gerar execution_id deterministicamente
        execution_id = generate_execution_id(playbook_id, thread_id, idempotency_key)
        
        # Check idempotency cache
        if execution_id in self._cache:
            return self._cache[execution_id]
        
        # Check kill-switch
        if chain_options.kill_switch or self._kill_switch_active:
            raise RuntimeError("Kill-switch ativo - execução bloqueada")
        
        # Check cooldown
        allowed, reason = check_cooldown(
            playbook_id, thread_id, chain_options.cooldown_seconds, self.execution_history
        )
        if not allowed:
            raise RuntimeError(f"Cooldown em efeito: {reason}")
        
        # Executar steps
        steps: list[ChainStepResult] = []
        any_failed = False
        stopped_early = False
        
        for i, step_config in enumerate(chain_options.steps):
            action = step_config.get("action", "")
            suppress_when = step_config.get("suppress_when")
            
            # Rate limit delay (exceto no primeiro step)
            if i > 0 and chain_options.rate_limit_delay_ms > 0:
                time.sleep(chain_options.rate_limit_delay_ms / 1000)
            
            # Check suppression
            if suppress_when:
                suppressed, suppress_reason = check_suppression(suppress_when, context)
                if suppressed:
                    steps.append(ChainStepResult(
                        action=action,
                        executed=False,
                        skipped=True,
                        error=None,
                        motivo=f"Suprimido: {suppress_reason}"
                    ))
                    continue
            
            # Execute action
            try:
                result = self._execute_action(action, step_config)
                steps.append(result)
                
                if result.error:
                    any_failed = True
                    if chain_options.stop_on_error:
                        stopped_early = True
                        # Marcar steps restantes como skipped
                        for remaining_step in chain_options.steps[i+1:]:
                            steps.append(ChainStepResult(
                                action=remaining_step.get("action", ""),
                                executed=False,
                                skipped=True,
                                error=None,
                                motivo="Abortado devido a erro em step anterior"
                            ))
                        break
                        
            except Exception as e:
                any_failed = True
                steps.append(ChainStepResult(
                    action=action,
                    executed=False,
                    skipped=False,
                    error=str(e),
                    motivo=f"Erro na execução: {str(e)}"
                ))
                if chain_options.stop_on_error:
                    stopped_early = True
                    # Marcar steps restantes como skipped
                    for remaining_step in chain_options.steps[i+1:]:
                        steps.append(ChainStepResult(
                            action=remaining_step.get("action", ""),
                            executed=False,
                            skipped=True,
                            error=None,
                            motivo="Abortado devido a erro em step anterior"
                        ))
                    break
        
        # Determinar status
        if any_failed and stopped_early:
            status: ChainStatus = "failed"
        elif any_failed:
            status = "partial"
        else:
            status = "completed"
        
        result = ChainExecutionResult(
            execution_id=execution_id,
            steps=steps,
            status=status
        )
        
        # Cache para idempotência
        self._cache[execution_id] = result
        
        # Registrar no histórico
        self.execution_history.append({
            "execution_id": execution_id,
            "playbook_id": playbook_id,
            "thread_id": thread_id,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
        })
        
        return result
    
    def _execute_action(self, action: str, step_config: dict[str, Any]) -> ChainStepResult:
        """Executa uma ação individual.
        
        Args:
            action: Identificador da ação
            step_config: Configuração completa do step
            
        Returns:
            ChainStepResult com resultado da execução
        """
        # Ações válidas do sistema
        valid_actions = {
            "open_review_task",
            "prepare_guided_regeneration",
            "suggest_policy_review",
        }
        
        if action not in valid_actions:
            return ChainStepResult(
                action=action,
                executed=False,
                skipped=False,
                error=f"Ação desconhecida: {action}",
                motivo=f"Ação '{action}' não é válida"
            )
        
        # Simular execução bem-sucedida
        # Em produção, aqui seria chamado o comando real
        return ChainStepResult(
            action=action,
            executed=True,
            skipped=False,
            error=None,
            motivo=f"Ação '{action}' executada com sucesso"
        )
    
    def activate_kill_switch(self) -> None:
        """Ativa o kill-switch global."""
        self._kill_switch_active = True
    
    def deactivate_kill_switch(self) -> None:
        """Desativa o kill-switch global."""
        self._kill_switch_active = False


def generate_execution_id(playbook_id: str, thread_id: str, idempotency_key: str) -> str:
    """Gera ID de execução deterministicamente.
    
    Garante idempotência: mesmos inputs = mesmo execution_id.
    
    Args:
        playbook_id: ID do playbook
        thread_id: ID do thread
        idempotency_key: Chave de idempotência
        
    Returns:
        Hash único da execução
    """
    content = f"{playbook_id}:{thread_id}:{idempotency_key}"
    return f"exec-{hashlib.sha256(content.encode()).hexdigest()[:16]}"


def check_cooldown(
    playbook_id: str,
    thread_id: str,
    cooldown_seconds: int,
    execution_history: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Verifica se cooldown está respeitado.
    
    Args:
        playbook_id: ID do playbook
        thread_id: ID do thread
        cooldown_seconds: Segundos de cooldown necessários
        execution_history: Histórico de execuções
        
    Returns:
        Tuple de (permitido, motivo)
    """
    if cooldown_seconds <= 0:
        return True, "Sem cooldown configurado"
    
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=cooldown_seconds)
    
    for execution in reversed(execution_history):
        if (
            execution.get("playbook_id") == playbook_id
            and execution.get("thread_id") == thread_id
        ):
            executed_at_str = execution.get("executed_at", "")
            try:
                executed_at = datetime.fromisoformat(executed_at_str.replace("Z", "+00:00"))
                if executed_at > cutoff:
                    remaining = cooldown_seconds - (now - executed_at).total_seconds()
                    return False, f"Cooldown em efeito. Aguarde {int(remaining)}s"
            except (ValueError, TypeError):
                continue
    
    return True, "OK"


def check_suppression(
    suppress_when: dict[str, Any],
    context: dict[str, Any],
) -> tuple[bool, str]:
    """Verifica se ação deve ser suprimida.
    
    Args:
        suppress_when: Condições para supressão
        context: Contexto atual
        
    Returns:
        Tuple de (suprimido, motivo)
    """
    for key, expected_value in suppress_when.items():
        actual_value = context.get(key)
        if actual_value == expected_value:
            return True, f"Suprimido: condição '{key}={expected_value}' atendida"
    
    return False, ""


def execute_playbook_chain(
    playbook_id: str,
    thread_id: str,
    idempotency_key: str,
    chain_options: dict[str, Any],
    context: dict[str, Any] | None = None,
    execution_history: list[dict[str, Any]] | None = None,
) -> ChainExecutionResult:
    """Função de conveniência para executar playbook chain.
    
    Args:
        playbook_id: ID do playbook
        thread_id: ID do thread
        idempotency_key: Chave de idempotência
        chain_options: Opções da cadeia (dict)
        context: Contexto para avaliação
        execution_history: Histórico de execuções
        
    Returns:
        ChainExecutionResult
    """
    options = ChainOptions(
        steps=chain_options.get("steps", []),
        stop_on_error=chain_options.get("stop_on_error", True),
        kill_switch=chain_options.get("kill_switch", False),
        rate_limit_delay_ms=chain_options.get("rate_limit_delay_ms", 0),
        cooldown_seconds=chain_options.get("cooldown_seconds", 0),
    )
    
    executor = PlaybookChainExecutor(execution_history=execution_history)
    return executor.execute(
        playbook_id=playbook_id,
        thread_id=thread_id,
        idempotency_key=idempotency_key,
        chain_options=options,
        context=context,
    )


def chain_result_to_dict(result: ChainExecutionResult) -> dict[str, Any]:
    """Converte ChainExecutionResult para dict JSON-serializável.
    
    Args:
        result: Resultado da execução
        
    Returns:
        Dict com estrutura da resposta API
    """
    return {
        "execution_id": result.execution_id,
        "status": result.status,
        "steps": [
            {
                "action": step.action,
                "executed": step.executed,
                "skipped": step.skipped,
                "error": step.error,
                "motivo": step.motivo,
            }
            for step in result.steps
        ],
    }
