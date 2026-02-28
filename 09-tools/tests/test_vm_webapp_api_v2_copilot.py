"""Tests for Editorial Copilot API v2 endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_copilot_suggestions_endpoint_returns_phase_payload(tmp_path: Path) -> None:
    """Test GET /api/v2/threads/{thread_id}/copilot/suggestions returns phase-based suggestions."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    
    # Create a brand and project first
    b = client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "idem-b1"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    assert b.status_code == 200
    
    p = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "idem-p1"},
        json={
            "project_id": "p1",
            "brand_id": "b1",
            "name": "Launch Q2",
            "objective": "Grow pipeline",
            "channels": ["seo"],
        },
    )
    assert p.status_code == 200
    
    # Create a thread
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test Thread"},
    )
    assert t.status_code == 200
    thread_id = t.json()["thread_id"]
    
    # Get initial phase suggestions
    resp = client.get(
        f"/api/v2/threads/{thread_id}/copilot/suggestions",
        params={"phase": "initial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    
    assert "suggestions" in data
    assert "phase" in data
    assert data["phase"] == "initial"
    assert isinstance(data["suggestions"], list)


def test_copilot_suggestions_endpoint_validates_phase_param(tmp_path: Path) -> None:
    """Test that invalid phase parameter returns 422."""
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
        },
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test Thread"},
    )
    thread_id = t.json()["thread_id"]
    
    # Invalid phase
    resp = client.get(
        f"/api/v2/threads/{thread_id}/copilot/suggestions",
        params={"phase": "invalid_phase"},
    )
    assert resp.status_code == 422


def test_copilot_feedback_endpoint_accepts_accepted_edited_ignored(tmp_path: Path) -> None:
    """Test POST /api/v2/threads/{thread_id}/copilot/feedback accepts all actions."""
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
        },
    )
    t = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t1"},
        json={"project_id": "p1", "brand_id": "b1", "title": "Test Thread"},
    )
    thread_id = t.json()["thread_id"]
    
    # Test accepted action
    resp = client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb1"},
        json={
            "suggestion_id": "sugg-123",
            "phase": "initial",
            "action": "accepted",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["feedback_id"].startswith("feedback-")
    assert data["action"] == "accepted"
    
    # Test edited action
    resp = client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb2"},
        json={
            "suggestion_id": "sugg-124",
            "phase": "refine",
            "action": "edited",
            "edited_content": "Modified suggestion text",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "edited"
    
    # Test ignored action
    resp = client.post(
        f"/api/v2/threads/{thread_id}/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb3"},
        json={
            "suggestion_id": "sugg-125",
            "phase": "strategy",
            "action": "ignored",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "ignored"


def test_copilot_suggestions_endpoint_returns_404_for_nonexistent_thread(tmp_path: Path) -> None:
    """Test that suggestions endpoint returns 404 for non-existent thread."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    
    resp = client.get(
        "/api/v2/threads/nonexistent/copilot/suggestions",
        params={"phase": "initial"},
    )
    assert resp.status_code == 404


def test_copilot_feedback_endpoint_returns_404_for_nonexistent_thread(tmp_path: Path) -> None:
    """Test that feedback endpoint returns 404 for non-existent thread."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    
    resp = client.post(
        "/api/v2/threads/nonexistent/copilot/feedback",
        headers={"Idempotency-Key": "idem-fb"},
        json={
            "suggestion_id": "sugg-123",
            "phase": "initial",
            "action": "accepted",
        },
    )
    assert resp.status_code == 404
