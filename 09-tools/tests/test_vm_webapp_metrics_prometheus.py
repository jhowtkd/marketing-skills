"""Tests for v28 Recovery Orchestration and v32 Onboarding Experimentation Prometheus Metrics.

TDD: Testes para runs/steps/failed/auto/manual/mttr metrics e experimentation metrics.
"""

from __future__ import annotations

import pytest

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.observability import (
    MetricsCollector,
    RecoveryOrchestrationMetrics,
    OnboardingRecoveryMetrics,
    OnboardingExperimentationMetrics,
    OnboardingPersonalizationMetrics,
    render_prometheus,
)


class TestRecoveryOrchestrationMetrics:
    """Testes para métricas de recovery v28 (orchestration domain)."""

    def test_collector_initializes_recovery_metrics(self):
        """Collector deve inicializar métricas de recovery orchestration."""
        collector = MetricsCollector()
        metrics = collector.get_orchestration_recovery_metrics()
        
        assert isinstance(metrics, RecoveryOrchestrationMetrics)
        assert metrics.runs_total == 0
        assert metrics.steps_total == 0

    def test_backward_compatible_alias(self):
        """get_recovery_metrics deve retornar orchestration metrics (backward compatibility)."""
        collector = MetricsCollector()
        metrics = collector.get_recovery_metrics()
        
        assert isinstance(metrics, RecoveryOrchestrationMetrics)

    def test_domains_dont_collide(self):
        """Métricas de orchestration e onboarding devem ser independentes."""
        collector = MetricsCollector()
        
        # Record v28 orchestration metrics
        collector.record_recovery_run(auto=True)
        collector.record_recovery_step("success")
        
        # Record v34 onboarding metrics
        collector.record_recovery_case_detected("abandoned_step", "high")
        collector.record_recovery_case_recovered()
        
        # Get both metric types
        orch_metrics = collector.get_orchestration_recovery_metrics()
        onboarding_metrics = collector.get_onboarding_recovery_metrics()
        
        # Verify they are different types
        assert isinstance(orch_metrics, RecoveryOrchestrationMetrics)
        assert isinstance(onboarding_metrics, OnboardingRecoveryMetrics)
        
        # Verify v28 data is in orchestration
        assert orch_metrics.runs_total == 1
        assert orch_metrics.steps_total == 1
        
        # Verify v34 data is in onboarding
        assert onboarding_metrics.cases_detected == 1
        assert onboarding_metrics.cases_recovered == 1

    def test_record_recovery_run(self):
        """Deve registrar recovery run."""
        collector = MetricsCollector()
        
        collector.record_recovery_run(auto=False)
        
        metrics = collector.get_orchestration_recovery_metrics()
        assert metrics.runs_total == 1
        assert metrics.runs_manual == 1
        assert metrics.runs_auto == 0
        assert metrics.active_runs == 1
        assert metrics.last_run_at is not None

    def test_record_recovery_run_auto(self):
        """Deve registrar recovery run auto."""
        collector = MetricsCollector()
        
        collector.record_recovery_run(auto=True)
        
        metrics = collector.get_orchestration_recovery_metrics()
        assert metrics.runs_total == 1
        assert metrics.runs_auto == 1
        assert metrics.runs_manual == 0

    def test_record_recovery_run_success(self):
        """Deve registrar sucesso de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_run()
        collector.record_recovery_run_success(duration_seconds=45.5)
        
        metrics = collector.get_orchestration_recovery_metrics()
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
        
        metrics = collector.get_orchestration_recovery_metrics()
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
        
        metrics = collector.get_orchestration_recovery_metrics()
        assert metrics.steps_total == 4
        assert metrics.steps_successful == 2
        assert metrics.steps_failed == 1
        assert metrics.steps_skipped == 1

    def test_record_approval_requested(self):
        """Deve registrar requisição de aprovação."""
        collector = MetricsCollector()
        
        collector.record_approval_requested()
        
        metrics = collector.get_orchestration_recovery_metrics()
        assert metrics.approval_requests_total == 1
        assert metrics.pending_approvals == 1

    def test_record_approval_granted(self):
        """Deve registrar aprovação concedida."""
        collector = MetricsCollector()
        
        collector.record_approval_requested()
        collector.record_approval_granted()
        
        metrics = collector.get_orchestration_recovery_metrics()
        assert metrics.approvals_granted == 1
        assert metrics.pending_approvals == 0
        assert metrics.last_approval_at is not None

    def test_record_approval_rejected(self):
        """Deve registrar aprovação rejeitada."""
        collector = MetricsCollector()
        
        collector.record_approval_requested()
        collector.record_approval_rejected()
        
        metrics = collector.get_orchestration_recovery_metrics()
        assert metrics.approvals_rejected == 1
        assert metrics.pending_approvals == 0
        assert metrics.last_rejection_at is not None

    def test_record_recovery_frozen(self):
        """Deve registrar freeze de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_frozen()
        
        metrics = collector.get_orchestration_recovery_metrics()
        assert metrics.frozen_incidents == 1
        assert metrics.last_freeze_at is not None

    def test_record_recovery_rollback(self):
        """Deve registrar rollback de recovery."""
        collector = MetricsCollector()
        
        collector.record_recovery_rollback()
        
        metrics = collector.get_orchestration_recovery_metrics()
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
        
        metrics = collector.get_orchestration_recovery_metrics()
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
        
        metrics = collector.get_orchestration_recovery_metrics()
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


