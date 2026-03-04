"""API v2 tests for Adaptive Escalation endpoints (v21)."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from vm_webapp.app import create_app
from vm_webapp.adaptive_escalation import AdaptiveEscalationEngine


@pytest.fixture
def app():
    """FastAPI app fixture."""
    return create_app()


@pytest.fixture
def client(app):
    """Test client for API."""
    return TestClient(app)


@pytest.fixture
def escalation_engine():
    """Adaptive escalation engine."""
    return AdaptiveEscalationEngine()


class TestAdaptiveEscalationEndpoints:
    """Test adaptive escalation API endpoints."""

    def test_get_escalation_windows_endpoint(self, client):
        """POST /v2/escalation/windows returns adaptive windows."""
        response = client.post(
            "/v2/escalation/windows",
            json={
                "step_id": "step-001",
                "risk_level": "medium",
                "approver_id": "admin@example.com",
                "pending_count": 5,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "windows" in data
        assert len(data["windows"]) == 3
        assert all(w > 0 for w in data["windows"])
        assert data["windows"][0] < data["windows"][1] < data["windows"][2]

    def test_get_escalation_windows_with_context(self, client):
        """Endpoint considers time context."""
        response = client.post(
            "/v2/escalation/windows",
            json={
                "step_id": "step-002",
                "risk_level": "high",
                "approver_id": "admin@example.com",
                "pending_count": 15,  # High load
                "current_time": datetime.now().isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "windows" in data
        assert "adaptive_factors" in data

    def test_record_approval_endpoint(self, client):
        """POST /v2/escalation/approvals records approval."""
        response = client.post(
            "/v2/escalation/approvals",
            json={
                "approver_id": "admin@example.com",
                "step_id": "step-001",
                "response_time_seconds": 600,  # 10 minutes
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "recorded"
        assert data["approver_id"] == "admin@example.com"

    def test_record_timeout_endpoint(self, client):
        """POST /v2/escalation/timeouts records timeout."""
        response = client.post(
            "/v2/escalation/timeouts",
            json={
                "approver_id": "admin@example.com",
                "step_id": "step-001",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "recorded"

    def test_get_approver_profile_endpoint(self, client):
        """GET /v2/escalation/profiles/{approver_id} returns profile."""
        # First record some activity
        client.post(
            "/v2/escalation/approvals",
            json={
                "approver_id": "user@example.com",
                "step_id": "step-001",
                "response_time_seconds": 600,
            },
        )
        
        response = client.get("/v2/escalation/profiles/user@example.com")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["approver_id"] == "user@example.com"
        assert data["approvals_count"] == 1
        assert "avg_response_time_minutes" in data

    def test_get_escalation_metrics_endpoint(self, client):
        """GET /v2/escalation/metrics returns engine metrics."""
        response = client.get("/v2/escalation/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "approver_count" in data
        assert "total_approvals" in data
        assert "timeout_rate" in data


class TestAdaptiveEscalationService:
    """Test adaptive escalation service layer."""

    def test_service_calculate_windows(self, escalation_engine):
        """Service calculates escalation windows."""
        windows = escalation_engine.calculate_escalation_windows(
            step_id="step-001",
            risk_level="medium",
            approver_id="admin@example.com",
            pending_count=5,
        )
        
        assert len(windows) == 3
        assert all(w > 0 for w in windows)
        assert windows[0] < windows[1] < windows[2]

    def test_service_adapts_to_approver_profile(self, escalation_engine):
        """Service adapts windows based on approver profile."""
        # Create profile with fast response time
        for _ in range(5):
            escalation_engine.record_approval(
                "fast@example.com", "step-001", 300  # 5 min
            )
        
        fast_windows = escalation_engine.calculate_escalation_windows(
            step_id="step-001",
            risk_level="medium",
            approver_id="fast@example.com",
            pending_count=5,
        )
        
        # Create profile with slow response time
        for _ in range(5):
            escalation_engine.record_approval(
                "slow@example.com", "step-002", 2700  # 45 min
            )
        
        slow_windows = escalation_engine.calculate_escalation_windows(
            step_id="step-003",
            risk_level="medium",
            approver_id="slow@example.com",
            pending_count=5,
        )
        
        # Fast approver should have shorter first window
        assert fast_windows[0] < slow_windows[0]

    def test_service_metrics(self, escalation_engine):
        """Service provides metrics."""
        # Record some activity
        escalation_engine.record_approval("user@example.com", "step-001", 600)
        escalation_engine.record_approval("user@example.com", "step-002", 900)
        
        metrics = escalation_engine.get_metrics()
        
        assert metrics["approver_count"] == 1
        assert metrics["total_approvals"] == 2
        assert metrics["timeout_rate"] == 0.0
