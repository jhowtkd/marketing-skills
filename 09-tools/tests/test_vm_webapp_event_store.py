from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.repo import append_event, list_events_by_stream


def test_append_event_enforces_stream_version(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    event = EventEnvelope(
        event_id="evt-1",
        event_type="BrandCreated",
        aggregate_type="brand",
        aggregate_id="brand-1",
        stream_id="brand:brand-1",
        expected_version=0,
        actor_type="human",
        actor_id="workspace-owner",
        payload={"name": "Acme"},
    )

    with session_scope(engine) as session:
        saved = append_event(session, event)
        assert saved.stream_version == 1

    with session_scope(engine) as session:
        rows = list_events_by_stream(session, "brand:brand-1")
        assert len(rows) == 1
        assert rows[0].event_type == "BrandCreated"
