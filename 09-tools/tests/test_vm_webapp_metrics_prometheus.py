"""Tests for v18 multibrand policy metrics and Prometheus output.

Metrics to test:
- policy_proposal_total
- policy_applied_total
- policy_blocked_total
- policy_rollback_total
- policy_freeze_total
- cross_brand_gap_p90_p10
"""

import pytest
from datetime import datetime, timezone

from vm_webapp.observability import MetricsCollector, render_prometheus


class TestPolicyMetrics:
    """Test v18 policy-related metrics."""

    def test_record_policy_proposal(self):
        """Should record policy proposal metric."""
        # Arrange
        collector = MetricsCollector()
        
        # Act
        collector.record_count("policy_proposal_total", 1)
        collector.record_count("policy_proposal_total", 1)
        
        # Assert
        snapshot = collector.snapshot()
        assert snapshot["counts"]["policy_proposal_total"] == 2

    def test_record_policy_applied(self):
        """Should record policy applied metric."""
        # Arrange
        collector = MetricsCollector()
        
        # Act
        collector.record_count("policy_applied_total")
        
        # Assert
        snapshot = collector.snapshot()
        assert snapshot["counts"]["policy_applied_total"] == 1

    def test_record_policy_blocked(self):
        """Should record policy blocked metric."""
        # Arrange
        collector = MetricsCollector()
        
        # Act
        collector.record_count("policy_blocked_total", 3)
        
        # Assert
        snapshot = collector.snapshot()
        assert snapshot["counts"]["policy_blocked_total"] == 3

    def test_record_policy_rollback(self):
        """Should record policy rollback metric."""
        # Arrange
        collector = MetricsCollector()
        
        # Act
        collector.record_count("policy_rollback_total")
        collector.record_count("policy_rollback_total")
        collector.record_count("policy_rollback_total")
        
        # Assert
        snapshot = collector.snapshot()
        assert snapshot["counts"]["policy_rollback_total"] == 3

    def test_record_policy_freeze(self):
        """Should record policy freeze metric."""
        # Arrange
        collector = MetricsCollector()
        
        # Act
        collector.record_count("policy_freeze_total", 2)
        
        # Assert
        snapshot = collector.snapshot()
        assert snapshot["counts"]["policy_freeze_total"] == 2

    def test_record_cross_brand_gap(self):
        """Should record cross-brand p90-p10 gap as gauge."""
        # Arrange
        collector = MetricsCollector()
        
        # Act - record as latency (gauge)
        collector.record_latency("cross_brand_gap_p90_p10", 0.12)
        collector.record_latency("cross_brand_gap_p90_p10", 0.15)
        
        # Assert
        snapshot = collector.snapshot()
        # Average of 0.12 and 0.15 = 0.135
        assert pytest.approx(snapshot["avg_latencies"]["cross_brand_gap_p90_p10"], 0.001) == 0.135

    def test_cross_brand_gap_by_brand(self):
        """Should record cross-brand gap per brand."""
        # Arrange
        collector = MetricsCollector()
        
        # Act
        collector.record_latency("cross_brand_gap_p90_p10:brand1", 0.10)
        collector.record_latency("cross_brand_gap_p90_p10:brand2", 0.20)
        
        # Assert
        snapshot = collector.snapshot()
        assert "cross_brand_gap_p90_p10:brand1" in snapshot["avg_latencies"]
        assert "cross_brand_gap_p90_p10:brand2" in snapshot["avg_latencies"]


