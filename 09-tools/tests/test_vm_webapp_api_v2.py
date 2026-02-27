import json
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.models import ApprovalView, BrandView, ProjectView, TaskView, ThreadView
from vm_webapp.settings import Settings
from vm_webapp.workflow_runtime_v2 import FoundationStageResult


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
        "/api/v2/approvals/apr-1/grant",
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
            f"/api/v2/approvals/{approval_id}/grant",
            headers={"Idempotency-Key": f"run-approval-{approvals}"},
        )
        assert granted.status_code == 200
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
                f"/api/v2/approvals/{pending[0]['approval_id']}/grant",
                headers={"Idempotency-Key": f"idem-approval-{approvals}"},
            )
            assert granted.status_code == 200
            approvals += 1
        time.sleep(0.05)
    else:
        raise AssertionError("run did not complete in time")

    resumed_1 = client.post(
        f"/api/v2/workflow-runs/{run_id}/resume",
        headers={"Idempotency-Key": "idem-resume-1"},
    )
    resumed_2 = client.post(
        f"/api/v2/workflow-runs/{run_id}/resume",
        headers={"Idempotency-Key": "idem-resume-2"},
    )

    assert resumed_1.status_code == 200
    assert resumed_2.status_code == 200
    assert resumed_1.json()["status"] == "completed"
    assert resumed_2.json()["status"] == "completed"


def test_api_approval_cycle_moves_to_next_gate_without_failed_run(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "cycle-b"}, json={"name": "Acme"}
    ).json()["brand_id"]
    project_id = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "cycle-p"},
        json={"brand_id": brand_id, "name": "Launch"},
    ).json()["project_id"]
    thread_id = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "cycle-t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()["thread_id"]

    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "cycle-run"},
        json={"request_text": "Generate plan assets", "mode": "content_calendar"},
    ).json()["run_id"]

    detail = wait_for_run_status(client, run_id, {"waiting_approval", "completed"})
    assert detail["status"] == "waiting_approval"
    pending = detail["pending_approvals"]
    assert pending
    approval_id = pending[0]["approval_id"]

    runtime = client.app.state.workflow_runtime
    execute_calls = {"count": 0}

    def _reentrant_execute_stage(**kwargs):
        execute_calls["count"] += 1
        if execute_calls["count"] == 1:
            with session_scope(client.app.state.engine) as nested_session:
                runtime.process_event(
                    session=nested_session,
                    event_type="WorkflowRunResumed",
                    payload={
                        "thread_id": thread_id,
                        "brand_id": brand_id,
                        "project_id": project_id,
                        "run_id": run_id,
                        "request_text": "Generate plan assets",
                    },
                    actor_id="agent:vm-workflow",
                    causation_id="evt-api-reentrant",
                    correlation_id="evt-api-reentrant",
                )
            return FoundationStageResult(
                stage_key=str(kwargs["stage_key"]),
                pipeline_status="waiting_approval",
                output_payload={"summary": "ok", "mode": "foundation_stack"},
                artifacts={"strategy/brand-voice-guide.md": "# Brand voice"},
            )

        return FoundationStageResult(
            stage_key=str(kwargs["stage_key"]),
            pipeline_status="failed",
            output_payload={},
            artifacts={},
            error_code="foundation_execution_error",
            error_message="Stage brand-voice cannot be approved while current_stage is positioning",
            retryable=False,
        )

    runtime.foundation_runner.execute_stage = _reentrant_execute_stage

    granted = client.post(
        f"/api/v2/approvals/{approval_id}/grant",
        headers={"Idempotency-Key": "cycle-grant"},
    )
    assert granted.status_code == 200

    final = wait_for_run_status(client, run_id, {"waiting_approval", "completed", "failed"})
    assert final["status"] in {"waiting_approval", "completed"}
    assert all(stage["error_code"] is None for stage in final["stages"])


