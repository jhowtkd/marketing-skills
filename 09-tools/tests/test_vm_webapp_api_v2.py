import time
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.models import ApprovalView, BrandView, ProjectView, TaskView, ThreadView
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


def seed_minimal_thread(client: TestClient) -> None:
    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "seed-b1"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "seed-p1"},
        json={"project_id": "p1", "brand_id": "b1", "name": "Plan"},
    )
    client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "seed-t1"},
        json={
            "thread_id": "t1",
            "project_id": "p1",
            "brand_id": "b1",
            "title": "Planning",
        },
    )

    with session_scope(client.app.state.engine) as session:
        session.add(TaskView(task_id="task-1", thread_id="t1", title="Draft strategy"))
        session.add(
            ApprovalView(approval_id="apr-1", thread_id="t1", status="pending")
        )


def wait_for_run_status(
    client: TestClient, run_id: str, expected: set[str], timeout_s: float = 2.0
) -> dict[str, object]:
    deadline = time.time() + timeout_s
    payload: dict[str, object] = {}
    while time.time() < deadline:
        response = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload.get("status") in expected:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach one of {sorted(expected)}")


def test_v2_collaboration_flow_comment_task_complete_and_approval(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    seed_minimal_thread(client)

    c = client.post(
        "/api/v2/tasks/task-1/comment",
        headers={"Idempotency-Key": "comment-1"},
        json={"message": "Need stronger KPI rationale"},
    )
    assert c.status_code == 200

    done = client.post(
        "/api/v2/tasks/task-1/complete",
        headers={"Idempotency-Key": "task-done-1"},
    )
    assert done.status_code == 200

    granted = client.post(
        "/api/v2/approvals/apr-1/grant-and-resume",
        headers={"Idempotency-Key": "apr-1-grant"},
    )
    assert granted.status_code == 200


def test_v2_auto_generates_hidden_ids_when_not_provided(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    created_brand = client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "auto-brand"},
        json={"name": "Acme"},
    )
    assert created_brand.status_code == 200
    brand_id = created_brand.json()["brand_id"]
    assert brand_id.startswith("b-")

    created_project = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "auto-project"},
        json={"brand_id": brand_id, "name": "Launch Q2"},
    )
    assert created_project.status_code == 200
    project_id = created_project.json()["project_id"]
    assert project_id.startswith("p-")

    created_thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "auto-thread"},
        json={"project_id": project_id, "brand_id": brand_id, "title": "Planning"},
    )
    assert created_thread.status_code == 200
    assert created_thread.json()["thread_id"].startswith("t-")


def test_v2_edit_entities_and_remove_mode(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "seed-brand"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "seed-project"},
        json={
            "project_id": "p1",
            "brand_id": "b1",
            "name": "Plan",
            "objective": "Old objective",
            "channels": ["seo"],
            "due_date": "2026-06-30",
        },
    )
    client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "seed-thread"},
        json={
            "thread_id": "t1",
            "project_id": "p1",
            "brand_id": "b1",
            "title": "Planning",
        },
    )
    client.post(
        "/api/v2/threads/t1/modes",
        headers={"Idempotency-Key": "seed-mode-1"},
        json={"mode": "plan_90d"},
    )
    client.post(
        "/api/v2/threads/t1/modes",
        headers={"Idempotency-Key": "seed-mode-2"},
        json={"mode": "content_calendar"},
    )

    edited_brand = client.patch(
        "/api/v2/brands/b1",
        headers={"Idempotency-Key": "edit-brand"},
        json={"name": "Acme Updated"},
    )
    assert edited_brand.status_code == 200

    edited_project = client.patch(
        "/api/v2/projects/p1",
        headers={"Idempotency-Key": "edit-project"},
        json={
            "name": "Plan Updated",
            "objective": "New objective",
            "channels": ["seo", "email"],
            "due_date": "2026-12-31",
        },
    )
    assert edited_project.status_code == 200

    edited_thread = client.patch(
        "/api/v2/threads/t1",
        headers={"Idempotency-Key": "edit-thread"},
        json={"title": "Planning Updated"},
    )
    assert edited_thread.status_code == 200

    removed_mode = client.post(
        "/api/v2/threads/t1/modes/plan_90d/remove",
        headers={"Idempotency-Key": "remove-mode"},
    )
    assert removed_mode.status_code == 200

    with session_scope(app.state.engine) as session:
        brand = session.get(BrandView, "b1")
        project = session.get(ProjectView, "p1")
        thread = session.get(ThreadView, "t1")
        assert brand is not None
        assert project is not None
        assert thread is not None
        assert brand.name == "Acme Updated"
        assert project.name == "Plan Updated"
        assert project.objective == "New objective"
        assert thread.title == "Planning Updated"
        assert "plan_90d" not in thread.modes_json
        assert "content_calendar" in thread.modes_json

    timeline = client.get("/api/v2/threads/t1/timeline")
    assert timeline.status_code == 200
    assert any(item["event_type"] == "ThreadModeRemoved" for item in timeline.json()["items"])


