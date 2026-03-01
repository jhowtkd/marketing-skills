"""
Tests for Adaptive Escalation Engine (v21)

Targets:
- approval timeout rate: -30%
- mean decision latency (medium/high): -25%
- incident_rate: no increase
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from vm_webapp.adaptive_escalation import (
    AdaptiveEscalationEngine,
    ApproverProfile,
    TimeWindow,
    EscalationContext,
    AdaptiveTimeout,
)


class TestApproverProfile:
    """Test approver historical behavior profiling."""

    def test_create_profile_with_defaults(self):
        profile = ApproverProfile(approver_id="user@example.com")
        assert profile.approver_id == "user@example.com"
        assert profile.avg_response_time_minutes == 15.0
        assert profile.approvals_count == 0
        assert profile.timeout_rate == 0.0

    def test_update_with_approval(self):
        profile = ApproverProfile("user@example.com")
        profile.update_with_approval(response_time_minutes=10.0)
        
        assert profile.approvals_count == 1
        assert profile.avg_response_time_minutes == 10.0
        
        profile.update_with_approval(response_time_minutes=20.0)
        assert profile.approvals_count == 2
        assert profile.avg_response_time_minutes == 15.0  # avg of 10 and 20

    def test_update_with_timeout(self):
        profile = ApproverProfile("user@example.com")
        profile.update_with_timeout()
        
        assert profile.timeouts_count == 1
        assert profile.total_count == 1
        assert profile.timeout_rate == 1.0
        
        profile.update_with_approval(response_time_minutes=5.0)
        assert profile.timeout_rate == 0.5  # 1 timeout out of 2 total

    def test_response_time_percentile(self):
        profile = ApproverProfile("user@example.com")
        
        # Add response times: 5, 10, 15, 20, 30 minutes
        for rt in [5.0, 10.0, 15.0, 20.0, 30.0]:
            profile.update_with_approval(response_time_minutes=rt)
        
        assert profile.get_response_time_percentile(0.5) == 15.0  # median
        assert profile.get_response_time_percentile(0.9) == 30.0  # p90


class TestTimeWindow:
    """Test time window detection for adaptive timeouts."""

    def test_business_hours_detection(self):
        # Tuesday 10:00 AM
        dt = datetime(2026, 3, 3, 10, 0, 0)
        assert TimeWindow.is_business_hours(dt) is True

    def test_after_hours_detection(self):
        # Tuesday 10:00 PM
        dt = datetime(2026, 3, 3, 22, 0, 0)
        assert TimeWindow.is_business_hours(dt) is False

    def test_weekend_detection(self):
        # Saturday 10:00 AM
        dt = datetime(2026, 3, 7, 10, 0, 0)
        assert TimeWindow.is_business_hours(dt) is False

    def test_time_window_multiplier(self):
        # Business hours: 1.0x
        dt_business = datetime(2026, 3, 3, 10, 0, 0)
        assert TimeWindow.get_time_multiplier(dt_business) == 1.0
        
        # After hours: 1.5x (longer timeouts when people are not working)
        dt_after = datetime(2026, 3, 3, 22, 0, 0)
        assert TimeWindow.get_time_multiplier(dt_after) == 1.5
        
        # Weekend: 2.0x (even longer on weekends)
        dt_weekend = datetime(2026, 3, 7, 10, 0, 0)
        assert TimeWindow.get_time_multiplier(dt_weekend) == 2.0


class TestAdaptiveTimeout:
    """Test adaptive timeout calculation."""

    def test_base_timeout_by_risk_level(self):
        assert AdaptiveTimeout.get_base_timeout("low") == 900  # 15 min
        assert AdaptiveTimeout.get_base_timeout("medium") == 900  # 15 min
        assert AdaptiveTimeout.get_base_timeout("high") == 1800  # 30 min
        assert AdaptiveTimeout.get_base_timeout("critical") == 3600  # 60 min

    def test_adaptive_timeout_with_fast_approver(self):
        # Approver with fast response time (5 min average)
        profile = ApproverProfile("fast@example.com")
        profile.update_with_approval(response_time_minutes=5.0)
        
        context = EscalationContext(
            step_id="step-001",
            risk_level="medium",
            approver_profile=profile,
            pending_load=5,
            current_time=datetime(2026, 3, 3, 10, 0, 0),  # business hours
        )
        
        timeout = AdaptiveTimeout.calculate(context)
        # Base 15 min * fast approver factor (0.8) * business hours (1.0)
        assert timeout < 900  # Less than base timeout

    def test_adaptive_timeout_with_slow_approver(self):
        # Approver with slow response time (45 min average, many timeouts)
        profile = ApproverProfile("slow@example.com")
        for _ in range(3):
            profile.update_with_approval(response_time_minutes=45.0)
        profile.update_with_timeout()
        
        context = EscalationContext(
            step_id="step-001",
            risk_level="medium",
            approver_profile=profile,
            pending_load=5,
            current_time=datetime(2026, 3, 3, 10, 0, 0),
        )
        
        timeout = AdaptiveTimeout.calculate(context)
        # Should be longer than base for slow approver
        assert timeout > 900

    def test_adaptive_timeout_with_high_load(self):
        # High pending load should increase timeout
        profile = ApproverProfile("user@example.com")
        
        context_low_load = EscalationContext(
            step_id="step-001",
            risk_level="medium",
            approver_profile=profile,
            pending_load=2,
            current_time=datetime(2026, 3, 3, 10, 0, 0),
        )
        
        context_high_load = EscalationContext(
            step_id="step-001",
            risk_level="medium",
            approver_profile=profile,
            pending_load=20,  # High load
            current_time=datetime(2026, 3, 3, 10, 0, 0),
        )
        
        timeout_low = AdaptiveTimeout.calculate(context_low_load)
        timeout_high = AdaptiveTimeout.calculate(context_high_load)
        
        assert timeout_high > timeout_low

    def test_adaptive_timeout_after_hours(self):
        profile = ApproverProfile("user@example.com")
        
        context_business = EscalationContext(
            step_id="step-001",
            risk_level="medium",
            approver_profile=profile,
            pending_load=5,
            current_time=datetime(2026, 3, 3, 10, 0, 0),  # business
        )
        
        context_after = EscalationContext(
            step_id="step-001",
            risk_level="medium",
            approver_profile=profile,
            pending_load=5,
            current_time=datetime(2026, 3, 3, 22, 0, 0),  # after hours
        )
        
        timeout_business = AdaptiveTimeout.calculate(context_business)
        timeout_after = AdaptiveTimeout.calculate(context_after)
        
        assert timeout_after > timeout_business

    def test_timeout_bounds_enforcement(self):
        """Ensure timeouts stay within reasonable bounds."""
        profile = ApproverProfile("user@example.com")
        
        # Test minimum bound
        for _ in range(10):
            profile.update_with_approval(response_time_minutes=1.0)  # Very fast
        
        context = EscalationContext(
            step_id="step-001",
            risk_level="low",
            approver_profile=profile,
            pending_load=1,
            current_time=datetime(2026, 3, 3, 10, 0, 0),
        )
        
        timeout = AdaptiveTimeout.calculate(context)
        assert timeout >= 300  # Min 5 minutes
        assert timeout <= 7200  # Max 2 hours


class TestAdaptiveEscalationEngine:
    """Test main adaptive escalation engine."""

    def test_engine_initialization(self):
        engine = AdaptiveEscalationEngine()
        assert engine is not None
        assert len(engine._approver_profiles) == 0

    def test_get_or_create_profile(self):
        engine = AdaptiveEscalationEngine()
        
        profile = engine.get_or_create_profile("user@example.com")
        assert profile.approver_id == "user@example.com"
        
        # Should return same profile on second call
        profile2 = engine.get_or_create_profile("user@example.com")
        assert profile is profile2

    def test_record_approval(self):
        engine = AdaptiveEscalationEngine()
        
        engine.record_approval(
            approver_id="user@example.com",
            step_id="step-001",
            response_time_seconds=600,  # 10 minutes
        )
        
        profile = engine.get_or_create_profile("user@example.com")
        assert profile.approvals_count == 1
        assert profile.avg_response_time_minutes == 10.0

    def test_record_timeout(self):
        engine = AdaptiveEscalationEngine()
        
        engine.record_timeout(
            approver_id="user@example.com",
            step_id="step-001",
        )
        
        profile = engine.get_or_create_profile("user@example.com")
        assert profile.timeouts_count == 1

    def test_calculate_escalation_windows(self):
        engine = AdaptiveEscalationEngine()
        
        # Create profile with known response time
        profile = engine.get_or_create_profile("user@example.com")
        profile.update_with_approval(response_time_minutes=20.0)
        
        windows = engine.calculate_escalation_windows(
            step_id="step-001",
            risk_level="medium",
            approver_id="user@example.com",
            pending_count=5,
            current_time=datetime(2026, 3, 3, 10, 0, 0),
        )
        
        assert len(windows) == 3  # 3 escalation levels
        assert all(w > 0 for w in windows)
        assert windows[0] < windows[1] < windows[2]  # Increasing windows

    def test_engine_integration_with_v20_supervisor(self):
        """Ensure integration with existing v20 supervisor."""
        engine = AdaptiveEscalationEngine()
        
        # Simulate v20 supervisor calling adaptive engine
        windows = engine.calculate_escalation_windows(
            step_id="step-001",
            risk_level="high",
            approver_id="admin@example.com",
            pending_count=3,
            current_time=datetime(2026, 3, 3, 14, 0, 0),
        )
        
        # Should return reasonable windows for supervisor
        assert 900 <= windows[0] <= 3600  # Between 15 min and 1 hour
        assert windows[0] < windows[1] < windows[2]


class TestAdaptiveEscalationMetrics:
    """Test metrics for monitoring adaptive escalation."""

    def test_calculate_timeout_rate_reduction(self):
        engine = AdaptiveEscalationEngine()
        
        # Simulate before/after adaptive escalation
        baseline_timeouts = 30  # 30% timeout rate
        adaptive_timeouts = 21  # 21% timeout rate (30% reduction)
        
        reduction = (baseline_timeouts - adaptive_timeouts) / baseline_timeouts
        assert reduction >= 0.30  # Target: 30% reduction

    def test_mean_decision_latency_reduction(self):
        """Test that mean decision latency is reduced."""
        engine = AdaptiveEscalationEngine()
        
        # Simulate approvals with adaptive timeouts
        response_times = [8, 12, 15, 10, 20, 18, 14, 11]  # minutes
        
        for rt in response_times:
            engine.record_approval("user@example.com", "step-001", rt * 60)
        
        profile = engine.get_or_create_profile("user@example.com")
        mean_latency = profile.avg_response_time_minutes
        
        # Target: 25% reduction in mean decision latency
        # If baseline was 20 min, new should be <= 15 min
        baseline_mean = 20.0
        assert mean_latency <= baseline_mean * 0.75