def test_resume_recovers_waiting_gate_when_run_is_running_and_approval_missing(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "recover-b"},
        json={"name": "Acme"},
    ).json()["brand_id"]
    project_id = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "recover-p"},
        json={"brand_id": brand_id, "name": "Launch"},
    ).json()["project_id"]
    thread_id = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "recover-t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()["thread_id"]

    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "recover-run"},
        json={"request_text": "Generate plan assets", "mode": "content_calendar"},
    ).json()["run_id"]

    detail = wait_for_run_status(client, run_id, {"waiting_approval", "completed"})
    assert detail["status"] == "waiting_approval"
    approval_id = detail["pending_approvals"][0]["approval_id"]

    with session_scope(client.app.state.engine) as session:
        session.execute(delete(ApprovalView).where(ApprovalView.approval_id == approval_id))
        session.execute(delete(ApprovalView).where(ApprovalView.reason.like(f"workflow_gate:{run_id}:%")))
        session.commit()

    with session_scope(client.app.state.engine) as session:
        runtime = client.app.state.workflow_runtime
        run = runtime.execute_queued_run(
            session=session,
            run_id=run_id,
            actor_id="agent:vm-workflow",
            causation_id="evt-recover",
            correlation_id="evt-recover",
            trigger_event_type="WorkflowRunResumed",
        )
        assert run["status"] == "waiting_approval"

    refreshed = client.get(f"/api/v2/workflow-runs/{run_id}")
    assert refreshed.status_code == 200
    payload = refreshed.json()
    assert payload["status"] == "waiting_approval"
    assert payload["pending_approvals"]


def test_grant_unknown_approval_returns_404(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    response = client.post(
        "/api/v2/approvals/apr-missing/grant",
        headers={"Idempotency-Key": "idem-missing-apr"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "approval not found: apr-missing"


def test_list_workflow_runs_exposes_requested_and_effective_modes(tmp_path: Path) -> None:
    """Contract test: list workflow runs must expose request_text, requested_mode, effective_mode.
    
    This test prevents regression of the run binding bug where the frontend
    needs these fields to correctly display run context.
    """
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Setup: create brand, project, thread
    client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "list-b"}, json={"name": "Acme"}
    )
    brand_id = client.get("/api/v2/brands").json()["brands"][0]["brand_id"]

    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "list-p"},
        json={"brand_id": brand_id, "name": "Launch"},
    )
    project_id = client.get("/api/v2/projects", params={"brand_id": brand_id}).json()[
        "projects"
    ][0]["project_id"]

    thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "list-t"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()
    thread_id = thread["thread_id"]

    # Start a workflow run with specific mode
    started = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "list-run"},
        json={"request_text": "Generate quarterly marketing plan", "mode": "content_calendar"},
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    # Call list workflow runs endpoint
    listed = client.get(f"/api/v2/threads/{thread_id}/workflow-runs")
    assert listed.status_code == 200
    
    runs = listed.json()["runs"]
    assert len(runs) >= 1
    
    # Find our run in the list
    run = next((r for r in runs if r["run_id"] == run_id), None)
    assert run is not None, f"Run {run_id} not found in list"
    
    # Contract assertions - these fields are required by the frontend for run binding
    assert "request_text" in run, "request_text field missing from run list item"
    assert run["request_text"] == "Generate quarterly marketing plan", "request_text mismatch"
    
    assert "requested_mode" in run, "requested_mode field missing from run list item"
    assert run["requested_mode"] == "content_calendar", "requested_mode mismatch"
    
    assert "effective_mode" in run, "effective_mode field missing from run list item"
    assert run["effective_mode"] == "foundation_stack", "effective_mode mismatch"


# Task 4: Editorial Decisions Endpoints

