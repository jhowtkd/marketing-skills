"""Tests for v14 Segmented Copilot API endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_copilot_suggestions_include_segment_status_and_adjustment_factor(tmp_path: Path) -> None:
    """Test GET /api/v2/threads/{id}/copilot/suggestions returns segment status and adjustment."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    
    # Create brand, project, thread
    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "idem-b1"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "idem-p1"},
        json={
            "project_id": "p1",
            "brand_id": "b1",
            "name": "Launch Q2",
            "objective": "awareness",
        },
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test Thread"},
    )
    thread_id = t.json()["thread_id"]
    
    # Get suggestions with segment info
    resp = client.get(
        f"/api/v2/threads/{thread_id}/copilot/suggestions",
        params={"phase": "initial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    
    # v14: Response should include segment metadata
    assert "segment_status" in data
    assert "segment_key" in data
    assert "adjustment_factor" in data
    
    # Segment key should be brand:objective_key format
    assert data["segment_key"] == "b1:awareness"
    
    # Status should be one of the valid values
    assert data["segment_status"] in ["eligible", "insufficient_volume", "frozen", "fallback"]
    
    # Adjustment factor should be between -0.15 and +0.15
    assert -0.15 <= data["adjustment_factor"] <= 0.15


def test_segment_status_endpoint_returns_eligibility_and_metrics(tmp_path: Path) -> None:
    """Test GET /api/v2/threads/{id}/copilot/segment-status returns segment details."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    
    # Create brand, project, thread
    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "idem-b1"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "idem-p1"},
        json={
            "project_id": "p1",
            "brand_id": "b1",
            "name": "Launch Q2",
            "objective": "conversion",
        },
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test Thread"},
    )
    thread_id = t.json()["thread_id"]
    
    # Get segment status
    resp = client.get(
        f"/api/v2/threads/{thread_id}/copilot/segment-status",
    )
    assert resp.status_code == 200
    data = resp.json()
    
    # Should include segment identification
    assert data["segment_key"] == "b1:conversion"
    assert "segment_status" in data
    
    # Should include eligibility metrics
    assert "segment_runs_total" in data
    assert "segment_success_24h_rate" in data
    assert "segment_v1_score_avg" in data
    assert "segment_regen_rate" in data
    
    # Should include personalization info
    assert "adjustment_factor" in data
    assert "is_eligible" in data
    assert isinstance(data["is_eligible"], bool)


def test_segment_status_endpoint_returns_404_for_nonexistent_thread(tmp_path: Path) -> None:
    """Test that segment-status endpoint returns 404 for non-existent thread."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    
    resp = client.get("/api/v2/threads/nonexistent/copilot/segment-status")
    assert resp.status_code == 404


def test_copilot_suggestions_segment_status_is_insufficient_for_new_segment(tmp_path: Path) -> None:
    """Test that new segments (low volume) return insufficient_volume status."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    
    # Create brand, project, thread
    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "idem-b1"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "idem-p1"},
        json={
            "project_id": "p1",
            "brand_id": "b1",
            "name": "Launch Q2",
            "objective": "awareness",
        },
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test Thread"},
    )
    thread_id = t.json()["thread_id"]
    
    # Get suggestions - new segment should be insufficient_volume
    resp = client.get(
        f"/api/v2/threads/{thread_id}/copilot/suggestions",
        params={"phase": "initial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    
    # New segments have 0 runs, so should be insufficient_volume
    assert data["segment_status"] == "insufficient_volume"
    assert data["adjustment_factor"] == 0.0
    assert data["is_eligible"] is False
