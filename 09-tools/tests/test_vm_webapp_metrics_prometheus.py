"""Tests for v28 Recovery Orchestration Prometheus Metrics.

TDD: Testes para runs/steps/failed/auto/manual/mttr metrics.
"""

from __future__ import annotations

import pytest

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.observability import (
    MetricsCollector,
    RecoveryOrchestrationMetrics,
    render_prometheus,
)


class TestRecoveryOrchestrationMetrics:
    """Testes para métricas de recovery v28."""

    def test_collector_initializes_recovery_metrics(self):
        """Collector deve inicializar métricas de recovery."""
        collector = MetricsCollector()
        metrics = collector.get_recovery_metrics()
        
        assert isinstance(metrics, RecoveryOrchestrationMetrics)
        assert metrics.runs_total == 0
        assert metrics.steps_total == 0

    def test_record_recovery_run(self):
        """Deve registrar recovery run."""
        collector = MetricsCollector()
        
        collector.record_recovery_run(auto=False)
        
        metrics = collector.get_recovery_metrics()
        assert metrics.runs_total == 1
        assert metrics.runs_manual == 1
        assert metrics.runs_auto == 0
        assert metrics.active_runs == 1
        assert metrics.last_run_at is not None

    def test_record_recovery_run_auto(self):
        """Deve registrar recovery run auto."""
        collector = MetricsCollector()
        
        collector.record_recovery_run(auto=True)
        
        metrics = collector.get_recovery_metrics()
        assert metrics.runs_total == 1
        assert metrics.runs_auto == 1
        assert metrics.runs_manual == 0

    def test_record_recovery_run_success(self):
        """Deve registrar sucesso de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_run()
        collector.record_recovery_run_success(duration_seconds=45.5)
        
        metrics = collector.get_recovery_metrics()
        assert metrics.runs_successful == 1
        assert metrics.active_runs == 0
        assert metrics.mttr_count == 1
        assert metrics.mttr_seconds_avg == 45.5
        assert metrics.last_successful_run_at is not None

    def test_record_recovery_run_failure(self):
        """Deve registrar falha de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_run()
        collector.record_recovery_run_failure()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.runs_failed == 1
        assert metrics.active_runs == 0
        assert metrics.last_failed_run_at is not None

    def test_record_recovery_step(self):
        """Deve registrar step de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_step("success")
        collector.record_recovery_step("success")
        collector.record_recovery_step("failed")
        collector.record_recovery_step("skipped")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.steps_total == 4
        assert metrics.steps_successful == 2
        assert metrics.steps_failed == 1
        assert metrics.steps_skipped == 1

    def test_record_approval_requested(self):
        """Deve registrar requisição de aprovação."""
        collector = MetricsCollector()
        
        collector.record_approval_requested()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.approval_requests_total == 1
        assert metrics.pending_approvals == 1

    def test_record_approval_granted(self):
        """Deve registrar aprovação concedida."""
        collector = MetricsCollector()
        
        collector.record_approval_requested()
        collector.record_approval_granted()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.approvals_granted == 1
        assert metrics.pending_approvals == 0
        assert metrics.last_approval_at is not None

    def test_record_approval_rejected(self):
        """Deve registrar aprovação rejeitada."""
        collector = MetricsCollector()
        
        collector.record_approval_requested()
        collector.record_approval_rejected()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.approvals_rejected == 1
        assert metrics.pending_approvals == 0
        assert metrics.last_rejection_at is not None

    def test_record_recovery_frozen(self):
        """Deve registrar freeze de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_frozen()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.frozen_incidents == 1
        assert metrics.last_freeze_at is not None

    def test_record_recovery_rollback(self):
        """Deve registrar rollback de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_rollback()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.rolled_back_runs == 1
        assert metrics.last_rollback_at is not None

    def test_record_incident_classified(self):
        """Deve registrar classificação de incidente."""
        collector = MetricsCollector()
        
        collector.record_incident_classified("handoff_timeout")
        collector.record_incident_classified("handoff_timeout")
        collector.record_incident_classified("approval_sla_breach")
        collector.record_incident_classified("quality_regression")
        collector.record_incident_classified("system_failure")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.incident_handoff_timeout == 2
        assert metrics.incident_approval_sla_breach == 1
        assert metrics.incident_quality_regression == 1
        assert metrics.incident_system_failure == 1

    def test_mttr_calculation(self):
        """Deve calcular MTTR corretamente."""
        collector = MetricsCollector()
        
        collector.record_recovery_run()
        collector.record_recovery_run_success(duration_seconds=30.0)
        
        collector.record_recovery_run()
        collector.record_recovery_run_success(duration_seconds=60.0)
        
        collector.record_recovery_run()
        collector.record_recovery_run_success(duration_seconds=90.0)
        
        metrics = collector.get_recovery_metrics()
        assert metrics.mttr_count == 3
        assert metrics.mttr_seconds_avg == 60.0  # (30+60+90)/3

    def test_recovery_metrics_in_snapshot(self):
        """Métricas de recovery devem estar no snapshot."""
        collector = MetricsCollector()
        
        collector.record_recovery_run(auto=True)
        collector.record_recovery_step("success")
        collector.record_approval_requested()
        
        snapshot = collector.snapshot()
        
        assert "recovery_orchestration_v28" in snapshot
        recovery = snapshot["recovery_orchestration_v28"]
        assert recovery["runs_total"] == 1
        assert recovery["runs_auto"] == 1
        assert recovery["steps_total"] == 1
        assert recovery["steps_successful"] == 1
        assert recovery["approval_requests_total"] == 1


class TestRecoveryPrometheusRendering:
    """Testes para renderização Prometheus de recovery."""

    def test_render_recovery_counts(self):
        """Deve renderizar métricas de recovery no formato Prometheus."""
        collector = MetricsCollector()
        collector.record_count("recovery_runs_total", 5)
        collector.record_count("recovery_steps_total", 20)
        
        snapshot = collector.snapshot()
        output = render_prometheus(snapshot)
        
        assert "vm_recovery_runs_total" in output
        assert "vm_recovery_steps_total" in output
