from pathlib import Path
from unittest.mock import MagicMock
import json

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace
from vm_webapp.memory import MemoryIndex


def test_runtime_executes_stage_via_tool_executor_and_logs_audit(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)
    
    workspace = Workspace(root=tmp_path / "ws")
    memory = MagicMock(spec=MemoryIndex)
    llm = MagicMock()
    
    runtime = WorkflowRuntimeV2(
        engine=engine,
        workspace=workspace,
        memory=memory,
        llm=llm,
    )
    from vm_webapp.foundation_runner_service import FoundationStageResult
    runtime.foundation_runner.execute_stage = MagicMock(return_value=FoundationStageResult(
        stage_key="stage-1",
        pipeline_status="completed",
        output_payload={"summary": "done"},
        artifacts={}
    ))
    
    # Simulate execute_stage calling tool_executor
    with session_scope(engine) as session:
        # Mocking the dependencies for a full execute_stage is complex,
        # but we can test the internal _execute_stage call
        
        manifest = runtime._execute_stage(
            run_id="run-1",
            thread_id="thread-1",
            project_id="project-1",
            request_text="test request",
            mode="plan_90d",
            stage_key="stage-1",
            stage_position=0,
            skills=["skill-1"],
            attempts=1,
            context={"test": "data"},
            session=session,
            actor_id="user-1",
            causation_id="evt-1",
            correlation_id="evt-1",
        )
        
        assert manifest is not None
        # Verify tool_executor was called and logged
        from vm_webapp.repo import list_events_by_thread
        events = list_events_by_thread(session, "thread-1")
        assert any(e.event_type == "ToolInvoked" for e in events)
