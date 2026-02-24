from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_v2_create_and_list_brand_and_project(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

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
            "objective": "Grow qualified pipeline",
            "channels": ["seo", "email"],
            "due_date": "2026-06-30",
        },
    )
    assert p.status_code == 200

    listed = client.get("/api/v2/projects", params={"brand_id": "b1"})
    assert listed.status_code == 200
    assert listed.json()["projects"][0]["project_id"] == "p1"


def test_v2_thread_lifecycle_with_modes_and_timeline(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "b1"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "p1"},
        json={"project_id": "p1", "brand_id": "b1", "name": "Plan"},
    )

    created = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "t1"},
        json={
            "thread_id": "t1",
            "project_id": "p1",
            "brand_id": "b1",
            "title": "Planning",
        },
    )
    assert created.status_code == 200

    added = client.post(
        "/api/v2/threads/t1/modes",
        headers={"Idempotency-Key": "m1"},
        json={"mode": "plan_90d"},
    )
    assert added.status_code == 200

    timeline = client.get("/api/v2/threads/t1/timeline")
    assert timeline.status_code == 200
    assert any(item["event_type"] == "ThreadModeAdded" for item in timeline.json()["items"])
