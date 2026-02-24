from pathlib import Path

from vm_webapp.commands_v2 import create_brand_command
from vm_webapp.db import build_engine, init_db, session_scope


def test_create_brand_command_is_idempotent(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        first = create_brand_command(
            session,
            brand_id="b1",
            name="Acme",
            actor_id="workspace-owner",
            idempotency_key="idem-brand-b1",
        )

    with session_scope(engine) as session:
        second = create_brand_command(
            session,
            brand_id="b1",
            name="Acme",
            actor_id="workspace-owner",
            idempotency_key="idem-brand-b1",
        )

    assert first.event_id == second.event_id
