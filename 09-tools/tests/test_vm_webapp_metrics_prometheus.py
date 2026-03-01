"""Tests for v25 Quality Optimizer metrics and observability."""

import pytest
from datetime import datetime, timezone

from vm_webapp.observability import (
    MetricsCollector,
    QualityOptimizerMetrics,
    render_prometheus,
)


@pytest.fixture
def collector():
    """Metrics collector fixture."""
    return MetricsCollector()


class TestQualityOptimizerMetrics:
    """Test v25 Quality Optimizer metrics collection."""

    def test_record_quality_cycle(self, collector):
        """Should record a quality optimizer cycle."""
        collector.record_quality_cycle()
        
        metrics = collector.get_quality_metrics()
        assert metrics.cycles_total == 1
        assert metrics.last_cycle_at is not None

    def test_record_quality_proposal_generated(self, collector):
        """Should record proposal generation."""
        collector.record_quality_proposal("generated")
        
        metrics = collector.get_quality_metrics()
        assert metrics.proposals_generated_total == 1

    def test_record_quality_proposal_blocked(self, collector):
        """Should record blocked proposal."""
        collector.record_quality_proposal("blocked")
        
        metrics = collector.get_quality_metrics()
        assert metrics.proposals_generated_total == 1
        assert metrics.proposals_blocked_total == 1

    def test_record_quality_proposal_rejected(self, collector):
        """Should record rejected proposal."""
        collector.record_quality_proposal("rejected")
        
        metrics = collector.get_quality_metrics()
        assert metrics.proposals_generated_total == 1
        assert metrics.proposals_rejected_total == 1

    def test_record_quality_proposal_applied(self, collector):
        """Should record applied proposal."""
        collector.record_quality_proposal_applied()
        
        metrics = collector.get_quality_metrics()
        assert metrics.proposals_applied_total == 1
        assert metrics.last_proposal_applied_at is not None

    def test_record_quality_rollback(self, collector):
        """Should record rollback operation."""
        collector.record_quality_rollback()
        
        metrics = collector.get_quality_metrics()
        assert metrics.rollbacks_total == 1

    def test_record_quality_impact(self, collector):
        """Should record expected impact metrics."""
        collector.record_quality_impact(
            quality_gain=8.5,
            cost_impact_pct=8.2,
            time_impact_pct=7.5,
        )
        
        metrics = collector.get_quality_metrics()
        assert metrics.quality_gain_expected == 8.5
        assert metrics.cost_impact_expected_pct == 8.2
        assert metrics.time_impact_expected_pct == 7.5

    def test_record_constraint_violation_cost(self, collector):
        """Should record cost constraint violation."""
        collector.record_constraint_violation("cost")
        
        metrics = collector.get_quality_metrics()
        assert metrics.constraint_violations_cost == 1
        assert metrics.constraint_violations_time == 0
        assert metrics.constraint_violations_incident == 0

    def test_record_constraint_violation_time(self, collector):
        """Should record time constraint violation."""
        collector.record_constraint_violation("time")
        
        metrics = collector.get_quality_metrics()
        assert metrics.constraint_violations_cost == 0
        assert metrics.constraint_violations_time == 1
        assert metrics.constraint_violations_incident == 0

    def test_record_constraint_violation_incident(self, collector):
        """Should record incident constraint violation."""
        collector.record_constraint_violation("incident")
        
        metrics = collector.get_quality_metrics()
        assert metrics.constraint_violations_cost == 0
        assert metrics.constraint_violations_time == 0
        assert metrics.constraint_violations_incident == 1

    def test_get_quality_metrics_returns_snapshot(self, collector):
        """Should return independent snapshot."""
        collector.record_quality_cycle()
        
        metrics1 = collector.get_quality_metrics()
        collector.record_quality_cycle()
        metrics2 = collector.get_quality_metrics()
        
        assert metrics1.cycles_total == 1
        assert metrics2.cycles_total == 2

    def test_quality_metrics_counters_accumulate(self, collector):
        """Counters should accumulate across multiple records."""
        collector.record_quality_cycle()
        collector.record_quality_cycle()
        collector.record_quality_cycle()
        
        collector.record_quality_proposal("generated")
        collector.record_quality_proposal("blocked")
        collector.record_quality_proposal("rejected")
        
        metrics = collector.get_quality_metrics()
        assert metrics.cycles_total == 3
        assert metrics.proposals_generated_total == 3
        assert metrics.proposals_blocked_total == 1
        assert metrics.proposals_rejected_total == 1


