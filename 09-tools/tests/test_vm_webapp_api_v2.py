"""API v2 tests for Quality Optimizer endpoints (v25)."""

import pytest
from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.quality_optimizer import QualityOptimizer, ProposalState


@pytest.fixture
def app():
    """FastAPI app fixture."""
    return create_app(enable_in_process_worker=False)


@pytest.fixture
def client(app):
    """Test client for API."""
    return TestClient(app)


@pytest.fixture
def sample_run_data():
    """Sample run data for testing."""
    return {
        "run_id": "run-001",
        "brand_id": "brand-001",
        "quality_score": 65.0,
        "v1_score": 60.0,
        "cost_per_job": 100.0,
        "mttc": 300.0,
        "incident_rate": 0.05,
        "approval_without_regen_24h": 0.70,
        "params": {
            "temperature": 0.7,
            "max_tokens": 2000,
            "model": "gpt-4",
        },
    }


class TestOptimizerStatusEndpoint:
    """Test GET /v2/optimizer/status."""

    def test_get_optimizer_status(self, client):
        """Should return optimizer version and stats."""
        response = client.get("/v2/optimizer/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["version"] == "v25"
        assert "total_proposals" in data
        assert "proposals_by_state" in data


class TestOptimizerRunEndpoint:
    """Test POST /v2/optimizer/run."""

    def test_run_optimizer_creates_proposal(self, client, sample_run_data):
        """Should create and return a proposal."""
        response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
                "constraints": {
                    "max_cost_increase_pct": 10.0,
                    "max_mttc_increase_pct": 10.0,
                    "max_incident_rate": 0.05,
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "proposal_id" in data
        assert data["run_id"] == "run-001"
        assert data["state"] == "pending"
        assert "recommended_params" in data
        assert "feasibility_check_passed" in data
        assert "estimated_v1_improvement" in data
        assert "estimated_cost_delta_pct" in data
        assert "estimated_mttc_delta_pct" in data

    def test_run_optimizer_with_constraints(self, client, sample_run_data):
        """Should respect custom constraints."""
        response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
                "constraints": {
                    "max_cost_increase_pct": 5.0,
                    "max_mttc_increase_pct": 5.0,
                    "max_incident_rate": 0.03,
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # With strict constraints, may not be feasible
        assert "proposal_id" in data


class TestGetProposalEndpoint:
    """Test GET /v2/optimizer/proposals/{proposal_id}."""

    def test_get_proposal(self, client, sample_run_data):
        """Should return proposal details."""
        # First create a proposal
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Get the proposal
        response = client.get(f"/v2/optimizer/proposals/{proposal_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["proposal_id"] == proposal_id
        assert data["state"] == "pending"
        assert "feasibility_check_passed" in data
        assert "quality_score" in data

    def test_get_proposal_not_found(self, client):
        """Should return 404 for unknown proposal."""
        response = client.get("/v2/optimizer/proposals/nonexistent-id")
        
        assert response.status_code == 404


class TestGetRunProposalsEndpoint:
    """Test GET /v2/optimizer/runs/{run_id}/proposals."""

    def test_get_run_proposals(self, client, sample_run_data):
        """Should return all proposals for a run."""
        # Create a proposal first
        client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        
        response = client.get("/v2/optimizer/runs/run-001/proposals")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "run-001"
        assert "proposal_count" in data
        assert "proposals" in data


class TestApplyProposalEndpoint:
    """Test POST /v2/optimizer/proposals/{proposal_id}/apply."""

    def test_apply_proposal(self, client, sample_run_data):
        """Should apply a pending proposal."""
        # Create a proposal first
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Apply the proposal
        response = client.post(f"/v2/optimizer/proposals/{proposal_id}/apply")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "applied"
        assert data["proposal_id"] == proposal_id
        assert "applied_at" in data

    def test_apply_proposal_not_found(self, client):
        """Should return 404 for unknown proposal."""
        response = client.post("/v2/optimizer/proposals/nonexistent-id/apply")
        
        assert response.status_code == 404

    def test_apply_blocked_if_infeasible(self, client, sample_run_data):
        """Should block apply if not feasible and enforce_feasibility=True."""
        # Create run with high tokens that will exceed strict constraints
        high_cost_run = {
            **sample_run_data,
            "params": {"temperature": 0.7, "max_tokens": 10000, "model": "gpt-4"},
        }
        
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": high_cost_run,
                "historical_runs": [],
                "constraints": {
                    "max_cost_increase_pct": 5.0,  # Very strict
                },
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Try to apply with enforce_feasibility (default)
        response = client.post(
            f"/v2/optimizer/proposals/{proposal_id}/apply",
            json={"enforce_feasibility": True},
        )
        
        assert response.status_code == 409

    def test_apply_allowed_with_override(self, client, sample_run_data):
        """Should allow apply with enforce_feasibility=False."""
        # Create run with high tokens
        high_cost_run = {
            **sample_run_data,
            "params": {"temperature": 0.7, "max_tokens": 10000, "model": "gpt-4"},
        }
        
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": high_cost_run,
                "historical_runs": [],
                "constraints": {
                    "max_cost_increase_pct": 5.0,
                },
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Apply with override
        response = client.post(
            f"/v2/optimizer/proposals/{proposal_id}/apply",
            json={"enforce_feasibility": False},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "applied"


class TestRejectProposalEndpoint:
    """Test POST /v2/optimizer/proposals/{proposal_id}/reject."""

    def test_reject_proposal(self, client, sample_run_data):
        """Should reject a pending proposal."""
        # Create a proposal first
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Reject the proposal
        response = client.post(f"/v2/optimizer/proposals/{proposal_id}/reject")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "rejected"
        assert data["proposal_id"] == proposal_id


class TestFreezeProposalEndpoint:
    """Test POST /v2/optimizer/proposals/{proposal_id}/freeze."""

    def test_freeze_proposal(self, client, sample_run_data):
        """Should freeze a pending proposal."""
        # Create a proposal first
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Freeze the proposal
        response = client.post(f"/v2/optimizer/proposals/{proposal_id}/freeze")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "frozen"
        assert data["proposal_id"] == proposal_id

    def test_cannot_apply_frozen(self, client, sample_run_data):
        """Cannot apply a frozen proposal."""
        # Create and freeze a proposal
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        client.post(f"/v2/optimizer/proposals/{proposal_id}/freeze")
        
        # Try to apply
        response = client.post(f"/v2/optimizer/proposals/{proposal_id}/apply")
        
        assert response.status_code == 409


class TestRollbackProposalEndpoint:
    """Test POST /v2/optimizer/proposals/{proposal_id}/rollback."""

    def test_rollback_proposal(self, client, sample_run_data):
        """Should rollback an applied proposal."""
        # Create and apply a proposal
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        client.post(f"/v2/optimizer/proposals/{proposal_id}/apply")
        
        # Rollback
        response = client.post(f"/v2/optimizer/proposals/{proposal_id}/rollback")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "rolled_back"
        assert data["proposal_id"] == proposal_id

    def test_cannot_rollback_without_apply(self, client, sample_run_data):
        """Cannot rollback without prior apply."""
        # Create a proposal but don't apply
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Try to rollback
        response = client.post(f"/v2/optimizer/proposals/{proposal_id}/rollback")
        
        assert response.status_code == 409


class TestProposalSnapshotEndpoint:
    """Test GET /v2/optimizer/proposals/{proposal_id}/snapshot."""

    def test_get_snapshot(self, client, sample_run_data):
        """Should return snapshot for applied proposal."""
        # Create and apply a proposal
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        client.post(f"/v2/optimizer/proposals/{proposal_id}/apply")
        
        # Get snapshot
        response = client.get(f"/v2/optimizer/proposals/{proposal_id}/snapshot")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["proposal_id"] == proposal_id
        assert "previous_params" in data
        assert "applied_params" in data
        assert "applied_at" in data

    def test_snapshot_not_found_for_pending(self, client, sample_run_data):
        """Should return 404 for pending proposal."""
        # Create but don't apply
        create_response = client.post(
            "/v2/optimizer/run",
            json={
                "current_run": sample_run_data,
                "historical_runs": [],
            },
        )
        proposal_id = create_response.json()["proposal_id"]
        
        # Try to get snapshot
        response = client.get(f"/v2/optimizer/proposals/{proposal_id}/snapshot")
        
        assert response.status_code == 404
