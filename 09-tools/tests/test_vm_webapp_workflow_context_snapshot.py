from pathlib import Path
from unittest.mock import MagicMock
import json

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace
from vm_webapp.memory import MemoryIndex


def test_run_stores_context_snapshot(tmp_path: Path) -> None:
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
    
    run_id = "run-1"
    context = {"test": "data"}
    runtime._write_run_context_snapshot(run_id, context)
    
    context_path = workspace.root / "runs" / run_id / "context.json"
    assert context_path.exists()
    assert json.loads(context_path.read_text()) == context
