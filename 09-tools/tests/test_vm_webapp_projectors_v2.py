from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import append_event, list_brands_view, list_editorial_decisions_view


def test_brand_created_event_projects_to_brands_view(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-brand",
                event_type="BrandCreated",
                aggregate_type="brand",
                aggregate_id="b1",
                stream_id="brand:b1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                payload={"brand_id": "b1", "name": "Acme"},
                brand_id="b1",
            ),
        )
        apply_event_to_read_models(session, row)

    with session_scope(engine) as session:
        brands = list_brands_view(session)
        assert len(brands) == 1
        assert brands[0].brand_id == "b1"
        assert brands[0].name == "Acme"


def test_editorial_golden_marked_projects_to_decisions_view(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-golden",
                event_type="EditorialGoldenMarked",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="workspace-owner",
                thread_id="t1",
                payload={
                    "thread_id": "t1",
                    "run_id": "run-1",
                    "scope": "global",
                    "objective_key": None,
                    "justification": "best final quality",
                },
            ),
        )
        apply_event_to_read_models(session, row)

    with session_scope(engine) as session:
        rows = list_editorial_decisions_view(session, thread_id="t1")
        assert len(rows) == 1
        assert rows[0].run_id == "run-1"
        assert rows[0].scope == "global"


# First-run outcome projector tests (v12)

def test_first_run_outcome_success_when_no_new_run_within_24h(tmp_path: Path) -> None:
    """Outcome is successful when approved and no new run within 24h."""
    from datetime import datetime, timedelta, timezone
    from vm_webapp.models import FirstRunOutcomeView
    from vm_webapp.repo import get_first_run_outcome, list_first_run_outcomes
    
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    
    now = datetime.now(timezone.utc)
    
    with session_scope(engine) as session:
        # Simulate a run that was approved
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-run-completed",
                event_type="RunCompleted",
                aggregate_type="run",
                aggregate_id="run-1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="system",
                actor_id="runner",
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
                payload={
                    "run_id": "run-1",
                    "thread_id": "t1",
                    "brand_id": "b1",
                    "project_id": "p1",
                    "profile": "engagement",
                    "mode": "fast",
                    "approved": True,
                    "quality_score": 0.85,
                    "duration_ms": 5000,
                    "completed_at": now.isoformat(),
                },
            ),
        )
        apply_event_to_read_models(session, row)
    
    with session_scope(engine) as session:
        outcomes = list_first_run_outcomes(session, thread_id="t1")
        assert len(outcomes) == 1
        assert outcomes[0].run_id == "run-1"
        assert outcomes[0].profile == "engagement"
        assert outcomes[0].mode == "fast"
        assert outcomes[0].approved is True
        # No new run within 24h, so success_24h should be True
        assert outcomes[0].success_24h is True


def test_first_run_outcome_failure_when_new_run_created_within_24h(tmp_path: Path) -> None:
    """Outcome fails when a new run is created within 24h of approval."""
    from datetime import datetime, timedelta, timezone
    from vm_webapp.repo import list_first_run_outcomes
    
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    
    now = datetime.now(timezone.utc)
    
    with session_scope(engine) as session:
        # First run completed and approved
        row1 = append_event(
            session,
            EventEnvelope(
                event_id="evt-run-1-completed",
                event_type="RunCompleted",
                aggregate_type="run",
                aggregate_id="run-1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="system",
                actor_id="runner",
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
                payload={
                    "run_id": "run-1",
                    "thread_id": "t1",
                    "brand_id": "b1",
                    "project_id": "p1",
                    "profile": "engagement",
                    "mode": "fast",
                    "approved": True,
                    "quality_score": 0.85,
                    "duration_ms": 5000,
                    "completed_at": now.isoformat(),
                },
            ),
        )
        apply_event_to_read_models(session, row1)
        
        # Second run created within 24h (2 hours later)
        row2 = append_event(
            session,
            EventEnvelope(
                event_id="evt-run-2-created",
                event_type="RunCreated",
                aggregate_type="run",
                aggregate_id="run-2",
                stream_id="thread:t1",
                expected_version=1,
                actor_type="human",
                actor_id="user",
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
                payload={
                    "run_id": "run-2",
                    "thread_id": "t1",
                    "created_at": (now + timedelta(hours=2)).isoformat(),
                },
            ),
        )
        apply_event_to_read_models(session, row2)
    
    with session_scope(engine) as session:
        outcomes = list_first_run_outcomes(session, thread_id="t1")
        # Only completed runs have outcomes (RunCreated doesn't create an outcome)
        assert len(outcomes) == 1
        # First run should now be marked as not successful (new run within 24h)
        run1_outcome = [o for o in outcomes if o.run_id == "run-1"][0]
        assert run1_outcome.success_24h is False


def test_first_run_outcome_aggregate_updates_with_multiple_runs(tmp_path: Path) -> None:
    """Aggregate should update correctly with multiple runs."""
    from datetime import datetime, timedelta, timezone
    from vm_webapp.repo import get_first_run_outcome_aggregate
    
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    
    now = datetime.now(timezone.utc)
    
    with session_scope(engine) as session:
        # Multiple runs with same profile/mode
        for i in range(3):
            row = append_event(
                session,
                EventEnvelope(
                    event_id=f"evt-run-{i}-completed",
                    event_type="RunCompleted",
                    aggregate_type="run",
                    aggregate_id=f"run-{i}",
                    stream_id="thread:t1",
                    expected_version=i,
                    actor_type="system",
                    actor_id="runner",
                    thread_id="t1",
                    brand_id="b1",
                    project_id="p1",
                    payload={
                        "run_id": f"run-{i}",
                        "thread_id": "t1",
                        "brand_id": "b1",
                        "project_id": "p1",
                        "profile": "engagement",
                        "mode": "fast",
                        "approved": True,
                        "quality_score": 0.8 + (i * 0.05),
                        "duration_ms": 4000 + (i * 500),
                        "completed_at": (now + timedelta(hours=i*25)).isoformat(),
                    },
                ),
            )
            apply_event_to_read_models(session, row)
    
    with session_scope(engine) as session:
        agg = get_first_run_outcome_aggregate(
            session,
            brand_id="b1",
            project_id="p1",
            profile="engagement",
            mode="fast",
        )
        assert agg is not None
        assert agg.total_runs == 3
        assert agg.success_24h_count == 3  # All separated by 25h
        assert agg.approved_count == 3
