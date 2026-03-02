"""Tests for v28 Recovery Orchestration and v32 Onboarding Experimentation API Endpoints.

TDD: Testes para run/status/events/approve/reject/freeze/rollback e onboarding experiments.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.api_recovery import router as recovery_router
from fastapi import FastAPI


# Create test app
app = FastAPI()
app.include_router(recovery_router)
client = TestClient(app)


def _reset_state():
    """Reset global state between tests."""
    from vm_webapp.api_recovery import (
        _recovery_runs,
        _recovery_events,
        _approval_requests,
        _frozen_incidents,
        _recovery_metrics,
    )
    _recovery_runs.clear()
    _recovery_events.clear()
    _approval_requests.clear()
    _frozen_incidents.clear()
    _recovery_metrics["total_runs"] = 0
    _recovery_metrics["successful_runs"] = 0
    _recovery_metrics["failed_runs"] = 0


class TestRecoveryStatusEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/recovery/status."""

    def test_status_returns_basic_info(self):
        """Status deve retornar informações básicas."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "state" in data
        assert "version" in data
        assert data["version"] == "v28"

    def test_status_includes_recovery_metrics(self):
        """Status deve incluir métricas de recovery."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "total_runs" in data["metrics"]
        assert "successful_runs" in data["metrics"]
        assert "failed_runs" in data["metrics"]

    def test_status_includes_active_incidents(self):
        """Status deve incluir incidentes ativos."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_incidents" in data
        assert isinstance(data["active_incidents"], list)

    def test_status_includes_pending_approvals(self):
        """Status deve incluir aprovações pendentes."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "pending_approvals" in data
        assert isinstance(data["pending_approvals"], list)


class TestRecoveryRunEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/run."""

    def test_run_starts_new_recovery(self):
        """Run deve iniciar novo recovery."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["brand_id"] == "brand-001"
        assert "plan" in data
        assert data["status"] in ["started", "pending_approval"]

    def test_run_low_severity_auto_executes(self):
        """Run com severidade LOW deve auto-executar."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["auto_executed"] is True

    def test_run_high_severity_requires_approval(self):
        """Run com severidade HIGH deve requerer aprovação."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_approval"
        assert data["requires_approval"] is True
        assert "approval_request_id" in data


class TestRecoveryEventsEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para GET /api/v2/brands/{brand_id}/recovery/events."""

    def test_events_returns_list(self):
        """Events deve retornar lista de eventos."""
        response = client.get("/api/v2/brands/brand-001/recovery/events")
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)
        assert "total" in data

    def test_events_supports_pagination(self):
        """Events deve suportar paginação."""
        response = client.get("/api/v2/brands/brand-001/recovery/events?limit=10&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0


class TestRecoveryApproveEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/approve/{request_id}."""

    def test_approve_starts_recovery(self):
        """Approve deve iniciar recovery pendente."""
        # First create a pending recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        run_data = run_response.json()
        approval_request_id = run_data["approval_request_id"]
        
        # Now approve it
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/approve/{approval_request_id}",
            json={"approved_by": "user-001", "reason": "Approved for execution"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["approval_request_id"] == approval_request_id
        assert data["status"] == "approved"
        assert data["recovery_status"] == "started"

    def test_approve_nonexistent_returns_404(self):
        """Approve de request inexistente deve retornar 404."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/approve/nonexistent",
            json={"approved_by": "user-001"}
        )
        
        assert response.status_code == 404


class TestRecoveryRejectEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/reject/{request_id}."""

    def test_reject_cancels_recovery(self):
        """Reject deve cancelar recovery pendente."""
        # First create a pending recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        run_data = run_response.json()
        approval_request_id = run_data["approval_request_id"]
        
        # Now reject it
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/reject/{approval_request_id}",
            json={"rejected_by": "user-001", "reason": "Risk too high"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["approval_request_id"] == approval_request_id
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Risk too high"


class TestRecoveryFreezeEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/freeze/{incident_id}."""

    def test_freeze_stops_recovery(self):
        """Freeze deve parar recovery em execução."""
        # First start a recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        run_data = run_response.json()
        incident_id = run_data["incident_id"]
        
        # Now freeze it
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/freeze/{incident_id}",
            json={"reason": "Investigating side effects"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["incident_id"] == incident_id
        assert data["status"] == "frozen"
        assert data["frozen_at"] is not None

    def test_freeze_nonexistent_returns_404(self):
        """Freeze de incidente inexistente deve retornar 404."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/freeze/nonexistent",
            json={"reason": "Test"}
        )
        
        assert response.status_code == 404


class TestRecoveryRollbackEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/rollback/{run_id}."""

    def test_rollback_reverts_recovery(self):
        """Rollback deve reverter ações do recovery."""
        # First complete a recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        run_data = run_response.json()
        run_id = run_data["run_id"]
        
        # Now rollback
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/rollback/{run_id}",
            json={"reason": "Recovery caused issues"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["status"] == "rolled_back"
        assert "rolled_back_at" in data
        assert "affected_steps" in data

    def test_rollback_nonexistent_returns_404(self):
        """Rollback de run inexistente deve retornar 404."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/rollback/nonexistent",
            json={"reason": "Test"}
        )
        
        assert response.status_code == 404