def test_v2_workflow_profiles_endpoint_lists_modes(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    profiles = client.get("/api/v2/workflow-profiles")
    assert profiles.status_code == 200
    modes = {row["mode"] for row in profiles.json()["profiles"]}
    assert "plan_90d" in modes
    assert "content_calendar" in modes


def test_v2_workflow_run_endpoints_queue_resume_and_list_artifacts(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "b"}, json={"name": "Acme"}
    )
    brands = client.get("/api/v2/brands").json()["brands"]
    brand_id = brands[0]["brand_id"]

    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "p"},
        json={"brand_id": brand_id, "name": "Launch"},
    )
    project_id = client.get("/api/v2/projects", params={"brand_id": brand_id}).json()[
        "projects"
    ][0]["project_id"]

    thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()

    started = client.post(
        f"/api/v2/threads/{thread['thread_id']}/workflow-runs",
        headers={"Idempotency-Key": "run-1"},
        json={"request_text": "Generate plan assets", "mode": "plan_90d"},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "queued"
    run_id = started.json()["run_id"]

    detail = wait_for_run_status(client, run_id, {"waiting_approval", "completed"})
    approvals = 0
    while detail["status"] == "waiting_approval":
        pending = detail["pending_approvals"]
        assert pending
        approval_id = pending[0]["approval_id"]
        granted = client.post(
            f"/api/v2/approvals/{approval_id}/grant-and-resume",
            headers={"Idempotency-Key": f"run-approval-{approvals}"},
        )
        assert granted.status_code == 200
        # Verify new response fields
        grant_body = granted.json()
        assert "run_id" in grant_body
        assert "resume_applied" in grant_body
        assert "run_status" in grant_body
        approvals += 1
        detail = wait_for_run_status(client, run_id, {"waiting_approval", "completed"})

    artifacts = client.get(f"/api/v2/workflow-runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json()["stages"]
    assert artifacts.json()["stages"][0]["artifacts"]

    listed = client.get(f"/api/v2/threads/{thread['thread_id']}/workflow-runs")
    assert listed.status_code == 200
    assert any(row["run_id"] == run_id for row in listed.json()["runs"])


def test_start_workflow_run_returns_requested_and_effective_mode(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "mode-b"}, json={"name": "Acme"}
    )
    brand_id = client.get("/api/v2/brands").json()["brands"][0]["brand_id"]

    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "mode-p"},
        json={"brand_id": brand_id, "name": "Launch"},
    )
    project_id = client.get("/api/v2/projects", params={"brand_id": brand_id}).json()[
        "projects"
    ][0]["project_id"]

    thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "mode-t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()

    started = client.post(
        f"/api/v2/threads/{thread['thread_id']}/workflow-runs",
        headers={"Idempotency-Key": "mode-run"},
        json={"request_text": "Generate plan assets", "mode": "content_calendar"},
    )
    assert started.status_code == 200
    assert started.json()["requested_mode"] == "content_calendar"
    assert started.json()["effective_mode"] == "foundation_stack"

    detail = wait_for_run_status(client, started.json()["run_id"], {"waiting_approval", "completed"})
    assert detail["requested_mode"] == "content_calendar"
    assert detail["effective_mode"] == "foundation_stack"
    assert detail["profile_version"] == "v1"
    assert detail["fallback_applied"] is True
    assert "error_code" in detail["stages"][0]
    assert "error_message" in detail["stages"][0]
    assert "retryable" in detail["stages"][0]


