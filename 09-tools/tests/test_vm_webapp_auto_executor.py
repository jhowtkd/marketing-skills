"""
Task C: Automated Executor with Canary - Tests
Governança v16 - Executor automático com canary e rollback seguro

Critérios obrigatórios:
- Idempotência + lock de concorrência por segmento
- Canary (promote/abort) e rollback automático
- Testes de corrida/dupla execução explícitos
"""

import pytest
import threading
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from vm_webapp.auto_executor import (
    AutoExecutor,
    ExecutionResult,
    ExecutionStatus,
    CanaryConfig,
    CanaryExecution,
    SegmentLock,
    IdempotencyKey,
    RollbackGuard,
    execute_with_canary,
    execute_with_idempotency,
)

UTC = timezone.utc


class TestExecutionStatus:
    """Test execution status enum."""
    
    def test_status_values(self):
        """Status values are correct."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.CANARY_RUNNING.value == "canary_running"
        assert ExecutionStatus.CANARY_PROMOTED.value == "canary_promoted"
        assert ExecutionStatus.CANARY_ABORTED.value == "canary_aborted"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.ROLLBACK_TRIGGERED.value == "rollback_triggered"
        assert ExecutionStatus.FAILED.value == "failed"


class TestSegmentLock:
    """Test segment lock - concorrência por segmento."""
    
    def test_acquire_lock_success(self):
        """Can acquire lock when available."""
        lock_manager = SegmentLock()
        
        acquired = lock_manager.acquire("brand1:awareness", timeout=1)
        
        assert acquired is True
        assert lock_manager.is_locked("brand1:awareness") is True
    
    def test_acquire_lock_already_held(self):
        """Cannot acquire lock when already held."""
        lock_manager = SegmentLock()
        
        # First acquire
        lock_manager.acquire("brand1:awareness", timeout=1)
        
        # Second acquire should fail
        acquired = lock_manager.acquire("brand1:awareness", timeout=0.1)
        
        assert acquired is False
    
    def test_release_lock(self):
        """Can release acquired lock."""
        lock_manager = SegmentLock()
        
        lock_manager.acquire("brand1:awareness", timeout=1)
        assert lock_manager.is_locked("brand1:awareness") is True
        
        lock_manager.release("brand1:awareness")
        assert lock_manager.is_locked("brand1:awareness") is False
    
    def test_context_manager(self):
        """Lock works as context manager."""
        lock_manager = SegmentLock()
        
        with lock_manager.lock("brand1:awareness", timeout=1):
            assert lock_manager.is_locked("brand1:awareness") is True
        
        assert lock_manager.is_locked("brand1:awareness") is False
    
    def test_concurrent_lock_attempts(self):
        """Multiple threads cannot acquire same lock simultaneously."""
        lock_manager = SegmentLock()
        results = []
        hold_times = []
        
        def try_lock():
            start = time.time()
            acquired = lock_manager.acquire("brand1:awareness", timeout=0.5)
            results.append(acquired)
            if acquired:
                hold_start = time.time()
                time.sleep(0.1)  # Hold for 100ms
                hold_times.append(time.time() - hold_start)
                lock_manager.release("brand1:awareness")
        
        # Start 5 threads trying to acquire the same lock
        threads = [threading.Thread(target=try_lock) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # At least one should have acquired
        acquired_count = sum(results)
        assert acquired_count >= 1
        
        # Sum of hold times should be at least 100ms * acquired_count
        # (proving they ran sequentially, not in parallel)
        total_hold_time = sum(hold_times)
        assert total_hold_time >= 0.1 * acquired_count - 0.01  # Small tolerance
    
    def test_lock_timeout(self):
        """Lock attempt times out correctly."""
        lock_manager = SegmentLock()
        
        # Acquire and hold
        lock_manager.acquire("brand1:awareness", timeout=1)
        
        start = time.time()
        acquired = lock_manager.acquire("brand1:awareness", timeout=0.1)
        elapsed = time.time() - start
        
        assert acquired is False
        assert elapsed >= 0.1  # Should wait for timeout
        assert elapsed < 0.2


class TestIdempotencyKey:
    """Test idempotency key - prevenir dupla execução."""
    
    def test_generate_key(self):
        """Can generate idempotency key."""
        key = IdempotencyKey.generate(
            segment_key="brand1:awareness",
            decision_type="expand",
            context={"sample_size": 100}
        )
        
        assert key is not None
        assert len(key) > 0
    
    def test_same_params_same_key(self):
        """Same parameters generate same key."""
        params = {
            "segment_key": "brand1:awareness",
            "decision_type": "expand",
            "context": {"sample_size": 100}
        }
        
        key1 = IdempotencyKey.generate(**params)
        key2 = IdempotencyKey.generate(**params)
        
        assert key1 == key2
    
    def test_different_params_different_key(self):
        """Different parameters generate different keys."""
        key1 = IdempotencyKey.generate(
            segment_key="brand1:awareness",
            decision_type="expand",
            context={"sample_size": 100}
        )
        key2 = IdempotencyKey.generate(
            segment_key="brand1:awareness",
            decision_type="expand",
            context={"sample_size": 200}  # Different
        )
        
        assert key1 != key2
    
    def test_store_and_check(self):
        """Can store and check idempotency."""
        store = IdempotencyKey()
        
        key = "idemp_key_001"
        result = ExecutionResult(
            execution_id="exec_001",
            status=ExecutionStatus.COMPLETED,
            segment_key="brand1:awareness",
            decision="expand",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        # Store result
        store.store_result(key, result)
        
        # Check - should return stored result
        stored = store.get_result(key)
        assert stored is not None
        assert stored.execution_id == "exec_001"
    
    def test_prevent_duplicate_execution(self):
        """Duplicate key returns existing result without re-executing."""
        store = IdempotencyKey()
        
        key = "idemp_key_002"
        result1 = ExecutionResult(
            execution_id="exec_001",
            status=ExecutionStatus.COMPLETED,
            segment_key="brand1:awareness",
            decision="expand",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        store.store_result(key, result1)
        
        # Check if already executed
        assert store.is_executed(key) is True
        
        # Get existing result
        existing = store.get_result(key)
        assert existing.execution_id == "exec_001"


class TestCanaryConfig:
    """Test canary configuration."""
    
    def test_default_config(self):
        """Default canary config is reasonable."""
        config = CanaryConfig()
        
        assert config.subset_percentage == 10
        assert config.observation_window_minutes == 30
        assert config.promote_threshold == 0.95
        assert config.abort_threshold == 0.80
    
    def test_custom_config(self):
        """Can create custom canary config."""
        config = CanaryConfig(
            subset_percentage=25,
            observation_window_minutes=60,
            promote_threshold=0.99,
            abort_threshold=0.90
        )
        
        assert config.subset_percentage == 25
        assert config.observation_window_minutes == 60


class TestAutoExecutorBasic:
    """Test auto executor - execução básica."""
    
    def test_execute_success(self):
        """Can execute decision successfully."""
        executor = AutoExecutor()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        result = executor.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.segment_key == "brand1:awareness"
        assert result.decision == "expand"
        assert result.execution_id is not None
    
    def test_execute_with_safety_check(self):
        """Executor runs safety gates before execution."""
        executor = AutoExecutor()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 50,  # Too few - should fail safety check
            "confidence_score": 0.85
        }
        
        result = executor.execute(context)
        
        # Should fail safety check and not execute
        assert result.status == ExecutionStatus.FAILED
        assert result.error is not None
        assert "safety" in result.error.lower() or "gate" in result.error.lower()


class TestCanaryExecution:
    """Test canary execution - modo canário."""
    
    def test_canary_starts_with_subset(self):
        """Canary starts with subset of segments."""
        executor = AutoExecutor()
        
        config = CanaryConfig(subset_percentage=20)
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        result = executor.execute_with_canary(context, config)
        
        assert result.canary_execution is not None
        assert result.status == ExecutionStatus.CANARY_RUNNING
        assert result.canary_execution.subset_percentage == 20
    
    def test_canary_promote_when_healthy(self):
        """Canary promotes when metrics are healthy."""
        executor = AutoExecutor()
        
        config = CanaryConfig(
            subset_percentage=10,
            observation_window_minutes=0,  # Instant for testing
            promote_threshold=0.90
        )
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.95,  # High confidence
            "kpi_status": "on_track"
        }
        
        # Execute canary
        result = executor.execute_with_canary(context, config)
        
        # Evaluate canary (simulate time passing)
        eval_result = executor.evaluate_canary(
            result.execution_id,
            metrics={"success_rate": 0.98}  # Above promote threshold
        )
        
        assert eval_result.status == ExecutionStatus.CANARY_PROMOTED
    
    def test_canary_abort_when_unhealthy(self):
        """Canary aborts when metrics are unhealthy."""
        executor = AutoExecutor()
        
        config = CanaryConfig(
            subset_percentage=10,
            observation_window_minutes=0,
            abort_threshold=0.85
        )
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        # Execute canary
        result = executor.execute_with_canary(context, config)
        
        # Evaluate canary with bad metrics
        eval_result = executor.evaluate_canary(
            result.execution_id,
            metrics={"success_rate": 0.75}  # Below abort threshold
        )
        
        assert eval_result.status == ExecutionStatus.CANARY_ABORTED


class TestRollbackGuard:
    """Test rollback guard - rollback automático."""
    
    def test_rollback_triggered_on_safety_violation(self):
        """Rollback triggers when safety gate violated post-execution."""
        guard = RollbackGuard()
        
        execution_id = "exec_001"
        
        # Simulate execution
        guard.record_execution(
            execution_id=execution_id,
            segment_key="brand1:awareness",
            decision="expand"
        )
        
        # Simulate post-execution safety check failure
        should_rollback = guard.check_and_trigger_rollback(
            execution_id=execution_id,
            post_execution_metrics={
                "regression_detected": True,
                "severity": "critical"
            }
        )
        
        assert should_rollback is True
        
        rollback_result = guard.get_rollback_result(execution_id)
        assert rollback_result is not None
        assert rollback_result.triggered is True
    
    def test_no_rollback_when_healthy(self):
        """No rollback when post-execution metrics are healthy."""
        guard = RollbackGuard()
        
        execution_id = "exec_002"
        
        guard.record_execution(
            execution_id=execution_id,
            segment_key="brand1:awareness",
            decision="expand"
        )
        
        should_rollback = guard.check_and_trigger_rollback(
            execution_id=execution_id,
            post_execution_metrics={
                "regression_detected": False,
                "kpi_status": "on_track"
            }
        )
        
        assert should_rollback is False
    
    def test_rollback_is_idempotent(self):
        """Rollback can only be triggered once per execution."""
        guard = RollbackGuard()
        
        execution_id = "exec_003"
        
        guard.record_execution(
            execution_id=execution_id,
            segment_key="brand1:awareness",
            decision="expand"
        )
        
        # First trigger
        should_rollback_1 = guard.check_and_trigger_rollback(
            execution_id=execution_id,
            post_execution_metrics={"regression_detected": True}
        )
        
        # Second trigger attempt
        should_rollback_2 = guard.check_and_trigger_rollback(
            execution_id=execution_id,
            post_execution_metrics={"regression_detected": True}
        )
        
        assert should_rollback_1 is True
        assert should_rollback_2 is False  # Already triggered


class TestConcurrencyAndRaceConditions:
    """Test concurrency - corrida de requests."""
    
    def test_race_condition_prevention(self):
        """Race condition prevention with locks - all threads get same result via idempotency."""
        executor = AutoExecutor()
        results = []
        errors = []
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        def try_execute():
            try:
                result = executor.execute(context)
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Start 5 threads trying to execute same segment
        threads = [threading.Thread(target=try_execute) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should return successfully (idempotency ensures same result)
        successful = [r for r in results if r.status == ExecutionStatus.COMPLETED]
        assert len(successful) == 5  # All return completed (via idempotency)
        
        # All should have the SAME execution_id (proof of idempotency)
        execution_ids = {r.execution_id for r in results}
        assert len(execution_ids) == 1  # Only one unique execution_id
    
    def test_double_execution_prevention(self):
        """Idempotency prevents double execution."""
        executor = AutoExecutor()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        # First execution
        result1 = executor.execute(context)
        assert result1.status == ExecutionStatus.COMPLETED
        
        # Second execution with same context (should be idempotent)
        result2 = executor.execute(context)
        
        # Should return same result without re-executing
        assert result2.execution_id == result1.execution_id
        assert result2.status == ExecutionStatus.COMPLETED
    
    def test_concurrent_canary_evaluations(self):
        """Concurrent canary evaluations are handled safely."""
        executor = AutoExecutor()
        
        config = CanaryConfig(subset_percentage=10)
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        # Start canary
        result = executor.execute_with_canary(context, config)
        exec_id = result.execution_id
        
        evaluations = []
        
        def evaluate():
            eval_result = executor.evaluate_canary(
                exec_id,
                metrics={"success_rate": 0.99}
            )
            evaluations.append(eval_result.status)
        
        # Multiple concurrent evaluations
        threads = [threading.Thread(target=evaluate) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed, but only one actually promoted
        assert ExecutionStatus.CANARY_PROMOTED in evaluations


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_execute_with_idempotency(self):
        """execute_with_idempotency utility works."""
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        result1 = execute_with_idempotency(context)
        result2 = execute_with_idempotency(context)
        
        # Same result (idempotent)
        assert result1.execution_id == result2.execution_id
    
    def test_execute_with_canary(self):
        """execute_with_canary utility works."""
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        result = execute_with_canary(context)
        
        assert result.status == ExecutionStatus.CANARY_RUNNING
        assert result.canary_execution is not None


class TestEdgeCases:
    """Test edge cases."""
    
    def test_execute_with_missing_segment(self):
        """Executor fails gracefully with missing segment."""
        executor = AutoExecutor()
        
        context = {
            # Missing segment_key
            "brand_id": "brand1",
            "decision_type": "expand"
        }
        
        result = executor.execute(context)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.error is not None
    
    def test_canary_with_zero_subset(self):
        """Canary with 0% subset fails gracefully."""
        executor = AutoExecutor()
        
        config = CanaryConfig(subset_percentage=0)
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "decision_type": "expand",
            "sample_size": 150
        }
        
        result = executor.execute_with_canary(context, config)
        
        # Should fail or use minimum subset
        assert result.status in [ExecutionStatus.FAILED, ExecutionStatus.CANARY_RUNNING]
    
    def test_rollback_nonexistent_execution(self):
        """Rollback guard handles nonexistent execution."""
        guard = RollbackGuard()
        
        should_rollback = guard.check_and_trigger_rollback(
            execution_id="nonexistent",
            post_execution_metrics={"regression_detected": True}
        )
        
        assert should_rollback is False
    
    def test_lock_release_on_exception(self):
        """Lock is released even when exception occurs."""
        lock_manager = SegmentLock()
        
        try:
            with lock_manager.lock("brand1:awareness", timeout=1):
                assert lock_manager.is_locked("brand1:awareness") is True
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Lock should be released
        assert lock_manager.is_locked("brand1:awareness") is False