def test_editorial_decisions_endpoints_mark_and_list(tmp_path: Path) -> None:
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    # seed brand/project/thread/run
    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "ed-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "ed-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "ed-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "ed-run"}, json={"request_text": "Campanha Lancamento", "mode": "content_calendar"}).json()["run_id"]

    marked = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "ed-mark-1", "X-User-Id": "admin-test", "X-User-Role": "admin"},
        json={"run_id": run_id, "scope": "global", "justification": "melhor equilibrio editorial"},
    )
    assert marked.status_code == 200

    listed = client.get(f"/api/v2/threads/{thread_id}/editorial-decisions")
    assert listed.status_code == 200
    assert listed.json()["global"]["run_id"] == run_id


def test_editorial_golden_validates_justification_empty(tmp_path: Path) -> None:
    """422 para justification vazia"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "val-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "val-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "val-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "val-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "val-mark-empty", "X-User-Id": "admin-test", "X-User-Role": "admin"},
        json={"run_id": run_id, "scope": "global", "justification": ""},
    )
    assert resp.status_code == 422


def test_editorial_golden_validates_scope_objective_without_key(tmp_path: Path) -> None:
    """422 para scope=objective sem objective_key"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "val2-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "val2-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "val2-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "val2-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "val-mark-obj", "X-User-Id": "admin-test", "X-User-Role": "admin"},
        json={"run_id": run_id, "scope": "objective", "justification": "bom resultado"},
    )
    assert resp.status_code == 422


def test_editorial_golden_returns_404_for_run_outside_thread(tmp_path: Path) -> None:
    """404 para run_id que nao pertence ao thread"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "404-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "404-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread1_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "404-t1"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Thread 1"}).json()["thread_id"]
    thread2_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "404-t2"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Thread 2"}).json()["thread_id"]
    
    # Create run in thread2
    run_id = client.post(f"/api/v2/threads/{thread2_id}/workflow-runs", headers={"Idempotency-Key": "404-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Try to mark golden in thread1 with run from thread2 (admin should get 404, not 403)
    resp = client.post(
        f"/api/v2/threads/{thread1_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "404-mark", "X-User-Id": "admin-test", "X-User-Role": "admin"},
        json={"run_id": run_id, "scope": "global", "justification": "nao deve funcionar"},
    )
    assert resp.status_code == 404


# Task 5: Objective Key and Baseline Endpoint

def test_workflow_run_includes_objective_key_in_list_and_detail(tmp_path: Path) -> None:
    """Contrato aditivo: objective_key presente em list e detail de runs"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "obj-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "obj-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "obj-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "obj-run"}, json={"request_text": "Campanha Lancamento", "mode": "content_calendar"}).json()["run_id"]

    # Check list endpoint includes objective_key
    listed = client.get(f"/api/v2/threads/{thread_id}/workflow-runs")
    assert listed.status_code == 200
    runs = listed.json()["runs"]
    run = next((r for r in runs if r["run_id"] == run_id), None)
    assert run is not None
    assert "objective_key" in run, "objective_key missing in list endpoint"
    assert run["objective_key"] != "", "objective_key should not be empty"

    # Check detail endpoint includes objective_key
    detail = client.get(f"/api/v2/workflow-runs/{run_id}")
    assert detail.status_code == 200
    assert "objective_key" in detail.json(), "objective_key missing in detail endpoint"
    assert detail.json()["objective_key"] != "", "objective_key should not be empty"


