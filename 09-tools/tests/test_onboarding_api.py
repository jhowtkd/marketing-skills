"""Tests for v30 onboarding API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """Create test client for onboarding API."""
    from vm_webapp.app import create_app
    from vm_webapp.settings import Settings

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    app = create_app(
        settings=Settings(
            vm_workspace_root=str(workspace_root),
            vm_db_path=workspace_root / "test.sqlite3",
            kimi_api_key="test-api-key",
        ),
        enable_in_process_worker=False,
    )
    return TestClient(app)


class TestOnboardingStateEndpoints:
    """Test onboarding state management endpoints."""

    def test_get_onboarding_state_empty(self, client):
        """Test getting onboarding state for new user."""
        response = client.get("/api/v2/onboarding/state?user_id=new-user")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "new-user"
        assert data["has_started"] is False
        assert data["has_completed"] is False
        assert data["current_step"] is None

    def test_update_onboarding_state(self, client):
        """Test updating onboarding state."""
        payload = {
            "user_id": "test-user",
            "current_step": "workspace_setup",
            "has_started": True,
            "has_completed": False,
        }
        response = client.post("/api/v2/onboarding/state", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user"
        assert data["current_step"] == "workspace_setup"
        assert data["has_started"] is True

    def test_get_onboarding_state_after_update(self, client):
        """Test getting state after update."""
        # First update state
        payload = {
            "user_id": "test-user-2",
            "current_step": "template_selection",
            "has_started": True,
            "has_completed": False,
        }
        client.post("/api/v2/onboarding/state", json=payload)
        
        # Then get state
        response = client.get("/api/v2/onboarding/state?user_id=test-user-2")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-2"
        assert data["current_step"] == "template_selection"

    def test_complete_onboarding(self, client):
        """Test marking onboarding as completed."""
        payload = {
            "user_id": "complete-user",
            "current_step": "completion",
            "has_started": True,
            "has_completed": True,
            "duration_ms": 125000,
        }
        response = client.post("/api/v2/onboarding/state", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["has_completed"] is True
        assert data["duration_ms"] == 125000


class TestOnboardingTemplatesEndpoints:
    """Test onboarding templates endpoints."""

    def test_get_templates(self, client):
        """Test getting all first-success templates."""
        response = client.get("/api/v2/onboarding/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) > 0
        
        # Check template structure
        template = data["templates"][0]
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "category" in template
        assert "icon" in template
        assert "default_prompt" in template

    def test_get_templates_by_category(self, client):
        """Test filtering templates by category."""
        response = client.get("/api/v2/onboarding/templates?category=content")
        assert response.status_code == 200
        data = response.json()
        
        for template in data["templates"]:
            assert template["category"] == "content"

    def test_get_template_by_id(self, client):
        """Test getting specific template."""
        response = client.get("/api/v2/onboarding/templates/blog-post")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "blog-post"
        assert "name" in data
        assert "description" in data

    def test_get_template_not_found(self, client):
        """Test getting non-existent template."""
        response = client.get("/api/v2/onboarding/templates/non-existent")
        assert response.status_code == 404

    def test_get_recommended_template(self, client):
        """Test getting recommended first template."""
        response = client.get("/api/v2/onboarding/templates/recommended")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "is_recommended" in data
        assert data["is_recommended"] is True


class TestOnboardingEventsEndpoints:
    """Test onboarding telemetry events endpoints."""

    def test_track_onboarding_started(self, client):
        """Test tracking onboarding started event."""
        payload = {
            "event": "onboarding_started",
            "user_id": "user-123",
            "timestamp": "2026-03-02T12:00:00Z",
        }
        response = client.post("/api/v2/onboarding/events", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event"] == "onboarding_started"

    def test_track_onboarding_completed(self, client):
        """Test tracking onboarding completed event."""
        payload = {
            "event": "onboarding_completed",
            "user_id": "user-123",
            "timestamp": "2026-03-02T12:05:00Z",
            "duration_ms": 300000,
        }
        response = client.post("/api/v2/onboarding/events", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event"] == "onboarding_completed"

    def test_track_time_to_first_value(self, client):
        """Test tracking time to first value."""
        payload = {
            "event": "time_to_first_value",
            "user_id": "user-123",
            "timestamp": "2026-03-02T12:02:00Z",
            "duration_ms": 120000,
            "template_id": "blog-post",
        }
        response = client.post("/api/v2/onboarding/events", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_track_onboarding_dropoff(self, client):
        """Test tracking onboarding dropoff."""
        payload = {
            "event": "onboarding_dropoff",
            "user_id": "user-123",
            "timestamp": "2026-03-02T12:01:00Z",
            "step": "workspace_setup",
        }
        response = client.post("/api/v2/onboarding/events", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestOnboardingMetricsEndpoints:
    """Test onboarding metrics endpoints."""

    def test_get_onboarding_metrics(self, client):
        """Test getting onboarding metrics."""
        response = client.get("/api/v2/onboarding/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_started" in data
        assert "total_completed" in data
        assert "completion_rate" in data
        assert "average_time_to_first_value_ms" in data
        assert "dropoff_by_step" in data

    def test_get_onboarding_metrics_structure(self, client):
        """Test metrics response structure."""
        response = client.get("/api/v2/onboarding/metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Verify types
        assert isinstance(data["total_started"], int)
        assert isinstance(data["total_completed"], int)
        assert isinstance(data["completion_rate"], float)
        assert isinstance(data["average_time_to_first_value_ms"], (int, float))
        assert isinstance(data["dropoff_by_step"], dict)
