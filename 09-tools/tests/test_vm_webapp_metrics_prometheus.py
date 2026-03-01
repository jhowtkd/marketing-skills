"""Tests for v26 Control Loop metrics and Prometheus export.

TDD approach: tests for cycles/regressions/mitigations/blocked/rollbacks/time_to_detect/time_to_mitigate.
"""

import pytest
from datetime import datetime, timezone

from vm_webapp.observability import MetricsCollector, ControlLoopMetrics


class TestControlLoopMetrics:
    """Test v26 Control Loop metrics collection."""
    
    def test_record_cycle_increments_counter(self):
        """Should increment cycles_total counter."""
        collector = MetricsCollector()
        
        collector.record_control_loop_cycle()
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.cycles_total == 1
        assert metrics.active_cycles == 1
        assert metrics.last_cycle_at is not None
    
    def test_record_multiple_cycles(self):
        """Should track multiple cycles."""
        collector = MetricsCollector()
        
        for _ in range(5):
            collector.record_control_loop_cycle()
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.cycles_total == 5
    
    def test_record_regression_detected(self):
        """Should track regression detections."""
        collector = MetricsCollector()
        
        collector.record_regression_detected()
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.regressions_detected_total == 1
        assert metrics.last_regression_detected_at is not None
    
    def test_record_mitigation_applied(self):
        """Should track applied mitigations."""
        collector = MetricsCollector()
        
        collector.record_mitigation_applied()
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.mitigations_applied_total == 1
        assert metrics.last_mitigation_applied_at is not None
    
    def test_record_mitigation_blocked(self):
        """Should track blocked mitigations."""
        collector = MetricsCollector()
        
        collector.record_mitigation_blocked()
        collector.record_mitigation_blocked()
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.mitigations_blocked_total == 2
    
    def test_record_rollback(self):
        """Should track rollbacks."""
        collector = MetricsCollector()
        
        collector.record_control_loop_rollback()
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.rollbacks_total == 1
        assert metrics.last_rollback_at is not None
    
    def test_record_time_to_detect(self):
        """Should track time to detect regressions."""
        collector = MetricsCollector()
        
        collector.record_time_to_detect(30.0)  # 30 seconds
        collector.record_time_to_detect(60.0)  # 60 seconds
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.time_to_detect_count == 2
        # Running average: (30 + 60) / 2 = 45
        assert metrics.time_to_detect_seconds == 45.0
    
    def test_record_time_to_mitigate(self):
        """Should track time to mitigate regressions."""
        collector = MetricsCollector()
        
        collector.record_time_to_mitigate(120.0)  # 2 minutes
        collector.record_time_to_mitigate(180.0)  # 3 minutes
        collector.record_time_to_mitigate(300.0)  # 5 minutes
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.time_to_mitigate_count == 3
        # Running average: (120 + 180 + 300) / 3 = 200
        assert metrics.time_to_mitigate_seconds == 200.0
    
    def test_update_active_cycles(self):
        """Should update active cycles count."""
        collector = MetricsCollector()
        
        collector.update_active_cycles(3)
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.active_cycles == 3
    
    def test_update_frozen_brands(self):
        """Should update frozen brands count."""
        collector = MetricsCollector()
        
        collector.update_frozen_brands(2)
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.frozen_brands == 2
    
    def test_metrics_thread_safety(self):
        """Should be thread-safe for concurrent updates."""
        import threading
        
        collector = MetricsCollector()
        
        def record_cycles():
            for _ in range(100):
                collector.record_control_loop_cycle()
        
        threads = [threading.Thread(target=record_cycles) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        metrics = collector.get_control_loop_metrics()
        assert metrics.cycles_total == 500


class TestControlLoopMetricsSnapshot:
    """Test metrics snapshot functionality."""
    
    def test_snapshot_includes_control_loop_v26(self):
        """Snapshot should include v26 control loop metrics."""
        collector = MetricsCollector()
        
        collector.record_control_loop_cycle()
        collector.record_regression_detected()
        collector.record_mitigation_applied()
        
        snapshot = collector.snapshot()
        
        assert "control_loop_v26" in snapshot
        v26 = snapshot["control_loop_v26"]
        assert v26["cycles_total"] == 1
        assert v26["regressions_detected_total"] == 1
        assert v26["mitigations_applied_total"] == 1
    
    def test_snapshot_includes_time_metrics(self):
        """Snapshot should include time-based metrics."""
        collector = MetricsCollector()
        
        collector.record_time_to_detect(45.0)
        collector.record_time_to_mitigate(200.0)
        
        snapshot = collector.snapshot()
        
        v26 = snapshot["control_loop_v26"]
        assert v26["time_to_detect_seconds"] == 45.0
        assert v26["time_to_mitigate_seconds"] == 200.0
    
    def test_snapshot_includes_state_metrics(self):
        """Snapshot should include state metrics."""
        collector = MetricsCollector()
        
        collector.update_active_cycles(5)
        collector.update_frozen_brands(1)
        
        snapshot = collector.snapshot()
        
        v26 = snapshot["control_loop_v26"]
        assert v26["active_cycles"] == 5
        assert v26["frozen_brands"] == 1


class TestControlLoopPrometheusExport:
    """Test Prometheus format export for control loop metrics."""
    
    def test_prometheus_includes_control_loop_metrics(self):
        """Prometheus output should include control loop metrics via snapshot."""
        from vm_webapp.observability import render_prometheus
        
        collector = MetricsCollector()
        collector.record_control_loop_cycle()
        collector.record_regression_detected()
        collector.record_mitigation_applied()
        
        snapshot = collector.snapshot()
        
        # Snapshot should contain v26 metrics
        assert "control_loop_v26" in snapshot
        assert snapshot["control_loop_v26"]["cycles_total"] == 1
        assert snapshot["control_loop_v26"]["regressions_detected_total"] == 1
    
    def test_prometheus_time_metrics_format(self):
        """Time metrics should be in correct format."""
        from vm_webapp.observability import render_prometheus
        
        collector = MetricsCollector()
        collector.record_time_to_detect(45.0)
        collector.record_time_to_mitigate(200.0)
        
        snapshot = collector.snapshot()
        
        # Time metrics should be in snapshot
        assert snapshot["control_loop_v26"]["time_to_detect_seconds"] == 45.0
        assert snapshot["control_loop_v26"]["time_to_mitigate_seconds"] == 200.0


class TestControlLoopMetricsDataclass:
    """Test ControlLoopMetrics dataclass."""
    
    def test_default_values(self):
        """Should have correct default values."""
        metrics = ControlLoopMetrics()
        
        assert metrics.cycles_total == 0
        assert metrics.regressions_detected_total == 0
        assert metrics.mitigations_applied_total == 0
        assert metrics.mitigations_blocked_total == 0
        assert metrics.rollbacks_total == 0
        assert metrics.time_to_detect_seconds == 0.0
        assert metrics.time_to_mitigate_seconds == 0.0
        assert metrics.time_to_detect_count == 0
        assert metrics.time_to_mitigate_count == 0
        assert metrics.active_cycles == 0
        assert metrics.frozen_brands == 0
        assert metrics.last_cycle_at is None
        assert metrics.last_regression_detected_at is None
        assert metrics.last_mitigation_applied_at is None
        assert metrics.last_rollback_at is None
