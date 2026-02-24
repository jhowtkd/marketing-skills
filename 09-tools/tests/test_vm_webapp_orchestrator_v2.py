from pathlib import Path

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
