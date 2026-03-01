"""
Tests for Operational Checkpoint v22 Week 1
"""

import pytest
from datetime import datetime, timezone


class TestKpiCalculation:
    """Test KPI calculation functions."""

    def test_calculate_status_pass(self):
        """Should return PASS when target is achieved."""
        from scripts.ops_checkpoint_v22_week1 import calculate_status, KpiStatus
        
        # Higher is better - current exceeds target
        status = calculate_status(
            current=50.0,
            target=45.0,
            baseline=40.0,
            direction="higher_better"
        )
        assert status == KpiStatus.PASS

    def test_calculate_status_attention(self):
        """Should return ATTENTION when >=70% of target."""
        from scripts.ops_checkpoint_v22_week1 import calculate_status, KpiStatus
        
        # 75% progress should be ATTENTION
        # baseline=40, target=45 (delta=5)
        # current=43.75 -> progress=(43.75-40)/5=0.75
        status = calculate_status(
            current=43.75,
            target=45.0,
            baseline=40.0,
            direction="higher_better"
        )
        assert status == KpiStatus.ATTENTION

    def test_calculate_status_fail(self):
        """Should return FAIL when <70% of target."""
        from scripts.ops_checkpoint_v22_week1 import calculate_status, KpiStatus
        
        # baseline=40, target=45 (delta=5)
        # current=42 -> progress=(42-40)/5=0.4 (40% < 70%)
        status = calculate_status(
            current=42.0,
            target=45.0,
            baseline=40.0,
            direction="higher_better"
        )
        assert status == KpiStatus.FAIL

    def test_calculate_status_lower_better_pass(self):
        """Should handle lower_is_better correctly."""
        from scripts.ops_checkpoint_v22_week1 import calculate_status, KpiStatus
        
        # Lower is better - current below target
        status = calculate_status(
            current=18.0,
            target=20.0,
            baseline=25.0,
            direction="lower_better"
        )
        assert status == KpiStatus.PASS

    def test_calculate_status_maintain_no_increase(self):
        """Should return PASS for maintain when no increase."""
        from scripts.ops_checkpoint_v22_week1 import calculate_status, KpiStatus
        
        status = calculate_status(
            current=0.02,
            target=0.02,
            baseline=0.02,
            direction="maintain"
        )
        assert status == KpiStatus.PASS

    def test_calculate_status_maintain_fail_on_increase(self):
        """Should return FAIL for maintain when increased."""
        from scripts.ops_checkpoint_v22_week1 import calculate_status, KpiStatus
        
        status = calculate_status(
            current=0.03,
            target=0.02,
            baseline=0.02,
            direction="maintain"
        )
        assert status == KpiStatus.FAIL

    def test_calculate_status_no_data(self):
        """Should return NO_DATA when current is None."""
        from scripts.ops_checkpoint_v22_week1 import calculate_status, KpiStatus
        
        status = calculate_status(
            current=None,
            target=45.0,
            baseline=40.0,
            direction="higher_better"
        )
        assert status == KpiStatus.NO_DATA


class TestMetricsCollection:
    """Test metrics collection functions."""

    def test_collect_dag_metrics_returns_dict(self):
        """Should return metrics dictionary."""
        from scripts.ops_checkpoint_v22_week1 import collect_dag_metrics
        
        metrics = collect_dag_metrics(7)
        
        assert isinstance(metrics, dict)
        assert "runs" in metrics
        assert "nodes" in metrics
        assert "retries_total" in metrics

    def test_collect_baseline_metrics(self):
        """Should return baseline metrics."""
        from scripts.ops_checkpoint_v22_week1 import collect_baseline_metrics
        
        baseline = collect_baseline_metrics()
        
        assert isinstance(baseline, dict)
        assert "throughput_jobs_per_day" in baseline
        assert "mean_time_to_completion_minutes" in baseline
        assert "handoff_timeout_failure_rate" in baseline
        assert "incident_rate" in baseline


