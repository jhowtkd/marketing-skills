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
        collector.record_latency("cross_brand_gap_brand_a", 0.10)
        collector.record_latency("cross_brand_gap_brand_b", 0.20)
        
        # Assert
        snapshot = collector.snapshot()
        assert "cross_brand_gap_brand_a" in snapshot["avg_latencies"]
        assert "cross_brand_gap_brand_b" in snapshot["avg_latencies"]


# v22 DAG Metrics Tests

class TestDagMetrics:
    """Test v22 DAG-related metrics."""

    def test_record_dag_run_total(self):
        """Should record DAG run metric."""
        collector = MetricsCollector()
        
        collector.record_count("dag_runs_total_completed", 1)
        collector.record_count("dag_runs_total_failed", 1)
        
        snapshot = collector.snapshot()
        assert snapshot["counts"]["dag_runs_total_completed"] == 1
        assert snapshot["counts"]["dag_runs_total_failed"] == 1

    def test_record_dag_node_execution_total(self):
        """Should record DAG node execution metric."""
        collector = MetricsCollector()
        
        collector.record_count("dag_node_executions_completed", 1)
        collector.record_count("dag_node_executions_failed", 1)
        collector.record_count("dag_node_executions_timeout", 1)
        
        snapshot = collector.snapshot()
        assert snapshot["counts"]["dag_node_executions_completed"] == 1
        assert snapshot["counts"]["dag_node_executions_failed"] == 1
        assert snapshot["counts"]["dag_node_executions_timeout"] == 1

    def test_record_dag_retry_total(self):
        """Should record DAG retry metric."""
        collector = MetricsCollector()
        
        collector.record_count("dag_retries_total", 5)
        
        snapshot = collector.snapshot()
        assert snapshot["counts"]["dag_retries_total"] == 5

    def test_record_dag_timeout_total(self):
        """Should record DAG timeout metric."""
        collector = MetricsCollector()
        
        collector.record_count("dag_timeouts_total", 2)
        
        snapshot = collector.snapshot()
        assert snapshot["counts"]["dag_timeouts_total"] == 2

    def test_record_dag_approval_wait_seconds(self):
        """Should record DAG approval wait time."""
        collector = MetricsCollector()
        
        collector.record_latency("dag_approval_wait_seconds", 30.5)
        collector.record_latency("dag_approval_wait_seconds", 45.2)
        
        snapshot = collector.snapshot()
        assert "dag_approval_wait_seconds" in snapshot["avg_latencies"]

    def test_record_dag_handoff_failed_total(self):
        """Should record DAG handoff failed metric."""
        collector = MetricsCollector()
        
        collector.record_count("dag_handoff_failed_total", 1)
        
        snapshot = collector.snapshot()
        assert snapshot["counts"]["dag_handoff_failed_total"] == 1

    def test_dag_metrics_in_prometheus_output(self):
        """DAG metrics should appear in Prometheus output."""
        from vm_webapp.agent_dag_audit import DagMetricsCollector
        
        dag_collector = DagMetricsCollector()
        dag_collector.record_run(status="completed")
        dag_collector.record_node_execution(status="completed")
        dag_collector.record_retry()
        
        output = dag_collector.render_prometheus()
        
        assert "dag_runs_total" in output
        assert "dag_node_executions_total" in output
        assert "dag_retries_total" in output
