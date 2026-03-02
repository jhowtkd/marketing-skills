"""Onboarding personalization segment profiler and policy model.

v33: Personalization by segment with deterministic serving and safe rollout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RiskLevel(str, Enum):
    """Risk level for policy promotion decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PolicyStatus(str, Enum):
    """Status of a personalization policy."""
    DRAFT = "draft"
    ACTIVE = "active"
    FROZEN = "frozen"
    ROLLED_BACK = "rolled_back"


@dataclass
class SegmentKey:
    """Key for identifying a user segment."""
    company_size: str = "unknown"
    industry: str = "unknown"
    experience_level: str = "unknown"
    traffic_source: str = "unknown"

    @classmethod
    def from_profile(cls, profile: dict) -> "SegmentKey":
        """Derive segment key from user profile."""
        return cls(
            company_size=profile.get("company_size", "unknown"),
            industry=profile.get("industry", "unknown"),
            experience_level=profile.get("experience_level", "unknown"),
            traffic_source=profile.get("traffic_source", "unknown"),
        )

    def __str__(self) -> str:
        return f"{self.company_size}:{self.industry}:{self.experience_level}:{self.traffic_source}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SegmentKey):
            return False
        return (
            self.company_size == other.company_size
            and self.industry == other.industry
            and self.experience_level == other.experience_level
            and self.traffic_source == other.traffic_source
        )

    def __hash__(self) -> int:
        return hash(str(self))

    def is_wildcard(self) -> bool:
        """Check if this is a wildcard (brand-level) key."""
        return all(
            v == "*"
            for v in [self.company_size, self.industry, self.experience_level, self.traffic_source]
        )


@dataclass
class PersonalizationPolicy:
    """A personalization policy for a specific segment."""
    policy_id: str
    segment_key: Optional[SegmentKey]  # None = global policy
    nudge_delay_ms: int
    template_order: list[str]
    welcome_message: str
    show_video_tutorial: bool
    max_steps: int
    risk_level: RiskLevel
    status: PolicyStatus = field(default=PolicyStatus.DRAFT)
    created_at: str = field(default_factory=_now_iso)
    activated_at: Optional[str] = field(default=None)
    frozen_at: Optional[str] = field(default=None)
    rolled_back_at: Optional[str] = field(default=None)

    def activate(self) -> None:
        """Activate the policy."""
        self.status = PolicyStatus.ACTIVE
        self.activated_at = _now_iso()

    def freeze(self) -> None:
        """Freeze the policy."""
        self.status = PolicyStatus.FROZEN
        self.frozen_at = _now_iso()

    def rollback(self) -> None:
        """Roll back the policy."""
        self.status = PolicyStatus.ROLLED_BACK
        self.rolled_back_at = _now_iso()

    def requires_approval(self) -> bool:
        """Check if this policy requires human approval for promotion."""
        return self.risk_level != RiskLevel.LOW

    def get_level(self) -> str:
        """Get the policy level: segment, brand, or global."""
        if self.segment_key is None:
            return "global"
        if self.segment_key.is_wildcard():
            return "brand"
        return "segment"


@dataclass
class PolicyResult:
    """Result of policy lookup with source information."""
    policy: PersonalizationPolicy
    source: str  # "segment", "brand", or "global"
    fallback_used: bool = False


@dataclass
class SegmentMetrics:
    """Metrics compiled for a segment."""
    segment_key: str
    conversion_rate: float
    time_to_first_value_ms: float
    nudge_acceptance_rate: float
    dropoff_rate: float
    compiled_at: str = field(default_factory=_now_iso)


class SegmentProfiler:
    """Profiler for onboarding segments with policy management."""

    def __init__(self):
        self._policies: dict[str, PersonalizationPolicy] = {}
        self._segment_metrics: dict[str, SegmentMetrics] = {}

    def register_policy(self, policy: PersonalizationPolicy) -> None:
        """Register a new policy."""
        if policy.policy_id in self._policies:
            raise ValueError(f"Policy already registered: {policy.policy_id}")
        self._policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> PersonalizationPolicy:
        """Get a policy by ID."""
        if policy_id not in self._policies:
            raise ValueError(f"Policy not found: {policy_id}")
        return self._policies[policy_id]

    def get_policy_count(self) -> int:
        """Get total number of registered policies."""
        return len(self._policies)

    def list_policies(self) -> list[PersonalizationPolicy]:
        """List all registered policies."""
        return list(self._policies.values())

    def list_active_policies(self) -> list[PersonalizationPolicy]:
        """List only active policies."""
        return [p for p in self._policies.values() if p.status == PolicyStatus.ACTIVE]

    def get_policy_for_segment(self, segment_key: SegmentKey) -> Optional[PolicyResult]:
        """Get the effective policy for a segment with fallback resolution.
        
        Priority: segment > brand > global
        """
        # First, try exact segment match
        for policy in self._policies.values():
            if (
                policy.status == PolicyStatus.ACTIVE
                and policy.segment_key == segment_key
                and not policy.segment_key.is_wildcard()
            ):
                return PolicyResult(policy, "segment", False)

        # Second, try brand-level (wildcard) match
        for policy in self._policies.values():
            if (
                policy.status == PolicyStatus.ACTIVE
                and policy.segment_key is not None
                and policy.segment_key.is_wildcard()
            ):
                return PolicyResult(policy, "brand", True)

        # Third, try global policy
        for policy in self._policies.values():
            if policy.status == PolicyStatus.ACTIVE and policy.segment_key is None:
                return PolicyResult(policy, "global", True)

        return None

    def compile_segment_metrics(
        self,
        segment_key: SegmentKey,
        metrics: dict,
    ) -> SegmentMetrics:
        """Compile metrics for a segment."""
        compiled = SegmentMetrics(
            segment_key=str(segment_key),
            conversion_rate=metrics.get("conversion_rate", 0.0),
            time_to_first_value_ms=metrics.get("time_to_first_value_ms", 0.0),
            nudge_acceptance_rate=metrics.get("nudge_acceptance_rate", 0.0),
            dropoff_rate=metrics.get("dropoff_rate", 0.0),
        )
        self._segment_metrics[str(segment_key)] = compiled
        return compiled

    def get_segment_metrics(self, segment_key: SegmentKey) -> Optional[SegmentMetrics]:
        """Get compiled metrics for a segment."""
        return self._segment_metrics.get(str(segment_key))

    def clear(self) -> None:
        """Clear all policies and metrics (for testing)."""
        self._policies.clear()
        self._segment_metrics.clear()
