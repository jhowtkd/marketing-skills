import time
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.orchestrator_v2 import process_new_events
from vm_webapp.repo import (
    append_event,
    list_events_by_thread,
    list_runs_by_thread,
    list_timeline_items_view,
)
from vm_webapp.settings import Settings
from vm_webapp.workflow_runtime_v2 import FoundationStageResult


def test_orchestrator_requests_approval_after_agent_plan_start(
    tmp_path: Path,
) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        append_event(
            session,
            EventEnvelope(
                event_id="evt-start",
                event_type="AgentPlanStarted",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                payload={"thread_id": "t1", "plan_id": "plan-t1"},
                thread_id="t1",
            ),
        )
        process_new_events(session)

    with session_scope(engine) as session:
        events = list_events_by_thread(session, "t1")
        assert any(e.event_type == "ApprovalRequested" for e in events)


def test_orchestrator_executes_workflow_run_requested_and_publishes_timeline(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )

    with session_scope(app.state.engine) as session:
        append_event(
            session,
            EventEnvelope(
                event_id="evt-run-request",
                event_type="WorkflowRunQueued",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                payload={
                    "thread_id": "t1",
                    "brand_id": "b1",
                    "project_id": "p1",
                    "request_text": "Build workflow output",
                    "mode": "content_calendar",
                    "run_id": "run-test-1",
                    "skill_overrides": {},
                },
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
            ),
        )
        process_new_events(session)

    with session_scope(app.state.engine) as session:
        runs = list_runs_by_thread(session, "t1")
        timeline = list_timeline_items_view(session, thread_id="t1")
        assert runs
        assert any(
            i.event_type in {"WorkflowRunStarted", "WorkflowRunCompleted"} for i in timeline
        )


def test_workflow_gate_approval_auto_resumes_without_manual_resume(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "auto-b"},
        json={"brand_id": "b1", "name": "Acme"},
    )
    client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "auto-p"},
        json={"project_id": "p1", "brand_id": "b1", "name": "Plan"},
    )
    created_thread = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "auto-t"},
        json={
            "thread_id": "t1",
            "project_id": "p1",
            "brand_id": "b1",
            "title": "Planning",
        },
    )
    assert created_thread.status_code == 200

    started = client.post(
        "/api/v2/threads/t1/workflow-runs",
        headers={"Idempotency-Key": "auto-run"},
        json={"request_text": "Build assets", "mode": "content_calendar"},
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    deadline = time.time() + 4.0
    approvals_granted = 0
    final_status = "queued"
    while time.time() < deadline:
        detail = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert detail.status_code == 200
        payload = detail.json()
        final_status = payload["status"]
        if final_status == "completed":
            break
        if final_status == "waiting_approval":
            pending = payload["pending_approvals"]
            assert pending
            approval_id = pending[0]["approval_id"]
            granted = client.post(
                f"/api/v2/approvals/{approval_id}/grant",
                headers={"Idempotency-Key": f"auto-approval-{approvals_granted}"},
            )
            assert granted.status_code == 200
            approvals_granted += 1
        time.sleep(0.05)

    assert final_status == "completed"
    assert approvals_granted >= 1


def test_workflow_gate_reentry_does_not_fail_run(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post(
        "/api/v2/brands",
        headers={"Idempotency-Key": "re-b"},
        json={"brand_id": "b1", "name": "Acme"},
    ).json()["brand_id"]
    project_id = client.post(
        "/api/v2/projects",
        headers={"Idempotency-Key": "re-p"},
        json={"project_id": "p1", "brand_id": brand_id, "name": "Plan"},
    ).json()["project_id"]
    thread_id = client.post(
        "/api/v2/threads",
        headers={"Idempotency-Key": "re-t"},
        json={
            "thread_id": "t1",
            "project_id": project_id,
            "brand_id": brand_id,
            "title": "Planning",
        },
    ).json()["thread_id"]

    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "re-run"},
        json={"request_text": "Build assets", "mode": "content_calendar"},
    ).json()["run_id"]

    deadline = time.time() + 4.0
    detail_payload: dict[str, object] = {}
    while time.time() < deadline:
        detail = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert detail.status_code == 200
        detail_payload = detail.json()
        if detail_payload.get("status") == "waiting_approval":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("run did not reach waiting_approval")

    pending = detail_payload.get("pending_approvals") or []
    assert pending
    approval_id = pending[0]["approval_id"]

    runtime = app.state.workflow_runtime
    execute_calls = {"count": 0}

    def _reentrant_execute_stage(**kwargs):
        execute_calls["count"] += 1
        if execute_calls["count"] == 1:
            with session_scope(app.state.engine) as nested_session:
                runtime.process_event(
                    session=nested_session,
                    event_type="WorkflowRunResumed",
                    payload={
                        "thread_id": thread_id,
                        "brand_id": brand_id,
                        "project_id": project_id,
                        "run_id": run_id,
                        "request_text": "Build assets",
                    },
                    actor_id="agent:vm-workflow",
                    causation_id="evt-reentrant",
                    correlation_id="evt-reentrant",
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
        headers={"Idempotency-Key": "re-grant"},
    )
    assert granted.status_code == 200

    final_status = "queued"
    deadline = time.time() + 4.0
    while time.time() < deadline:
        detail = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert detail.status_code == 200
        detail_payload = detail.json()
        final_status = str(detail_payload.get("status"))
        if final_status in {"waiting_approval", "completed", "failed"}:
            break
        time.sleep(0.05)

    assert final_status != "failed"
    with session_scope(app.state.engine) as session:
        events = list_events_by_thread(session, thread_id)
    failed_events = [
        event
        for event in events
        if event.event_type == "WorkflowRunStageFailed" and f'"run_id": "{run_id}"' in event.payload_json
    ]
    assert not failed_events
