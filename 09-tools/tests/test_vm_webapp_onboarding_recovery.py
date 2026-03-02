"""Tests for v34 Onboarding Recovery Reactivation Autopilot.

Dropoff detection, recovery cases, and state management.
"""

import pytest
from datetime import datetime, timezone, timedelta

from vm_webapp.onboarding_recovery import (
    DropoffReason,
    RecoveryCaseStatus,
    RecoveryPriority,
    DropoffDetector,
    RecoveryCase,
)


class TestDropoffReason:
    """Test DropoffReason enum."""

    def test_dropoff_reason_values(self):
        """DropoffReason should have expected values."""
        assert DropoffReason.ABANDONED_STEP == "abandoned_step"
        assert DropoffReason.TIMEOUT == "timeout"
        assert DropoffReason.ERROR == "error"
        assert DropoffReason.EXTERNAL_INTERRUPTION == "external_interruption"
        assert DropoffReason.USER_INITIATED_EXIT == "user_initiated_exit"


class TestRecoveryCaseStatus:
    """Test RecoveryCaseStatus enum."""

    def test_recovery_status_values(self):
        """RecoveryCaseStatus should have expected values."""
        assert RecoveryCaseStatus.ACTIVE == "active"
        assert RecoveryCaseStatus.RECOVERABLE == "recoverable"
        assert RecoveryCaseStatus.RECOVERED == "recovered"
        assert RecoveryCaseStatus.EXPIRED == "expired"


class TestRecoveryPriority:
    """Test RecoveryPriority enum."""

    def test_recovery_priority_values(self):
        """RecoveryPriority should have expected values."""
        assert RecoveryPriority.LOW == "low"
        assert RecoveryPriority.MEDIUM == "medium"
        assert RecoveryPriority.HIGH == "high"


