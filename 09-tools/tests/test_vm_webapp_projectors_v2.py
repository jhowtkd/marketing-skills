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
