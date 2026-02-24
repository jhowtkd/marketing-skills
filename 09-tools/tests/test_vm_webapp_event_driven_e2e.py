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
        f"/api/v2/approvals/{seed['approval_id']}/grant",
        headers={"Idempotency-Key": "grant-1"},
    )
    assert grant.status_code == 200

    timeline_after = client.get(f"/api/v2/threads/{seed['thread_id']}/timeline").json()[
        "items"
    ]
    assert any(i["event_type"] == "AgentStepCompleted" for i in timeline_after)
