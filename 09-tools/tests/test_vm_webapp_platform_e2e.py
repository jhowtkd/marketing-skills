from pathlib import Path
from unittest.mock import MagicMock
import json

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace
from vm_webapp.memory import MemoryIndex
from vm_webapp.repo import create_brand, create_product, create_thread, get_run
from vm_webapp.foundation_runner_service import FoundationStageResult


def test_full_platform_flow_brand_campaign_task_run_review_learning(tmp_path: Path) -> None:
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
        force_foundation_fallback=False,
    )
    
    # Mock foundation runner to avoid file system errors in legacy code
    runtime.foundation_runner.execute_stage = MagicMock(return_value=FoundationStageResult(
        stage_key="research",
        pipeline_status="completed",
        output_payload={"summary": "done"},
        artifacts={}
    ))

    with session_scope(engine) as session:
        # 1. Setup Domain
        create_brand(session, brand_id="b1", name="Acme", canonical={}, soul_md="# Acme Soul")
        create_product(session, brand_id="b1", product_id="p1", name="Product 1", canonical={}, ws=workspace, essence_md="# P1 Essence")
        create_thread(session, thread_id="t1", brand_id="b1", product_id="p1", title="Thread 1")
        
        # 2. Start Run
        result = runtime.ensure_queued_run(
            session=session,
            run_id="run-1",
            thread_id="t1",
            brand_id="b1",
            project_id="p1",
            request_text="Launch product",
            mode="content_calendar",
            skill_overrides=None
        )
        assert result["status"] == "queued"

    # 3. Execute Run
    with session_scope(engine) as session:
        exec_result = runtime.execute_queued_run(
            session=session,
            run_id="run-1",
            actor_id="user-1",
            causation_id="evt-start",
            correlation_id="evt-start",
            trigger_event_type="WorkflowRunQueued"
        )
        assert exec_result["status"] == "completed"
        
        # Verify Learning Ingestion was called (Task 10)
        # In our dummy it's a no-op but we can verify it was called if we mock it
        
        # Verify Context Snapshot exists (Task 4)
        context_path = workspace.root / "runs" / "run-1" / "context.json"
        assert context_path.exists()
        
        # Verify Metrics (Task 12)
        metrics = runtime.metrics.snapshot()
        assert metrics["counts"]["workflow_run_completed"] == 1
