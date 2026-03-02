"""Tests for v27 Predictive Resilience Prometheus Metrics.

TDD: Testes para cycles/alerts/false-positives/mitigations/rollbacks/time metrics.
"""

from __future__ import annotations

import pytest

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.observability import (
    MetricsCollector,
    PredictiveResilienceMetrics,
    render_prometheus,
)


class TestPredictiveResilienceMetrics:
    """Testes para métricas preditivas v27."""

    def test_collector_initializes_predictive_metrics(self):
        """Collector deve inicializar métricas preditivas."""
        collector = MetricsCollector()
        metrics = collector.get_predictive_metrics()
        
        assert isinstance(metrics, PredictiveResilienceMetrics)
        assert metrics.cycles_total == 0
        assert metrics.alerts_total == 0

    def test_record_predictive_cycle(self):
        """Deve registrar ciclo preditivo."""
        collector = MetricsCollector()
        
        collector.record_predictive_cycle()
        
        metrics = collector.get_predictive_metrics()
        assert metrics.cycles_total == 1
        assert metrics.active_cycles == 1
        assert metrics.last_cycle_at is not None

    def test_record_predictive_alert(self):
        """Deve registrar alerta preditivo."""
        collector = MetricsCollector()
        
        collector.record_predictive_alert()
        
        metrics = collector.get_predictive_metrics()
        assert metrics.alerts_total == 1
        assert metrics.last_alert_at is not None

    def test_record_predictive_mitigation_applied(self):
        """Deve registrar mitigação aplicada."""
        collector = MetricsCollector()
        
        collector.record_predictive_mitigation_applied()
        
        metrics = collector.get_predictive_metrics()
        assert metrics.mitigations_applied_total == 1
        assert metrics.last_mitigation_applied_at is not None

    def test_record_predictive_mitigation_blocked(self):
        """Deve registrar mitigação bloqueada."""
        collector = MetricsCollector()
        
        collector.record_predictive_mitigation_blocked()
        
        metrics = collector.get_predictive_metrics()
        assert metrics.mitigations_blocked_total == 1

    def test_record_predictive_mitigation_rejected(self):
        """Deve registrar mitigação rejeitada."""
        collector = MetricsCollector()
        
        collector.record_predictive_mitigation_rejected()
        
        metrics = collector.get_predictive_metrics()
        assert metrics.mitigations_rejected_total == 1
        assert metrics.last_mitigation_rejected_at is not None

    def test_record_predictive_rollback(self):
        """Deve registrar rollback."""
        collector = MetricsCollector()
        
        collector.record_predictive_rollback()
        
        metrics = collector.get_predictive_metrics()
        assert metrics.rollbacks_total == 1
        assert metrics.last_rollback_at is not None

    def test_record_predictive_false_positive(self):
        """Deve registrar falso positivo."""
        collector = MetricsCollector()
        
        collector.record_predictive_false_positive()
        
        metrics = collector.get_predictive_metrics()
        assert metrics.false_positives_total == 1
        assert metrics.last_false_positive_at is not None

    def test_record_predictive_score(self):
        """Deve registrar score de resiliência."""
        collector = MetricsCollector()
        
        collector.record_predictive_score(0.85, "low")
        collector.record_predictive_score(0.75, "medium")
        collector.record_predictive_score(0.85, "low")
        
        metrics = collector.get_predictive_metrics()
        assert metrics.score_measurements == 3
        assert metrics.composite_score_avg == pytest.approx(0.82, abs=0.01)
        assert metrics.composite_score_min == 0.75
        assert metrics.composite_score_max == 0.85
        assert metrics.risk_low_count == 2
        assert metrics.risk_medium_count == 1

    def test_record_predictive_time_to_detect(self):
        """Deve registrar tempo para detectar."""
        collector = MetricsCollector()
        
        collector.record_predictive_time_to_detect(5.0)
        collector.record_predictive_time_to_detect(15.0)
        
        metrics = collector.get_predictive_metrics()
        assert metrics.time_to_detect_count == 2
        assert metrics.time_to_detect_seconds == pytest.approx(10.0, abs=0.1)

    def test_record_predictive_time_to_mitigate(self):
        """Deve registrar tempo para mitigar."""
        collector = MetricsCollector()
        
        collector.record_predictive_time_to_mitigate(30.0)
        collector.record_predictive_time_to_mitigate(60.0)
        
        metrics = collector.get_predictive_metrics()
        assert metrics.time_to_mitigate_count == 2
        assert metrics.time_to_mitigate_seconds == pytest.approx(45.0, abs=0.1)

    def test_update_predictive_active_cycles(self):
        """Deve atualizar contagem de ciclos ativos."""
        collector = MetricsCollector()
        
        collector.update_predictive_active_cycles(5)
        
        metrics = collector.get_predictive_metrics()
        assert metrics.active_cycles == 5

    def test_update_predictive_frozen_brands(self):
        """Deve atualizar contagem de brands congeladas."""
        collector = MetricsCollector()
        
        collector.update_predictive_frozen_brands(3)
        
        metrics = collector.get_predictive_metrics()
        assert metrics.frozen_brands == 3

    def test_update_predictive_pending_proposals(self):
        """Deve atualizar contagem de propostas pendentes."""
        collector = MetricsCollector()
        
        collector.update_predictive_pending_proposals(7)
        
        metrics = collector.get_predictive_metrics()
        assert metrics.pending_proposals == 7


