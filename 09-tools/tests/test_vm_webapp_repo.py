from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.repo import create_brand, list_brands


def test_brand_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    engine = build_engine(db_path)
    init_db(engine)

    with session_scope(engine) as session:
        create_brand(
            session,
            brand_id="b1",
            name="Acme",
            canonical={"tone": "pragmatic"},
        )

    with session_scope(engine) as session:
        brands = list_brands(session)
        assert len(brands) == 1
        assert brands[0].brand_id == "b1"
        assert brands[0].name == "Acme"
