"""Integration tests for API v2 endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestEditorialDecisionsAPI:
    """Tests for editorial decisions v2 API."""

    def test_create_editorial_decision_returns_not_implemented(self):
        """Editorial create endpoint should return 501, not fake success."""
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v2/editorial/decisions")
        
        # Should return 501 Not Implemented, not 201 with fake data
        assert response.status_code == 501, (
            f"Expected 501 Not Implemented, got {response.status_code}. "
            f"Endpoint may be returning fake success data."
        )
        
        # Verify no placeholder data is returned
        data = response.json()
        assert data.get("detail") or "not implemented" in data.get("message", "").lower(), (
            "Response should indicate not implemented status"
        )
