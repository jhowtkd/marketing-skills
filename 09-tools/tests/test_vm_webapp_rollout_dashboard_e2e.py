"""E2E Integration tests for Rollout Dashboard v46.

Fluxo completo: dashboard -> approve/reject -> atualização de estado -> rollback manual
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI

from vm_webapp.api_rollout_dashboard import router as rollout_router
from vm_webapp.onboarding_rollout_policy import (
    RolloutMode,
    RolloutPolicy,
    save_policy,
    load_policy,
    clear_telemetry_logs,
    list_active_policies,
    delete_policy,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def clean_policies_and_logs():
    """Clean up policies and telemetry logs before each test."""
    clear_telemetry_logs()
    # Clean up any existing test policies
    for policy in list_active_policies():
        if policy.experiment_id.startswith("test-") or policy.experiment_id.startswith("e2e-"):
            delete_policy(policy.experiment_id)
    yield
    # Cleanup after test
    clear_telemetry_logs()
    for policy in list_active_policies():
        if policy.experiment_id.startswith("test-") or policy.experiment_id.startswith("e2e-"):
            delete_policy(policy.experiment_id)


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create temporary config directory for tests."""
    import vm_webapp.onboarding_rollout_policy as policy_module
    config_dir = tmp_path / "config" / "rollout_policies"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Monkeypatch the config dir
    monkeypatch.setattr(policy_module, "_get_config_dir", lambda: config_dir)
    
    yield config_dir


@pytest.fixture
def client(temp_config_dir) -> TestClient:
    """Create FastAPI test client with rollout router."""
    app = FastAPI()
    app.include_router(rollout_router)
    return TestClient(app)


# =============================================================================
# TESTS: COMPLETE E2E FLOWS
# =============================================================================