class TestKpiGeneration:
    """Test KPI generation."""

    def test_calculate_kpis_returns_list(self):
        """Should return list of KPI results."""
        from scripts.ops_checkpoint_v22_week1 import calculate_kpis
        
        metrics = {
            "runs": {"completed": 100, "failed": 5, "aborted": 2, "timeout": 3},
            "nodes": {"completed": 500, "failed": 10, "timeout": 5, "skipped": 1},
            "retries_total": 20,
            "handoff_failures_total": 2,
            "approvals": {"pending": 1, "granted": 50, "rejected": 2},
            "avg_approval_wait_sec": 45.0,
            "avg_node_execution_sec": 120.0,
        }
        baseline = {
            "throughput_jobs_per_day": 40.0,
            "mean_time_to_completion_minutes": 25.0,
            "handoff_timeout_failure_rate": 0.08,
            "incident_rate": 0.02,
            "approval_without_regen_24h": 0.65,
        }
        
        kpis = calculate_kpis(metrics, baseline, 7)
        
        assert isinstance(kpis, list)
        assert len(kpis) > 0
        
        # Check required KPIs exist
        kpi_names = [k.name for k in kpis]
        assert "throughput_jobs_per_day" in kpi_names
        assert "mean_time_to_completion_minutes" in kpi_names
        assert "handoff_timeout_failure_rate" in kpi_names
        assert "incident_rate" in kpi_names

    def test_kpi_has_required_fields(self):
        """Each KPI should have required fields."""
        from scripts.ops_checkpoint_v22_week1 import calculate_kpis
        
        metrics = {
            "runs": {"completed": 100, "failed": 5, "aborted": 2, "timeout": 3},
            "nodes": {"completed": 500, "failed": 10, "timeout": 5, "skipped": 1},
            "retries_total": 20,
            "handoff_failures_total": 2,
            "approvals": {"pending": 1, "granted": 50, "rejected": 2},
            "avg_approval_wait_sec": 45.0,
            "avg_node_execution_sec": 120.0,
        }
        baseline = {
            "throughput_jobs_per_day": 40.0,
            "mean_time_to_completion_minutes": 25.0,
            "handoff_timeout_failure_rate": 0.08,
            "incident_rate": 0.02,
            "approval_without_regen_24h": 0.65,
        }
        
        kpis = calculate_kpis(metrics, baseline, 7)
        
        for kpi in kpis:
            assert kpi.name
            assert kpi.description
            assert kpi.formula
            assert kpi.target_value is not None
            assert kpi.target_direction in ["higher_better", "lower_better", "maintain"]
            assert kpi.status is not None


class TestBottleneckIdentification:
    """Test bottleneck identification."""

    def test_identify_bottlenecks_with_approval_backlog(self):
        """Should identify approval backlog."""
        from scripts.ops_checkpoint_v22_week1 import identify_bottlenecks
        
        metrics = {
            "approvals": {"pending": 10},
            "retries_total": 20,
            "handoff_failures_total": 1,
            "nodes": {"timeout": 2},
        }
        
        bottlenecks = identify_bottlenecks(metrics)
        
        assert len(bottlenecks) > 0
        assert any(b["type"] == "approval_backlog" for b in bottlenecks)

    def test_identify_bottlenecks_with_handoff_failures(self):
        """Should identify handoff failures."""
        from scripts.ops_checkpoint_v22_week1 import identify_bottlenecks
        
        metrics = {
            "approvals": {"pending": 1},
            "retries_total": 20,
            "handoff_failures_total": 5,
            "nodes": {"timeout": 2},
        }
        
        bottlenecks = identify_bottlenecks(metrics)
        
        assert any(b["type"] == "handoff_failure" for b in bottlenecks)
        handoff = next(b for b in bottlenecks if b["type"] == "handoff_failure")
        assert handoff["severity"] == "high"


