"""Tests for Editorial Copilot metrics."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings
from vm_webapp.observability import MetricsCollector, render_prometheus


def test_copilot_metrics_count_suggestions_by_phase(tmp_path: Path) -> None:
    """Test that copilot suggestion metrics are recorded by phase."""
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
    
    # Get suggestions for different phases
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=refine")
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=strategy")
    
    # Check metrics
    metrics = client.get("/api/v2/metrics").json()
    
    assert "copilot_suggestion_generated_total" in metrics["counts"]
    assert metrics["counts"]["copilot_suggestion_generated_total"] == 3
    
    # Phase-specific metrics
    assert metrics["counts"]["copilot_suggestion_phase:initial"] == 1
    assert metrics["counts"]["copilot_suggestion_phase:refine"] == 1
    assert metrics["counts"]["copilot_suggestion_phase:strategy"] == 1


def test_copilot_feedback_metrics_count_actions(tmp_path: Path) -> None:
    """Test that copilot feedback metrics are recorded by action type."""
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
    
    # Submit feedback with different actions
    client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb1"},
        json={"suggestion_id": "sugg-1", "phase": "initial", "action": "accepted"},
    )
    client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb2"},
        json={"suggestion_id": "sugg-2", "phase": "initial", "action": "edited", "edited_content": "x"},
    )
    client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb3"},
        json={"suggestion_id": "sugg-3", "phase": "refine", "action": "ignored"},
    )
    
    # Check metrics
    metrics = client.get("/api/v2/metrics").json()
    
    assert "copilot_feedback_submitted_total" in metrics["counts"]
    assert metrics["counts"]["copilot_feedback_submitted_total"] == 3
    
    # Action-specific metrics
    assert metrics["counts"]["copilot_feedback_action:accepted"] == 1
    assert metrics["counts"]["copilot_feedback_action:edited"] == 1
    assert metrics["counts"]["copilot_feedback_action:ignored"] == 1


def test_copilot_metrics_in_prometheus_format(tmp_path: Path) -> None:
    """Test that copilot metrics are correctly rendered in Prometheus format."""
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
    
    # Generate some copilot activity
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb"},
        json={"suggestion_id": "sugg-1", "phase": "initial", "action": "accepted"},
    )
    
    # Get Prometheus metrics
    response = client.get("/api/v2/metrics/prometheus")
    assert response.status_code == 200
    
    prom_text = response.text
    
    # Check for copilot metrics
    assert "vm_copilot_suggestion_generated_total" in prom_text
    assert "vm_copilot_suggestion_phase_initial" in prom_text
    assert "vm_copilot_feedback_submitted_total" in prom_text
    assert "vm_copilot_feedback_action_accepted" in prom_text


def test_effective_acceptance_metric_calculation(tmp_path: Path) -> None:
    """Test effective acceptance rate calculation from metrics."""
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
    
    # Generate suggestions and feedback
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    client.get(f"/api/v2/threads/{thread_id}/copilot/suggestions?phase=initial")
    
    # 2 accepted, 1 ignored (66.7% effective acceptance)
    client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb1"},
        json={"suggestion_id": "sugg-1", "phase": "initial", "action": "accepted"},
    )
    client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb2"},
        json={"suggestion_id": "sugg-2", "phase": "initial", "action": "accepted"},
    )
    client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb3"},
        json={"suggestion_id": "sugg-3", "phase": "initial", "action": "ignored"},
    )
    
    metrics = client.get("/api/v2/metrics").json()
    
    # Verify counts for effective acceptance calculation
    assert metrics["counts"]["copilot_suggestion_generated_total"] == 3
    assert metrics["counts"]["copilot_feedback_submitted_total"] == 3
    
    # Calculate effective acceptance: (accepted + edited) / total_feedback
    accepted = metrics["counts"].get("copilot_feedback_action:accepted", 0)
    edited = metrics["counts"].get("copilot_feedback_action:edited", 0)
    total_feedback = metrics["counts"].get("copilot_feedback_submitted_total", 0)
    
    if total_feedback > 0:
        effective_acceptance = (accepted + edited) / total_feedback
        assert effective_acceptance == 2 / 3  # 66.7%
