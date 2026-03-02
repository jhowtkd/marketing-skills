"""Tests for v31 onboarding activation API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for onboarding activation API."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from vm_webapp.api_onboarding_activation import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router, prefix="/api/v2/brands/{brand_id}/onboarding-activation")
    
    return TestClient(app)


class TestOnboardingActivationStatusEndpoint:
    """Test GET /status endpoint."""

    def test_get_status(self, client):
        """Test getting activation status for a brand."""
        response = client.get("/api/v2/brands/brand-123/onboarding-activation/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["brand_id"] == "brand-123"
        assert "metrics" in data
        assert "top_frictions" in data
        assert "active_proposals_count" in data
        assert "frozen" in data

    def test_status_includes_metrics(self, client):
        """Test that status includes onboarding metrics."""
        response = client.get("/api/v2/brands/brand-123/onboarding-activation/status")
        assert response.status_code == 200
        
        metrics = response.json()["metrics"]
        assert "completion_rate" in metrics
        assert "step_1_dropoff_rate" in metrics
        assert "template_to_first_run_conversion" in metrics


class TestOnboardingActivationRunEndpoint:
    """Test POST /run endpoint."""

    def test_run_activation(self, client):
        """Test running the activation engine."""
        response = client.post("/api/v2/brands/brand-123/onboarding-activation/run")
        assert response.status_code == 200
        
        data = response.json()
        assert data["brand_id"] == "brand-123"
        assert "proposals_generated" in data
        assert "proposals" in data

    def test_run_when_frozen(self, client):
        """Test running when proposals are frozen."""
        # First freeze
        client.post("/api/v2/brands/brand-frozen/onboarding-activation/freeze")
        
        # Then try to run
        response = client.post("/api/v2/brands/brand-frozen/onboarding-activation/run")
        assert response.status_code == 200
        
        data = response.json()
        assert data["frozen"] is True
        assert data["proposals_generated"] == 0


class TestOnboardingActivationProposalsEndpoint:
    """Test GET /proposals endpoint."""

    def test_get_proposals(self, client):
        """Test getting proposals for a brand."""
        # First generate some proposals
        client.post("/api/v2/brands/brand-456/onboarding-activation/run")
        
        response = client.get("/api/v2/brands/brand-456/onboarding-activation/proposals")
        assert response.status_code == 200
        
        data = response.json()
        assert "proposals" in data
        assert isinstance(data["proposals"], list)

    def test_get_proposals_with_status_filter(self, client):
        """Test filtering proposals by status."""
        # Generate proposals
        client.post("/api/v2/brands/brand-filter/onboarding-activation/run")
        
        response = client.get(
            "/api/v2/brands/brand-filter/onboarding-activation/proposals?status=pending"
        )
        assert response.status_code == 200
        
        proposals = response.json()["proposals"]
        for proposal in proposals:
            assert proposal["status"] == "pending"


class TestOnboardingActivationApplyEndpoint:
    """Test POST /proposals/{id}/apply endpoint."""

    def test_apply_proposal(self, client):
        """Test applying a proposal."""
        # First generate proposals
        run_response = client.post("/api/v2/brands/brand-apply/onboarding-activation/run")
        proposals = run_response.json()["proposals"]
        
        if not proposals:
            pytest.skip("No proposals generated")
        
        proposal_id = proposals[0]["id"]
        
        response = client.post(
            f"/api/v2/brands/brand-apply/onboarding-activation/proposals/{proposal_id}/apply"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["proposal_id"] == proposal_id
        assert data["status"] == "applied"


class TestOnboardingActivationRejectEndpoint:
    """Test POST /proposals/{id}/reject endpoint."""

    def test_reject_proposal(self, client):
        """Test rejecting a proposal."""
        # First generate proposals
        run_response = client.post("/api/v2/brands/brand-reject/onboarding-activation/run")
        proposals = run_response.json()["proposals"]
        
        if not proposals:
            pytest.skip("No proposals generated")
        
        proposal_id = proposals[0]["id"]
        
        response = client.post(
            f"/api/v2/brands/brand-reject/onboarding-activation/proposals/{proposal_id}/reject",
            json={"reason": "Too aggressive for current phase"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["proposal_id"] == proposal_id
        assert data["status"] == "rejected"


class TestOnboardingActivationFreezeEndpoint:
    """Test POST /freeze endpoint."""

    def test_freeze_proposals(self, client):
        """Test freezing proposals."""
        response = client.post("/api/v2/brands/brand-freeze/onboarding-activation/freeze")
        assert response.status_code == 200
        
        data = response.json()
        assert data["brand_id"] == "brand-freeze"
        assert data["frozen"] is True
        assert "frozen_at" in data


class TestOnboardingActivationRollbackEndpoint:
    """Test POST /rollback endpoint."""

    def test_rollback_last(self, client):
        """Test rolling back last applied proposal."""
        # Generate and apply a low-risk proposal
        run_response = client.post("/api/v2/brands/brand-rollback/onboarding-activation/run")
        proposals = run_response.json()["proposals"]
        
        # Find a low-risk proposal
        low_risk = [p for p in proposals if p["risk_level"] == "low"]
        if not low_risk:
            pytest.skip("No low-risk proposals to test rollback")
        
        proposal_id = low_risk[0]["id"]
        
        # Apply it
        client.post(
            f"/api/v2/brands/brand-rollback/onboarding-activation/proposals/{proposal_id}/apply"
        )
        
        # Then rollback
        response = client.post("/api/v2/brands/brand-rollback/onboarding-activation/rollback")
        assert response.status_code == 200
        
        data = response.json()
        assert data["brand_id"] == "brand-rollback"
        assert data["rolled_back"] is True
