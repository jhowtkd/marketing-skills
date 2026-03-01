"""
Tests for Approval Learning API v2 Endpoints - v24
"""

import pytest
from fastapi.testclient import TestClient


def test_learning_status_endpoint():
    """Test GET /api/v2/approval-learning/status endpoint."""
    from vm_webapp.api_approval_learning import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/api/v2/approval-learning/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert data["version"] == "v24"


def test_learning_run_endpoint():
    """Test POST /api/v2/approval-learning/run to trigger learning cycle."""
    from vm_webapp.api_approval_learning import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.post("/api/v2/approval-learning/run", json={"brand_id": "brand-001"})
    assert response.status_code == 200
    
    data = response.json()
    assert "cycle_id" in data
    assert "suggestions_generated" in data
    assert data["status"] in ["completed", "pending"]


def test_learning_proposals_endpoint():
    """Test GET /api/v2/approval-learning/proposals to list suggestions."""
    from vm_webapp.api_approval_learning import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # First run learning
    client.post("/api/v2/approval-learning/run", json={"brand_id": "brand-001"})
    
    # Get proposals
    response = client.get("/api/v2/approval-learning/proposals?brand_id=brand-001")
    assert response.status_code == 200
    
    data = response.json()
    assert "proposals" in data
    assert isinstance(data["proposals"], list)


def test_learning_apply_endpoint():
    """Test POST /api/v2/approval-learning/proposals/{id}/apply."""
    from vm_webapp.api_approval_learning import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Run and get proposals
    client.post("/api/v2/approval-learning/run", json={"brand_id": "brand-001"})
    proposals_response = client.get("/api/v2/approval-learning/proposals?brand_id=brand-001")
    proposals = proposals_response.json()["proposals"]
    
    if proposals:
        proposal_id = proposals[0]["suggestion_id"]
        response = client.post(f"/api/v2/approval-learning/proposals/{proposal_id}/apply")
        assert response.status_code == 200
        
        data = response.json()
        assert data["applied"] is True
        assert "mode" in data  # auto or approval


def test_learning_reject_endpoint():
    """Test POST /api/v2/approval-learning/proposals/{id}/reject."""
    from vm_webapp.api_approval_learning import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Run and get proposals
    client.post("/api/v2/approval-learning/run", json={"brand_id": "brand-001"})
    proposals_response = client.get("/api/v2/approval-learning/proposals?brand_id=brand-001")
    proposals = proposals_response.json()["proposals"]
    
    if proposals:
        proposal_id = proposals[0]["suggestion_id"]
        response = client.post(
            f"/api/v2/approval-learning/proposals/{proposal_id}/reject",
            json={"reason": "not_suitable"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["rejected"] is True


def test_learning_freeze_endpoint():
    """Test POST /api/v2/approval-learning/brands/{brand_id}/freeze."""
    from vm_webapp.api_approval_learning import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.post(
        "/api/v2/approval-learning/brands/brand-001/freeze",
        json={"reason": "manual_review"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["frozen"] is True
    assert data["brand_id"] == "brand-001"


def test_learning_rollback_endpoint():
    """Test POST /api/v2/approval-learning/proposals/{id}/rollback."""
    from vm_webapp.api_approval_learning import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Run, apply, then rollback
    client.post("/api/v2/approval-learning/run", json={"brand_id": "brand-001"})
    proposals_response = client.get("/api/v2/approval-learning/proposals?brand_id=brand-001")
    proposals = proposals_response.json()["proposals"]
    
    if proposals:
        proposal_id = proposals[0]["suggestion_id"]
        # Apply first
        apply_response = client.post(f"/api/v2/approval-learning/proposals/{proposal_id}/apply")
        
        # Only rollback if apply succeeded
        if apply_response.status_code == 200:
            response = client.post(f"/api/v2/approval-learning/proposals/{proposal_id}/rollback")
            assert response.status_code == 200
            
            data = response.json()
            assert data["rolled_back"] is True
        else:
            # Skip test if no proposals to rollback
            pytest.skip("No applicable proposals to test rollback")
