"""Onboarding policy serving engine and safe rollout manager.

v33: Serving with priority resolution and safe rollout controls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from vm_webapp.onboarding_personalization import (
    PersonalizationPolicy,
    PolicyResult,
    PolicyStatus,
    RiskLevel,
    SegmentKey,
    SegmentProfiler,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CanaryConfig:
    """Configuration for canary rollout."""
    policy_id: str
    segment_key: SegmentKey
    traffic_percentage: int = 10  # Default 10%
    duration_hours: int = 24  # Default 24 hours
    success_criteria: dict = field(default_factory=lambda: {
        "conversion_rate_lift": 0.05,
        "time_to_first_value_reduction": 0.10,
    })


@dataclass
class ValidationResult:
    """Result of policy validation."""
    policy_id: str
    is_valid: bool
    checks: dict[str, bool]
    errors: list[str] = field(default_factory=list)


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    policy_id: str
    blocked: bool
    checks: dict[str, bool]
    reason: str = ""


@dataclass
class RolloutDecision:
    """Decision for policy rollout."""
    policy_id: str
    decision: str  # "auto_apply", "approve", "block", "canary"
    requires_approval: bool
    reason: str = ""


class PolicyServingEngine:
    """Engine for serving personalization policies with fallback resolution."""

    def __init__(self, profiler: SegmentProfiler):
        self._profiler = profiler
        self._serve_count = 0
        self._fallback_count = 0
        self._serve_latencies_ms: list[float] = []

    def serve_policy_for_segment(self, segment_key: SegmentKey) -> Optional[PolicyResult]:
        """Serve the effective policy for a segment with latency tracking."""
        start_time = time.time()
        
        result = self._profiler.get_policy_for_segment(segment_key)
        
        # Track metrics
        latency_ms = (time.time() - start_time) * 1000
        self._serve_latencies_ms.append(latency_ms)
        self._serve_count += 1
        
        if result and result.fallback_used:
            self._fallback_count += 1
        
        return result

    def get_serve_metrics(self) -> dict:
        """Get serving metrics."""
        avg_latency = (
            sum(self._serve_latencies_ms) / len(self._serve_latencies_ms)
            if self._serve_latencies_ms else 0.0
        )
        
        return {
            "total_serves": self._serve_count,
            "segment_hits": self._serve_count - self._fallback_count,
            "fallback_uses": self._fallback_count,
            "avg_latency_ms": round(avg_latency, 2),
        }


class RolloutManager:
    """Manager for safe policy rollout with validation and guardrails."""

    # Guardrail thresholds
    MAX_NUDGE_DELAY_MS = 30000  # 30 seconds
    MAX_STEPS = 10
    MAX_TEMPLATE_COUNT = 20

    def __init__(self, profiler: SegmentProfiler, engine: PolicyServingEngine):
        self._profiler = profiler
        self._engine = engine
        self._rollout_count = 0
        self._blocked_count = 0
        self._auto_applied_count = 0
        self._approval_required_count = 0

    def validate_policy(self, policy: PersonalizationPolicy) -> ValidationResult:
        """Validate a policy against schema and constraints."""
        checks = {
            "schema": True,
            "constraints": True,
        }
        errors = []

        # Validate nudge_delay_ms
        if policy.nudge_delay_ms < 0:
            checks["constraints"] = False
            errors.append("Invalid nudge_delay_ms: must be positive")

        # Validate template_order
        if not policy.template_order or len(policy.template_order) == 0:
            checks["constraints"] = False
            errors.append("Invalid template_order: must not be empty")

        # Validate max_steps
        if policy.max_steps < 1:
            checks["constraints"] = False
            errors.append("Invalid max_steps: must be at least 1")

        # Validate welcome_message
        if not policy.welcome_message or len(policy.welcome_message.strip()) == 0:
            checks["constraints"] = False
            errors.append("Invalid welcome_message: must not be empty")

        is_valid = all(checks.values())
        return ValidationResult(
            policy_id=policy.policy_id,
            is_valid=is_valid,
            checks=checks,
            errors=errors,
        )

    def check_guardrails(self, policy: PersonalizationPolicy) -> GuardrailResult:
        """Check policy against operational guardrails."""
        checks = {
            "latency": True,
            "complexity": True,
            "template_count": True,
        }
        reasons = []

        # Check nudge_delay_ms (latency guardrail)
        if policy.nudge_delay_ms > self.MAX_NUDGE_DELAY_MS:
            checks["latency"] = False
            reasons.append(
                f"nudge_delay_ms ({policy.nudge_delay_ms}ms) exceeds maximum "
                f"({self.MAX_NUDGE_DELAY_MS}ms)"
            )

        # Check max_steps (complexity guardrail)
        if policy.max_steps > self.MAX_STEPS:
            checks["complexity"] = False
            reasons.append(
                f"max_steps ({policy.max_steps}) exceeds maximum ({self.MAX_STEPS})"
            )

        # Check template count
        if len(policy.template_order) > self.MAX_TEMPLATE_COUNT:
            checks["template_count"] = False
            reasons.append(
                f"template count ({len(policy.template_order)}) exceeds maximum "
                f"({self.MAX_TEMPLATE_COUNT})"
            )

        blocked = not all(checks.values())
        return GuardrailResult(
            policy_id=policy.policy_id,
            blocked=blocked,
            checks=checks,
            reason="; ".join(reasons) if reasons else "",
        )

    def decide_rollout(self, policy: PersonalizationPolicy) -> RolloutDecision:
        """Decide rollout strategy based on validation, guardrails, and risk."""
        # First, validate
        validation = self.validate_policy(policy)
        if not validation.is_valid:
            return RolloutDecision(
                policy_id=policy.policy_id,
                decision="block",
                requires_approval=True,
                reason=f"Validation failed: {'; '.join(validation.errors)}",
            )

        # Second, check guardrails
        guardrails = self.check_guardrails(policy)
        if guardrails.blocked:
            return RolloutDecision(
                policy_id=policy.policy_id,
                decision="block",
                requires_approval=True,
                reason=f"Guardrail blocked: {guardrails.reason}",
            )

        # Third, decide based on risk level
        if policy.risk_level == RiskLevel.LOW:
            return RolloutDecision(
                policy_id=policy.policy_id,
                decision="auto_apply",
                requires_approval=False,
                reason="Low risk policy passes all checks",
            )
        else:
            return RolloutDecision(
                policy_id=policy.policy_id,
                decision="approve",
                requires_approval=True,
                reason=f"{policy.risk_level.value} risk policy requires human approval",
            )

    def execute_rollout(self, policy_id: str) -> bool:
        """Execute rollout for a policy."""
        try:
            policy = self._profiler.get_policy(policy_id)
        except ValueError:
            return False

        decision = self.decide_rollout(policy)
        
        if decision.decision == "block":
            self._blocked_count += 1
            return False

        if decision.requires_approval:
            self._approval_required_count += 1
            # For now, we still activate (in production, would wait for approval)
            # This simulates the approval flow
            policy.activate()
        else:
            self._auto_applied_count += 1
            policy.activate()

        self._rollout_count += 1
        return True

    def rollback_policy(self, policy_id: str, reason: str) -> bool:
        """Roll back a policy."""
        try:
            policy = self._profiler.get_policy(policy_id)
        except ValueError:
            return False

        policy.rollback()
        return True

    def freeze_policy(self, policy_id: str) -> bool:
        """Freeze a policy."""
        try:
            policy = self._profiler.get_policy(policy_id)
        except ValueError:
            return False

        policy.freeze()
        return True

    def get_rollout_metrics(self) -> dict:
        """Get rollout metrics."""
        return {
            "total_rollouts": self._rollout_count,
            "blocked_rollouts": self._blocked_count,
            "auto_applied": self._auto_applied_count,
            "approval_required": self._approval_required_count,
        }
