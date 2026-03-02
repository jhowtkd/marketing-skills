"""Tests for v35 Onboarding Continuity Metrics.

TDD: Testes para métricas de continuidade cross-session.
"""

import pytest
from datetime import datetime, timezone

from vm_webapp.observability import MetricsCollector, OnboardingContinuityMetrics


class TestOnboardingContinuityMetrics:
    """Test v35 Onboarding Continuity metrics."""

    def test_collector_initializes_continuity_metrics(self):
        """Collector deve inicializar métricas de continuidade."""
        collector = MetricsCollector()
        metrics = collector.get_continuity_metrics()
        
        assert metrics is not None
        assert isinstance(metrics, OnboardingContinuityMetrics)
        assert metrics.checkpoints_created == 0
        assert metrics.bundles_created == 0

    def test_record_checkpoint_created(self):
        """Deve registrar checkpoint criado."""
        collector = MetricsCollector()
        
        collector.record_continuity_checkpoint_created("user-123", "step_3")
        
        metrics = collector.get_continuity_metrics()
        assert metrics.checkpoints_created == 1

    def test_record_bundle_created(self):
        """Deve registrar bundle criado."""
        collector = MetricsCollector()
        
        collector.record_continuity_bundle_created("session", "pending")
        
        metrics = collector.get_continuity_metrics()
        assert metrics.bundles_created == 1
        assert metrics.bundles_pending == 1

    def test_record_bundle_completed(self):
        """Deve registrar bundle completado."""
        collector = MetricsCollector()
        
        collector.record_continuity_bundle_created("session", "pending")
        collector.record_continuity_bundle_completed(True)  # Auto-applied
        
        metrics = collector.get_continuity_metrics()
        assert metrics.bundles_completed == 1
        assert metrics.bundles_pending == 0
        assert metrics.resumes_auto_applied == 1

    def test_record_bundle_failed(self):
        """Deve registrar bundle falho."""
        collector = MetricsCollector()
        
        collector.record_continuity_bundle_created("recovery", "pending")
        collector.record_continuity_bundle_failed("version_gap")
        
        metrics = collector.get_continuity_metrics()
        assert metrics.bundles_failed == 1
        assert metrics.bundles_pending == 0

    def test_record_context_loss(self):
        """Deve registrar evento de perda de contexto."""
        collector = MetricsCollector()
        
        collector.record_continuity_context_loss("step_regression", 3)
        
        metrics = collector.get_continuity_metrics()
        assert metrics.context_loss_events == 1
        assert metrics.context_loss_step_regression == 1

    def test_record_conflict_detected(self):
        """Deve registrar conflito detectado."""
        collector = MetricsCollector()
        
        collector.record_continuity_conflict_detected("data_mismatch")
        collector.record_continuity_conflict_detected("version_gap")
        
        metrics = collector.get_continuity_metrics()
        assert metrics.conflicts_detected == 2
        assert metrics.conflict_data_mismatch == 1
        assert metrics.conflict_version_gap == 1

    def test_record_resume_rolled_back(self):
        """Deve registrar rollback de resume."""
        collector = MetricsCollector()
        
        collector.record_continuity_resume_rolled_back()
        
        metrics = collector.get_continuity_metrics()
        assert metrics.resumes_rolled_back == 1

    def test_record_needs_approval(self):
        """Deve registrar necessidade de aprovação."""
        collector = MetricsCollector()
        
        collector.record_continuity_needs_approval("high", "version_gap_exceeded")
        
        metrics = collector.get_continuity_metrics()
        assert metrics.resumes_needing_approval == 1
        assert metrics.approvals_pending == 1

    def test_source_priority_tracking(self):
        """Deve rastrear prioridade de fonte."""
        collector = MetricsCollector()
        
        collector.record_continuity_bundle_created("session", "completed")
        collector.record_continuity_bundle_created("recovery", "completed")
        collector.record_continuity_bundle_created("default", "completed")
        
        metrics = collector.get_continuity_metrics()
        assert metrics.source_session_count == 1
        assert metrics.source_recovery_count == 1
        assert metrics.source_default_count == 1

    def test_get_continuity_metrics_full(self):
        """Deve retornar todas as métricas de continuidade."""
        collector = MetricsCollector()
        
        # Generate various metrics
        collector.record_continuity_checkpoint_created("user-1", "step_2")
        collector.record_continuity_checkpoint_created("user-2", "step_4")
        collector.record_continuity_bundle_created("session", "completed")
        collector.record_continuity_bundle_completed(True)
        collector.record_continuity_context_loss("form_inconsistency", 2)
        collector.record_continuity_conflict_detected("data_mismatch")
        collector.record_continuity_resume_rolled_back()
        
        metrics = collector.get_continuity_metrics()
        
        assert metrics.checkpoints_created == 2
        assert metrics.bundles_created == 1
        assert metrics.bundles_completed == 1
        assert metrics.resumes_auto_applied == 1
        assert metrics.context_loss_events == 1
        assert metrics.conflicts_detected == 1
        assert metrics.resumes_rolled_back == 1

    def test_continuity_metrics_in_snapshot(self):
        """Métricas de continuidade devem aparecer no snapshot."""
        collector = MetricsCollector()
        
        collector.record_continuity_checkpoint_created("user-1", "step_3")
        collector.record_continuity_bundle_created("session", "pending")
        
        snapshot = collector.snapshot()
        
        assert "onboarding_continuity_v35" in snapshot
        assert snapshot["onboarding_continuity_v35"]["checkpoints"]["created"] == 1
        assert snapshot["onboarding_continuity_v35"]["bundles"]["created"] == 1

    def test_context_loss_reason_tracking(self):
        """Deve rastrear razões de perda de contexto."""
        collector = MetricsCollector()
        
        collector.record_continuity_context_loss("step_regression", 2)
        collector.record_continuity_context_loss("form_inconsistency", 1)
        collector.record_continuity_context_loss("version_gap", 5)
        
        metrics = collector.get_continuity_metrics()
        assert metrics.context_loss_step_regression == 1
        assert metrics.context_loss_form_inconsistency == 1
        assert metrics.context_loss_version_gap == 1

    def test_step_distribution_tracking(self):
        """Deve rastrear distribuição de steps nos checkpoints."""
        collector = MetricsCollector()
        
        collector.record_continuity_checkpoint_created("user-1", "step_1")
        collector.record_continuity_checkpoint_created("user-2", "step_2")
        collector.record_continuity_checkpoint_created("user-3", "step_2")
        
        metrics = collector.get_continuity_metrics()
        assert metrics.checkpoints_created == 3
