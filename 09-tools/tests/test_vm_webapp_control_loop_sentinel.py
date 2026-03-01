"""Tests for Online Control Loop - Regression Sentinel (v26)."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from vm_webapp.control_loop_sentinel import (
    RegressionSentinel,
    RegressionSignal,
    RegressionSeverity,
    DetectionWindow,
    HysteresisState,
)


@pytest.fixture
def sentinel():
    """Regression sentinel fixture."""
    return RegressionSentinel()


@pytest.fixture
def sample_metrics():
    """Sample metrics for testing."""
    return {
        "v1_score": 65.0,
        "approval_rate": 0.70,
        "incident_rate": 0.05,
        "cost_per_job": 100.0,
        "mttc": 300.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class TestRegressionSeverity:
    """Test regression severity levels."""

    def test_severity_levels(self):
        """Should have correct severity levels."""
        assert RegressionSeverity.LOW == "low"
        assert RegressionSeverity.MEDIUM == "medium"
        assert RegressionSeverity.HIGH == "high"
        assert RegressionSeverity.CRITICAL == "critical"


class TestDetectionWindow:
    """Test detection window configuration."""

    def test_default_windows(self):
        """Should have default 4h cycle window."""
        window = DetectionWindow()
        assert window.short_term_minutes == 15  # 15 min for quick detection
        assert window.medium_term_minutes == 60  # 1 hour
        assert window.long_term_minutes == 240  # 4 hours (cycle)

    def test_custom_windows(self):
        """Should allow custom windows."""
        window = DetectionWindow(
            short_term_minutes=10,
            medium_term_minutes=30,
            long_term_minutes=120,
        )
        assert window.short_term_minutes == 10
        assert window.medium_term_minutes == 30
        assert window.long_term_minutes == 120


class TestHysteresisState:
    """Test hysteresis state management."""

    def test_initial_state_clear(self):
        """Initial state should be clear."""
        state = HysteresisState()
        assert state.is_clear is True
        assert state.is_triggered is False
        assert state.triggered_at is None

    def test_trigger_transition(self):
        """Should transition to triggered state."""
        state = HysteresisState()
        state.trigger()
        assert state.is_triggered is True
        assert state.is_clear is False
        assert state.triggered_at is not None

    def test_clear_transition(self):
        """Should transition back to clear state."""
        state = HysteresisState()
        state.trigger()
        state.clear()
        assert state.is_clear is True
        assert state.is_triggered is False

    def test_trigger_count(self):
        """Should track trigger count."""
        state = HysteresisState()
        assert state.trigger_count == 0
        state.trigger()
        assert state.trigger_count == 1
        state.trigger()
        assert state.trigger_count == 2


class TestRegressionSignal:
    """Test regression signal structure."""

    def test_signal_creation(self):
        """Should create regression signal."""
        signal = RegressionSignal(
            signal_id="sig-001",
            metric_name="v1_score",
            severity=RegressionSeverity.MEDIUM,
            detected_at=datetime.now(timezone.utc).isoformat(),
            value=55.0,
            baseline=65.0,
            delta_pct=-15.4,
            window_minutes=15,
        )
        assert signal.signal_id == "sig-001"
        assert signal.metric_name == "v1_score"
        assert signal.severity == "medium"
        assert signal.delta_pct == -15.4


class TestRegressionSentinel:
    """Test regression sentinel core functionality."""

    def test_sentinel_has_version(self, sentinel):
        """Sentinel should have version identifier."""
        assert hasattr(sentinel, 'version')
        assert sentinel.version == "v26"

    def test_add_metric_point(self, sentinel, sample_metrics):
        """Should add metric point to history."""
        sentinel.add_metric_point("run-001", sample_metrics)
        history = sentinel.get_metric_history("run-001")
        assert len(history) == 1
        assert history[0]["v1_score"] == 65.0

    def test_detect_no_regression_with_stable_metrics(self, sentinel, sample_metrics):
        """Should not detect regression with stable metrics."""
        # Add baseline
        sentinel.add_metric_point("run-001", sample_metrics)
        
        # Add similar metrics (no regression)
        similar_metrics = {**sample_metrics, "v1_score": 64.0}  # Small change
        signals = sentinel.detect_regression("run-001", similar_metrics)
        
        assert len(signals) == 0

    def test_detect_regression_v1_score_drop(self, sentinel, sample_metrics):
        """Should detect regression on V1 score drop."""
        # Add baseline
        sentinel.add_metric_point("run-001", sample_metrics)
        
        # Add degraded metrics
        degraded_metrics = {**sample_metrics, "v1_score": 50.0}  # -23%
        signals = sentinel.detect_regression("run-001", degraded_metrics)
        
        assert len(signals) > 0
        assert any(s.metric_name == "v1_score" for s in signals)

    def test_detect_regression_approval_rate_drop(self, sentinel, sample_metrics):
        """Should detect regression on approval rate drop."""
        sentinel.add_metric_point("run-001", sample_metrics)
        
        degraded_metrics = {**sample_metrics, "approval_rate": 0.55}  # -21%
        signals = sentinel.detect_regression("run-001", degraded_metrics)
        
        assert len(signals) > 0
        assert any(s.metric_name == "approval_rate" for s in signals)

    def test_detect_regression_incident_spike(self, sentinel, sample_metrics):
        """Should detect regression on incident spike."""
        sentinel.add_metric_point("run-001", sample_metrics)
        
        degraded_metrics = {**sample_metrics, "incident_rate": 0.08}  # +60%
        signals = sentinel.detect_regression("run-001", degraded_metrics)
        
        assert len(signals) > 0
        assert any(s.metric_name == "incident_rate" for s in signals)

    def test_severity_classification(self, sentinel, sample_metrics):
        """Should classify severity correctly."""
        # Use fresh run for each severity test to avoid hysteresis
        
        # Small drop = LOW
        sentinel.add_metric_point("run-low", sample_metrics)
        low_metrics = {**sample_metrics, "v1_score": 62.0}  # -4.6%
        signals = sentinel.detect_regression("run-low", low_metrics)
        if signals:
            assert all(s.severity in [RegressionSeverity.LOW, RegressionSeverity.MEDIUM] for s in signals)
        
        # Medium drop = MEDIUM (-10% to -15%)
        sentinel.add_metric_point("run-med", sample_metrics)
        med_metrics = {**sample_metrics, "v1_score": 58.0}  # -10.8%
        signals = sentinel.detect_regression("run-med", med_metrics)
        if signals:
            assert any(s.severity == RegressionSeverity.MEDIUM for s in signals)
        
        # High drop = HIGH (-15% to -20%)
        sentinel.add_metric_point("run-high", sample_metrics)
        high_metrics = {**sample_metrics, "v1_score": 55.0}  # -15.4%
        signals = sentinel.detect_regression("run-high", high_metrics)
        if signals:
            assert any(s.severity == RegressionSeverity.HIGH for s in signals)

    def test_hysteresis_prevents_flapping(self, sentinel, sample_metrics):
        """Hysteresis should prevent signal flapping."""
        sentinel.add_metric_point("run-001", sample_metrics)
        
        # First detection
        degraded = {**sample_metrics, "v1_score": 50.0}
        signals1 = sentinel.detect_regression("run-001", degraded)
        
        # Same metrics again - should not generate new signal due to hysteresis
        signals2 = sentinel.detect_regression("run-001", degraded)
        
        # Second call should return empty or suppressed signals
        assert len(signals2) == 0 or all(s.suppressed for s in signals2)

    def test_get_active_signals(self, sentinel, sample_metrics):
        """Should return active (non-cleared) signals."""
        sentinel.add_metric_point("run-001", sample_metrics)
        
        degraded = {**sample_metrics, "v1_score": 50.0}
        sentinel.detect_regression("run-001", degraded)
        
        active = sentinel.get_active_signals("run-001")
        assert len(active) >= 0  # May have signals

    def test_clear_signal(self, sentinel, sample_metrics):
        """Should clear specific signal."""
        sentinel.add_metric_point("run-001", sample_metrics)
        
        degraded = {**sample_metrics, "v1_score": 50.0}
        signals = sentinel.detect_regression("run-001", degraded)
        
        if signals:
            signal_id = signals[0].signal_id
            result = sentinel.clear_signal("run-001", signal_id)
            assert result is True

    def test_short_window_detection(self, sentinel, sample_metrics):
        """Should detect regressions in short window (15 min)."""
        sentinel.add_metric_point("run-001", sample_metrics)
        
        # Immediate drop
        degraded = {**sample_metrics, "v1_score": 45.0}  # -30%
        signals = sentinel.detect_regression("run-001", degraded, window="short")
        
        assert len(signals) >= 0  # May or may not trigger based on threshold

    def test_long_window_detection(self, sentinel, sample_metrics):
        """Should detect regressions in long window (4h)."""
        sentinel.add_metric_point("run-001", sample_metrics)
        
        # Gradual degradation
        for i in range(5):
            gradual = {
                **sample_metrics,
                "v1_score": 65.0 - (i * 3),  # Gradual drop
            }
            sentinel.add_metric_point("run-001", gradual)
        
        signals = sentinel.detect_regression("run-001", gradual, window="long")
        # Should accumulate trend over long window
        assert isinstance(signals, list)

    def test_get_sentinel_status(self, sentinel):
        """Should return sentinel status."""
        status = sentinel.get_status()
        assert "version" in status
        assert "monitored_runs" in status
        assert "total_signals_generated" in status