class TestOnboardingExperimentationMetrics:
    """Testes para métricas de onboarding experimentation v32."""

    def test_collector_initializes_experimentation_metrics(self):
        """Collector deve inicializar métricas de experimentation."""
        collector = MetricsCollector()
        metrics = collector.get_experimentation_metrics()
        
        assert isinstance(metrics, OnboardingExperimentationMetrics)
        assert metrics.experiments_total == 0
        assert metrics.assignments_total == 0

    def test_record_experiment_created(self):
        """Deve registrar criação de experimento."""
        collector = MetricsCollector()
        
        collector.record_experiment_created()
        collector.record_experiment_created()
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.experiments_total == 2

    def test_record_experiment_started(self):
        """Deve registrar início de experimento."""
        collector = MetricsCollector()
        
        collector.record_experiment_started()
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.experiments_running == 1

    def test_record_experiment_paused(self):
        """Deve registrar pausa de experimento."""
        collector = MetricsCollector()
        
        collector.record_experiment_started()
        collector.record_experiment_paused()
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.experiments_paused == 1
        assert metrics.experiments_running == 0

    def test_record_experiment_completed(self):
        """Deve registrar conclusão de experimento."""
        collector = MetricsCollector()
        
        collector.record_experiment_started()
        collector.record_experiment_completed()
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.experiments_completed == 1
        assert metrics.experiments_running == 0
        assert metrics.last_promotion_at is not None

    def test_record_experiment_rolled_back(self):
        """Deve registrar rollback de experimento."""
        collector = MetricsCollector()
        
        collector.record_experiment_started()
        collector.record_experiment_rolled_back()
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.experiments_rolled_back == 1
        assert metrics.rollbacks_triggered == 1
        assert metrics.experiments_running == 0
        assert metrics.last_rollback_at is not None

    def test_record_assignment(self):
        """Deve registrar assignment."""
        collector = MetricsCollector()
        
        collector.record_assignment()
        collector.record_assignment()
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.assignments_total == 2
        assert metrics.assignments_today == 2
        assert metrics.last_assignment_at is not None

    def test_record_promotion_decision(self):
        """Deve registrar decisão de promoção."""
        collector = MetricsCollector()
        
        collector.record_promotion_decision("auto_apply")
        collector.record_promotion_decision("approved")
        collector.record_promotion_decision("blocked")
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.promotions_auto_applied == 1
        assert metrics.promotions_approved == 1
        assert metrics.promotions_blocked == 1
        assert metrics.guardrail_blocks_total == 1

    def test_record_evaluation_run(self):
        """Deve registrar execução de avaliação."""
        collector = MetricsCollector()
        
        collector.record_evaluation_run(significant_results=3, insignificant_results=2)
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.evaluations_run_total == 1
        assert metrics.significant_results == 3
        assert metrics.insignificant_results == 2
        assert metrics.last_evaluation_at is not None

    def test_record_guardrail_block(self):
        """Deve registrar bloqueio de guardrail."""
        collector = MetricsCollector()
        
        collector.record_guardrail_block("sample_size")
        collector.record_guardrail_block("lift_threshold")
        
        metrics = collector.get_experimentation_metrics()
        assert metrics.sample_size_violations == 1
        assert metrics.lift_threshold_violations == 1

    def test_experimentation_metrics_in_snapshot(self):
        """Métricas de experimentation devem estar no snapshot."""
        collector = MetricsCollector()
        
        collector.record_experiment_created()
        collector.record_experiment_started()
        collector.record_assignment()
        collector.record_promotion_decision("auto_apply")
        
        snapshot = collector.snapshot()
        
        assert "onboarding_experimentation_v32" in snapshot
        exp = snapshot["onboarding_experimentation_v32"]
        assert exp["experiments"]["total"] == 1
        assert exp["experiments"]["running"] == 1
        assert exp["assignments"]["total"] == 1
        assert exp["promotions"]["auto_applied"] == 1


