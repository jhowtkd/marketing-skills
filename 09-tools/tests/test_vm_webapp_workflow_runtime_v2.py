from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.memory import MemoryIndex
from vm_webapp.models import ThreadView
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace


def test_workflow_runtime_creates_run_and_stage_artifacts(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    workspace = Workspace(root=tmp_path / "runtime" / "vm")
    memory = MemoryIndex(root=tmp_path / "zvec")

    with session_scope(engine) as session:
        session.add(
            ThreadView(
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
                title="Planning",
                status="open",
                modes_json='["plan_90d"]',
            )
        )

    runtime = WorkflowRuntimeV2(engine=engine, workspace=workspace, memory=memory, llm=None)
    result = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Create campaign workflow",
        mode="content_calendar",
        actor_id="agent:vm-planner",
    )

    run_root = workspace.root / "runs" / result["run_id"]
    assert (run_root / "run.json").exists()
    manifests = list(run_root.glob("stages/*/manifest.json"))
    assert manifests


def test_workflow_runtime_never_overwrites_previous_run(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    workspace = Workspace(root=tmp_path / "runtime" / "vm")
    memory = MemoryIndex(root=tmp_path / "zvec")

    runtime = WorkflowRuntimeV2(engine=engine, workspace=workspace, memory=memory, llm=None)
    first = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Run one",
        mode="content_calendar",
        actor_id="agent:vm-planner",
    )
    second = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Run two",
        mode="content_calendar",
        actor_id="agent:vm-planner",
    )

    assert first["run_id"] != second["run_id"]