class TestDropoffDetector:
    """Test DropoffDetector functionality."""

    def test_detector_initialization(self):
        """Detector should initialize with empty registry."""
        detector = DropoffDetector()
        assert detector._cases == {}

    def test_detect_dropoff_abandoned_step(self):
        """Detect dropoff when user abandons a step."""
        detector = DropoffDetector()
        
        session = {
            "user_id": "user-123",
            "brand_id": "brand-456",
            "current_step": 3,
            "total_steps": 7,
            "last_activity": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "step_start_time": (datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)).isoformat(),
        }
        
        case = detector.detect_dropoff(session)
        
        assert case is not None
        assert case.user_id == "user-123"
        assert case.brand_id == "brand-456"
        assert case.reason == DropoffReason.ABANDONED_STEP
        assert case.status == RecoveryCaseStatus.RECOVERABLE

    def test_detect_dropoff_timeout(self):
        """Detect dropoff due to session timeout."""
        detector = DropoffDetector()
        
        session = {
            "user_id": "user-456",
            "brand_id": "brand-789",
            "current_step": 5,
            "total_steps": 7,
            "last_activity": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
            "step_start_time": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
        }
        
        case = detector.detect_dropoff(session)
        
        assert case is not None
        assert case.reason == DropoffReason.TIMEOUT
        assert case.status == RecoveryCaseStatus.RECOVERABLE

    def test_no_dropoff_active_session(self):
        """No dropoff detected for active sessions."""
        detector = DropoffDetector()
        
        session = {
            "user_id": "user-789",
            "brand_id": "brand-abc",
            "current_step": 3,
            "total_steps": 7,
            "last_activity": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            "step_start_time": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        }
        
        case = detector.detect_dropoff(session)
        
        assert case is None

    def test_detect_dropoff_error(self):
        """Detect dropoff due to error."""
        detector = DropoffDetector()
        
        session = {
            "user_id": "user-error",
            "brand_id": "brand-xyz",
            "current_step": 2,
            "total_steps": 7,
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "error_occurred": True,
            "error_code": "TEMPLATE_RENDER_FAILED",
        }
        
        case = detector.detect_dropoff(session)
        
        assert case is not None
        assert case.reason == DropoffReason.ERROR

    def test_calculate_priority_high_abandonment(self):
        """High priority for late-stage abandonment."""
        detector = DropoffDetector()
        
        session = {
            "user_id": "user-high",
            "brand_id": "brand-1",
            "current_step": 6,
            "total_steps": 7,
            "last_activity": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        }
        
        priority = detector._calculate_priority(session, DropoffReason.ABANDONED_STEP)
        
        assert priority == RecoveryPriority.HIGH

    def test_calculate_priority_medium_mid_stage_abandonment(self):
        """Medium priority for mid-stage abandonment (30-70%)."""
        detector = DropoffDetector()
        
        session = {
            "user_id": "user-med",
            "brand_id": "brand-2",
            "current_step": 3,
            "total_steps": 7,
            "last_activity": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        }
        
        priority = detector._calculate_priority(session, DropoffReason.ABANDONED_STEP)
        
        assert priority == RecoveryPriority.MEDIUM

    def test_register_recovery_case(self):
        """Register a recovery case."""
        detector = DropoffDetector()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-123",
            brand_id="brand-456",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=5,
            total_steps=7,
        )
        
        detector.register_case(case)
        
        assert "case-001" in detector._cases
        assert detector._cases["case-001"] == case

    def test_get_recoverable_cases(self):
        """Get all recoverable cases."""
        detector = DropoffDetector()
        
        # Add recoverable case
        case1 = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=3,
            total_steps=7,
        )
        detector.register_case(case1)
        
        # Add expired case
        case2 = RecoveryCase(
            case_id="case-002",
            user_id="user-2",
            brand_id="brand-a",
            reason=DropoffReason.TIMEOUT,
            status=RecoveryCaseStatus.EXPIRED,
            priority=RecoveryPriority.LOW,
            current_step=1,
            total_steps=7,
        )
        detector.register_case(case2)
        
        recoverable = detector.get_recoverable_cases()
        
        assert len(recoverable) == 1
        assert recoverable[0].case_id == "case-001"

    def test_get_cases_by_priority(self):
        """Get cases filtered by priority."""
        detector = DropoffDetector()
        
        case1 = RecoveryCase(
            case_id="case-high",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=6,
            total_steps=7,
        )
        case2 = RecoveryCase(
            case_id="case-medium",
            user_id="user-2",
            brand_id="brand-a",
            reason=DropoffReason.TIMEOUT,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.MEDIUM,
            current_step=3,
            total_steps=7,
        )
        detector.register_case(case1)
        detector.register_case(case2)
        
        high_cases = detector.get_cases_by_priority(RecoveryPriority.HIGH)
        
        assert len(high_cases) == 1
        assert high_cases[0].case_id == "case-high"

    def test_mark_recovered(self):
        """Mark a case as recovered."""
        detector = DropoffDetector()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=5,
            total_steps=7,
        )
        detector.register_case(case)
        
        result = detector.mark_recovered("case-001")
        
        assert result is True
        assert detector._cases["case-001"].status == RecoveryCaseStatus.RECOVERED

    def test_mark_expired(self):
        """Mark a case as expired."""
        detector = DropoffDetector()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.TIMEOUT,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.LOW,
            current_step=2,
            total_steps=7,
        )
        detector.register_case(case)
        
        result = detector.mark_expired("case-001")
        
        assert result is True
        assert detector._cases["case-001"].status == RecoveryCaseStatus.EXPIRED


class TestRecoveryCase:
    """Test RecoveryCase model."""

    def test_case_creation(self):
        """Create a recovery case with all fields."""
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-123",
            brand_id="brand-456",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=4,
            total_steps=7,
            dropoff_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert case.case_id == "case-001"
        assert case.user_id == "user-123"
        assert case.brand_id == "brand-456"
        assert case.current_step == 4
        assert case.total_steps == 7

    def test_progress_percentage(self):
        """Calculate progress percentage."""
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-123",
            brand_id="brand-456",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.MEDIUM,
            current_step=4,
            total_steps=8,
        )
        
        assert case.progress_percentage() == 50.0

    def test_is_late_stage(self):
        """Detect late-stage dropoffs."""
        late_case = RecoveryCase(
            case_id="case-late",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=6,
            total_steps=7,
        )
        
        assert late_case.is_late_stage() is True

    def test_is_not_late_stage(self):
        """Early stage is not late."""
        early_case = RecoveryCase(
            case_id="case-early",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.MEDIUM,
            current_step=2,
            total_steps=7,
        )
        
        assert early_case.is_late_stage() is False

    def test_to_dict(self):
        """Convert case to dictionary."""
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-123",
            brand_id="brand-456",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=5,
            total_steps=7,
        )
        
        data = case.to_dict()
        
        assert data["case_id"] == "case-001"
        assert data["user_id"] == "user-123"
        assert data["reason"] == "abandoned_step"
        assert data["status"] == "recoverable"
        assert data["priority"] == "high"
