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


# DAG Ops API v2 Tests - Task 4 v22

class TestDagOpsEndpoints:
    """Test DAG Operations API endpoints."""

    def test_create_dag_run_endpoint(self, client):
        """POST /api/v2/dag/run creates a DAG run."""
        response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_001",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [
                    {"node_id": "node_a", "task_type": "research", "params": {}},
                    {"node_id": "node_b", "task_type": "write", "params": {}},
                ],
                "edges": [
                    {"from_node": "node_a", "to_node": "node_b"},
                ],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "run_id" in data
        assert data["dag_id"] == "test_dag_001"
        assert data["brand_id"] == "brand_001"
        assert data["status"] == "pending"
        assert len(data["node_states"]) == 2

    def test_get_dag_run_endpoint(self, client):
        """GET /api/v2/dag/run/{run_id} returns DAG run details."""
        # First create a run
        create_response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_002",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [
                    {"node_id": "node_a", "task_type": "research", "params": {}},
                ],
                "edges": [],
            }
        )
        
        run_id = create_response.json()["run_id"]
        
        # Get the run
        response = client.get(f"/api/v2/dag/run/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == run_id
        assert "status" in data
        assert "node_states" in data

    def test_pause_dag_run_endpoint(self, client):
        """POST /api/v2/dag/run/{run_id}/pause pauses a DAG run."""
        # Create a run
        create_response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_003",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [{"node_id": "node_a", "task_type": "research", "params": {}}],
                "edges": [],
            }
        )
        
        run_id = create_response.json()["run_id"]
        
        # Pause the run
        response = client.post(f"/api/v2/dag/run/{run_id}/pause")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "paused"
        assert data["run_id"] == run_id

    def test_resume_dag_run_endpoint(self, client):
        """POST /api/v2/dag/run/{run_id}/resume resumes a paused DAG run."""
        # Create and pause a run
        create_response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_004",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [{"node_id": "node_a", "task_type": "research", "params": {}}],
                "edges": [],
            }
        )
        
        run_id = create_response.json()["run_id"]
        client.post(f"/api/v2/dag/run/{run_id}/pause")
        
        # Resume the run
        response = client.post(f"/api/v2/dag/run/{run_id}/resume")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "running"
        assert data["run_id"] == run_id

    def test_abort_dag_run_endpoint(self, client):
        """POST /api/v2/dag/run/{run_id}/abort aborts a DAG run."""
        # Create a run
        create_response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_005",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [{"node_id": "node_a", "task_type": "research", "params": {}}],
                "edges": [],
            }
        )
        
        run_id = create_response.json()["run_id"]
        
        # Abort the run
        response = client.post(f"/api/v2/dag/run/{run_id}/abort")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "aborted"
        assert data["run_id"] == run_id

    def test_retry_node_endpoint(self, client):
        """POST /api/v2/dag/run/{run_id}/node/{node_id}/retry retries a node."""
        # Create a run
        create_response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_006",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [{"node_id": "node_a", "task_type": "research", "params": {}}],
                "edges": [],
            }
        )
        
        run_id = create_response.json()["run_id"]
        
        # Retry the node
        response = client.post(f"/api/v2/dag/run/{run_id}/node/node_a/retry")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == run_id
        assert data["node_id"] == "node_a"
        assert "status" in data

    def test_grant_dag_approval_endpoint(self, client):
        """POST /api/v2/dag/approval/{request_id}/grant grants approval."""
        # Create a run with high-risk node
        create_response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_007",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [
                    {"node_id": "critical_node", "task_type": "publish", "params": {}, "risk_level": "high"}
                ],
                "edges": [],
            }
        )
        
        run_id = create_response.json()["run_id"]
        
        # Request approval
        approval_response = client.post(
            f"/api/v2/dag/run/{run_id}/node/critical_node/approve-request"
        )
        
        request_id = approval_response.json()["request_id"]
        
        # Grant approval
        response = client.post(
            f"/api/v2/dag/approval/{request_id}/grant",
            json={"granted_by": "admin_001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "granted"
        assert data["granted_by"] == "admin_001"
        assert data["request_id"] == request_id

    def test_reject_dag_approval_endpoint(self, client):
        """POST /api/v2/dag/approval/{request_id}/reject rejects approval."""
        # Create a run
        create_response = client.post(
            "/api/v2/dag/run",
            json={
                "dag_id": "test_dag_008",
                "brand_id": "brand_001",
                "project_id": "project_001",
                "nodes": [
                    {"node_id": "risky_node", "task_type": "publish", "params": {}, "risk_level": "high"}
                ],
                "edges": [],
            }
        )
        
        run_id = create_response.json()["run_id"]
        
        # Request approval
        approval_response = client.post(
            f"/api/v2/dag/run/{run_id}/node/risky_node/approve-request"
        )
        
        request_id = approval_response.json()["request_id"]
        
        # Reject approval
        response = client.post(
            f"/api/v2/dag/approval/{request_id}/reject",
            json={"rejected_by": "admin_002", "reason": "Too risky"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "rejected"
        assert data["rejected_by"] == "admin_002"
        assert data["reason"] == "Too risky"
