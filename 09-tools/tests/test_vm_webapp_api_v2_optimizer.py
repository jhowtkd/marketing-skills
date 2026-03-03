"""Tests for API v2 optimizer endpoints."""

from fastapi.testclient import TestClient


def test_optimizer_queue_returns_not_implemented():
    """Optimizer queue endpoint should return 501 Not Implemented."""
    from vm_webapp.app import create_app
    
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v2/optimizer/queue")
    
    # Should return 501 Not Implemented
    assert response.status_code == 501, (
        f"Expected 501 Not Implemented, got {response.status_code}. "
        f"Endpoint may be returning stubbed data."
    )
    
    # Verify error message indicates not implemented
    data = response.json()
    assert "detail" in data, "Response should include detail message"
    # Accept both "not implemented" and "not yet implemented"
    assert "not" in data["detail"].lower() and "implemented" in data["detail"].lower(), (
        "Error message should indicate not implemented status"
    )


def test_optimizer_request_returns_not_implemented():
    """Optimizer request endpoint should return 501 Not Implemented."""
    from vm_webapp.app import create_app
    
    app = create_app()
    client = TestClient(app)
    
    response = client.post(
        "/api/v2/optimizer/request",
        json={
            "thread_id": "test-thread",
            "brand_id": "test-brand",
            "request_type": "workflow",
            "priority": 5,
        }
    )
    
    # Should return 501 Not Implemented
    assert response.status_code == 501, (
        f"Expected 501 Not Implemented, got {response.status_code}. "
        f"Endpoint may be returning stubbed data."
    )
    
    # Verify error message indicates not implemented
    data = response.json()
    assert "detail" in data, "Response should include detail message"
    # Accept both "not implemented" and "not yet implemented"
    assert "not" in data["detail"].lower() and "implemented" in data["detail"].lower(), (
        "Error message should indicate not implemented status"
    )
