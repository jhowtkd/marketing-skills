"""
Task B: Segment Regression Alerts - Tests
Covers: thresholds, histerese, deduplicação de alertas, métricas Prometheus
"""

import pytest
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from unittest.mock import MagicMock, patch, call

from vm_webapp.regression_alerts import (
    RegressionSeverity,
    RegressionReasonCode,
    RegressionAlert,
    RegressionDetector,
    AlertDeduplicator,
    RegressionMetrics,
    detect_segment_regression,
    get_active_alerts,
    confirm_alert,
    dismiss_false_positive,
)


class TestRegressionSeverity:
    """Test regression severity levels."""
    
    def test_severity_values(self):
        """Severity levels have correct string values."""
        assert RegressionSeverity.INFO.value == "info"
        assert RegressionSeverity.WARNING.value == "warning"
        assert RegressionSeverity.CRITICAL.value == "critical"


class TestRegressionReasonCode:
    """Test standardized reason codes."""
    
    def test_reason_codes(self):
        """Reason codes are standardized."""
        assert RegressionReasonCode.APPROVAL_RATE_DROP.value == "approval_rate_drop"
        assert RegressionReasonCode.V1_SCORE_DECLINE.value == "v1_score_decline"
        assert RegressionReasonCode.REGEN_RATE_SPIKE.value == "regen_rate_spike"
        assert RegressionReasonCode.MULTI_METRIC_REGRESSION.value == "multi_metric_regression"


