"""Tests for v46 Rollout Dashboard API endpoints.

Testes abrangentes para os endpoints API do dashboard de rollout:
- Dashboard listing
- Approval actions (approve, reject)
- Manual rollback
- History tracking
- Input validation
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from fastapi import FastAPI

from vm_webapp.api_rollout_dashboard import (
    router,
    ApproveRequest,
    RejectRequest,
    RollbackRequest,
    _get_policy_status,
    _get_policy_timeline,
    _get_policy_metrics,
)
from vm_webapp.onboarding_rollout_policy import (
    RolloutMode,
    RolloutPolicy,
    save_policy,
    load_policy,
    clear_telemetry_logs,
    log_promotion_decision,
    PromotionResult,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory for tests."""
    config_dir = tmp_path / "config" / "rollout_policies"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Patch the config dir function
    import vm_webapp.onboarding_rollout_policy as policy_module
    original_get_config_dir = policy_module._get_config_dir
    policy_module._get_config_dir = lambda: config_dir
    
    yield config_dir
    
    # Restore original function
    policy_module._get_config_dir = original_get_config_dir
    clear_telemetry_logs()


@pytest.fixture
def client(temp_config_dir):
    """Create FastAPI test client."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def sample_policy_control():
    """Create a sample policy on control variant."""
    return RolloutPolicy(
        experiment_id="exp-control-001",
        active_variant="control",
        rollout_mode=RolloutMode.AUTO,
        rollback_target="control",
        decision_reason="Initial setup",
        last_evaluation=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def sample_policy_promoted():
    """Create a sample policy with promoted variant."""
    return RolloutPolicy(
        experiment_id="exp-promoted-001",
        active_variant="variant-a",
        rollout_mode=RolloutMode.AUTO,
        rollback_target="control",
        decision_reason="All gates passed",
        last_evaluation=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def sample_policy_manual():
    """Create a sample policy in manual mode."""
    return RolloutPolicy(
        experiment_id="exp-manual-001",
        active_variant="control",
        rollout_mode=RolloutMode.MANUAL,
        rollback_target="control",
        decision_reason="",
        last_evaluation=None,
    )


# =============================================================================
# TESTS: DASHBOARD ENDPOINT
# =============================================================================

class TestGetRolloutDashboard:
    """Test GET /api/v2/onboarding/rollout-dashboard"""
    
    def test_empty_dashboard(self, client, temp_config_dir):
        """Test dashboard with no policies."""
        response = client.get("/api/v2/onboarding/rollout-dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["policies"] == []
        assert data["promoted_count"] == 0
        assert data["evaluating_count"] == 0
    
    def test_dashboard_with_policies(
        self, client, temp_config_dir, sample_policy_control, sample_policy_promoted
    ):
        """Test dashboard with multiple policies."""
        save_policy(sample_policy_control)
        save_policy(sample_policy_promoted)
        
        response = client.get("/api/v2/onboarding/rollout-dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert data["evaluating_count"] == 1  # control
        assert data["promoted_count"] == 1  # variant-a
    
    def test_dashboard_status_counts(self, client, temp_config_dir):
        """Test dashboard counts different statuses correctly."""
        # Create policies with different states
        policies = [
            RolloutPolicy(experiment_id="exp-1", active_variant="control"),
            RolloutPolicy(experiment_id="exp-2", active_variant="variant-a"),
            RolloutPolicy(
                experiment_id="exp-3",
                active_variant="control",
                decision_reason="Manual rollback"
            ),
        ]
        for p in policies:
            save_policy(p)
        
        response = client.get("/api/v2/onboarding/rollout-dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert data["evaluating_count"] == 1
        assert data["promoted_count"] == 1
        assert data["rolled_back_count"] == 1
    
    def test_dashboard_policy_fields(self, client, temp_config_dir, sample_policy_promoted):
        """Test that dashboard returns all required policy fields."""
        save_policy(sample_policy_promoted)
        
        response = client.get("/api/v2/onboarding/rollout-dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["policies"]) == 1
        
        policy = data["policies"][0]
        assert "experiment_id" in policy
        assert "active_variant" in policy
        assert "mode" in policy
        assert "status" in policy
        assert "decision_reason" in policy
        assert "rollback_target" in policy
        assert "can_rollback" in policy
        assert "timeline" in policy
        assert "metrics" in policy
    
    def test_dashboard_can_rollback(self, client, temp_config_dir):
        """Test can_rollback field logic."""
        # Policy on control - cannot rollback
        control_policy = RolloutPolicy(experiment_id="exp-control", active_variant="control")
        save_policy(control_policy)
        
        # Policy on variant - can rollback
        variant_policy = RolloutPolicy(experiment_id="exp-variant", active_variant="variant-a")
        save_policy(variant_policy)
        
        response = client.get("/api/v2/onboarding/rollout-dashboard")
        
        assert response.status_code == 200
        data = response.json()
        
        control_entry = next(p for p in data["policies"] if p["experiment_id"] == "exp-control")
        variant_entry = next(p for p in data["policies"] if p["experiment_id"] == "exp-variant")
        
        assert control_entry["can_rollback"] is False
        assert variant_entry["can_rollback"] is True


# =============================================================================
# TESTS: APPROVE ENDPOINT
# =============================================================================

class TestApprovePromotion:
    """Test POST /api/v2/onboarding/rollout-policy/{experiment_id}/approve"""
    
    def test_approve_promotion_success(self, client, temp_config_dir, sample_policy_manual):
        """Test successful approval of promotion."""
        save_policy(sample_policy_manual)
        
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing promotion approval endpoint",
            "variant": "variant-b",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-manual-001/approve",
            json=request_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_status"] == "promoted"
        assert "variant-b" in data["message"]
        
        # Verify policy was updated
        policy = load_policy("exp-manual-001")
        assert policy.active_variant == "variant-b"
        assert policy.rollout_mode == RolloutMode.AUTO
        assert "admin-001" in policy.decision_reason
    
    def test_approve_default_variant(self, client, temp_config_dir):
        """Test approval with default variant (variant-a)."""
        policy = RolloutPolicy(experiment_id="exp-approve-default", active_variant="control")
        save_policy(policy)
        
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing default variant approval",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-approve-default/approve",
            json=request_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify default variant was used
        policy = load_policy("exp-approve-default")
        assert policy.active_variant == "variant-a"
    
    def test_approve_creates_policy_if_not_exists(self, client, temp_config_dir):
        """Test approval creates default policy if not exists."""
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing policy creation on approve",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-new/approve",
            json=request_data,
        )
        
        assert response.status_code == 200
        
        # Verify policy was created
        policy = load_policy("exp-new")
        assert policy.active_variant == "variant-a"
    
    def test_approve_validation_operator_id_required(self, client, temp_config_dir):
        """Test validation rejects empty operator_id."""
        request_data = {
            "operator_id": "",
            "reason": "Testing validation failure",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-001/approve",
            json=request_data,
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "operator_id" in str(data) or "validation" in str(data).lower()
    
    def test_approve_validation_reason_min_length(self, client, temp_config_dir):
        """Test validation rejects short reason."""
        request_data = {
            "operator_id": "admin-001",
            "reason": "Short",  # Less than 10 chars
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-001/approve",
            json=request_data,
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "reason" in str(data) or "10" in str(data)


# =============================================================================
# TESTS: REJECT ENDPOINT
# =============================================================================

class TestRejectPromotion:
    """Test POST /api/v2/onboarding/rollout-policy/{experiment_id}/reject"""
    
    def test_reject_promotion_success(self, client, temp_config_dir, sample_policy_promoted):
        """Test successful rejection of promotion."""
        save_policy(sample_policy_promoted)
        
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing promotion rejection endpoint",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-promoted-001/reject",
            json=request_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_status"] == "blocked"
        assert "variant-a" in data["message"]
        
        # Verify policy was rolled back to control
        policy = load_policy("exp-promoted-001")
        assert policy.active_variant == "control"
        assert "rejected" in policy.decision_reason.lower()
    
    def test_reject_already_on_control(self, client, temp_config_dir, sample_policy_control):
        """Test rejection when already on control."""
        save_policy(sample_policy_control)
        
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing rejection on control",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-control-001/reject",
            json=request_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_status"] == "blocked"
        
        # Should still be on control
        policy = load_policy("exp-control-001")
        assert policy.active_variant == "control"
    
    def test_reject_validation_reason_min_length(self, client, temp_config_dir):
        """Test validation rejects short reason."""
        request_data = {
            "operator_id": "admin-001",
            "reason": "Too short",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-001/reject",
            json=request_data,
        )
        
        assert response.status_code == 422
    
    def test_reject_creates_policy_if_not_exists(self, client, temp_config_dir):
        """Test rejection creates default policy if not exists."""
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing policy creation on reject",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-reject-new/reject",
            json=request_data,
        )
        
        assert response.status_code == 200
        
        # Verify policy was created and is on control
        policy = load_policy("exp-reject-new")
        assert policy.active_variant == "control"


# =============================================================================
# TESTS: ROLLBACK ENDPOINT
# =============================================================================

class TestManualRollback:
    """Test POST /api/v2/onboarding/rollout-policy/{experiment_id}/rollback"""
    
    def test_manual_rollback_success(self, client, temp_config_dir, sample_policy_promoted):
        """Test successful manual rollback."""
        save_policy(sample_policy_promoted)
        
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing manual rollback endpoint",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-promoted-001/rollback",
            json=request_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_status"] == "rolled_back"
        assert "control" in data["message"].lower()
        
        # Verify policy was rolled back
        policy = load_policy("exp-promoted-001")
        assert policy.active_variant == "control"
        assert "Manual rollback" in policy.decision_reason
    
    def test_manual_rollback_already_on_control(self, client, temp_config_dir, sample_policy_control):
        """Test rollback fails when already on control."""
        save_policy(sample_policy_control)
        
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing rollback on control",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-control-001/rollback",
            json=request_data,
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already on control" in data["detail"].lower()
    
    def test_manual_rollback_validation_reason_min_length(self, client, temp_config_dir):
        """Test validation rejects short reason."""
        request_data = {
            "operator_id": "admin-001",
            "reason": "Too short",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-001/rollback",
            json=request_data,
        )
        
        assert response.status_code == 422
    
    def test_manual_rollback_creates_policy_if_not_exists(self, client, temp_config_dir):
        """Test rollback creates default policy if not exists."""
        request_data = {
            "operator_id": "admin-001",
            "reason": "Testing policy creation on rollback",
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-rollback-new/rollback",
            json=request_data,
        )
        
        # Should fail because new policy is on control
        assert response.status_code == 400
        assert "already on control" in response.json()["detail"].lower()


# =============================================================================
# TESTS: HISTORY ENDPOINT
# =============================================================================

class TestGetPolicyHistory:
    """Test GET /api/v2/onboarding/rollout-policy/{experiment_id}/history"""
    
    def test_history_returns_timeline(self, client, temp_config_dir, sample_policy_promoted):
        """Test history endpoint returns timeline."""
        save_policy(sample_policy_promoted)
        
        response = client.get("/api/v2/onboarding/rollout-policy/exp-promoted-001/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-promoted-001"
        assert "timeline" in data
        assert data["total_events"] >= 1  # At least current_state
        
        # Check current_state event
        current_event = data["timeline"][0]
        assert current_event["type"] == "current_state"
        assert current_event["active_variant"] == "variant-a"
    
    def test_history_with_telemetry_logs(self, client, temp_config_dir):
        """Test history includes telemetry logs."""
        # Create policy and add some telemetry
        policy = RolloutPolicy(experiment_id="exp-history-001", active_variant="control")
        save_policy(policy)
        
        # Add promotion log
        log_promotion_decision(
            PromotionResult(
                success=True,
                variant_id="variant-a",
                gates_passed=["gain_gate"],
                gates_failed=[],
                reason="Test promotion",
            )
        )
        
        response = client.get("/api/v2/onboarding/rollout-policy/exp-history-001/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] >= 2  # current_state + promotion log
    
    def test_history_creates_default_policy(self, client, temp_config_dir):
        """Test history creates default policy if not exists."""
        response = client.get("/api/v2/onboarding/rollout-policy/exp-history-new/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-history-new"
        assert data["total_events"] >= 1


# =============================================================================
# TESTS: GET POLICY ENDPOINT
# =============================================================================

class TestGetRolloutPolicy:
    """Test GET /api/v2/onboarding/rollout-policy/{experiment_id}"""
    
    def test_get_policy_success(self, client, temp_config_dir, sample_policy_promoted):
        """Test getting a specific policy."""
        save_policy(sample_policy_promoted)
        
        response = client.get("/api/v2/onboarding/rollout-policy/exp-promoted-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-promoted-001"
        assert data["active_variant"] == "variant-a"
        assert data["mode"] == "AUTO"
        assert data["status"] == "promoted"
    
    def test_get_policy_creates_default(self, client, temp_config_dir):
        """Test getting nonexistent policy creates default."""
        response = client.get("/api/v2/onboarding/rollout-policy/exp-get-new")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "exp-get-new"
        assert data["active_variant"] == "control"
        assert data["mode"] == "AUTO"
    
    def test_get_policy_all_fields_present(self, client, temp_config_dir, sample_policy_promoted):
        """Test that all expected fields are present in response."""
        save_policy(sample_policy_promoted)
        
        response = client.get("/api/v2/onboarding/rollout-policy/exp-promoted-001")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "experiment_id", "active_variant", "mode", "status",
            "decision_reason", "rollback_target", "can_rollback",
            "timeline", "metrics",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


# =============================================================================
# TESTS: EVALUATE ENDPOINT
# =============================================================================

class TestEvaluatePolicy:
    """Test POST /api/v2/onboarding/rollout-policy/{experiment_id}/evaluate"""
    
    def test_evaluate_without_benchmark(self, client, temp_config_dir, sample_policy_promoted):
        """Test evaluation without benchmark data returns status."""
        save_policy(sample_policy_promoted)
        
        response = client.post("/api/v2/onboarding/rollout-policy/exp-promoted-001/evaluate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "status"
        assert data["experiment_id"] == "exp-promoted-001"
        assert data["active_variant"] == "variant-a"
    
    def test_evaluate_promotion_with_benchmark(self, client, temp_config_dir):
        """Test evaluation with benchmark data for promotion."""
        policy = RolloutPolicy(experiment_id="exp-eval-promote", active_variant="control")
        save_policy(policy)
        
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
                "completion_rate": 0.78,
                "abandonment_rate": 0.14,
                "score": 0.85,  # Better than control
                "sample_size": 50,
            },
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-eval-promote/evaluate",
            json=benchmark_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "promotion_evaluation"
        assert data["experiment_id"] == "exp-eval-promote"
        assert data["can_promote"] is True
        assert "variant-a" in data["gates_passed"] or len(data["gates_passed"]) > 0
    
    def test_evaluate_rollback_with_benchmark(self, client, temp_config_dir):
        """Test evaluation with benchmark data for rollback."""
        policy = RolloutPolicy(
            experiment_id="exp-eval-rollback",
            active_variant="variant-a",
        )
        save_policy(policy)
        
        benchmark_data = {
            "control": {
                "ttfv": 120.0,
                "completion_rate": 0.75,
                "abandonment_rate": 0.15,
                "score": 0.80,
                "sample_size": 100,
            },
            "variant-a": {
                "ttfv": 120.0,
                "completion_rate": 0.60,  # Degraded
                "abandonment_rate": 0.15,
                "score": 0.80,
                "sample_size": 100,
            },
        }
        
        response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-eval-rollback/evaluate",
            json=benchmark_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "rollback_evaluation"
        assert data["experiment_id"] == "exp-eval-rollback"
        assert "should_rollback" in data
        assert data["from_variant"] == "variant-a"


# =============================================================================
# TESTS: HELPER FUNCTIONS
# =============================================================================

class TestHelperFunctions:
    """Test internal helper functions."""
    
    def test_get_policy_status_evaluating(self, sample_policy_control):
        """Test status detection for evaluating state."""
        status = _get_policy_status(sample_policy_control)
        assert status == "evaluating"
    
    def test_get_policy_status_promoted(self, sample_policy_promoted):
        """Test status detection for promoted state."""
        status = _get_policy_status(sample_policy_promoted)
        assert status == "promoted"
    
    def test_get_policy_status_rolled_back(self):
        """Test status detection for rolled_back state."""
        policy = RolloutPolicy(
            experiment_id="test",
            active_variant="control",
            decision_reason="Manual rollback executed",
        )
        status = _get_policy_status(policy)
        assert status == "rolled_back"
    
    def test_get_policy_timeline_empty(self, sample_policy_control):
        """Test timeline with no logs."""
        clear_telemetry_logs()
        timeline = _get_policy_timeline(sample_policy_control)
        assert isinstance(timeline, list)
    
    def test_get_policy_metrics_structure(self, sample_policy_promoted):
        """Test metrics structure."""
        metrics = _get_policy_metrics(sample_policy_promoted)
        assert "experiment_id" in metrics
        assert "active_variant" in metrics
        assert "variant_traffic" in metrics
        assert "control_traffic" in metrics


# =============================================================================
# TESTS: REQUEST MODEL VALIDATION
# =============================================================================

class TestRequestValidation:
    """Test Pydantic model validation."""
    
    def test_approve_request_valid(self):
        """Test valid ApproveRequest."""
        request = ApproveRequest(
            operator_id="admin-001",
            reason="This is a valid reason with enough characters",
            variant="variant-a",
        )
        assert request.operator_id == "admin-001"
        assert request.reason == "This is a valid reason with enough characters"
        assert request.variant == "variant-a"
    
    def test_approve_request_reason_too_short(self):
        """Test ApproveRequest with short reason fails."""
        with pytest.raises(ValueError) as exc_info:
            ApproveRequest(operator_id="admin-001", reason="Too short")
        assert "10" in str(exc_info.value) or "reason" in str(exc_info.value).lower()
    
    def test_reject_request_valid(self):
        """Test valid RejectRequest."""
        request = RejectRequest(
            operator_id="admin-001",
            reason="This is a valid rejection reason",
        )
        assert request.operator_id == "admin-001"
        assert request.reason == "This is a valid rejection reason"
    
    def test_rollback_request_valid(self):
        """Test valid RollbackRequest."""
        request = RollbackRequest(
            operator_id="admin-001",
            reason="This is a valid rollback reason",
        )
        assert request.operator_id == "admin-001"
        assert request.reason == "This is a valid rollback reason"
    
    def test_request_operator_id_whitespace(self):
        """Test that whitespace is stripped from operator_id."""
        request = ApproveRequest(
            operator_id="  admin-001  ",
            reason="Valid reason for testing whitespace",
        )
        assert request.operator_id == "admin-001"
    
    def test_request_reason_whitespace(self):
        """Test that whitespace is stripped from reason."""
        request = ApproveRequest(
            operator_id="admin-001",
            reason="  Valid reason with whitespace padding  ",
        )
        assert request.reason == "Valid reason with whitespace padding"


# =============================================================================
# TESTS: COMPLETE FLOW
# =============================================================================

class TestCompleteFlow:
    """Test complete approval and rollback workflows."""
    
    def test_complete_promotion_flow(self, client, temp_config_dir):
        """Test complete flow from control to promoted."""
        # 1. Start with control
        policy = RolloutPolicy(experiment_id="exp-flow-001", active_variant="control")
        save_policy(policy)
        
        # 2. Approve promotion
        approve_response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-flow-001/approve",
            json={
                "operator_id": "admin-001",
                "reason": "Promoting after successful evaluation",
                "variant": "variant-a",
            },
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["success"] is True
        
        # 3. Verify promoted
        policy = load_policy("exp-flow-001")
        assert policy.active_variant == "variant-a"
        
        # 4. Check dashboard shows promoted
        dashboard_response = client.get("/api/v2/onboarding/rollout-dashboard")
        data = dashboard_response.json()
        exp_entry = next(
            (p for p in data["policies"] if p["experiment_id"] == "exp-flow-001"),
            None
        )
        assert exp_entry is not None
        assert exp_entry["status"] == "promoted"
    
    def test_complete_rollback_flow(self, client, temp_config_dir):
        """Test complete flow from promoted to rolled back."""
        # 1. Start with promoted variant
        policy = RolloutPolicy(
            experiment_id="exp-flow-002",
            active_variant="variant-b",
        )
        save_policy(policy)
        
        # 2. Execute rollback
        rollback_response = client.post(
            "/api/v2/onboarding/rollout-policy/exp-flow-002/rollback",
            json={
                "operator_id": "admin-002",
                "reason": "Rolling back due to detected issues",
            },
        )
        assert rollback_response.status_code == 200
        assert rollback_response.json()["success"] is True
        
        # 3. Verify rolled back
        policy = load_policy("exp-flow-002")
        assert policy.active_variant == "control"
        
        # 4. Check history shows rollback
        history_response = client.get(
            "/api/v2/onboarding/rollout-policy/exp-flow-002/history"
        )
        data = history_response.json()
        assert data["experiment_id"] == "exp-flow-002"
        assert data["total_events"] >= 1