class TestQualityOptimizerMetricsStructure:
    """Test QualityOptimizerMetrics dataclass structure."""

    def test_default_values(self):
        """Should have correct default values."""
        metrics = QualityOptimizerMetrics()
        
        assert metrics.cycles_total == 0
        assert metrics.proposals_generated_total == 0
        assert metrics.proposals_applied_total == 0
        assert metrics.proposals_blocked_total == 0
        assert metrics.proposals_rejected_total == 0
        assert metrics.rollbacks_total == 0
        assert metrics.quality_gain_expected == 0.0
        assert metrics.cost_impact_expected_pct == 0.0
        assert metrics.time_impact_expected_pct == 0.0
        assert metrics.constraint_violations_cost == 0
        assert metrics.constraint_violations_time == 0
        assert metrics.constraint_violations_incident == 0
        assert metrics.last_cycle_at is None
        assert metrics.last_proposal_applied_at is None

    def test_custom_values(self):
        """Should accept custom values."""
        metrics = QualityOptimizerMetrics(
            cycles_total=10,
            proposals_generated_total=20,
            proposals_applied_total=15,
            proposals_blocked_total=3,
            proposals_rejected_total=2,
            rollbacks_total=1,
            quality_gain_expected=8.5,
            cost_impact_expected_pct=8.2,
            time_impact_expected_pct=7.5,
            constraint_violations_cost=1,
            constraint_violations_time=0,
            constraint_violations_incident=0,
            last_cycle_at=datetime.now(timezone.utc).isoformat(),
            last_proposal_applied_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert metrics.cycles_total == 10
        assert metrics.quality_gain_expected == 8.5
        assert metrics.cost_impact_expected_pct == 8.2


class TestPrometheusRendering:
    """Test Prometheus format rendering for v25 metrics."""

    def test_render_quality_metrics_in_snapshot(self, collector):
        """Quality metrics should appear in snapshot."""
        collector.record_quality_cycle()
        collector.record_quality_proposal("generated")
        collector.record_quality_proposal_applied()  # This increments proposals_applied_total
        collector.record_quality_impact(8.5, 8.2, 7.5)
        
        snapshot = collector.snapshot()
        
        # Should contain v25 quality optimizer metrics
        assert "quality_optimizer_v25" in snapshot
        v25_metrics = snapshot["quality_optimizer_v25"]
        assert v25_metrics["cycles_total"] == 1
        assert v25_metrics["proposals_generated_total"] == 1
        assert v25_metrics["proposals_applied_total"] == 1
        assert v25_metrics["quality_gain_expected"] == 8.5
        assert v25_metrics["cost_impact_expected_pct"] == 8.2
        assert v25_metrics["time_impact_expected_pct"] == 7.5

    def test_render_includes_timestamp(self, collector):
        """Should include timestamp in output."""
        snapshot = collector.snapshot()
        
        assert "timestamp" in snapshot
        assert snapshot["timestamp"] is not None


class TestMetricsIsolation:
    """Test isolation between different metric types."""

    def test_quality_metrics_isolated_from_roi(self, collector):
        """Quality metrics should not affect ROI metrics."""
        collector.record_quality_cycle()
        collector.record_quality_proposal_applied()
        
        roi_metrics = collector.get_roi_metrics()
        
        # ROI metrics should be unaffected
        assert roi_metrics.cycles_total == 0
        assert roi_metrics.proposals_applied_total == 0

    def test_quality_metrics_isolated_from_learning(self, collector):
        """Quality metrics should not affect learning metrics."""
        collector.record_quality_cycle()
        collector.record_quality_proposal_applied()
        
        learning_metrics = collector.get_learning_metrics()
        
        # Learning metrics should be unaffected
        assert learning_metrics.learning_cycles_total == 0
        assert learning_metrics.proposals_applied_total == 0


class TestConcurrentAccess:
    """Test thread safety of metrics collection."""

    def test_concurrent_quality_cycle_recording(self, collector):
        """Should handle concurrent cycle recording."""
        import threading
        
        def record_cycles(n):
            for _ in range(n):
                collector.record_quality_cycle()
        
        threads = [
            threading.Thread(target=record_cycles, args=(10,))
            for _ in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        metrics = collector.get_quality_metrics()
        assert metrics.cycles_total == 50

    def test_concurrent_proposal_recording(self, collector):
        """Should handle concurrent proposal recording."""
        import threading
        
        def record_proposals(n):
            for _ in range(n):
                collector.record_quality_proposal("generated")
        
        threads = [
            threading.Thread(target=record_proposals, args=(10,))
            for _ in range(3)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        metrics = collector.get_quality_metrics()
        assert metrics.proposals_generated_total == 30