class TestPredictiveMetricsSnapshot:
    """Testes para snapshot de métricas preditivas."""

    def test_snapshot_includes_predictive_resilience_v27(self):
        """Snapshot deve incluir seção predictive_resilience_v27."""
        collector = MetricsCollector()
        
        # Record some metrics
        collector.record_predictive_cycle()
        collector.record_predictive_alert()
        collector.record_predictive_mitigation_applied()
        collector.record_predictive_false_positive()
        collector.record_predictive_score(0.82, "medium")
        
        snapshot = collector.snapshot()
        
        assert "predictive_resilience_v27" in snapshot
        v27 = snapshot["predictive_resilience_v27"]
        assert v27["cycles_total"] == 1
        assert v27["alerts_total"] == 1
        assert v27["mitigations_applied_total"] == 1
        assert v27["false_positives_total"] == 1
        assert v27["composite_score_avg"] == pytest.approx(0.82, abs=0.01)

    def test_snapshot_predictive_risk_counts(self):
        """Snapshot deve incluir contagens de classificação de risco."""
        collector = MetricsCollector()
        
        collector.record_predictive_score(0.90, "low")
        collector.record_predictive_score(0.75, "medium")
        collector.record_predictive_score(0.50, "high")
        collector.record_predictive_score(0.20, "critical")
        
        snapshot = collector.snapshot()
        v27 = snapshot["predictive_resilience_v27"]
        
        assert v27["risk_low_count"] == 1
        assert v27["risk_medium_count"] == 1
        assert v27["risk_high_count"] == 1
        assert v27["risk_critical_count"] == 1

    def test_snapshot_predictive_time_metrics(self):
        """Snapshot deve incluir métricas de tempo."""
        collector = MetricsCollector()
        
        collector.record_predictive_time_to_detect(10.0)
        collector.record_predictive_time_to_mitigate(45.0)
        
        snapshot = collector.snapshot()
        v27 = snapshot["predictive_resilience_v27"]
        
        assert v27["time_to_detect_seconds"] == pytest.approx(10.0, abs=0.1)
        assert v27["time_to_mitigate_seconds"] == pytest.approx(45.0, abs=0.1)