class TestRootCauseAnalysis:
    """Test root cause analysis."""

    def test_identify_root_causes_with_failures(self):
        """Should identify causes for failures."""
        from scripts.ops_checkpoint_v22_week1 import identify_root_causes, KpiResult, KpiStatus
        
        kpis = [
            KpiResult(
                name="handoff_timeout_failure_rate",
                description="Test",
                formula="test",
                target_value=0.05,
                target_direction="lower_better",
                status=KpiStatus.FAIL,
            )
        ]
        bottlenecks = []
        
        causes = identify_root_causes(kpis, bottlenecks)
        
        assert len(causes) > 0
        assert any("handoff" in c.lower() for c in causes)

    def test_identify_root_causes_healthy(self):
        """Should return healthy message when no issues."""
        from scripts.ops_checkpoint_v22_week1 import identify_root_causes, KpiResult, KpiStatus
        
        kpis = [
            KpiResult(
                name="test_kpi",
                description="Test",
                formula="test",
                target_value=1.0,
                target_direction="higher_better",
                status=KpiStatus.PASS,
            )
        ]
        bottlenecks = []
        
        causes = identify_root_causes(kpis, bottlenecks)
        
        assert len(causes) > 0
        assert any("operando" in c.lower() or "esperados" in c.lower() for c in causes)


class TestActionRecommendations:
    """Test action recommendations."""

    def test_recommend_actions_with_failures(self):
        """Should recommend P0 actions for failures."""
        from scripts.ops_checkpoint_v22_week1 import recommend_actions, KpiResult, KpiStatus
        
        kpis = [
            KpiResult(
                name="test_kpi",
                description="Test",
                formula="test",
                target_value=1.0,
                target_direction="higher_better",
                status=KpiStatus.FAIL,
            )
        ]
        bottlenecks = []
        
        actions = recommend_actions(kpis, bottlenecks)
        
        assert any(a["priority"] == "P0" for a in actions)

    def test_recommend_actions_healthy(self):
        """Should recommend P2 actions for healthy system."""
        from scripts.ops_checkpoint_v22_week1 import recommend_actions, KpiResult, KpiStatus
        
        kpis = [
            KpiResult(
                name="test_kpi",
                description="Test",
                formula="test",
                target_value=1.0,
                target_direction="higher_better",
                status=KpiStatus.PASS,
            )
        ]
        bottlenecks = []
        
        actions = recommend_actions(kpis, bottlenecks)
        
        # Should still have P2 actions for continuous improvement
        assert any(a["priority"] == "P2" for a in actions)

    def test_action_has_required_fields(self):
        """Each action should have required fields."""
        from scripts.ops_checkpoint_v22_week1 import recommend_actions, KpiResult, KpiStatus
        
        kpis = [KpiResult(
            name="test_kpi",
            description="Test",
            formula="test",
            target_value=1.0,
            target_direction="higher_better",
            status=KpiStatus.PASS,
        )]
        
        actions = recommend_actions(kpis, [])
        
        for action in actions:
            assert "priority" in action
            assert "action" in action
            assert "owner" in action
            assert "due" in action
            assert "rationale" in action


class TestReportGeneration:
    """Test report generation."""

    def test_generate_checkpoint(self):
        """Should generate complete checkpoint."""
        from scripts.ops_checkpoint_v22_week1 import generate_checkpoint
        
        checkpoint = generate_checkpoint(7)
        
        assert checkpoint.version == "v22-week1"
        assert checkpoint.window_days == 7
        assert len(checkpoint.kpis) > 0
        assert checkpoint.generated_at

    def test_generate_markdown_report(self):
        """Should generate markdown report."""
        from scripts.ops_checkpoint_v22_week1 import generate_checkpoint, generate_markdown_report
        
        checkpoint = generate_checkpoint(7)
        report = generate_markdown_report(checkpoint)
        
        assert "# Operational Checkpoint v22" in report
        assert "## 📊 Resumo Executivo" in report
        assert "## 📈 KPI Table" in report
        assert "## 🔴 Top Gargalos DAG" in report
        assert "## 🔍 Causas Prováveis" in report
        assert "## 🎯 Ações Recomendadas" in report

    def test_format_kpi_table(self):
        """Should format KPI table correctly."""
        from scripts.ops_checkpoint_v22_week1 import format_kpi_table, KpiResult, KpiStatus
        
        kpis = [
            KpiResult(
                name="test_kpi",
                description="Test KPI",
                formula="test_formula",
                target_value=100.0,
                target_direction="higher_better",
                current_value=90.0,
                baseline_value=80.0,
                unit="count",
                status=KpiStatus.ATTENTION,
            )
        ]
        
        table = format_kpi_table(kpis)
        
        assert "| KPI |" in table
        assert "test_kpi" in table
        assert "Test KPI" in table
        assert "`test_formula`" in table
        assert "ATTENTION" in table