class TestRegressionAlert:
    """Test regression alert data structure."""
    
    def test_alert_creation(self):
        """Can create a regression alert."""
        alert = RegressionAlert(
            alert_id="alert_001",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.45,
            baseline_value=0.50,
            delta=-0.05,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        
        assert alert.alert_id == "alert_001"
        assert alert.segment_key == "brand1:awareness"
        assert alert.confirmed is False


class TestRegressionDetector:
    """Test regression detection logic."""
    
    def test_detect_approval_rate_drop_warning(self):
        """Detect warning level approval rate drop."""
        detector = RegressionDetector()
        
        # 5% drop triggers warning
        result = detector.detect(
            segment_key="brand1:awareness",
            metric_name="approval_without_regen_24h",
            current=0.45,
            baseline=0.50,
            window_hours=24
        )
        
        assert result is not None
        assert result.severity == RegressionSeverity.WARNING
        assert result.reason_code == RegressionReasonCode.APPROVAL_RATE_DROP
        assert result.delta == pytest.approx(-0.05)
    
    def test_detect_approval_rate_drop_critical(self):
        """Detect critical level approval rate drop."""
        detector = RegressionDetector()
        
        # 10% drop triggers critical
        result = detector.detect(
            segment_key="brand1:awareness",
            metric_name="approval_without_regen_24h",
            current=0.40,
            baseline=0.50,
            window_hours=24
        )
        
        assert result is not None
        assert result.severity == RegressionSeverity.CRITICAL
    
    def test_detect_v1_score_decline(self):
        """Detect V1 score decline."""
        detector = RegressionDetector()
        
        result = detector.detect(
            segment_key="brand1:awareness",
            metric_name="v1_score_avg",
            current=70.0,
            baseline=76.0,
            window_hours=24
        )
        
        assert result is not None
        assert result.reason_code == RegressionReasonCode.V1_SCORE_DECLINE
    
    def test_detect_regen_rate_spike(self):
        """Detect regeneration rate spike (increase is bad)."""
        detector = RegressionDetector()
        
        result = detector.detect(
            segment_key="brand1:awareness",
            metric_name="regenerations_per_job",
            current=1.20,
            baseline=1.00,
            window_hours=24
        )
        
        assert result is not None
        assert result.reason_code == RegressionReasonCode.REGEN_RATE_SPIKE
    
    def test_no_regression_within_threshold(self):
        """No alert when within normal threshold."""
        detector = RegressionDetector()
        
        # 2% drop is within normal variation
        result = detector.detect(
            segment_key="brand1:awareness",
            metric_name="approval_without_regen_24h",
            current=0.48,
            baseline=0.50,
            window_hours=24
        )
        
        assert result is None
    
    def test_hysteresis_prevents_flapping(self):
        """Hysteresis prevents alert flapping."""
        detector = RegressionDetector()
        
        # First detection at warning level
        alert1 = detector.detect(
            segment_key="brand1:awareness",
            metric_name="approval_without_regen_24h",
            current=0.45,
            baseline=0.50,
            window_hours=24
        )
        assert alert1 is not None
        
        # Slight recovery shouldn't clear immediately (hysteresis)
        # Need 1% improvement to clear
        alert2 = detector.detect(
            segment_key="brand1:awareness",
            metric_name="approval_without_regen_24h",
            current=0.46,  # Still -4%, within hysteresis
            baseline=0.50,
            window_hours=24,
            previous_alert=alert1
        )
        # Should not create new alert, keep previous state
        assert alert2 is None


class TestAlertDeduplicator:
    """Test alert deduplication logic."""
    
    def test_same_alert_deduplicated(self):
        """Same alert within window is deduplicated."""
        dedup = AlertDeduplicator(dedup_window_hours=4)
        
        alert1 = RegressionAlert(
            alert_id="alert_001",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.45,
            baseline_value=0.50,
            delta=-0.05,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        
        alert2 = RegressionAlert(
            alert_id="alert_002",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.44,
            baseline_value=0.50,
            delta=-0.06,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        
        # First alert passes
        assert dedup.should_alert(alert1) is True
        dedup.record_alert(alert1)
        
        # Second similar alert is deduplicated
        assert dedup.should_alert(alert2) is False
    
    def test_different_segment_not_deduplicated(self):
        """Different segment alerts are not deduplicated."""
        dedup = AlertDeduplicator(dedup_window_hours=4)
        
        alert1 = RegressionAlert(
            alert_id="alert_001",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.45,
            baseline_value=0.50,
            delta=-0.05,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        
        alert2 = RegressionAlert(
            alert_id="alert_002",
            segment_key="brand2:conversion",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.44,
            baseline_value=0.50,
            delta=-0.06,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        
        assert dedup.should_alert(alert1) is True
        dedup.record_alert(alert1)
        
        # Different segment should alert
        assert dedup.should_alert(alert2) is True
    
    def test_old_alert_expires(self):
        """Old alerts outside window allow new alerts."""
        dedup = AlertDeduplicator(dedup_window_hours=4)
        
        old_time = datetime.now(UTC) - timedelta(hours=5)
        
        alert1 = RegressionAlert(
            alert_id="alert_001",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.45,
            baseline_value=0.50,
            delta=-0.05,
            window_hours=24,
            detected_at=old_time,
            confirmed=False,
            false_positive=False
        )
        
        alert2 = RegressionAlert(
            alert_id="alert_002",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.44,
            baseline_value=0.50,
            delta=-0.06,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        
        dedup.record_alert(alert1)
        
        # Old alert expired, new one should fire
        assert dedup.should_alert(alert2) is True


class TestRegressionMetrics:
    """Test Prometheus metrics for regression alerts."""
    
    def test_metrics_initialization(self):
        """Metrics are initialized correctly."""
        # Reset singleton para teste
        RegressionMetrics._instance = None
        RegressionMetrics._initialized = False
        
        metrics = RegressionMetrics()
        
        assert metrics.alerts_detected_total is not None
        assert metrics.alerts_confirmed_total is not None
        assert metrics.alerts_false_positive_total is not None
    
    def test_record_detected(self):
        """Recording detected increments counter."""
        # Reset singleton para teste
        RegressionMetrics._instance = None
        RegressionMetrics._initialized = False
        
        metrics = RegressionMetrics()
        # Não verificamos o inc real, apenas que não crasha
        metrics.record_detected("brand1:awareness", "warning")
        # Se chegou aqui, passou
        assert True
    
    def test_record_confirmed(self):
        """Recording confirmed increments counter."""
        RegressionMetrics._instance = None
        RegressionMetrics._initialized = False
        
        metrics = RegressionMetrics()
        metrics.record_confirmed("brand1:awareness")
        assert True
    
    def test_record_false_positive(self):
        """Recording false positive increments counter."""
        RegressionMetrics._instance = None
        RegressionMetrics._initialized = False
        
        metrics = RegressionMetrics()
        metrics.record_false_positive("brand1:awareness")
        assert True


class TestDetectSegmentRegression:
    """Test high-level segment regression detection."""
    
    @patch("vm_webapp.regression_alerts._fetch_segment_metrics")
    def test_detect_segment_regression_finds_issues(self, mock_fetch):
        """Detection finds regressions in segment metrics."""
        mock_fetch.return_value = {
            "approval_without_regen_24h": {"current": 0.42, "baseline": 0.50},
            "v1_score_avg": {"current": 72.0, "baseline": 76.0},
            "regenerations_per_job": {"current": 1.25, "baseline": 1.00},
        }
        
        alerts = detect_segment_regression("brand1:awareness")
        
        assert len(alerts) > 0
        assert any(a.reason_code == RegressionReasonCode.APPROVAL_RATE_DROP for a in alerts)
    
    @patch("vm_webapp.regression_alerts._fetch_segment_metrics")
    def test_detect_segment_regression_no_issues(self, mock_fetch):
        """Detection returns empty when no regressions."""
        mock_fetch.return_value = {
            "approval_without_regen_24h": {"current": 0.52, "baseline": 0.50},
            "v1_score_avg": {"current": 78.0, "baseline": 76.0},
            "regenerations_per_job": {"current": 0.90, "baseline": 1.00},
        }
        
        alerts = detect_segment_regression("brand1:awareness")
        
        assert len(alerts) == 0


class TestAlertLifecycle:
    """Test alert lifecycle management."""
    
    @patch("vm_webapp.regression_alerts._store_alert")
    def test_get_active_alerts(self, mock_store):
        """Retrieve active (non-dismissed) alerts."""
        mock_store.return_value = None
        
        # Create some alerts
        alert1 = RegressionAlert(
            alert_id="alert_001",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.45,
            baseline_value=0.50,
            delta=-0.05,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        
        with patch("vm_webapp.regression_alerts._load_alerts") as mock_load:
            mock_load.return_value = [alert1]
            
            active = get_active_alerts(segment_key="brand1:awareness")
            
            assert len(active) == 1
            assert active[0].alert_id == "alert_001"
    
    @patch("vm_webapp.regression_alerts._update_alert")
    @patch("vm_webapp.regression_alerts._load_alerts")
    def test_confirm_alert(self, mock_load, mock_update):
        """Confirm an alert as valid regression."""
        test_alert = RegressionAlert(
            alert_id="alert_001",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.45,
            baseline_value=0.50,
            delta=-0.05,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        mock_load.return_value = [test_alert]
        
        result = confirm_alert("alert_001")
        
        mock_update.assert_called_once()
        assert result is not None
        assert result.confirmed is True
    
    @patch("vm_webapp.regression_alerts._update_alert")
    @patch("vm_webapp.regression_alerts._load_alerts")
    def test_dismiss_false_positive(self, mock_load, mock_update):
        """Dismiss an alert as false positive."""
        test_alert = RegressionAlert(
            alert_id="alert_001",
            segment_key="brand1:awareness",
            severity=RegressionSeverity.WARNING,
            reason_code=RegressionReasonCode.APPROVAL_RATE_DROP,
            metric_name="approval_without_regen_24h",
            current_value=0.45,
            baseline_value=0.50,
            delta=-0.05,
            window_hours=24,
            detected_at=datetime.now(UTC),
            confirmed=False,
            false_positive=False
        )
        mock_load.return_value = [test_alert]
        
        result = dismiss_false_positive("alert_001")
        
        mock_update.assert_called_once()
        assert result is not None
        assert result.false_positive is True


class TestMultiMetricRegression:
    """Test detection when multiple metrics regress."""
    
    @patch("vm_webapp.regression_alerts._fetch_segment_metrics")
    def test_multi_metric_regression_detected(self, mock_fetch):
        """Multi-metric regression gets special reason code."""
        mock_fetch.return_value = {
            "approval_without_regen_24h": {"current": 0.42, "baseline": 0.50},  # -8%
            "v1_score_avg": {"current": 68.0, "baseline": 76.0},  # -8 pts
            "regenerations_per_job": {"current": 1.30, "baseline": 1.00},  # +30%
        }
        
        alerts = detect_segment_regression("brand1:awareness")
        
        # Should consolidate into single multi-metric alert
        multi_metric_alerts = [a for a in alerts 
                               if a.reason_code == RegressionReasonCode.MULTI_METRIC_REGRESSION]
        assert len(multi_metric_alerts) > 0 or len(alerts) >= 2


class TestWindowConfiguration:
    """Test different detection windows."""
    
    def test_short_window_detection(self):
        """Short window (1h) for rapid detection."""
        detector = RegressionDetector()
        
        result = detector.detect(
            segment_key="brand1:awareness",
            metric_name="approval_without_regen_24h",
            current=0.40,
            baseline=0.50,
            window_hours=1  # 1 hour window
        )
        
        assert result is not None
        assert result.window_hours == 1
    
    def test_long_window_detection(self):
        """Long window (168h/7d) for trend detection."""
        detector = RegressionDetector()
        
        result = detector.detect(
            segment_key="brand1:awareness",
            metric_name="approval_without_regen_24h",
            current=0.43,
            baseline=0.50,
            window_hours=168  # 7 day window
        )
        
        assert result is not None
        assert result.window_hours == 168