def test_workflow_run_baseline_endpoint_respects_priority(tmp_path: Path) -> None:
    """Baseline respeita prioridade: objective > global > previous. Nunca retorna a propria run."""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "base-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "base-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "base-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    
    # Create 3 runs with same objective
    run1_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "base-run1"}, json={"request_text": "Campanha Lancamento", "mode": "content_calendar"}).json()["run_id"]
    run2_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "base-run2"}, json={"request_text": "Campanha Lancamento", "mode": "content_calendar"}).json()["run_id"]
    run3_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "base-run3"}, json={"request_text": "Campanha Lancamento", "mode": "content_calendar"}).json()["run_id"]

    # Get objective_key from one of the runs
    detail = client.get(f"/api/v2/workflow-runs/{run1_id}")
    objective_key = detail.json()["objective_key"]

    # Mark run1 as global golden (need admin)
    client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "base-mark-global", "X-User-Id": "admin-test", "X-User-Role": "admin"},
        json={"run_id": run1_id, "scope": "global", "justification": "melhor run global"},
    )

    # Mark run2 as objective golden (same objective as run3) - editor can do objective
    client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "base-mark-obj", "X-User-Id": "editor-test", "X-User-Role": "editor"},
        json={"run_id": run2_id, "scope": "objective", "objective_key": objective_key, "justification": "melhor run objetivo"},
    )

    # Check baseline for run3 - should be run2 (objective_golden has priority)
    baseline = client.get(f"/api/v2/workflow-runs/{run3_id}/baseline")
    assert baseline.status_code == 200
    baseline_data = baseline.json()
    assert baseline_data["baseline_run_id"] == run2_id, "Expected objective_golden to win"
    assert baseline_data["source"] == "objective_golden"
    assert baseline_data["objective_key"] == objective_key

    # Check baseline for run2 - should be run1 (global_golden, cannot be itself)
    baseline2 = client.get(f"/api/v2/workflow-runs/{run2_id}/baseline")
    assert baseline2.status_code == 200
    baseline2_data = baseline2.json()
    assert baseline2_data["baseline_run_id"] == run1_id, "Expected global_golden"
    assert baseline2_data["source"] == "global_golden"

    # Check baseline for run1 - should be run2 (objective_golden, same objective as run3)
    # run1 cannot be baseline for itself, but run2 (objective_golden) is valid
    baseline1 = client.get(f"/api/v2/workflow-runs/{run1_id}/baseline")
    assert baseline1.status_code == 200
    baseline1_data = baseline1.json()
    assert baseline1_data["baseline_run_id"] == run2_id, "Expected objective_golden for run1"
    assert baseline1_data["source"] == "objective_golden"


def test_baseline_endpoint_returns_404_for_unknown_run(tmp_path: Path) -> None:
    """404 para run_id inexistente no endpoint de baseline"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    resp = client.get("/api/v2/workflow-runs/run-inexistente/baseline")
    assert resp.status_code == 404


# Observability metrics for editorial decisions

def test_editorial_golden_increments_metrics(tmp_path: Path) -> None:
    """Marcar golden deve incrementar metricas editorial_golden_marked_total e editorial_golden_marked_scope"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "met-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "met-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "met-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "met-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Get initial metrics
    metrics_before = app.state.workflow_runtime.metrics.snapshot()
    golden_total_before = metrics_before.get("counts", {}).get("editorial_golden_marked_total", 0)
    golden_scope_before = metrics_before.get("counts", {}).get("editorial_golden_marked_scope:global", 0)

    # Mark as golden (need admin for global)
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "met-mark", "X-User-Id": "admin-test", "X-User-Role": "admin"},
        json={"run_id": run_id, "scope": "global", "justification": "metric test"},
    )
    assert resp.status_code == 200

    # Verify metrics incremented
    metrics_after = app.state.workflow_runtime.metrics.snapshot()
    golden_total_after = metrics_after.get("counts", {}).get("editorial_golden_marked_total", 0)
    golden_scope_after = metrics_after.get("counts", {}).get("editorial_golden_marked_scope:global", 0)

    assert golden_total_after == golden_total_before + 1, "editorial_golden_marked_total should increment"
    assert golden_scope_after == golden_scope_before + 1, "editorial_golden_marked_scope:global should increment"


