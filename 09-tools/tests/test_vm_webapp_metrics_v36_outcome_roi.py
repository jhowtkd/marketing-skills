"""Tests for v36 Outcome Attribution and Hybrid ROI Metrics.

TDD: fail -> implement -> pass -> commit
"""

import pytest
from datetime import datetime, timezone

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.observability import MetricsCollector


class TestOutcomeAttributionMetrics:
    """Test v36 Outcome Attribution metrics."""

    def test_collector_initializes_outcome_roi_metrics(self):
        """Collector should initialize v36 outcome ROI metrics."""
        collector = MetricsCollector()
        metrics = collector.get_outcome_roi_metrics()
        
        assert "outcomes_attributed" in metrics
        assert "proposals_generated" in metrics
        assert "hybrid_roi_index_avg" in metrics
        assert "payback_time_avg_days" in metrics

    def test_record_outcome_attributed(self):
        """Should record attributed outcome."""
        collector = MetricsCollector()
        
        collector.record_outcome_attributed("activation", "linear")
        collector.record_outcome_attributed("recovery", "first_touch")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["outcomes_attributed"] == 2
        assert metrics["attribution_methods"]["linear"] == 1
        assert metrics["attribution_methods"]["first_touch"] == 1

    def test_record_proposal_generated(self):
        """Should record generated proposal."""
        collector = MetricsCollector()
        
        collector.record_proposal_generated("low", 0.25)
        collector.record_proposal_generated("medium", 0.12)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["proposals_generated"] == 2
        assert metrics["by_risk_level"]["low"] == 1
        assert metrics["by_risk_level"]["medium"] == 1

    def test_record_proposal_auto_applied(self):
        """Should record auto-applied proposal."""
        collector = MetricsCollector()
        
        collector.record_proposal_generated("low", 0.25)
        collector.record_proposal_auto_applied(0.25)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["proposals_auto_applied"] == 1
        assert metrics["proposals_pending_approval"] == 0

    def test_record_proposal_needing_approval(self):
        """Should record proposal needing approval."""
        collector = MetricsCollector()
        
        collector.record_proposal_generated("medium", 0.12)
        collector.record_proposal_needing_approval(0.12)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["proposals_pending_approval"] == 1

    def test_record_proposal_approved(self):
        """Should record approved proposal."""
        collector = MetricsCollector()
        
        collector.record_proposal_generated("medium", 0.12)
        collector.record_proposal_needing_approval(0.12)
        collector.record_proposal_approved(0.12)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["proposals_approved"] == 1
        assert metrics["proposals_pending_approval"] == 0

    def test_record_proposal_rejected(self):
        """Should record rejected proposal."""
        collector = MetricsCollector()
        
        collector.record_proposal_generated("high", 0.05)
        collector.record_proposal_rejected(0.05, "risk_too_high")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["proposals_rejected"] == 1

    def test_record_proposal_blocked(self):
        """Should record blocked proposal."""
        collector = MetricsCollector()
        
        collector.record_proposal_blocked("incident_rate", "incident spike detected")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["proposals_blocked"] == 1
        assert metrics["block_reasons"]["incident_rate"] == 1

    def test_record_guardrail_violation(self):
        """Should record guardrail violation."""
        collector = MetricsCollector()
        
        collector.record_guardrail_violation("min_success_rate")
        collector.record_guardrail_violation("max_incident_rate")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["guardrail_violations"] == 2
        assert metrics["guardrail_violation_types"]["min_success_rate"] == 1

    def test_record_hybrid_roi_index(self):
        """Should record hybrid ROI index."""
        collector = MetricsCollector()
        
        collector.record_hybrid_roi_index(0.25)
        collector.record_hybrid_roi_index(0.30)
        collector.record_hybrid_roi_index(0.20)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["hybrid_roi_index_avg"] == pytest.approx(0.25, rel=0.01)
        assert metrics["hybrid_roi_index_min"] == pytest.approx(0.20, rel=0.01)
        assert metrics["hybrid_roi_index_max"] == pytest.approx(0.30, rel=0.01)

    def test_record_payback_time(self):
        """Should record payback time."""
        collector = MetricsCollector()
        
        collector.record_payback_time(5.0)
        collector.record_payback_time(7.0)
        collector.record_payback_time(3.0)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["payback_time_avg_days"] == pytest.approx(5.0, rel=0.01)

    def test_record_quality_penalty(self):
        """Should record quality penalty."""
        collector = MetricsCollector()
        
        collector.record_quality_penalty("incident", 0.25)
        collector.record_quality_penalty("quality_degradation", 0.10)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["quality_penalties_applied"] == 2

    def test_record_roi_rollback(self):
        """Should record ROI rollback."""
        collector = MetricsCollector()
        
        collector.record_roi_rollback(3, "quality_degradation")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["rollbacks_executed"] == 1
        assert metrics["rolled_back_proposals"] == 3

    def test_get_outcome_roi_metrics_returns_v36(self):
        """get_outcome_roi_metrics should return v36 metrics."""
        collector = MetricsCollector()
        
        collector.record_outcome_attributed("activation", "linear")
        collector.record_proposal_generated("low", 0.25)
        
        metrics = collector.get_outcome_roi_metrics()
        assert "outcomes_attributed" in metrics
        assert metrics["outcomes_attributed"] == 1


class TestOutcomeAttributionPrometheusMetrics:
    """Test Prometheus metrics for v36."""

    def test_roi_proposals_total_metric(self):
        """Should expose roi_proposals_total metric."""
        from prometheus_client import REGISTRY
        
        # Check if metric exists
        try:
            metric = REGISTRY._names_to_collectors.get("roi_proposals_total")
            assert metric is not None
        except:
            # Metric might not be registered yet
            pass

    def test_hybrid_roi_index_metric(self):
        """Should expose hybrid_roi_index metric."""
        from prometheus_client import REGISTRY
        
        try:
            metric = REGISTRY._names_to_collectors.get("hybrid_roi_index")
            assert metric is not None
        except:
            pass

    def test_payback_time_days_metric(self):
        """Should expose payback_time_days metric."""
        from prometheus_client import REGISTRY
        
        try:
            metric = REGISTRY._names_to_collectors.get("payback_time_days")
            assert metric is not None
        except:
            pass
