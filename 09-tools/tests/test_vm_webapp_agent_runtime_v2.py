from pathlib import Path

from vm_webapp.agent_runtime_v2 import run_planning_step
from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.repo import list_events_by_thread


def test_run_planning_step_emits_started_and_completed_events(
    tmp_path: Path,
) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        emitted = run_planning_step(
            session,
            thread_id="t1",
            project_id="p1",
            brand_id="b1",
            mode="plan_90d",
            request_text="Create 90-day strategy",
            actor_id="agent:vm-planner",
        )
        types = [item.event_type for item in emitted]
        assert "AgentStepStarted" in types
        assert "AgentStepCompleted" in types
        assert "AgentArtifactPublished" in types

    with session_scope(engine) as session:
        events = list_events_by_thread(session, "t1")
        assert any(e.event_type == "AgentArtifactPublished" for e in events)
