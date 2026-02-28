"""API v2 tests for ROI Optimizer endpoints."""

import pytest
from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.roi_operations import RoiOperationsService


@pytest.fixture
def app():
    """FastAPI app fixture."""
    return create_app()


@pytest.fixture
def client(app):
    """Test client for API."""
    return TestClient(app)


@pytest.fixture
def roi_service():
    """ROI operations service."""
    return RoiOperationsService()


class TestRoiOptimizerEndpoints:
    """Test ROI optimizer API endpoints."""

    def test_status_endpoint(self, client):
        """GET /api/v2/roi/status returns optimizer status."""
        response = client.get("/api/v2/roi/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "mode" in data
        assert "cadence" in data
        assert "current_score" in data
        assert "weights" in data

    def test_proposals_list_endpoint(self, client):
        """GET /api/v2/roi/proposals returns list of proposals."""
        response = client.get("/api/v2/roi/proposals")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        for proposal in data:
            assert "id" in proposal
            assert "description" in proposal
            assert "expected_roi_delta" in proposal
            assert "risk_level" in proposal
            assert "status" in proposal

    def test_run_endpoint_creates_proposals(self, client):
        """POST /api/v2/roi/run generates new proposals."""
        # First, run the optimizer
        response = client.post(
            "/api/v2/roi/run",
            json={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "proposals" in data
        assert "score_before" in data
        assert "score_after" in data
        assert len(data["proposals"]) > 0

    def test_apply_proposal_endpoint(self, client):
        """POST /api/v2/roi/proposals/{id}/apply applies a proposal."""
        # First run to create proposals
        run_response = client.post(
            "/api/v2/roi/run",
            json={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
            }
        )
        
        proposals = run_response.json()["proposals"]
        proposal_id = proposals[0]["id"]
        
        # Apply the proposal
        response = client.post(f"/api/v2/roi/proposals/{proposal_id}/apply")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "applied"
        assert "applied_at" in data

    def test_reject_proposal_endpoint(self, client):
        """POST /api/v2/roi/proposals/{id}/reject rejects a proposal."""
        # First run to create proposals
        run_response = client.post(
            "/api/v2/roi/run",
            json={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
            }
        )
        
        proposals = run_response.json()["proposals"]
        proposal_id = proposals[0]["id"]
        
        # Reject the proposal
        response = client.post(
            f"/api/v2/roi/proposals/{proposal_id}/reject",
            json={"reason": "Test rejection"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "rejected"

    def test_rollback_endpoint(self, client):
        """POST /api/v2/roi/rollback rolls back last applied proposal."""
        # First run and apply a proposal
        run_response = client.post(
            "/api/v2/roi/run",
            json={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
            }
        )
        
        proposals = run_response.json()["proposals"]
        proposal_id = proposals[0]["id"]
        
        # Apply it
        client.post(f"/api/v2/roi/proposals/{proposal_id}/apply")
        
        # Rollback
        response = client.post("/api/v2/roi/rollback")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "rolled_back_proposal" in data
        assert data["rolled_back_proposal"]["id"] == proposal_id

    def test_run_with_incident_hard_stop(self, client):
        """POST /api/v2/roi/run blocks when incident_rate would increase."""
        response = client.post(
            "/api/v2/roi/run",
            json={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
                "projected_incident_rate": 0.02,  # Would increase
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have blocked proposals
        blocked = [p for p in data["proposals"] if p["status"] == "blocked"]
        assert len(blocked) > 0


class TestRoiOperationsService:
    """Test ROI operations service."""

    def test_service_get_status(self, roi_service):
        """Service returns optimizer status."""
        status = roi_service.get_status()
        
        assert status.mode is not None
        assert status.cadence is not None
        assert status.weights is not None

    def test_service_list_proposals(self, roi_service):
        """Service returns list of proposals."""
        # First run to create proposals
        roi_service.run_optimization(
            current_state={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
            }
        )
        
        proposals = roi_service.list_proposals()
        
        assert isinstance(proposals, list)
        assert len(proposals) > 0

    def test_service_apply_proposal(self, roi_service):
        """Service applies a proposal."""
        # Run and get proposals
        result = roi_service.run_optimization(
            current_state={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
            }
        )
        
        proposal_id = result["proposals"][0]["id"]
        
        # Apply it
        applied = roi_service.apply_proposal(proposal_id)
        
        assert applied.status == "applied"

    def test_service_rollback(self, roi_service):
        """Service rolls back last applied proposal."""
        # Run, apply, then rollback
        result = roi_service.run_optimization(
            current_state={
                "approval_without_regen_24h": 0.70,
                "revenue_attribution_usd": 100000,
                "regen_per_job": 0.5,
                "quality_score_avg": 0.80,
                "avg_latency_ms": 150,
                "cost_per_job_usd": 0.05,
                "incident_rate": 0.01,
            }
        )
        
        proposal_id = result["proposals"][0]["id"]
        roi_service.apply_proposal(proposal_id)
        
        # Rollback
        rollback_result = roi_service.rollback_last()
        
        assert rollback_result["rolled_back_proposal"]["id"] == proposal_id
