"""Tests for v28 Recovery Chain Executor.

TDD: Testes para sequência de steps, timeout/retry, idempotência.
"""

from __future__ import annotations

import pytest

from vm_webapp.recovery_chain import (
    ChainExecutionResult,
    ChainStep,
    ExecutionContext,
    IdempotencyStore,
    RecoveryChainExecutor,
    RecoveryStepExecutor,
    StepResult,
    StepStatus,
)


class TestStepExecutor:
    """Testes para executor de steps."""

    def test_execute_successful_step(self):
        """Step deve executar com sucesso."""
        executor = RecoveryStepExecutor()
        executor.register_action("test_action", lambda ctx: {"status": "ok"})
        
        context = ExecutionContext(
            execution_id="exec-001",
            brand_id="brand-001",
            incident_id="inc-001",
            plan_id="plan-001",
        )
        
        result = executor.execute(
            step_id="step-001",
            action="test_action",
            timeout_seconds=60,
            context=context,
        )
        
        assert result.status == StepStatus.SUCCESS
        assert result.output == {"status": "ok"}
        assert result.step_id == "step-001"

    def test_execute_unknown_action_fails(self):
        """Action desconhecida deve falhar."""
        executor = RecoveryStepExecutor()
        
        context = ExecutionContext(
            execution_id="exec-001",
            brand_id="brand-001",
            incident_id="inc-001",
            plan_id="plan-001",
        )
        
        result = executor.execute(
            step_id="step-001",
            action="unknown_action",
            timeout_seconds=60,
            context=context,
        )
        
        assert result.status == StepStatus.FAILED
        assert "No handler registered" in result.error

    def test_execute_with_retries(self):
        """Step deve fazer retry em caso de falha."""
        executor = RecoveryStepExecutor()
        
        call_count = 0
        def failing_then_success(ctx):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return {"status": "recovered"}
        
        executor.register_action("flaky_action", failing_then_success)
        
        context = ExecutionContext(
            execution_id="exec-001",
            brand_id="brand-001",
            incident_id="inc-001",
            plan_id="plan-001",
        )
        
        result = executor.execute(
            step_id="step-001",
            action="flaky_action",
            timeout_seconds=60,
            context=context,
            max_retries=3,
        )
        
        assert result.status == StepStatus.SUCCESS
        assert result.output == {"status": "recovered"}
        assert result.attempt_number == 3
        assert call_count == 3

    def test_execute_fails_after_max_retries(self):
        """Step deve falhar após max retries."""
        executor = RecoveryStepExecutor()
        executor.register_action("always_fails", lambda ctx: (_ for _ in ()).throw(ValueError("Always fails")))
        
        context = ExecutionContext(
            execution_id="exec-001",
            brand_id="brand-001",
            incident_id="inc-001",
            plan_id="plan-001",
        )
        
        result = executor.execute(
            step_id="step-001",
            action="always_fails",
            timeout_seconds=60,
            context=context,
            max_retries=2,
        )
        
        assert result.status == StepStatus.FAILED
        assert result.attempt_number == 3  # Initial + 2 retries


class TestIdempotencyStore:
    """Testes para store de idempotência."""

    def test_get_execution_key(self):
        """Deve gerar chave única correta."""
        store = IdempotencyStore()
        key = store.get_execution_key("brand-001", "inc-001", "plan-001")
        assert key == "brand-001:inc-001:plan-001"

    def test_is_executed_returns_false_for_new(self):
        """Execução nova não deve estar no store."""
        store = IdempotencyStore()
        key = store.get_execution_key("brand-001", "inc-001", "plan-001")
        assert store.is_executed(key) is False

    def test_store_and_retrieve_result(self):
        """Deve armazenar e recuperar resultado."""
        store = IdempotencyStore()
        key = store.get_execution_key("brand-001", "inc-001", "plan-001")
        
        result = {"status": "success", "steps": ["step-001"]}
        store.store_result(key, result)
        
        assert store.is_executed(key) is True
        stored = store.get_result(key)
        assert stored["result"] == result
        assert "executed_at" in stored

    def test_clear_execution(self):
        """Deve limpar execução do store."""
        store = IdempotencyStore()
        key = store.get_execution_key("brand-001", "inc-001", "plan-001")
        
        store.store_result(key, {"status": "success"})
        assert store.is_executed(key) is True
        
        store.clear(key)
        assert store.is_executed(key) is False


