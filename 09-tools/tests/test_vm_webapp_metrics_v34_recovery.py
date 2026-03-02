"""Tests for v34 Onboarding Recovery Metrics.

TDD: Testes para métricas de recovery.
"""

import pytest
from datetime import datetime, timezone

from vm_webapp.observability import MetricsCollector, OnboardingRecoveryMetrics


class TestOnboardingRecoveryMetrics:
    """Test v34 Onboarding Recovery metrics."""

    def test_collector_initializes_recovery_metrics(self):
        """Collector deve inicializar métricas de recovery."""
        collector = MetricsCollector()
        metrics = collector.get_recovery_metrics()
        
        assert metrics is not None
        assert isinstance(metrics, OnboardingRecoveryMetrics)
        assert metrics.cases_detected == 0
        assert metrics.cases_recovered == 0

    def test_record_case_detected(self):
        """Deve registrar caso detectado."""
        collector = MetricsCollector()
        
        collector.record_recovery_case_detected("abandoned_step", "high")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.cases_detected == 1
        assert metrics.cases_recoverable == 1

    def test_record_case_recovered(self):
        """Deve registrar caso recuperado."""
        collector = MetricsCollector()
        
        collector.record_recovery_case_detected("abandoned_step", "high")
        collector.record_recovery_case_recovered()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.cases_recovered == 1
        assert metrics.cases_recoverable == 0  # Decremented

    def test_record_case_expired(self):
        """Deve registrar caso expirado."""
        collector = MetricsCollector()
        
        collector.record_recovery_case_detected("timeout", "low")
        collector.record_recovery_case_expired()
        
        metrics = collector.get_recovery_metrics()
        assert metrics.cases_expired == 1

    def test_record_proposal_generated(self):
        """Deve registrar proposta gerada."""
        collector = MetricsCollector()
        
        collector.record_recovery_proposal_generated("fast_lane", "medium_touch")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.proposals_generated == 1

    def test_record_proposal_auto_applied(self):
        """Deve registrar proposta aplicada automaticamente."""
        collector = MetricsCollector()
        
        collector.record_recovery_proposal_auto_applied("reminder")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.proposals_auto_applied == 1

    def test_record_proposal_approved(self):
        """Deve registrar proposta aprovada."""
        collector = MetricsCollector()
        
        collector.record_recovery_proposal_approved("guided_resume")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.proposals_approved == 1

    def test_record_proposal_rejected(self):
        """Deve registrar proposta rejeitada."""
        collector = MetricsCollector()
        
        collector.record_recovery_proposal_rejected("template_boost")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.proposals_rejected == 1

    def test_record_strategy_distribution(self):
        """Deve registrar distribuição de estratégias."""
        collector = MetricsCollector()
        
        collector.record_recovery_proposal_generated("reminder", "low_touch")
        collector.record_recovery_proposal_generated("fast_lane", "medium_touch")
        collector.record_recovery_proposal_generated("guided_resume", "high_touch")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.strategy_reminder == 1
        assert metrics.strategy_fast_lane == 1
        assert metrics.strategy_guided_resume == 1

    def test_record_resume_path_generated(self):
        """Deve registrar path de resume gerado."""
        collector = MetricsCollector()
        
        collector.record_recovery_resume_path_generated(3, 0.4)
        
        metrics = collector.get_recovery_metrics()
        assert metrics.resume_paths_generated == 1
        assert metrics.resume_avg_friction_score > 0

    def test_get_recovery_metrics_full(self):
        """Deve retornar todas as métricas de recovery."""
        collector = MetricsCollector()
        
        # Generate various metrics
        collector.record_recovery_case_detected("abandoned_step", "high")
        collector.record_recovery_case_detected("timeout", "low")
        collector.record_recovery_case_recovered()
        collector.record_recovery_case_expired()
        collector.record_recovery_proposal_generated("fast_lane", "medium_touch")
        collector.record_recovery_proposal_auto_applied("reminder")
        collector.record_recovery_proposal_approved("guided_resume")
        collector.record_recovery_proposal_rejected("template_boost")
        collector.record_recovery_resume_path_generated(3, 0.5)
        
        metrics = collector.get_recovery_metrics()
        
        assert metrics.cases_detected == 2
        assert metrics.cases_recovered == 1
        assert metrics.cases_expired == 1
        assert metrics.proposals_generated == 1
        assert metrics.proposals_auto_applied == 1
        assert metrics.proposals_approved == 1
        assert metrics.proposals_rejected == 1

    def test_recovery_metrics_in_snapshot(self):
        """Métricas de recovery devem aparecer no snapshot."""
        collector = MetricsCollector()
        
        collector.record_recovery_case_detected("abandoned_step", "high")
        collector.record_recovery_proposal_generated("fast_lane", "medium_touch")
        
        snapshot = collector.snapshot()
        
        assert "onboarding_recovery_v34" in snapshot
        assert snapshot["onboarding_recovery_v34"]["cases"]["detected"] == 1
        assert snapshot["onboarding_recovery_v34"]["proposals"]["generated"] == 1

    def test_priority_distribution_tracking(self):
        """Deve rastrear distribuição por prioridade."""
        collector = MetricsCollector()
        
        collector.record_recovery_case_detected("abandoned_step", "high")
        collector.record_recovery_case_detected("timeout", "medium")
        collector.record_recovery_case_detected("error", "high")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.priority_high == 2
        assert metrics.priority_medium == 1
        assert metrics.priority_low == 0

    def test_dropoff_reason_tracking(self):
        """Deve rastrear razões de dropoff."""
        collector = MetricsCollector()
        
        collector.record_recovery_case_detected("abandoned_step", "high")
        collector.record_recovery_case_detected("timeout", "low")
        collector.record_recovery_case_detected("error", "high")
        collector.record_recovery_case_detected("external_interruption", "medium")
        
        metrics = collector.get_recovery_metrics()
        assert metrics.dropoff_abandoned == 1
        assert metrics.dropoff_timeout == 1
        assert metrics.dropoff_error == 1
        assert metrics.dropoff_external == 1