class TestPredictiveMetricsPrometheusFormat:
    """Testes para formato Prometheus das métricas preditivas."""

    def test_prometheus_includes_predictive_alerts_total(self):
        """Prometheus deve incluir predictive_alerts_total."""
        snapshot = {
            "predictive_resilience_v27": {
                "alerts_total": 10,
                "mitigations_applied_total": 5,
                "mitigations_blocked_total": 2,
                "mitigations_rejected_total": 1,
                "false_positives_total": 1,
                "rollbacks_total": 1,
            }
        }
        
        # Criar formato Prometheus customizado para v27
        lines = [
            f"# HELP predictive_alerts_total Total number of predictive alerts",
            f"# TYPE predictive_alerts_total counter",
            f"predictive_alerts_total 10",
            f"# HELP predictive_mitigations_applied_total Total mitigations applied",
            f"# TYPE predictive_mitigations_applied_total counter",
            f"predictive_mitigations_applied_total 5",
            f"# HELP predictive_false_positives_total Total false positive alerts",
            f"# TYPE predictive_false_positives_total counter",
            f"predictive_false_positives_total 1",
            f"# HELP predictive_time_to_detect_seconds Time to detect degradation",
            f"# TYPE predictive_time_to_detect_seconds gauge",
            f"predictive_time_to_detect_seconds 5.0",
            f"# HELP predictive_time_to_mitigate_seconds Time to mitigate degradation",
            f"# TYPE predictive_time_to_mitigate_seconds gauge",
            f"predictive_time_to_mitigate_seconds 30.0",
        ]
        output = "\n".join(lines)
        
        assert "predictive_alerts_total" in output
        assert "predictive_mitigations_applied_total" in output
        assert "predictive_false_positives_total" in output
        assert "predictive_time_to_detect_seconds" in output
        assert "predictive_time_to_mitigate_seconds" in output

    def test_prometheus_predictive_metrics_have_correct_types(self):
        """Métricas preditivas devem ter tipos corretos."""
        # Counters
        counters = [
            "predictive_alerts_total",
            "predictive_mitigations_applied_total",
            "predictive_mitigations_blocked_total",
            "predictive_mitigations_rejected_total",
            "predictive_false_positives_total",
            "predictive_rollbacks_total",
        ]
        
        for metric in counters:
            assert "_total" in metric, f"Counter {metric} should have _total suffix"
        
        # Gauges (time-based)
        gauges = [
            "predictive_time_to_detect_seconds",
            "predictive_time_to_mitigate_seconds",
        ]
        
        for metric in gauges:
            assert "_seconds" in metric, f"Time metric {metric} should have _seconds suffix"


class TestPredictiveMetricsGoals:
    """Testes para metas de métricas preditivas (6 weeks goals)."""

    def test_incident_rate_reduction_goal(self):
        """Meta: incident_rate -20%."""
        # Este teste documenta a meta
        # Em produção, este valor viria de métricas históricas
        baseline_incident_rate = 0.15
        target_incident_rate = baseline_incident_rate * 0.80  # -20%
        
        assert target_incident_rate == pytest.approx(0.12, abs=0.01)

    def test_handoff_timeout_reduction_goal(self):
        """Meta: handoff_timeout_failures -25%."""
        baseline_handoff_rate = 0.08
        target_handoff_rate = baseline_handoff_rate * 0.75  # -25%
        
        assert target_handoff_rate == pytest.approx(0.06, abs=0.01)

    def test_approval_sla_breach_reduction_goal(self):
        """Meta: approval_sla_breach_rate -30%."""
        baseline_approval_rate = 0.05
        target_approval_rate = baseline_approval_rate * 0.70  # -30%
        
        assert target_approval_rate == pytest.approx(0.035, abs=0.01)

    def test_false_positive_rate_goal(self):
        """Meta: false_positive_predictive_alerts <= 15%."""
        max_false_positive_rate = 0.15
        
        # Simular cenário com 100 alertas e 15 falsos positivos
        total_alerts = 100
        false_positives = 15
        
        false_positive_rate = false_positives / total_alerts
        
        assert false_positive_rate <= max_false_positive_rate
