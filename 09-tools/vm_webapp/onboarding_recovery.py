"""Onboarding recovery and reactivation dropoff detection.

v34: Detect -> prioritize -> propose -> apply/review -> measure cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(timestamp: str) -> datetime:
    """Parse ISO format timestamp."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


class DropoffReason(str, Enum):
    """Reason for user dropoff during onboarding."""
    ABANDONED_STEP = "abandoned_step"
    TIMEOUT = "timeout"
    ERROR = "error"
    EXTERNAL_INTERRUPTION = "external_interruption"
    USER_INITIATED_EXIT = "user_initiated_exit"


class RecoveryCaseStatus(str, Enum):
    """Status of a recovery case."""
    ACTIVE = "active"
    RECOVERABLE = "recoverable"
    RECOVERED = "recovered"
    EXPIRED = "expired"


class RecoveryPriority(str, Enum):
    """Priority level for recovery case."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RecoveryCase:
    """A recovery case for a user who dropped off during onboarding."""
    
    case_id: str
    user_id: str
    brand_id: str
    reason: DropoffReason
    status: RecoveryCaseStatus
    priority: RecoveryPriority
    current_step: int
    total_steps: int
    dropoff_at: str = field(default_factory=_now_iso)
    recovered_at: Optional[str] = field(default=None)
    expires_at: Optional[str] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def progress_percentage(self) -> float:
        """Calculate onboarding progress percentage at dropoff."""
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100

    def is_late_stage(self) -> bool:
        """Check if dropoff occurred in late stage (>70% complete)."""
        return self.progress_percentage() >= 70

    def to_dict(self) -> dict:
        """Convert case to dictionary representation."""
        return {
            "case_id": self.case_id,
            "user_id": self.user_id,
            "brand_id": self.brand_id,
            "reason": self.reason.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percentage": self.progress_percentage(),
            "is_late_stage": self.is_late_stage(),
            "dropoff_at": self.dropoff_at,
            "recovered_at": self.recovered_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }


class DropoffDetector:
    """Detects onboarding dropoffs and manages recovery cases."""

    # Configuration thresholds
    STEP_ABANDONMENT_THRESHOLD_MINUTES = 60  # 1 hour without activity
    SESSION_TIMEOUT_HOURS = 24
    RECOVERY_EXPIRY_DAYS = 7
    LATE_STAGE_THRESHOLD = 70  # Percentage

    def __init__(self) -> None:
        """Initialize detector with empty case registry."""
        self._cases: Dict[str, RecoveryCase] = {}

    def detect_dropoff(self, session: Dict[str, Any]) -> Optional[RecoveryCase]:
        """Detect if a session represents a dropoff.
        
        Args:
            session: User session data with activity timestamps
            
        Returns:
            RecoveryCase if dropoff detected, None otherwise
        """
        user_id = session.get("user_id")
        if not user_id:
            return None

        # Check for error-induced dropoff
        if session.get("error_occurred"):
            return self._create_case(session, DropoffReason.ERROR)

        # Check for session timeout
        last_activity = session.get("last_activity")
        if last_activity:
            last_activity_dt = _parse_iso(last_activity)
            hours_since_activity = (datetime.now(timezone.utc) - last_activity_dt).total_seconds() / 3600
            
            if hours_since_activity >= self.SESSION_TIMEOUT_HOURS:
                return self._create_case(session, DropoffReason.TIMEOUT)

        # Check for step abandonment
        step_start = session.get("step_start_time")
        if step_start:
            step_start_dt = _parse_iso(step_start)
            minutes_on_step = (datetime.now(timezone.utc) - step_start_dt).total_seconds() / 60
            
            if minutes_on_step >= self.STEP_ABANDONMENT_THRESHOLD_MINUTES:
                return self._create_case(session, DropoffReason.ABANDONED_STEP)

        return None

    def _create_case(
        self, 
        session: Dict[str, Any], 
        reason: DropoffReason
    ) -> RecoveryCase:
        """Create a recovery case from session data."""
        priority = self._calculate_priority(session, reason)
        
        case = RecoveryCase(
            case_id=f"case-{uuid.uuid4().hex[:8]}",
            user_id=session["user_id"],
            brand_id=session.get("brand_id", "unknown"),
            reason=reason,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=priority,
            current_step=session.get("current_step", 0),
            total_steps=session.get("total_steps", 7),
            metadata={
                "last_activity": session.get("last_activity"),
                "step_start_time": session.get("step_start_time"),
                "error_code": session.get("error_code"),
            }
        )
        
        # Set expiration based on priority
        expiry_days = {
            RecoveryPriority.HIGH: 3,
            RecoveryPriority.MEDIUM: 5,
            RecoveryPriority.LOW: 7,
        }.get(priority, 7)
        
        expiry_dt = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        case.expires_at = expiry_dt.isoformat()
        
        self.register_case(case)
        return case

    def _calculate_priority(
        self, 
        session: Dict[str, Any], 
        reason: DropoffReason
    ) -> RecoveryPriority:
        """Calculate recovery priority based on session context.
        
        High priority: late-stage dropoffs, errors
        Medium priority: mid-stage abandonment
        Low priority: early-stage timeout
        """
        current_step = session.get("current_step", 0)
        total_steps = session.get("total_steps", 7)
        progress = (current_step / total_steps) * 100 if total_steps > 0 else 0

        # Errors are always high priority
        if reason == DropoffReason.ERROR:
            return RecoveryPriority.HIGH

        # Late-stage dropoffs (>70%) are high priority
        if progress >= self.LATE_STAGE_THRESHOLD:
            return RecoveryPriority.HIGH

        # Mid-stage (30-70%) is medium priority
        if progress >= 30:
            return RecoveryPriority.MEDIUM

        # Early-stage (<30%) is low priority
        return RecoveryPriority.LOW

    def register_case(self, case: RecoveryCase) -> None:
        """Register a recovery case."""
        self._cases[case.case_id] = case

    def get_case(self, case_id: str) -> Optional[RecoveryCase]:
        """Get a specific recovery case by ID."""
        return self._cases.get(case_id)

    def get_recoverable_cases(self) -> List[RecoveryCase]:
        """Get all recoverable cases."""
        return [
            case for case in self._cases.values()
            if case.status == RecoveryCaseStatus.RECOVERABLE
        ]

    def get_cases_by_priority(self, priority: RecoveryPriority) -> List[RecoveryCase]:
        """Get cases filtered by priority."""
        return [
            case for case in self._cases.values()
            if case.priority == priority
        ]

    def get_cases_by_brand(self, brand_id: str) -> List[RecoveryCase]:
        """Get all cases for a specific brand."""
        return [
            case for case in self._cases.values()
            if case.brand_id == brand_id
        ]

    def mark_recovered(self, case_id: str) -> bool:
        """Mark a case as recovered.
        
        Returns:
            True if case was found and updated, False otherwise
        """
        case = self._cases.get(case_id)
        if not case:
            return False
        
        case.status = RecoveryCaseStatus.RECOVERED
        case.recovered_at = _now_iso()
        return True

    def mark_expired(self, case_id: str) -> bool:
        """Mark a case as expired.
        
        Returns:
            True if case was found and updated, False otherwise
        """
        case = self._cases.get(case_id)
        if not case:
            return False
        
        case.status = RecoveryCaseStatus.EXPIRED
        return True

    def expire_old_cases(self) -> int:
        """Mark expired cases based on expiry date.
        
        Returns:
            Number of cases marked as expired
        """
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for case in self._cases.values():
            if case.status == RecoveryCaseStatus.RECOVERABLE and case.expires_at:
                expiry_dt = _parse_iso(case.expires_at)
                if now > expiry_dt:
                    case.status = RecoveryCaseStatus.EXPIRED
                    expired_count += 1
        
        return expired_count

    def get_detection_metrics(self) -> Dict[str, Any]:
        """Get detection and case metrics."""
        total = len(self._cases)
        recoverable = len(self.get_recoverable_cases())
        recovered = len([c for c in self._cases.values() if c.status == RecoveryCaseStatus.RECOVERED])
        expired = len([c for c in self._cases.values() if c.status == RecoveryCaseStatus.EXPIRED])
        
        high_priority = len(self.get_cases_by_priority(RecoveryPriority.HIGH))
        medium_priority = len(self.get_cases_by_priority(RecoveryPriority.MEDIUM))
        low_priority = len(self.get_cases_by_priority(RecoveryPriority.LOW))

        return {
            "cases_total": total,
            "cases_recoverable": recoverable,
            "cases_recovered": recovered,
            "cases_expired": expired,
            "priority_high": high_priority,
            "priority_medium": medium_priority,
            "priority_low": low_priority,
        }
