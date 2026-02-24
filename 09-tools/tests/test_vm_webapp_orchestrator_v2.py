from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.orchestrator_v2 import process_new_events
from vm_webapp.repo import append_event, list_events_by_thread


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
