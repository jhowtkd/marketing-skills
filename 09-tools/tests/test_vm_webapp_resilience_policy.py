from pathlib import Path
import pytest
from vm_webapp.resilience import ResiliencePolicy, FallbackChain, ResilienceDecision


def test_retry_policy_transitions_to_fallback_after_max_attempts() -> None:
    policy = ResiliencePolicy(max_attempts=3)
    
    # Attempt 1 failed
    decision = policy.next_action(attempt=1, retryable=True)
    assert decision.action == "retry"
    assert decision.delay_seconds > 0
    
    # Attempt 2 failed
    decision = policy.next_action(attempt=2, retryable=True)
    assert decision.action == "retry"
    
    # Attempt 3 failed -> transitions to fallback (or fail if no fallback)
    decision = policy.next_action(attempt=3, retryable=True)
    assert decision.action == "fallback"

def test_retry_policy_fails_immediately_if_not_retryable() -> None:
    policy = ResiliencePolicy(max_attempts=3)
    decision = policy.next_action(attempt=1, retryable=False)
    assert decision.action == "fallback"

def test_fallback_chain_transitions_correctly() -> None:
    chain = FallbackChain(providers=["gpt-4", "claude-3", "llama-3"])
    
    assert chain.next_provider("gpt-4") == "claude-3"
    assert chain.next_provider("claude-3") == "llama-3"
    
    with pytest.raises(ValueError, match="no more fallback providers"):
        chain.next_provider("llama-3")

def test_fallback_chain_raises_on_unknown_provider() -> None:
    chain = FallbackChain(providers=["gpt-4"])
    with pytest.raises(ValueError, match="no more fallback providers"):
        chain.next_provider("unknown")

def test_circuit_breaker_blocks_execution_after_threshold() -> None:
    from vm_webapp.resilience import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=2)
    
    assert cb.can_execute() is True
    
    cb.record_failure()
    assert cb.can_execute() is True
    
    cb.record_failure()
    assert cb.can_execute() is False
    
    cb.record_success()
    assert cb.can_execute() is True