class TestRequiredKpis:
    """Test that all required KPIs are present."""

    def test_all_required_kpis_present(self):
        """All required KPIs should be calculated."""
        from scripts.ops_checkpoint_v22_week1 import calculate_kpis
        
        metrics = {
            "runs": {"completed": 100, "failed": 5, "aborted": 2, "timeout": 3},
            "nodes": {"completed": 500, "failed": 10, "timeout": 5, "skipped": 1},
            "retries_total": 20,
            "handoff_failures_total": 2,
            "approvals": {"pending": 1, "granted": 50, "rejected": 2},
            "avg_approval_wait_sec": 45.0,
            "avg_node_execution_sec": 120.0,
        }
        baseline = {
            "throughput_jobs_per_day": 40.0,
            "mean_time_to_completion_minutes": 25.0,
            "handoff_timeout_failure_rate": 0.08,
            "incident_rate": 0.02,
            "approval_without_regen_24h": 0.65,
        }
        
        kpis = calculate_kpis(metrics, baseline, 7)
        kpi_names = [k.name for k in kpis]
        
        required_kpis = [
            "throughput_jobs_per_day",
            "mean_time_to_completion_minutes",
            "handoff_timeout_failure_rate",
            "incident_rate",
            "dag_runs_created_total",
            "dag_nodes_completed_total",
            "dag_node_retry_total",
            "dag_handoff_timeout_total",
            "dag_approval_wait_seconds_avg",
            "dag_approval_wait_seconds_p95",
            "dag_mttc_seconds_avg",
            "dag_mttc_seconds_p95",
            "approval_without_regen_24h",
        ]
        
        for required in required_kpis:
            assert required in kpi_names, f"Missing required KPI: {required}"

    def test_kpi_targets_are_reasonable(self):
        """KPI targets should be reasonable."""
        from scripts.ops_checkpoint_v22_week1 import calculate_kpis
        
        metrics = {
            "runs": {"completed": 100, "failed": 5, "aborted": 2, "timeout": 3},
            "nodes": {"completed": 500, "failed": 10, "timeout": 5, "skipped": 1},
            "retries_total": 20,
            "handoff_failures_total": 2,
            "approvals": {"pending": 1, "granted": 50, "rejected": 2},
            "avg_approval_wait_sec": 45.0,
            "avg_node_execution_sec": 120.0,
        }
        baseline = {
            "throughput_jobs_per_day": 40.0,
            "mean_time_to_completion_minutes": 25.0,
            "handoff_timeout_failure_rate": 0.08,
            "incident_rate": 0.02,
            "approval_without_regen_24h": 0.65,
        }
        
        kpis = calculate_kpis(metrics, baseline, 7)
        
        # Check throughput target is +30%
        throughput_kpi = next(k for k in kpis if k.name == "throughput_jobs_per_day")
        expected_target = baseline["throughput_jobs_per_day"] * 1.30
        assert abs(throughput_kpi.target_value - expected_target) < 0.1
        
        # Check MTTC target is -25%
        mttc_kpi = next(k for k in kpis if k.name == "mean_time_to_completion_minutes")
        expected_target = baseline["mean_time_to_completion_minutes"] * 0.75
        assert abs(mttc_kpi.target_value - expected_target) < 0.1
        
        # Check handoff target is -40%
        handoff_kpi = next(k for k in kpis if k.name == "handoff_timeout_failure_rate")
        expected_target = baseline["handoff_timeout_failure_rate"] * 0.60
        assert abs(handoff_kpi.target_value - expected_target) < 0.01
