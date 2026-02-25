import json
from pathlib import Path

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.memory import MemoryIndex
from vm_webapp.models import ThreadView
from vm_webapp.repo import list_stages, update_run_status
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


def test_execute_queued_run_noops_when_run_already_running(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path, force_foundation=True)

    with session_scope(runtime.engine) as session:
        runtime.ensure_queued_run(
            session=session,
            run_id="run-1",
            thread_id="t1",
            brand_id="b1",
            project_id="p1",
            request_text="Build assets",
            mode="content_calendar",
            skill_overrides={},
        )
        update_run_status(session, run_id="run-1", status="running")

    def _unexpected_execute_stage(**_kwargs):
        raise AssertionError("stage execution should not run when run status is already running")

    runtime.foundation_runner.execute_stage = _unexpected_execute_stage

    with session_scope(runtime.engine) as session:
        result = runtime.execute_queued_run(
            session=session,
            run_id="run-1",
            actor_id="agent:test",
            causation_id="evt-test",
            correlation_id="evt-test",
            trigger_event_type="WorkflowRunResumed",
        )
        stages = list_stages(session, "run-1")

    assert result == {"run_id": "run-1", "status": "running"}
    assert stages[0].status == "pending"
    assert stages[0].attempts == 0