def test_editorial_baseline_increments_metrics_with_correct_source(tmp_path: Path) -> None:
    """Baseline deve incrementar editorial_baseline_resolved_total e editorial_baseline_source com source correto"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "met2-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "met2-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "met2-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run1_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "met2-run1"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]
    run2_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "met2-run2"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Get initial metrics
    metrics_before = app.state.workflow_runtime.metrics.snapshot()
    baseline_total_before = metrics_before.get("counts", {}).get("editorial_baseline_resolved_total", 0)
    baseline_source_before = metrics_before.get("counts", {}).get("editorial_baseline_source:previous", 0)

    # Get baseline for run2 (should be previous)
    resp = client.get(f"/api/v2/workflow-runs/{run2_id}/baseline")
    assert resp.status_code == 200
    assert resp.json()["source"] == "previous"

    # Verify metrics incremented
    metrics_after = app.state.workflow_runtime.metrics.snapshot()
    baseline_total_after = metrics_after.get("counts", {}).get("editorial_baseline_resolved_total", 0)
    baseline_source_after = metrics_after.get("counts", {}).get("editorial_baseline_source:previous", 0)

    assert baseline_total_after == baseline_total_before + 1, "editorial_baseline_resolved_total should increment"
    assert baseline_source_after == baseline_source_before + 1, "editorial_baseline_source:previous should increment"


def test_editorial_decisions_list_increments_metrics(tmp_path: Path) -> None:
    """Listar decisoes editoriais deve incrementar metrica editorial_decisions_list_total"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "met3-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "met3-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "met3-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]

    # Get initial metrics
    metrics_before = app.state.workflow_runtime.metrics.snapshot()
    list_total_before = metrics_before.get("counts", {}).get("editorial_decisions_list_total", 0)

    # List editorial decisions
    resp = client.get(f"/api/v2/threads/{thread_id}/editorial-decisions")
    assert resp.status_code == 200

    # Verify metrics incremented
    metrics_after = app.state.workflow_runtime.metrics.snapshot()
    list_total_after = metrics_after.get("counts", {}).get("editorial_decisions_list_total", 0)

    assert list_total_after == list_total_before + 1, "editorial_decisions_list_total should increment"


# Bloco A: RBAC - Role-based authorization for editorial golden

def test_editorial_golden_requires_editor_or_admin_role(tmp_path: Path) -> None:
    """Apenas roles editor (objective) e admin (global/objective) podem marcar golden; viewer recebe 403"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "rbac-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "rbac-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "rbac-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "rbac-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Viewer should get 403
    resp_viewer = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "rbac-viewer", "X-User-Role": "viewer"},
        json={"run_id": run_id, "scope": "global", "justification": "test"},
    )
    assert resp_viewer.status_code == 403, "viewer should not be allowed to mark golden"

    # Editor should succeed with objective scope
    resp_editor = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "rbac-editor", "X-User-Role": "editor"},
        json={"run_id": run_id, "scope": "objective", "objective_key": "obj-rbac", "justification": "test"},
    )
    assert resp_editor.status_code == 200, "editor should be allowed to mark objective golden"

    # Admin should succeed with global scope
    run2_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "rbac-run2"}, json={"request_text": "Campanha 2", "mode": "content_calendar"}).json()["run_id"]
    resp_admin = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "rbac-admin", "X-User-Role": "admin"},
        json={"run_id": run2_id, "scope": "global", "justification": "test"},
    )
    assert resp_admin.status_code == 200, "admin should be allowed to mark global golden"


def test_editorial_golden_fallback_role_to_editor(tmp_path: Path) -> None:
    """Sem header X-User-Role, deve fallback para editor (permitido para objective)"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "rbac-fb-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "rbac-fb-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "rbac-fb-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "rbac-fb-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # No X-User-Role header - should fallback to editor (editor can only do objective)
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "rbac-fb-mark"},
        json={"run_id": run_id, "scope": "objective", "objective_key": "obj-fallback", "justification": "test fallback"},
    )
    assert resp.status_code == 200, "fallback to editor role should succeed for objective scope"


# Bloco C: Hardening baseline-none