def test_resume_endpoint_is_idempotent_when_run_already_completed(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "idem-b"}, json={"name": "Acme"}
    )
    brand_id = client.get("/api/v2/brands").json()["brands"][0]["brand_id"]

    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "idem-p"},
        json={"brand_id": brand_id, "name": "Launch"},
    )
    project_id = client.get("/api/v2/projects", params={"brand_id": brand_id}).json()[
        "projects"
    ][0]["project_id"]

    thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "idem-t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()

    started = client.post(
        f"/api/v2/threads/{thread['thread_id']}/workflow-runs",
        headers={"Idempotency-Key": "idem-run"},
        json={"request_text": "Generate plan assets", "mode": "content_calendar"},
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    deadline = time.time() + 4.0
    approvals = 0
    while time.time() < deadline:
        detail = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert detail.status_code == 200
        payload = detail.json()
        if payload["status"] == "completed":
            break
        if payload["status"] == "waiting_approval":
            pending = payload["pending_approvals"]
            assert pending
            granted = client.post(
                f"/api/v2/approvals/{pending[0]['approval_id']}/grant-and-resume",
                headers={"Idempotency-Key": f"idem-approval-{approvals}"},
            )
            assert granted.status_code == 200
            approvals += 1
        time.sleep(0.05)
    else:
        raise AssertionError("run did not complete in time")

    # Legacy resume endpoint should now return 404
    resumed_legacy = client.post(
        f"/api/v2/workflow-runs/{run_id}/resume",
        headers={"Idempotency-Key": "idem-resume-legacy"},
    )
    assert resumed_legacy.status_code == 404


def test_v2_grant_and_resume_endpoint_returns_orchestrated_payload(tmp_path: Path) -> None:
    """Test that grant-and-resume returns complete orchestrated payload with run metadata."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Setup: brand, project, thread
    client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "gar-b"}, json={"name": "Acme"}
    )
    brand_id = client.get("/api/v2/brands").json()["brands"][0]["brand_id"]

    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "gar-p"},
        json={"brand_id": brand_id, "name": "Launch"},
    )
    project_id = client.get("/api/v2/projects", params={"brand_id": brand_id}).json()[
        "projects"
    ][0]["project_id"]

    thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "gar-t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()

    # Start a workflow run
    started = client.post(
        f"/api/v2/threads/{thread['thread_id']}/workflow-runs",
        headers={"Idempotency-Key": "gar-run"},
        json={"request_text": "Generate plan assets", "mode": "plan_90d"},
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    # Wait for waiting_approval status
    detail = wait_for_run_status(client, run_id, {"waiting_approval"})
    pending = detail["pending_approvals"]
    assert pending
    approval_id = pending[0]["approval_id"]

    # Call grant-and-resume endpoint
    response = client.post(
        f"/api/v2/approvals/{approval_id}/grant-and-resume",
        headers={"Idempotency-Key": "approval-gar-1"},
    )
    assert response.status_code == 200
    body = response.json()
    
    # Verify response structure
    assert body["approval_id"] == approval_id
    assert body["run_id"] == run_id
    assert "resume_applied" in body
    assert "run_status" in body
    assert "event_ids" in body
    assert "approval_status" in body


def test_v2_legacy_grant_and_resume_routes_are_removed(tmp_path: Path) -> None:
    """Test that legacy grant and resume endpoints return 404 or 405 (not found)."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    old_grant = client.post("/api/v2/approvals/apr-1/grant", headers={"Idempotency-Key": "x"})
    old_resume = client.post("/api/v2/workflow-runs/run-1/resume", headers={"Idempotency-Key": "y"})
    
    # Both 404 and 405 indicate the route is not available
    assert old_grant.status_code in (404, 405)
    assert old_resume.status_code in (404, 405)
