import json
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.memory import MemoryIndex
from vm_webapp.models import ThreadView
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace


def build_runtime(tmp_path: Path, *, force_foundation: bool) -> WorkflowRuntimeV2:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    workspace = Workspace(root=tmp_path / "runtime" / "vm")
    memory = MemoryIndex(root=tmp_path / "zvec")
    return WorkflowRuntimeV2(
        engine=engine,
        workspace=workspace,
        memory=memory,
        llm=None,
        force_foundation_fallback=force_foundation,
    )


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


def test_runtime_persists_requested_and_effective_mode_snapshot(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path, force_foundation=True)
    result = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Build assets",
        mode="content_calendar",
        actor_id="agent:test",
    )
    plan = json.loads(
        (tmp_path / "runtime" / "vm" / "runs" / result["run_id"] / "plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert plan["requested_mode"] == "content_calendar"
    assert plan["effective_mode"] == "foundation_stack"
    assert plan["profile_version"] == "v1"


def test_runtime_stage_output_includes_llm_metadata(tmp_path: Path) -> None:
    """Verify LLM metadata is exposed in stage outputs."""
    class FakeLLM:
        def chat(self, **kwargs):
            return "AI generated"

    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    workspace = Workspace(root=tmp_path / "runtime" / "vm")
    memory = MemoryIndex(root=tmp_path / "zvec")

    runtime = WorkflowRuntimeV2(
        engine=engine,
        workspace=workspace,
        memory=memory,
        llm=FakeLLM(),
        llm_model="kimi-for-coding",
    )
    result = runtime.execute_thread_run(
        thread_id="t1",
        brand_id="b1",
        project_id="p1",
        request_text="Test LLM metadata",
        mode="foundation_stack",
        actor_id="agent:test",
    )

    # Load manifest from first stage
    run_root = tmp_path / "runtime" / "vm" / "runs" / result["run_id"]
    stage_dirs = list((run_root / "stages").glob("*"))
    assert stage_dirs
    manifest_path = stage_dirs[0] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "output" in manifest
    assert "llm" in manifest["output"]
    assert manifest["output"]["llm"]["enabled"] is True
    assert manifest["output"]["llm"]["model"] == "kimi-for-coding"