class TestOnboardingPersonalizationMetrics:
    """Testes para métricas de onboarding personalization v33."""

    def test_collector_initializes_personalization_metrics(self):
        """Collector deve inicializar métricas de personalization."""
        collector = MetricsCollector()
        metrics = collector.get_personalization_metrics()
        
        assert isinstance(metrics, OnboardingPersonalizationMetrics)
        assert metrics.serves_total == 0
        assert metrics.policies_total == 0

    def test_record_policy_serve(self):
        """Deve registrar serve de política."""
        collector = MetricsCollector()
        
        collector.record_policy_serve("segment", 45.5)
        collector.record_policy_serve("brand", 52.3)
        
        metrics = collector.get_personalization_metrics()
        assert metrics.serves_total == 2
        assert metrics.serves_segment_hit == 1
        assert metrics.serves_brand_fallback == 1
        assert metrics.segment_served_count == 1
        assert metrics.brand_fallback_count == 1

    def test_record_policy_registered(self):
        """Deve registrar registro de política."""
        collector = MetricsCollector()
        
        collector.record_policy_registered()
        collector.record_policy_registered()
        
        metrics = collector.get_personalization_metrics()
        assert metrics.policies_total == 2

    def test_record_policy_activated(self):
        """Deve registrar ativação de política."""
        collector = MetricsCollector()
        
        collector.record_policy_activated()
        
        metrics = collector.get_personalization_metrics()
        assert metrics.policies_active == 1

    def test_record_policy_rolled_back(self):
        """Deve registrar rollback de política."""
        collector = MetricsCollector()
        
        collector.record_policy_activated()
        collector.record_policy_rolled_back()
        
        metrics = collector.get_personalization_metrics()
        assert metrics.policies_rolled_back == 1
        assert metrics.policies_active == 0

    def test_record_rollout_decision(self):
        """Deve registrar decisão de rollout."""
        collector = MetricsCollector()
        
        collector.record_rollout_decision("auto_apply")
        collector.record_rollout_decision("approved")
        collector.record_rollout_decision("block")
        
        metrics = collector.get_personalization_metrics()
        assert metrics.rollouts_total == 3
        assert metrics.rollouts_auto_applied == 1
        assert metrics.rollouts_approved == 1
        assert metrics.rollouts_blocked == 1

    def test_record_validation_failure(self):
        """Deve registrar falha de validação."""
        collector = MetricsCollector()
        
        collector.record_validation_failure()
        
        metrics = collector.get_personalization_metrics()
        assert metrics.validation_failures == 1

    def test_record_personalization_guardrail_block(self):
        """Deve registrar bloqueio de guardrail v33."""
        collector = MetricsCollector()
        
        collector.record_personalization_guardrail_block("latency")
        collector.record_personalization_guardrail_block("complexity")
        
        metrics = collector.get_personalization_metrics()
        assert metrics.guardrail_blocks == 2
        assert metrics.latency_violations == 1
        assert metrics.complexity_violations == 1

    def test_personalization_metrics_in_snapshot(self):
        """Métricas de personalization devem estar no snapshot."""
        collector = MetricsCollector()
        
        collector.record_policy_registered()
        collector.record_policy_activated()
        collector.record_policy_serve("segment", 45.5)
        collector.record_rollout_decision("auto_apply")
        
        snapshot = collector.snapshot()
        
        assert "onboarding_personalization_v33" in snapshot
        pers = snapshot["onboarding_personalization_v33"]
        assert pers["policies"]["total"] == 1
        assert pers["policies"]["active"] == 1
        assert pers["serves"]["total"] == 1
        assert pers["serves"]["segment_hit"] == 1
        assert pers["rollouts"]["auto_applied"] == 1