class TestRolloutDashboardE2E:
    """Fluxo completo de aprovação e rollback."""
    
    def test_complete_approve_flow(self, client: TestClient):
        """
        Cenário: Operador aprova promoção de variante
        Dado: Experimento em estado "pending_review"
        Quando: POST /approve com operator_id e reason válidos
        Então: Status muda para "promoted"
        E: Timeline atualizada com evento de aprovação
        """
        experiment_id = "e2e-approve-flow"
        
        # Setup: Create policy in evaluating state (control)
        policy = RolloutPolicy(
            experiment_id=experiment_id,
            active_variant="control",
            rollout_mode=RolloutMode.MANUAL,
            decision_reason="Awaiting manual approval",
        )
        save_policy(policy)
        
        # Verify initial state via dashboard
        dashboard_response = client.get("/api/v2/onboarding/rollout-dashboard")
        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        exp_entry = next(
            (p for p in dashboard_data["policies"] if p["experiment_id"] == experiment_id),
            None
        )
        assert exp_entry is not None
        assert exp_entry["status"] == "evaluating"
        
        # Action: Approve promotion
        approve_response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/approve",
            json={
                "operator_id": "operator_123",
                "reason": "Treatment shows consistent 2.3% improvement across all gates",
                "variant": "treatment_v2",
            },
        )
        
        # Assert: Approval response
        assert approve_response.status_code == 200
        approve_data = approve_response.json()
        assert approve_data["success"] is True
        assert approve_data["new_status"] == "promoted"
        
        # Assert: Verify via dashboard
        dashboard_response2 = client.get("/api/v2/onboarding/rollout-dashboard")
        assert dashboard_response2.status_code == 200
        dashboard_data2 = dashboard_response2.json()
        exp_entry2 = next(
            (p for p in dashboard_data2["policies"] if p["experiment_id"] == experiment_id),
            None
        )
        assert exp_entry2 is not None
        assert exp_entry2["status"] == "promoted"
        assert exp_entry2["active_variant"] == "treatment_v2"
        
        # Assert: Verify via history endpoint
        history_response = client.get(f"/api/v2/onboarding/rollout-policy/{experiment_id}/history")
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["experiment_id"] == experiment_id
        
        # Assert: Verify policy state in storage
        updated_policy = load_policy(experiment_id)
        assert updated_policy.active_variant == "treatment_v2"
        assert "operator_123" in updated_policy.decision_reason
        assert updated_policy.rollout_mode == RolloutMode.AUTO  # Switches to AUTO after approval
    
    def test_complete_reject_flow(self, client: TestClient):
        """
        Cenário: Operador rejeita promoção
        Dado: Experimento em estado "pending_review"
        Quando: POST /reject com reason válido
        Então: Status muda para "blocked"
        E: Timeline atualizada com evento de rejeição
        """
        experiment_id = "e2e-reject-flow"
        
        # Setup: Create policy with variant active (simulating a pending review state)
        policy = RolloutPolicy(
            experiment_id=experiment_id,
            active_variant="treatment_v2",
            rollout_mode=RolloutMode.MANUAL,
            decision_reason="Evaluation complete, awaiting decision",
            last_evaluation=datetime.now(timezone.utc).isoformat(),
        )
        save_policy(policy)
        
        # Action: Reject promotion
        reject_response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/reject",
            json={
                "operator_id": "operator_456",
                "reason": "Insufficient sample size for confidence - need 50 more samples",
            },
        )
        
        # Assert: Rejection response
        assert reject_response.status_code == 200
        reject_data = reject_response.json()
        assert reject_data["success"] is True
        assert reject_data["new_status"] == "blocked"
        assert "treatment_v2" in reject_data["message"]
        
        # Assert: Verify policy rolled back to control
        updated_policy = load_policy(experiment_id)
        assert updated_policy.active_variant == "control"
        assert "rejected" in updated_policy.decision_reason.lower()
        assert "operator_456" in updated_policy.decision_reason
        
        # Assert: Verify via dashboard
        dashboard_response = client.get("/api/v2/onboarding/rollout-dashboard")
        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        exp_entry = next(
            (p for p in dashboard_data["policies"] if p["experiment_id"] == experiment_id),
            None
        )
        assert exp_entry is not None
        assert exp_entry["status"] == "blocked"
        assert exp_entry["active_variant"] == "control"
    
    def test_complete_rollback_flow(self, client: TestClient):
        """
        Cenário: Rollback manual após promoção
        Dado: Experimento em estado "promoted"
        Quando: POST /rollback com reason válido
        Então: Status muda para "rolled_back"
        E: active_variant volta para "control"
        """
        experiment_id = "e2e-rollback-flow"
        
        # Setup: Create policy in promoted state
        policy = RolloutPolicy(
            experiment_id=experiment_id,
            active_variant="treatment_v2",
            rollout_mode=RolloutMode.AUTO,
            decision_reason="All gates passed - auto promoted",
            last_evaluation=datetime.now(timezone.utc).isoformat(),
        )
        save_policy(policy)
        
        # Verify: Initial promoted state
        policy_check = load_policy(experiment_id)
        assert policy_check.active_variant == "treatment_v2"
        
        # Action: Execute manual rollback
        rollback_response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/rollback",
            json={
                "operator_id": "operator_789",
                "reason": "Detected anomaly in conversion funnel - emergency rollback",
            },
        )
        
        # Assert: Rollback response
        assert rollback_response.status_code == 200
        rollback_data = rollback_response.json()
        assert rollback_data["success"] is True
        assert rollback_data["new_status"] == "rolled_back"
        assert "control" in rollback_data["message"].lower()
        
        # Assert: Verify rolled back to control
        updated_policy = load_policy(experiment_id)
        assert updated_policy.active_variant == "control"
        assert "Manual rollback" in updated_policy.decision_reason
        assert "operator_789" in updated_policy.decision_reason
        
        # Assert: Verify via dashboard - should show rolled_back status
        dashboard_response = client.get("/api/v2/onboarding/rollout-dashboard")
        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        exp_entry = next(
            (p for p in dashboard_data["policies"] if p["experiment_id"] == experiment_id),
            None
        )
        assert exp_entry is not None
        assert exp_entry["status"] == "rolled_back"
        assert exp_entry["active_variant"] == "control"
        assert exp_entry["can_rollback"] is False  # Already on control
    
    def test_regression_v45_policy_engine(self, client: TestClient):
        """
        Verificar que v46 não quebra v45:
        - Auto-rollout ainda funciona em modo AUTO
        - Gates de promoção ainda são aplicados
        - Rollback automático ainda ocorre em degradação
        """
        experiment_id = "e2e-regression-v45"
        
        # Test 1: Auto-rollout in AUTO mode
        policy_auto = RolloutPolicy(
            experiment_id=experiment_id,
            active_variant="control",
            rollout_mode=RolloutMode.AUTO,
            decision_reason="Initial state",
        )
        save_policy(policy_auto)
        
        # Evaluate with good benchmark data (should auto-promote in v45)
        benchmark_data = {
            "control": {
                "ttfv": 120.0,
                "completion_rate": 0.75,
                "abandonment_rate": 0.15,
                "score": 0.80,
                "sample_size": 100,
            },
            "variant-a": {
                "ttfv": 110.0,
                "completion_rate": 0.80,
                "abandonment_rate": 0.12,
                "score": 0.85,  # Better than control (> 0.5% gain)
                "sample_size": 50,  # Above stability threshold of 30
            },
        }
        
        evaluate_response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/evaluate",
            json=benchmark_data,
        )
        assert evaluate_response.status_code == 200
        eval_data = evaluate_response.json()
        assert eval_data["type"] == "promotion_evaluation"
        assert eval_data["can_promote"] is True
        assert "variant-a" in eval_data["gates_passed"] or len(eval_data["gates_passed"]) >= 1
        
        # Test 2: Verify gates are still applied (v45 gates)
        # Create another experiment with failing gates
        experiment_id_2 = "e2e-regression-v45-gates"
        policy_auto_2 = RolloutPolicy(
            experiment_id=experiment_id_2,
            active_variant="control",
            rollout_mode=RolloutMode.AUTO,
        )
        save_policy(policy_auto_2)
        
        # Benchmark with poor variant metrics
        bad_benchmark_data = {
            "control": {
                "ttfv": 120.0,
                "completion_rate": 0.75,
                "abandonment_rate": 0.15,
                "score": 0.80,
                "sample_size": 100,
            },
            "variant-b": {
                "ttfv": 140.0,  # Worse TTFV
                "completion_rate": 0.70,  # Below 95% of control
                "abandonment_rate": 0.20,  # Higher abandonment
                "score": 0.78,  # Below control (fails gain gate)
                "sample_size": 20,  # Below stability threshold
            },
        }
        
        evaluate_response_2 = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id_2}/evaluate",
            json=bad_benchmark_data,
        )
        assert evaluate_response_2.status_code == 200
        eval_data_2 = evaluate_response_2.json()
        assert eval_data_2["type"] == "promotion_evaluation"
        assert eval_data_2["can_promote"] is False
        assert len(eval_data_2["gates_failed"]) >= 1
        
        # Test 3: Rollback evaluation still works
        experiment_id_3 = "e2e-regression-v45-rollback"
        policy_promoted = RolloutPolicy(
            experiment_id=experiment_id_3,
            active_variant="variant-a",
            rollout_mode=RolloutMode.AUTO,
            decision_reason="Previously promoted",
            last_evaluation=datetime.now(timezone.utc).isoformat(),
        )
        save_policy(policy_promoted)
        
        # Degraded metrics should trigger rollback consideration
        degraded_benchmark = {
            "control": {
                "ttfv": 120.0,
                "completion_rate": 0.75,
                "abandonment_rate": 0.15,
                "score": 0.80,
                "sample_size": 100,
            },
            "variant-a": {
                "ttfv": 120.0,
                "completion_rate": 0.60,  # Degraded completion
                "abandonment_rate": 0.15,
                "score": 0.80,
                "sample_size": 100,
            },
        }
        
        rollback_eval_response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id_3}/evaluate",
            json=degraded_benchmark,
        )
        assert rollback_eval_response.status_code == 200
        rollback_eval_data = rollback_eval_response.json()
        assert rollback_eval_data["type"] == "rollback_evaluation"
        assert "should_rollback" in rollback_eval_data
        assert rollback_eval_data["from_variant"] == "variant-a"


