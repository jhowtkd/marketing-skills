"""Tests for v14 Segmented Copilot metrics."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_copilot_segment_metrics_track_eligible_fallback_freeze(tmp_path: Path) -> None:
    """Test that v14 segment metrics track eligible, fallback, and freeze states."""
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
        json={"project_id": "p1", "brand_id": "b1", "name": "Launch"},
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test"},
    )
    thread_id = t.json()["thread_id"]
    
    # Get suggestions (new segment = insufficient volume = fallback)
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    
    # Check metrics
    metrics = client.get("/api/v2/metrics").json()
    
    # v14: Segment metrics should be tracked
    assert "copilot_segment_fallback_total" in metrics["counts"]
    assert metrics["counts"]["copilot_segment_fallback_total"] >= 1


def test_copilot_segment_adjustment_bucket_metric_is_emitted(tmp_path: Path) -> None:
    """Test that adjustment factor bucket metrics are recorded."""
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
        json={"project_id": "p1", "brand_id": "b1", "name": "Launch"},
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test"},
    )
    thread_id = t.json()["thread_id"]
    
    # Get suggestions (new segments have adjustment_factor=0, bucket="zero")
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=refine")
    
    # Check metrics
    metrics = client.get("/api/v2/metrics").json()
    
    # v14: Adjustment bucket metric should be recorded
    assert "copilot_segment_adjustment_bucket:zero" in metrics["counts"]
    assert metrics["counts"]["copilot_segment_adjustment_bucket:zero"] >= 2


def test_copilot_segment_metrics_in_prometheus_format(tmp_path: Path) -> None:
    """Test that v14 segment metrics are correctly rendered in Prometheus format."""
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
        json={"project_id": "p1", "brand_id": "b1", "name": "Launch"},
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test"},
    )
    thread_id = t.json()["thread_id"]
    
    # Get suggestions and check segment status
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    client.get(f"/api/v2/threads/{thread_id}/copilot/segment-status")
    
    # Get Prometheus metrics
    response = client.get("/api/v2/metrics/prometheus")
    assert response.status_code == 200
    
    prom_text = response.text
    
    # v14: Segment metrics should be in Prometheus format
    assert "vm_copilot_segment_fallback_total" in prom_text
    assert "vm_copilot_segment_adjustment_bucket_zero" in prom_text


def test_copilot_segment_status_endpoint_records_freeze_metric(tmp_path: Path) -> None:
    """Test that checking frozen segment status records freeze metric."""
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
        json={"project_id": "p1", "brand_id": "b1", "name": "Launch"},
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test"},
    )
    thread_id = t.json()["thread_id"]
    
    # Check segment status (new segment, not frozen)
    resp = client.get(f"/api/v2/threads/{thread_id}/copilot/segment-status")
    assert resp.status_code == 200
    data = resp.json()
    
    # New segments should not be frozen
    assert data["segment_status"] != "frozen"
    
    # Check metrics - freeze should not be recorded for non-frozen segments
    metrics = client.get("/api/v2/metrics").json()
    
    # Freeze count should be 0 or not present
    freeze_count = metrics["counts"].get("copilot_segment_freeze_total", 0)
    assert freeze_count == 0
