from dataclasses import dataclass
from typing import Literal

@dataclass(slots=True, frozen=True)
class ResilienceDecision:
    action: Literal["retry", "fallback", "fail"]
    delay_seconds: int = 0

class ResiliencePolicy:
    def __init__(self, max_attempts: int, backoff_base: int = 2):
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base

    def next_action(self, attempt: int, retryable: bool) -> ResilienceDecision:
        if not retryable or attempt >= self.max_attempts:
            return ResilienceDecision(action="fallback")
        
        delay = self.backoff_base ** attempt
        return ResilienceDecision(action="retry", delay_seconds=delay)

class FallbackChain:
    def __init__(self, providers: list[str]):
        self.providers = providers

    def next_provider(self, current_provider: str) -> str:
        try:
            idx = self.providers.index(current_provider)
            if idx + 1 < len(self.providers):
                return self.providers[idx + 1]
        except ValueError:
            pass
        raise ValueError("no more fallback providers")

class CircuitBreaker:
    def __init__(self, failure_threshold: int):
        self.failure_threshold = failure_threshold
        self.failure_count = 0

    def can_execute(self) -> bool:
        return self.failure_count < self.failure_threshold

    def record_failure(self) -> None:
        self.failure_count += 1

    def record_success(self) -> None:
        self.failure_count = 0