class TestChainExecutor:
    """Testes para executor de cadeia."""

    def test_execute_single_step(self):
        """Cadeia com um step deve executar."""
        executor = RecoveryChainExecutor()
        executor.register_action("test_action", lambda ctx: {"done": True})
        
        steps = [
            ChainStep(step_id="step-1", name="Test", action="test_action"),
        ]
        
        result = executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert result.status == StepStatus.SUCCESS
        assert len(result.step_results) == 1
        assert result.step_results[0].status == StepStatus.SUCCESS

    def test_execute_multiple_steps_in_order(self):
        """Steps devem executar na ordem correta."""
        executor = RecoveryChainExecutor()
        
        execution_order = []
        def track_action(name):
            def action(ctx):
                execution_order.append(name)
                return {"name": name}
            return action
        
        executor.register_action("action_a", track_action("a"))
        executor.register_action("action_b", track_action("b"))
        executor.register_action("action_c", track_action("c"))
        
        steps = [
            ChainStep(step_id="step-1", name="A", action="action_a"),
            ChainStep(step_id="step-2", name="B", action="action_b"),
            ChainStep(step_id="step-3", name="C", action="action_c"),
        ]
        
        result = executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert result.status == StepStatus.SUCCESS
        assert execution_order == ["a", "b", "c"]

    def test_execute_with_dependencies(self):
        """Steps devem respeitar dependências."""
        executor = RecoveryChainExecutor()
        
        execution_order = []
        def track_action(name):
            def action(ctx):
                execution_order.append(name)
                return {"name": name}
            return action
        
        executor.register_action("action_a", track_action("a"))
        executor.register_action("action_b", track_action("b"))
        executor.register_action("action_c", track_action("c"))
        
        # C depends on A, B depends on nothing
        steps = [
            ChainStep(step_id="step-c", name="C", action="action_c", depends_on=["step-a"]),
            ChainStep(step_id="step-a", name="A", action="action_a"),
            ChainStep(step_id="step-b", name="B", action="action_b"),
        ]
        
        result = executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert result.status == StepStatus.SUCCESS
        # A must come before C, B can be anywhere
        assert execution_order.index("a") < execution_order.index("c")

    def test_skip_steps_when_dependency_fails(self):
        """Steps dependentes devem ser pulados quando dependência falha."""
        executor = RecoveryChainExecutor()
        executor.register_action("fail_action", lambda ctx: (_ for _ in ()).throw(ValueError("Fail")))
        executor.register_action("success_action", lambda ctx: {"ok": True})
        
        steps = [
            ChainStep(step_id="step-a", name="A", action="fail_action"),
            ChainStep(step_id="step-b", name="B", action="success_action", depends_on=["step-a"]),
        ]
        
        result = executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert result.status == StepStatus.FAILED
        step_results = {r.step_id: r for r in result.step_results}
        assert step_results["step-a"].status == StepStatus.FAILED
        assert step_results["step-b"].status == StepStatus.SKIPPED

    def test_idempotency_returns_cached_result(self):
        """Execução repetida deve retornar resultado cacheado."""
        executor = RecoveryChainExecutor()
        
        call_count = 0
        def counting_action(ctx):
            nonlocal call_count
            call_count += 1
            return {"count": call_count}
        
        executor.register_action("count_action", counting_action)
        
        steps = [
            ChainStep(step_id="step-1", name="Count", action="count_action"),
        ]
        
        # First execution
        result1 = executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert result1.status == StepStatus.SUCCESS
        assert call_count == 1
        
        # Second execution - should use cached result
        result2 = executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert result2.status == StepStatus.SUCCESS
        assert call_count == 1  # Action not called again

    def test_skip_idempotency_when_disabled(self):
        """Idempotência pode ser desabilitada."""
        executor = RecoveryChainExecutor()
        
        call_count = 0
        def counting_action(ctx):
            nonlocal call_count
            call_count += 1
            return {"count": call_count}
        
        executor.register_action("count_action", counting_action)
        
        steps = [
            ChainStep(step_id="step-1", name="Count", action="count_action"),
        ]
        
        # First execution
        executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
            skip_if_executed=True,
        )
        
        # Second execution with skip disabled
        executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
            skip_if_executed=False,
        )
        
        assert call_count == 2  # Action called again

    def test_reset_allows_reexecution(self):
        """Reset deve permitir reexecução."""
        executor = RecoveryChainExecutor()
        
        call_count = 0
        def counting_action(ctx):
            nonlocal call_count
            call_count += 1
            return {"count": call_count}
        
        executor.register_action("count_action", counting_action)
        
        steps = [
            ChainStep(step_id="step-1", name="Count", action="count_action"),
        ]
        
        # First execution
        executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        # Reset
        executor.reset_execution("brand-001", "inc-001", "plan-001")
        
        # Second execution after reset
        executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert call_count == 2

    def test_circular_dependency_detection(self):
        """Deve detectar dependências circulares."""
        executor = RecoveryChainExecutor()
        executor.register_action("action", lambda ctx: {"ok": True})
        
        steps = [
            ChainStep(step_id="a", name="A", action="action", depends_on=["b"]),
            ChainStep(step_id="b", name="B", action="action", depends_on=["a"]),
        ]
        
        result = executor.execute_chain(
            plan_id="plan-001",
            brand_id="brand-001",
            incident_id="inc-001",
            steps=steps,
        )
        
        assert result.status == StepStatus.FAILED
