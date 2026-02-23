from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.repo import create_brand, create_product, get_product, list_brands
from vm_webapp.workspace import Workspace


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


def test_create_brand_writes_soul(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path)
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        create_brand(
            session,
            brand_id="b1",
            name="Acme",
            canonical={"tone": "pragmatic"},
            ws=ws,
            soul_md="# Soul\n",
        )

    assert ws.brand_soul_path("b1").read_text(encoding="utf-8").startswith("# Soul")


def test_create_product_writes_essence(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path)
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        create_brand(
            session,
            brand_id="b1",
            name="Acme",
            canonical={},
            ws=ws,
            soul_md="",
        )
        create_product(
            session,
            brand_id="b1",
            product_id="p1",
            name="Widget",
            canonical={},
            ws=ws,
            essence_md="# Essence\n",
        )

    assert (
        ws.product_essence_path("b1", "p1").read_text(encoding="utf-8")
        == "# Essence\n"
    )
    with session_scope(engine) as session:
        product = get_product(session, product_id="p1")
        assert product is not None
        assert product.name == "Widget"