# =============================================================================
# TESTS: ERROR HANDLING AND EDGE CASES
# =============================================================================

class TestE2EErrorHandling:
    """Test error handling in E2E scenarios."""
    
    def test_approve_nonexistent_experiment(self, client: TestClient):
        """Test approving a promotion for non-existent experiment creates it."""
        experiment_id = "e2e-nonexistent-approve"
        
        response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/approve",
            json={
                "operator_id": "operator_test",
                "reason": "Auto-creating experiment via approval",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify experiment was created
        policy = load_policy(experiment_id)
        assert policy is not None
        assert policy.active_variant == "variant-a"  # Default variant
    
    def test_rollback_already_on_control(self, client: TestClient):
        """Test rollback fails gracefully when already on control."""
        experiment_id = "e2e-rollback-control"
        
        # Create policy already on control
        policy = RolloutPolicy(
            experiment_id=experiment_id,
            active_variant="control",
            rollout_mode=RolloutMode.AUTO,
        )
        save_policy(policy)
        
        response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/rollback",
            json={
                "operator_id": "operator_test",
                "reason": "Trying to rollback when already on control",
            },
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already on control" in data["detail"].lower()
    
    def test_validation_errors_return_422(self, client: TestClient):
        """Test validation errors return proper 422 status."""
        experiment_id = "e2e-validation"
        
        # Test short reason
        response = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/approve",
            json={
                "operator_id": "op",
                "reason": "Short",  # Less than 10 chars
            },
        )
        
        assert response.status_code == 422
        
        # Test empty operator_id
        response2 = client.post(
            f"/api/v2/onboarding/rollout-policy/{experiment_id}/reject",
            json={
                "operator_id": "",
                "reason": "Valid reason here",
            },
        )
        
        assert response2.status_code == 422


