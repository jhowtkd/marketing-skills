from pathlib import Path

from vm_webapp.db import build_engine, init_db
from vm_webapp.memory import MemoryIndex
from vm_webapp.run_engine import RunEngine
from vm_webapp.stacking import build_context_pack
from vm_webapp.workspace import Workspace


def test_context_pack_contains_canonical_and_retrieved(tmp_path: Path) -> None:
    ctx = build_context_pack(
        brand_soul_md="# Soul\nAcme: evidence-led.",
        product_essence_md="# Essence\nWidget: simple.",
        retrieved=[{"title": "old run", "text": "We tried X and it failed."}],
        stage_contract="Write output in Markdown.",
        user_request="Create landing copy.",
    )
    assert "Acme: evidence-led." in ctx
    assert "Widget: simple." in ctx
    assert "We tried X and it failed." in ctx


def test_run_pauses_on_gate(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path / "ws")
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    memory = MemoryIndex(root=tmp_path / "zvec")

    run_engine = RunEngine(
        engine=engine,
        workspace=ws,
        memory=memory,
        llm=None,
    )

    run = run_engine.start_run(
        brand_id="b1",
        product_id="p1",
        thread_id="t1",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        user_request="crm para clinicas",
    )
    run_engine.run_until_gate(run.run_id)
    run2 = run_engine.get_run(run.run_id)
    assert run2.status == "waiting_approval"


def test_approve_waiting_stage_continues_run(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path / "ws")
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    memory = MemoryIndex(root=tmp_path / "zvec")
    run_engine = RunEngine(engine=engine, workspace=ws, memory=memory, llm=None)

    run = run_engine.start_run(
        brand_id="b1",
        product_id="p1",
        thread_id="t1",
        stack_path="06-stacks/foundation-stack/stack.yaml",
        user_request="crm para clinicas",
    )
    run_engine.run_until_gate(run.run_id)
    run_engine.approve_and_continue(run.run_id)

    updated = run_engine.get_run(run.run_id)
    assert updated.status in {"waiting_approval", "completed"}