def test_baseline_none_contract_when_no_baseline_available(tmp_path: Path) -> None:
    """Contrato para source=none quando nao ha baseline disponivel (unica run no thread)"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "none-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "none-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "none-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "none-run"}, json={"request_text": "Campanha unica", "mode": "content_calendar"}).json()["run_id"]

    # Get baseline for single run - should be none
    resp = client.get(f"/api/v2/workflow-runs/{run_id}/baseline")
    assert resp.status_code == 200
    baseline_data = resp.json()
    
    assert baseline_data["run_id"] == run_id
    assert baseline_data["baseline_run_id"] is None, "baseline_run_id should be null when no baseline available"
    assert baseline_data["source"] == "none", "source should be 'none' when no baseline available"
    assert "objective_key" in baseline_data


def test_baseline_none_increments_metrics(tmp_path: Path) -> None:
    """Baseline source=none deve incrementar metrica editorial_baseline_source:none"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "none-met-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "none-met-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "none-met-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "none-met-run"}, json={"request_text": "Campanha unica", "mode": "content_calendar"}).json()["run_id"]

    # Get initial metrics
    metrics_before = app.state.workflow_runtime.metrics.snapshot()
    baseline_total_before = metrics_before.get("counts", {}).get("editorial_baseline_resolved_total", 0)
    baseline_none_before = metrics_before.get("counts", {}).get("editorial_baseline_source:none", 0)

    # Get baseline (should be none)
    resp = client.get(f"/api/v2/workflow-runs/{run_id}/baseline")
    assert resp.status_code == 200
    assert resp.json()["source"] == "none"

    # Verify metrics incremented
    metrics_after = app.state.workflow_runtime.metrics.snapshot()
    baseline_total_after = metrics_after.get("counts", {}).get("editorial_baseline_resolved_total", 0)
    baseline_none_after = metrics_after.get("counts", {}).get("editorial_baseline_source:none", 0)

    assert baseline_total_after == baseline_total_before + 1, "editorial_baseline_resolved_total should increment"
    assert baseline_none_after == baseline_none_before + 1, "editorial_baseline_source:none should increment"


# TASK A: Auditoria forte (identidade real no backend)

def test_editorial_golden_uses_actor_id_from_header(tmp_path: Path) -> None:
    """Deve usar X-User-Id como actor_id no evento EditorialGoldenMarked"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "actor-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "actor-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "actor-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "actor-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Mark golden with specific user id
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "actor-mark", "X-User-Id": "user-john-doe", "X-User-Role": "editor"},
        json={"run_id": run_id, "scope": "objective", "objective_key": "obj-123", "justification": "test actor"},
    )
    assert resp.status_code == 200

    # Verify event was created with correct actor
    with session_scope(app.state.engine) as session:
        from vm_webapp.repo import list_timeline_items_view
        timeline_items = list_timeline_items_view(session, thread_id=thread_id)
        golden_events = [item for item in timeline_items if item.event_type == "EditorialGoldenMarked"]
        assert len(golden_events) == 1
        event = golden_events[0]
        assert event.actor_id == "user-john-doe", f"Expected actor_id='user-john-doe', got '{event.actor_id}'"
        
        # Verify payload contains actor_role
        payload = json.loads(event.payload_json)
        assert payload.get("actor_role") == "editor", f"Expected actor_role='editor', got '{payload.get('actor_role')}'"


def test_editorial_golden_uses_fallback_actor_when_header_missing(tmp_path: Path) -> None:
    """Deve fallback para workspace-owner quando X-User-Id nao presente"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "actor-fb-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "actor-fb-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "actor-fb-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "actor-fb-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Mark golden without user id header (fallback) - editor can only do objective
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "actor-fb-mark"},  # No X-User-Id, No X-User-Role
        json={"run_id": run_id, "scope": "objective", "objective_key": "obj-fb", "justification": "test fallback actor"},
    )
    assert resp.status_code == 200

    # Verify event was created with fallback actor
    with session_scope(app.state.engine) as session:
        from vm_webapp.repo import list_timeline_items_view
        timeline_items = list_timeline_items_view(session, thread_id=thread_id)
        golden_events = [item for item in timeline_items if item.event_type == "EditorialGoldenMarked"]
        assert len(golden_events) == 1
        event = golden_events[0]
        assert event.actor_id == "workspace-owner", f"Expected actor_id='workspace-owner', got '{event.actor_id}'"
        
        # Verify payload contains fallback actor_role (editor)
        payload = json.loads(event.payload_json)
        assert payload.get("actor_role") == "editor", f"Expected actor_role='editor', got '{payload.get('actor_role')}'"