# =============================================================================
# TESTS: DASHBOARD CONSISTENCY
# =============================================================================

class TestDashboardConsistency:
    """Test dashboard consistency across operations."""
    
    def test_dashboard_reflects_all_operations(self, client: TestClient):
        """Test that dashboard accurately reflects all operations."""
        # Create multiple experiments in different states
        experiments = [
            ("e2e-dash-1", "control", RolloutMode.AUTO),      # evaluating
            ("e2e-dash-2", "variant-a", RolloutMode.AUTO),    # promoted
            ("e2e-dash-3", "control", RolloutMode.MANUAL),    # evaluating (manual)
        ]
        
        for exp_id, variant, mode in experiments:
            policy = RolloutPolicy(
                experiment_id=exp_id,
                active_variant=variant,
                rollout_mode=mode,
                decision_reason="Test setup",
                last_evaluation=datetime.now(timezone.utc).isoformat(),
            )
            save_policy(policy)
        
        # Get dashboard
        dashboard_response = client.get("/api/v2/onboarding/rollout-dashboard")
        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        
        # Verify counts
        assert dashboard_data["total_count"] >= 3
        
        # Verify each experiment is present with correct status
        for exp_id, variant, mode in experiments:
            exp_entry = next(
                (p for p in dashboard_data["policies"] if p["experiment_id"] == exp_id),
                None
            )
            assert exp_entry is not None, f"Experiment {exp_id} not found in dashboard"
            assert exp_entry["active_variant"] == variant
            assert exp_entry["mode"] == mode.value.upper()
            
            if variant == "control":
                assert exp_entry["status"] in ["evaluating", "rolled_back"]
            else:
                assert exp_entry["status"] == "promoted"
    
    def test_individual_policy_endpoint_consistency(self, client: TestClient):
        """Test individual policy endpoint matches dashboard data."""
        experiment_id = "e2e-consistency"
        
        policy = RolloutPolicy(
            experiment_id=experiment_id,
            active_variant="treatment_v2",
            rollout_mode=RolloutMode.SUPERVISED,
            decision_reason="Supervised mode test",
            last_evaluation=datetime.now(timezone.utc).isoformat(),
        )
        save_policy(policy)
        
        # Get via dashboard
        dashboard_response = client.get("/api/v2/onboarding/rollout-dashboard")
        dashboard_data = dashboard_response.json()
        dashboard_entry = next(
            (p for p in dashboard_data["policies"] if p["experiment_id"] == experiment_id),
            None
        )
        
        # Get via individual endpoint
        policy_response = client.get(f"/api/v2/onboarding/rollout-policy/{experiment_id}")
        policy_data = policy_response.json()
        
        # Verify consistency
        assert dashboard_entry["experiment_id"] == policy_data["experiment_id"]
        assert dashboard_entry["active_variant"] == policy_data["active_variant"]
        assert dashboard_entry["mode"] == policy_data["mode"]
        assert dashboard_entry["status"] == policy_data["status"]
        assert dashboard_entry["can_rollback"] == policy_data["can_rollback"]