class TestOutcomeAttributionROIMetrics:
    """Testes para métricas v36 Outcome Attribution e Hybrid ROI."""

    def test_collector_initializes_outcome_roi_metrics(self):
        """Collector deve inicializar métricas v36."""
        collector = MetricsCollector()
        metrics = collector.get_outcome_roi_metrics()
        
        assert "outcomes_attributed" in metrics
        assert "proposals_generated" in metrics
        assert "hybrid_roi_index_avg" in metrics

    def test_record_outcome_attributed(self):
        """Deve registrar outcome atribuído."""
        collector = MetricsCollector()
        
        collector.record_outcome_attributed("activation", "linear")
        collector.record_outcome_attributed("recovery", "first_touch")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["outcomes_attributed"] == 2
        assert metrics["attribution_methods"]["linear"] == 1
        assert metrics["attribution_methods"]["first_touch"] == 1

    def test_record_proposal_generated(self):
        """Deve registrar proposal gerada."""
        collector = MetricsCollector()
        
        collector.record_proposal_generated("low", 0.25)
        collector.record_proposal_generated("medium", 0.12)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["proposals_generated"] == 2
        assert metrics["by_risk_level"]["low"] == 1

    def test_record_hybrid_roi_index(self):
        """Deve registrar hybrid ROI index."""
        collector = MetricsCollector()
        
        collector.record_hybrid_roi_index(0.25)
        collector.record_hybrid_roi_index(0.30)
        collector.record_hybrid_roi_index(0.20)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["hybrid_roi_index_avg"] == pytest.approx(0.25, rel=0.01)
        assert metrics["hybrid_roi_index_min"] == pytest.approx(0.20, rel=0.01)
        assert metrics["hybrid_roi_index_max"] == pytest.approx(0.30, rel=0.01)

    def test_record_payback_time(self):
        """Deve registrar payback time."""
        collector = MetricsCollector()
        
        collector.record_payback_time(5.0)
        collector.record_payback_time(7.0)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["payback_time_avg_days"] == pytest.approx(6.0, rel=0.01)

    def test_record_guardrail_violation(self):
        """Deve registrar violação de guardrail."""
        collector = MetricsCollector()
        
        collector.record_guardrail_violation("min_success_rate")
        collector.record_guardrail_violation("max_incident_rate")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["guardrail_violations"] == 2

    def test_record_quality_penalty(self):
        """Deve registrar penalidade de qualidade."""
        collector = MetricsCollector()
        
        collector.record_quality_penalty("incident", 0.25)
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["quality_penalties_applied"] == 1

    def test_record_roi_rollback(self):
        """Deve registrar rollback de ROI."""
        collector = MetricsCollector()
        
        collector.record_roi_rollback(3, "quality_degradation")
        
        metrics = collector.get_outcome_roi_metrics()
        assert metrics["rollbacks_executed"] == 1
        assert metrics["rolled_back_proposals"] == 3

    def test_outcome_roi_metrics_in_snapshot(self):
        """Métricas v36 devem estar no snapshot."""
        collector = MetricsCollector()
        
        collector.record_outcome_attributed("activation", "linear")
        collector.record_proposal_generated("low", 0.25)
        collector.record_hybrid_roi_index(0.25)
        
        snapshot = collector.snapshot()
        
        assert "outcome_roi_v36" in snapshot
        roi = snapshot["outcome_roi_v36"]
        assert roi["attribution"]["outcomes_attributed"] == 1
        assert roi["proposals"]["generated"] == 1
        assert roi["hybrid_roi"]["index_avg"] == pytest.approx(0.25, rel=0.01)