# TASK B: Policy por escopo (global vs objective)

def test_editorial_golden_policy_editor_cannot_global_scope(tmp_path: Path) -> None:
    """Editor nao pode marcar golden global (apenas objective)"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "policy-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "policy-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "policy-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "policy-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Editor + global => 403
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "policy-editor-global", "X-User-Id": "editor-1", "X-User-Role": "editor"},
        json={"run_id": run_id, "scope": "global", "justification": "tentativa global"},
    )
    assert resp.status_code == 403, "editor should not be allowed to mark global golden"


def test_editorial_golden_policy_editor_can_objective_scope(tmp_path: Path) -> None:
    """Editor pode marcar golden objective"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "policy2-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "policy2-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "policy2-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "policy2-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Editor + objective => 200
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "policy-editor-obj", "X-User-Id": "editor-2", "X-User-Role": "editor"},
        json={"run_id": run_id, "scope": "objective", "objective_key": "obj-123", "justification": "objective ok"},
    )
    assert resp.status_code == 200, "editor should be allowed to mark objective golden"


def test_editorial_golden_policy_admin_can_global_scope(tmp_path: Path) -> None:
    """Admin pode marcar golden global"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "policy3-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "policy3-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "policy3-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "policy3-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Admin + global => 200
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "policy-admin-global", "X-User-Id": "admin-1", "X-User-Role": "admin"},
        json={"run_id": run_id, "scope": "global", "justification": "admin global ok"},
    )
    assert resp.status_code == 200, "admin should be allowed to mark global golden"


def test_editorial_golden_policy_viewer_cannot_any_scope(tmp_path: Path) -> None:
    """Viewer nao pode marcar golden em nenhum escopo"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "policy4-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "policy4-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "policy4-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "policy4-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Viewer + global => 403
    resp_global = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "policy-viewer-global", "X-User-Id": "viewer-1", "X-User-Role": "viewer"},
        json={"run_id": run_id, "scope": "global", "justification": "tentativa viewer"},
    )
    assert resp_global.status_code == 403, "viewer should not be allowed to mark global golden"

    # Viewer + objective => 403
    resp_obj = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "policy-viewer-obj", "X-User-Id": "viewer-1", "X-User-Role": "viewer"},
        json={"run_id": run_id, "scope": "objective", "objective_key": "obj-123", "justification": "tentativa viewer obj"},
    )
    assert resp_obj.status_code == 403, "viewer should not be allowed to mark objective golden"


# TASK D: Observability - Policy denies metrics

def test_editorial_golden_policy_denial_increments_metrics(tmp_path: Path) -> None:
    """Negacao de policy deve incrementar metricas de deny"""
    app = create_app(settings=Settings(vm_workspace_root=tmp_path / "runtime" / "vm", vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3"))
    client = TestClient(app)

    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "deny-met-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "deny-met-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "deny-met-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "deny-met-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Get initial metrics
    metrics_before = app.state.workflow_runtime.metrics.snapshot()
    deny_total_before = metrics_before.get("counts", {}).get("editorial_golden_policy_denied_total", 0)

    # Attempt editor + global (should be denied)
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "deny-met-attempt", "X-User-Id": "editor-1", "X-User-Role": "editor"},
        json={"run_id": run_id, "scope": "global", "justification": "tentativa"},
    )
    assert resp.status_code == 403

    # Verify metrics incremented
    metrics_after = app.state.workflow_runtime.metrics.snapshot()
    deny_total_after = metrics_after.get("counts", {}).get("editorial_golden_policy_denied_total", 0)

    assert deny_total_after == deny_total_before + 1, "editorial_golden_policy_denied_total should increment"