class TestRecoveryMetrics:
    """Testes para métricas de recovery."""
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    def test_metrics_tracked_after_run(self):
        """Métricas devem ser atualizadas após run."""
        # Initial state
        status_response = client.get("/api/v2/brands/brand-001/recovery/status")
        initial_metrics = status_response.json()["metrics"]
        initial_total = initial_metrics["total_runs"]
        
        # Run recovery
        client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        
        # Check metrics updated
        status_response = client.get("/api/v2/brands/brand-001/recovery/status")
        updated_metrics = status_response.json()["metrics"]
        
        assert updated_metrics["total_runs"] == initial_total + 1


# =============================================================================
# v32 Onboarding Experimentation API Tests
# =============================================================================

from vm_webapp.api_onboarding_experiments import router as experiments_router


# Create test app for experiments
app_exp = FastAPI()
app_exp.include_router(experiments_router)
client_exp = TestClient(app_exp)


def _reset_experiment_state():
    """Reset experiment global state between tests."""
    from vm_webapp.api_onboarding_experiments import _experiment_registry, _experiment_metrics
    _experiment_registry.clear_assignments()
    for key in _experiment_metrics:
        _experiment_metrics[key] = 0


class TestOnboardingExperimentsStatusEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-experiments/status."""

    def test_status_returns_basic_info(self):
        """Status deve retornar informações básicas."""
        response = client_exp.get("/api/v2/brands/brand-001/onboarding-experiments/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "version" in data
        assert data["version"] == "v32"

    def test_status_includes_experiment_metrics(self):
        """Status deve incluir métricas de experimentação."""
        response = client_exp.get("/api/v2/brands/brand-001/onboarding-experiments/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "total_experiments" in data["metrics"]
        assert "running_experiments" in data["metrics"]
        assert "assignments_today" in data["metrics"]

    def test_status_includes_active_experiments(self):
        """Status deve incluir experimentos ativos."""
        response = client_exp.get("/api/v2/brands/brand-001/onboarding-experiments/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_experiments" in data
        assert isinstance(data["active_experiments"], list)


class TestOnboardingExperimentsRunEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-experiments/run."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_experiment_state()

    def test_run_evaluates_all_running_experiments(self):
        """Run deve avaliar todos os experimentos em execução."""
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/run",
            json={"metrics_fetcher": "default"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "evaluations" in data
        assert isinstance(data["evaluations"], list)
        assert "run_at" in data

    def test_run_returns_decisions(self):
        """Run deve retornar decisões de promoção."""
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/run",
            json={"metrics_fetcher": "default"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for evaluation in data.get("evaluations", []):
            assert "decision" in evaluation
            assert "requires_approval" in evaluation


class TestOnboardingExperimentsListEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-experiments."""

    def test_list_returns_experiments(self):
        """List deve retornar lista de experimentos."""
        response = client_exp.get("/api/v2/brands/brand-001/onboarding-experiments")
        
        assert response.status_code == 200
        data = response.json()
        assert "experiments" in data
        assert isinstance(data["experiments"], list)
        assert "total" in data

    def test_list_supports_status_filter(self):
        """List deve suportar filtro por status."""
        response = client_exp.get("/api/v2/brands/brand-001/onboarding-experiments?status=running")
        
        assert response.status_code == 200
        data = response.json()
        for exp in data.get("experiments", []):
            assert exp["status"] == "running"


class TestOnboardingExperimentStartEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-experiments/{id}/start."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_experiment_state()

    def test_start_experiment(self):
        """Start deve iniciar um experimento em draft."""
        # Primeiro criar um experimento
        from vm_webapp.api_onboarding_experiments import _experiment_registry
        from vm_webapp.onboarding_experiments import Experiment, ExperimentVariant, RiskLevel
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="exp-test-001",
            name="Test Experiment",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        _experiment_registry.register(experiment)
        
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/exp-test-001/start",
            json={"started_by": "user-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-test-001"
        assert data["status"] == "running"
        assert data["started_at"] is not None

    def test_start_nonexistent_returns_404(self):
        """Start de experimento inexistente deve retornar 404."""
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/nonexistent/start",
            json={"started_by": "user-001"}
        )
        
        assert response.status_code == 404


class TestOnboardingExperimentPauseEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-experiments/{id}/pause."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_experiment_state()

    def test_pause_running_experiment(self):
        """Pause deve pausar um experimento em execução."""
        # Primeiro criar e iniciar um experimento
        from vm_webapp.api_onboarding_experiments import _experiment_registry
        from vm_webapp.onboarding_experiments import Experiment, ExperimentVariant, RiskLevel
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="exp-test-002",
            name="Test Experiment",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        _experiment_registry.register(experiment)
        _experiment_registry.start_experiment("exp-test-002")
        
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/exp-test-002/pause",
            json={"paused_by": "user-001", "reason": "Investigating anomaly"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-test-002"
        assert data["status"] == "paused"
        assert data["paused_at"] is not None


class TestOnboardingExperimentPromoteEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-experiments/{id}/promote."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_experiment_state()

    def test_promote_low_risk_auto(self):
        """Promote de experimento low-risk deve auto-aplicar."""
        # Criar experimento low-risk com resultados positivos
        from vm_webapp.api_onboarding_experiments import _experiment_registry
        from vm_webapp.onboarding_experiments import Experiment, ExperimentVariant, RiskLevel
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="exp-test-003",
            name="Test Experiment",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        _experiment_registry.register(experiment)
        _experiment_registry.start_experiment("exp-test-003")
        
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/exp-test-003/promote",
            json={
                "promoted_by": "system",
                "variant_id": "treatment",
                "auto_apply": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-test-003"
        assert data["decision"] in ["auto_apply", "approved", "pending_approval"]

    def test_promote_medium_risk_needs_approval(self):
        """Promote de experimento medium-risk deve requerer aprovação."""
        from vm_webapp.api_onboarding_experiments import _experiment_registry
        from vm_webapp.onboarding_experiments import Experiment, ExperimentVariant, RiskLevel
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="exp-test-004",
            name="Test Experiment",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.MEDIUM,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        _experiment_registry.register(experiment)
        _experiment_registry.start_experiment("exp-test-004")
        
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/exp-test-004/promote",
            json={
                "promoted_by": "user-001",
                "variant_id": "treatment",
                "auto_apply": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["requires_approval"] is True


class TestOnboardingExperimentRollbackEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-experiments/{id}/rollback."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_experiment_state()

    def test_rollback_experiment(self):
        """Rollback deve reverter um experimento."""
        from vm_webapp.api_onboarding_experiments import _experiment_registry
        from vm_webapp.onboarding_experiments import Experiment, ExperimentVariant, RiskLevel
        
        variants = [
            ExperimentVariant("control", "Control", {}, 50),
            ExperimentVariant("treatment", "Treatment", {}, 50),
        ]
        experiment = Experiment(
            experiment_id="exp-test-005",
            name="Test Experiment",
            description="Test",
            hypothesis="Test",
            primary_metric="conversion",
            variants=variants,
            risk_level=RiskLevel.LOW,
            min_sample_size=100,
            min_confidence=0.95,
            max_lift_threshold=0.10,
        )
        _experiment_registry.register(experiment)
        _experiment_registry.start_experiment("exp-test-005")
        
        response = client_exp.post(
            "/api/v2/brands/brand-001/onboarding-experiments/exp-test-005/rollback",
            json={
                "rolled_back_by": "user-001",
                "reason": "Negative lift detected"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-test-005"
        assert data["status"] == "rolled_back"
        assert data["rolled_back_at"] is not None


# =============================================================================
# v33 Onboarding Personalization API Tests
# =============================================================================

from vm_webapp.api_onboarding_personalization import router as personalization_router


# Create test app for personalization
app_pers = FastAPI()
app_pers.include_router(personalization_router)
client_pers = TestClient(app_pers)


def _reset_personalization_state():
    """Reset personalization global state between tests."""
    from vm_webapp.api_onboarding_personalization import _profiler, _engine, _manager
    _profiler.clear()
    _engine._serve_count = 0
    _engine._fallback_count = 0
    _engine._serve_latencies_ms.clear()


class TestOnboardingPersonalizationStatusEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-personalization/status."""

    def test_status_returns_basic_info(self):
        """Status deve retornar informações básicas."""
        response = client_pers.get("/api/v2/brands/brand-001/onboarding-personalization/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "version" in data
        assert data["version"] == "v33"

    def test_status_includes_serve_metrics(self):
        """Status deve incluir métricas de serving."""
        response = client_pers.get("/api/v2/brands/brand-001/onboarding-personalization/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "total_serves" in data["metrics"]
        assert "fallback_uses" in data["metrics"]
        assert "avg_latency_ms" in data["metrics"]

    def test_status_includes_active_policies(self):
        """Status deve incluir políticas ativas."""
        response = client_pers.get("/api/v2/brands/brand-001/onboarding-personalization/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_policies" in data
        assert isinstance(data["active_policies"], list)


class TestOnboardingPersonalizationRunEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-personalization/run."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_personalization_state()

    def test_run_executes_pending_rollouts(self):
        """Run deve executar rollouts pendentes."""
        from vm_webapp.api_onboarding_personalization import _profiler
        from vm_webapp.onboarding_personalization import PersonalizationPolicy, RiskLevel, SegmentKey
        
        policy = PersonalizationPolicy(
            policy_id="policy-test-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        _profiler.register_policy(policy)
        
        response = client_pers.post(
            "/api/v2/brands/brand-001/onboarding-personalization/run",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "rollouts" in data
        assert "run_at" in data


class TestOnboardingPersonalizationPoliciesEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-personalization/policies."""

    def test_list_returns_policies(self):
        """List deve retornar lista de políticas."""
        response = client_pers.get("/api/v2/brands/brand-001/onboarding-personalization/policies")
        
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert isinstance(data["policies"], list)
        assert "total" in data

    def test_list_supports_status_filter(self):
        """List deve suportar filtro por status."""
        response = client_pers.get("/api/v2/brands/brand-001/onboarding-personalization/policies?status=active")
        
        assert response.status_code == 200
        data = response.json()
        for policy in data.get("policies", []):
            assert policy["status"] == "active"


class TestOnboardingPersonalizationEffectiveEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-personalization/effective."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_personalization_state()

    def test_get_effective_policy(self):
        """Deve retornar política efetiva para segmento."""
        from vm_webapp.api_onboarding_personalization import _profiler
        from vm_webapp.onboarding_personalization import PersonalizationPolicy, RiskLevel, SegmentKey
        
        policy = PersonalizationPolicy(
            policy_id="policy-test-002",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        policy.activate()
        _profiler.register_policy(policy)
        
        response = client_pers.get(
            "/api/v2/brands/brand-001/onboarding-personalization/effective",
            params={
                "company_size": "small",
                "industry": "tech",
                "experience_level": "beginner",
                "traffic_source": "organic",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["policy_id"] == "policy-test-002"
        assert data["source"] == "segment"
        assert "fallback_used" in data


class TestOnboardingPersonalizationApplyEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-personalization/policies/{id}/apply."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_personalization_state()

    def test_apply_low_risk_auto(self):
        """Apply de política low-risk deve auto-aplicar."""
        from vm_webapp.api_onboarding_personalization import _profiler
        from vm_webapp.onboarding_personalization import PersonalizationPolicy, RiskLevel, SegmentKey
        
        policy = PersonalizationPolicy(
            policy_id="policy-test-003",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        _profiler.register_policy(policy)
        
        response = client_pers.post(
            "/api/v2/brands/brand-001/onboarding-personalization/policies/policy-test-003/apply",
            json={"applied_by": "system"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["policy_id"] == "policy-test-003"
        assert data["decision"] in ["auto_apply", "approved", "pending_approval"]

    def test_apply_medium_risk_needs_approval(self):
        """Apply de política medium-risk deve requerer aprovação."""
        from vm_webapp.api_onboarding_personalization import _profiler
        from vm_webapp.onboarding_personalization import PersonalizationPolicy, RiskLevel, SegmentKey
        
        policy = PersonalizationPolicy(
            policy_id="policy-test-004",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.MEDIUM,
        )
        _profiler.register_policy(policy)
        
        response = client_pers.post(
            "/api/v2/brands/brand-001/onboarding-personalization/policies/policy-test-004/apply",
            json={"applied_by": "user-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["requires_approval"] is True


class TestOnboardingPersonalizationRejectEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-personalization/policies/{id}/reject."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_personalization_state()

    def test_reject_policy(self):
        """Reject deve rejeitar uma política."""
        from vm_webapp.api_onboarding_personalization import _profiler
        from vm_webapp.onboarding_personalization import PersonalizationPolicy, RiskLevel, SegmentKey
        
        policy = PersonalizationPolicy(
            policy_id="policy-test-005",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.MEDIUM,
        )
        _profiler.register_policy(policy)
        
        response = client_pers.post(
            "/api/v2/brands/brand-001/onboarding-personalization/policies/policy-test-005/reject",
            json={
                "rejected_by": "user-001",
                "reason": "Too aggressive"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["policy_id"] == "policy-test-005"
        assert data["status"] == "rejected"


class TestOnboardingPersonalizationFreezeEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-personalization/freeze."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_personalization_state()

    def test_freeze_all_policies(self):
        """Freeze deve congelar todas as políticas ativas."""
        from vm_webapp.api_onboarding_personalization import _profiler
        from vm_webapp.onboarding_personalization import PersonalizationPolicy, RiskLevel, SegmentKey
        
        policy = PersonalizationPolicy(
            policy_id="policy-test-006",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        policy.activate()
        _profiler.register_policy(policy)
        
        response = client_pers.post(
            "/api/v2/brands/brand-001/onboarding-personalization/freeze",
            json={
                "frozen_by": "user-001",
                "reason": "Investigating metrics anomaly"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["frozen_count"] >= 0
        assert data["reason"] == "Investigating metrics anomaly"


class TestOnboardingPersonalizationRollbackEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-personalization/rollback."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_personalization_state()

    def test_rollback_policy(self):
        """Rollback deve reverter uma política."""
        from vm_webapp.api_onboarding_personalization import _profiler
        from vm_webapp.onboarding_personalization import PersonalizationPolicy, RiskLevel, SegmentKey
        
        policy = PersonalizationPolicy(
            policy_id="policy-test-007",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        policy.activate()
        _profiler.register_policy(policy)
        
        response = client_pers.post(
            "/api/v2/brands/brand-001/onboarding-personalization/rollback",
            json={
                "policy_id": "policy-test-007",
                "rolled_back_by": "user-001",
                "reason": "Negative metrics detected"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["policy_id"] == "policy-test-007"
        assert data["status"] == "rolled_back"
        assert data["rolled_back_at"] is not None
