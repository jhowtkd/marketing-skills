"""Auto-remediation system for editorial governance.

Provides safe automatic remediation with kill switch, rate limiting,
and audit logging.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

# Actions considered "safe" for automatic execution
SAFE_AUTO_ACTIONS = {
    "open_review_task",
    "prepare_guided_regeneration",
}

# Actions requiring manual approval
MANUAL_ONLY_ACTIONS = {
    "suggest_policy_review",
}

AutoRemediationResult = Literal["executed", "skipped", "blocked", "rate_limited"]


@dataclass
class AutoRemediationDecision:
    """Result of auto-remediation decision."""
    result: AutoRemediationResult
    action_id: str | None
    reason: str
    should_audit: bool


def check_auto_remediation_eligible(
    action_id: str,
    brand_auto_enabled: bool,
) -> tuple[bool, str]:
    """Check if an action is eligible for auto-remediation.
    
    Args:
        action_id: The action to check
        brand_auto_enabled: Whether auto-remediation is enabled for the brand
        
    Returns:
        Tuple of (eligible, reason)
    """
    if not brand_auto_enabled:
        return False, "Auto-remediation disabled for brand (kill switch)"
    
    if action_id in MANUAL_ONLY_ACTIONS:
        return False, f"Action {action_id} requires manual approval"
    
    if action_id not in SAFE_AUTO_ACTIONS:
        return False, f"Action {action_id} not in safe auto-actions list"
    
    return True, "Eligible for auto-remediation"


def check_rate_limit(
    recent_events: list[dict],
    max_executions_per_hour: int = 10,
) -> tuple[bool, str]:
    """Check if rate limit allows another auto-remediation execution.
    
    Args:
        recent_events: Recent AutoRemediationExecuted events
        max_executions_per_hour: Maximum executions allowed per hour
        
    Returns:
        Tuple of (allowed, reason)
    """
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    
    # Count executions in the last hour
    executions_last_hour = 0
    for event in recent_events:
        occurred_at = event.get("occurred_at", "")
        try:
            event_time = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            if event_time > hour_ago:
                executions_last_hour += 1
        except (ValueError, TypeError):
            continue
    
    if executions_last_hour >= max_executions_per_hour:
        return False, f"Rate limit exceeded: {executions_last_hour}/{max_executions_per_hour} executions in last hour"
    
    remaining = max_executions_per_hour - executions_last_hour
    return True, f"Rate limit OK: {remaining} remaining"


def decide_auto_remediation(
    action_id: str,
    brand_auto_enabled: bool,
    recent_auto_events: list[dict],
    drift_severity: str,
    max_executions_per_hour: int = 10,
) -> AutoRemediationDecision:
    """Decide whether to execute auto-remediation.
    
    Args:
        action_id: The action to potentially execute
        brand_auto_enabled: Whether auto-remediation is enabled for the brand
        recent_auto_events: Recent auto-remediation events for rate limiting
        drift_severity: Current drift severity level
        max_executions_per_hour: Rate limit threshold
        
    Returns:
        AutoRemediationDecision with result and reason
    """
    # Check eligibility
    eligible, reason = check_auto_remediation_eligible(action_id, brand_auto_enabled)
    if not eligible:
        return AutoRemediationDecision(
            result="blocked",
            action_id=None,
            reason=reason,
            should_audit=True,
        )
    
    # Check rate limiting (stricter for low drift)
    if drift_severity in ["none", "low"]:
        max_executions_per_hour = max_executions_per_hour // 2  # More restrictive
    
    allowed, rate_reason = check_rate_limit(recent_auto_events, max_executions_per_hour)
    if not allowed:
        return AutoRemediationDecision(
            result="rate_limited",
            action_id=None,
            reason=rate_reason,
            should_audit=True,
        )
    
    return AutoRemediationDecision(
        result="executed",
        action_id=action_id,
        reason="Auto-remediation criteria met",
        should_audit=True,
    )


def build_auto_remediation_event_payload(
    thread_id: str,
    action_id: str,
    decision: AutoRemediationDecision,
    drift_score: int,
    run_id: str | None = None,
) -> dict:
    """Build event payload for auto-remediation execution.
    
    Args:
        thread_id: Thread ID
        action_id: The action executed
        decision: The auto-remediation decision
        drift_score: Current drift score
        run_id: Optional run ID for context
        
    Returns:
        Event payload dictionary
    """
    return {
        "thread_id": thread_id,
        "action_id": action_id,
        "run_id": run_id,
        "auto_executed": decision.result == "executed",
        "decision_reason": decision.reason,
        "drift_score": drift_score,
        "actor_role": "system:auto-remediation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_auto_remediation_skipped_payload(
    thread_id: str,
    proposed_action: str,
    decision: AutoRemediationDecision,
    drift_score: int,
) -> dict:
    """Build event payload for skipped auto-remediation.
    
    Args:
        thread_id: Thread ID
        proposed_action: The action that was considered
        decision: The auto-remediation decision
        drift_score: Current drift score
        
    Returns:
        Event payload dictionary
    """
    return {
        "thread_id": thread_id,
        "proposed_action": proposed_action,
        "auto_executed": False,
        "skip_reason": decision.reason,
        "drift_score": drift_score,
        "actor_role": "system:auto-remediation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
