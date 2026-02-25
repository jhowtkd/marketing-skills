from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.repo import (
    claim_run_for_execution,
    close_thread,
    create_brand,
    create_product,
    create_run,
    create_thread,
    get_product,
    get_run,
    get_thread,
    list_brands,
    list_threads,
)
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


def test_thread_roundtrip_and_close(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        create_thread(
            session,
            thread_id="t1",
            brand_id="b1",
            product_id="p1",
            title="Thread 1",
        )
        create_thread(
            session,
            thread_id="t2",
            brand_id="b1",
            product_id="p2",
            title="Thread 2",
        )

    with session_scope(engine) as session:
        rows = list_threads(session, brand_id="b1", product_id="p1")
        assert len(rows) == 1
        assert rows[0].thread_id == "t1"
        assert rows[0].status == "open"

        close_thread(session, thread_id="t1")
        thread = get_thread(session, thread_id="t1")
        assert thread is not None
        assert thread.status == "closed"


def test_claim_run_for_execution_allows_single_winner(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        create_run(
            session,
            run_id="run-1",
            brand_id="b1",
            product_id="p1",
            thread_id="t1",
            stack_path="foundation_stack",
            user_request="request",
            status="queued",
        )

    with session_scope(engine) as session:
        first = claim_run_for_execution(
            session,
            run_id="run-1",
            allowed_statuses=("queued", "waiting_approval"),
            target_status="running",
        )
        second = claim_run_for_execution(
            session,
            run_id="run-1",
            allowed_statuses=("queued", "waiting_approval"),
            target_status="running",
        )
        run = get_run(session, "run-1")

    assert first is True
    assert second is False
    assert run is not None
    assert run.status == "running"