class TestPrometheusRender:
    """Test Prometheus format rendering for v18 metrics."""

    def test_render_policy_proposal_counter(self):
        """Should render policy_proposal as counter."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_proposal_total", 5)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert
        assert "vm_policy_proposal_total" in output
        assert "TYPE vm_policy_proposal_total counter" in output
        assert "vm_policy_proposal_total 5" in output

    def test_render_policy_applied_counter(self):
        """Should render policy_applied as counter."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_applied_total", 3)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert
        assert "vm_policy_applied_total 3" in output

    def test_render_policy_blocked_counter(self):
        """Should render policy_blocked as counter."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_blocked_total", 2)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert
        assert "vm_policy_blocked_total 2" in output

    def test_render_policy_rollback_counter(self):
        """Should render policy_rollback as counter."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_rollback_total", 1)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert
        assert "vm_policy_rollback_total 1" in output

    def test_render_policy_freeze_counter(self):
        """Should render policy_freeze as counter."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_freeze_total", 4)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert
        assert "vm_policy_freeze_total 4" in output

    def test_render_cross_brand_gap_gauge(self):
        """Should render cross_brand_gap_p90_p10 as gauge."""
        # Arrange
        collector = MetricsCollector()
        collector.record_latency("cross_brand_gap_p90_p10", 0.18)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert
        assert "vm_cross_brand_gap_p90_p10" in output
        assert "TYPE vm_cross_brand_gap_p90_p10 gauge" in output

    def test_render_all_policy_metrics_together(self):
        """Should render all policy metrics together."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_proposal_total", 10)
        collector.record_count("policy_applied_total", 7)
        collector.record_count("policy_blocked_total", 2)
        collector.record_count("policy_rollback_total", 1)
        collector.record_count("policy_freeze_total", 0)
        collector.record_latency("cross_brand_gap_p90_p10", 0.15)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert
        assert "vm_policy_proposal_total" in output
        assert "vm_policy_applied_total" in output
        assert "vm_policy_blocked_total" in output
        assert "vm_policy_rollback_total" in output
        assert "vm_policy_freeze_total" in output
        assert "vm_cross_brand_gap_p90_p10" in output

    def test_prometheus_output_format(self):
        """Should produce valid Prometheus format."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_proposal_total", 5)
        collector.record_latency("cross_brand_gap_p90_p10", 0.12)
        snapshot = collector.snapshot()
        
        # Act
        output = render_prometheus(snapshot, prefix="vm")
        
        # Assert - basic format checks
        lines = output.strip().split("\n")
        
        # Should have TYPE lines for each metric
        type_lines = [l for l in lines if l.startswith("# TYPE")]
        assert len(type_lines) >= 2
        
        # Should have metric value lines (not comments, not empty)
        value_lines = [l for l in lines if not l.startswith("#") and l.strip()]
        assert len(value_lines) >= 2
        
        # Each value line should have format: name value
        for line in value_lines:
            parts = line.split()
            assert len(parts) == 2, f"Invalid format: {line}"
            assert parts[1].replace(".", "").isdigit() or parts[1].replace("-", "").isdigit()


class TestMetricsCollectorSnapshot:
    """Test metrics collector snapshot functionality."""

    def test_snapshot_includes_timestamp(self):
        """Snapshot should include timestamp."""
        # Arrange
        collector = MetricsCollector()
        
        # Act
        snapshot = collector.snapshot()
        
        # Assert
        assert "timestamp" in snapshot
        # Should be valid ISO format
        timestamp = snapshot["timestamp"]
        assert "T" in timestamp  # ISO format has T separator

    def test_snapshot_thread_safety(self):
        """Snapshot should be thread-safe."""
        import threading
        import time
        
        # Arrange
        collector = MetricsCollector()
        errors = []
        
        def record_metrics():
            try:
                for _ in range(100):
                    collector.record_count("policy_proposal_total")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        def take_snapshots():
            try:
                for _ in range(100):
                    collector.snapshot()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        # Act
        threads = [
            threading.Thread(target=record_metrics),
            threading.Thread(target=take_snapshots),
            threading.Thread(target=record_metrics),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Assert
        assert len(errors) == 0, f"Thread errors: {errors}"

    def test_snapshot_is_immutable_copy(self):
        """Modifying snapshot should not affect collector."""
        # Arrange
        collector = MetricsCollector()
        collector.record_count("policy_proposal_total", 5)
        
        # Act
        snapshot1 = collector.snapshot()
        snapshot1["counts"]["policy_proposal_total"] = 999
        snapshot2 = collector.snapshot()
        
        # Assert
        assert snapshot2["counts"]["policy_proposal_total"] == 5
