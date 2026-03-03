"""Tests for API v2 metrics endpoint."""

from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_valid_payload():
    """Metrics endpoint should return valid payload without crashing."""
    from vm_webapp.app import create_app
    
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v2/metrics")
    
    # Should return 200 OK
    assert response.status_code == 200, (
        f"Expected 200 OK, got {response.status_code}. "
        f"Response: {response.text}"
    )
    
    # Verify payload structure
    data = response.json()
    assert "counts" in data, "Metrics should include 'counts' key"
    assert isinstance(data["counts"], dict), "Counts should be a dictionary"


def test_metrics_endpoint_does_not_crash_with_sqlalchemy():
    """Metrics endpoint should handle SQLAlchemy queries correctly."""
    from vm_webapp.app import create_app
    
    app = create_app()
    client = TestClient(app)
    
    # Multiple calls should not crash
    for _ in range(3):
        response = client.get("/api/v2/metrics")
        assert response.status_code == 200
        assert "counts" in response.json()
