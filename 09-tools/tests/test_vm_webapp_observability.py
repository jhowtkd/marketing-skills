from pathlib import Path
from unittest.mock import MagicMock

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace
from vm_webapp.memory import MemoryIndex


def test_metrics_endpoint_reports_run_stage_cost_and_latency(tmp_path: Path) -> None:
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
    
    # Simulate recording metrics
    runtime.metrics.record_count("test_count", 5)
    runtime.metrics.record_latency("test_latency", 0.5)
    runtime.metrics.record_cost("test_cost", 0.05)
    
    snapshot = runtime.metrics.snapshot()
    assert snapshot["counts"]["test_count"] == 5
    assert snapshot["avg_latencies"]["test_latency"] == 0.5
    assert snapshot["total_costs"]["test_cost"] == 0.05
