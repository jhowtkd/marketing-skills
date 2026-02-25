from pathlib import Path
from uuid import uuid4

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.context_versions import append_context_version
from vm_webapp.models import ContextVersion


def test_context_versions_are_append_only(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    scope = "brand"
    scope_id = "b1"

    with session_scope(engine) as session:
        v1_id = append_context_version(
            session,
            scope=scope,
            scope_id=scope_id,
            payload={"key": "v1"}
        )
        assert v1_id.startswith("ctxv-")

        v2_id = append_context_version(
            session,
            scope=scope,
            scope_id=scope_id,
            payload={"key": "v2"}
        )
        assert v2_id != v1_id

    with session_scope(engine) as session:
        v1 = session.get(ContextVersion, v1_id)
        assert v1.payload_json == '{"key": "v1"}'

        v2 = session.get(ContextVersion, v2_id)
        assert v2.payload_json == '{"key": "v2"}'
