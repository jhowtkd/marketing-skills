import time
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.models import ApprovalView
from vm_webapp.settings import Settings


def build_client(tmp_path: Path) -> TestClient:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    return TestClient(app)


def seed_thread_with_pending_approval(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "seed-brand"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "seed-project"},
        json={"project_id": "p1", "brand_id": "b1", "name": "Plan"},
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

    with session_scope(client.app.state.engine) as session:
        session.add(
            ApprovalView(
                approval_id="apr-1",
                thread_id="t1",
                status="pending",
                reason="Human gate before execution",
                required_role="editor",
            )
        )

    return {"thread_id": "t1", "approval_id": "apr-1"}


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


def grant_pending_approvals_until_completed(
    client: TestClient, run_id: str, *, timeout_s: float = 4.0
) -> dict[str, object]:
    deadline = time.time() + timeout_s
    grants = 0
    while time.time() < deadline:
        detail = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert detail.status_code == 200
        payload = detail.json()
        if payload.get("status") == "completed":
            return payload
        if payload.get("status") == "waiting_approval":
            pending = payload.get("pending_approvals") or []
            assert pending
            approval_id = pending[0]["approval_id"]
            grant = client.post(
                f"/api/v2/approvals/{approval_id}/grant-and-resume",
                headers={"Idempotency-Key": f"e2e-grant-{run_id}-{grants}"},
            )
            assert grant.status_code == 200
            assert grant.json()["resume_applied"] is True
            grants += 1
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach completed")


def test_duplicate_idempotency_key_returns_same_event(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    body = {"brand_id": "b1", "name": "Acme"}
    one = client.post("/api/v2/brands", headers={"Idempotency-Key": "dup-1"}, json=body)
    two = client.post("/api/v2/brands", headers={"Idempotency-Key": "dup-1"}, json=body)

    assert one.status_code == 200
    assert two.status_code == 200
    assert one.json()["event_id"] == two.json()["event_id"]


def test_stream_conflict_returns_409(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    bad = client.post("/api/v2/test/force-conflict", json={"thread_id": "t1"})
    assert bad.status_code == 409


def test_approval_gate_blocks_agent_run_until_granted(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    seed = seed_thread_with_pending_approval(client)
    start = client.post(
        f"/api/v2/threads/{seed['thread_id']}/agent-plan/start",
        headers={"Idempotency-Key": "start-1"},
    )
    assert start.status_code == 200

    timeline_before = client.get(f"/api/v2/threads/{seed['thread_id']}/timeline").json()[
        "items"
    ]
    assert not any(i["event_type"] == "AgentStepCompleted" for i in timeline_before)

    grant = client.post(
        f"/api/v2/approvals/{seed['approval_id']}/grant-and-resume",
        headers={"Idempotency-Key": "grant-1"},
    )
    assert grant.status_code == 200
    assert grant.json()["resume_applied"] in {True, False}

    timeline_after = client.get(f"/api/v2/threads/{seed['thread_id']}/timeline").json()[
        "items"
    ]
    assert any(i["event_type"] == "AgentStepCompleted" for i in timeline_after)


def test_thread_workflow_request_generates_versioned_artifacts_and_timeline(
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
        "/api/v2/brands", headers={"Idempotency-Key": "b1"}, json={"name": "Acme"}
    ).json()["brand_id"]
    project_id = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "p1"},
        json={"brand_id": brand_id, "name": "Launch"},
    ).json()["project_id"]
    thread_id = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "t1"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()["thread_id"]

    r1 = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "run-a"},
        json={"request_text": "First output", "mode": "content_calendar"},
    ).json()
    r2 = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "run-b"},
        json={"request_text": "Second output", "mode": "content_calendar"},
    ).json()

    assert r1["run_id"] != r2["run_id"]
    grant_pending_approvals_until_completed(client, r1["run_id"])
    grant_pending_approvals_until_completed(client, r2["run_id"])

    timeline = client.get(f"/api/v2/threads/{thread_id}/timeline").json()["items"]
    assert any(item["event_type"] == "WorkflowRunCompleted" for item in timeline)

    runs_root = app.state.workspace.root / "runs"
    assert (runs_root / r1["run_id"]).exists()
    assert (runs_root / r2["run_id"]).exists()


def test_workflow_queue_is_idempotent_by_idempotency_key(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    brand_id = client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "b1"}, json={"name": "Acme"}
    ).json()["brand_id"]
    project_id = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "p1"},
        json={"brand_id": brand_id, "name": "Launch"},
    ).json()["project_id"]
    thread_id = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "t1"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()["thread_id"]

    one = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "idem-run"},
        json={"request_text": "output", "mode": "content_calendar"},
    )
    two = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "idem-run"},
        json={"request_text": "output", "mode": "content_calendar"},
    )
    assert one.status_code == 200
    assert two.status_code == 200
    assert one.json()["run_id"] == two.json()["run_id"]


def test_any_mode_falls_back_to_foundation_and_completes_after_grant(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    brand_id = client.post(
        "/api/v2/brands", headers={"Idempotency-Key": "fb-b1"}, json={"name": "Acme"}
    ).json()["brand_id"]
    project_id = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "fb-p1"},
        json={"brand_id": brand_id, "name": "Launch"},
    ).json()["project_id"]
    thread_id = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "fb-t1"},
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"},
    ).json()["thread_id"]

    started = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "fb-run"},
        json={"request_text": "Output for fallback flow", "mode": "content_calendar"},
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    detail = wait_for_run_status(client, run_id, {"waiting_approval", "completed"})
    assert detail["requested_mode"] == "content_calendar"
    assert detail["effective_mode"] == "foundation_stack"
    assert detail["fallback_applied"] is True

    completed = grant_pending_approvals_until_completed(client, run_id)
    assert completed["status"] == "completed"
