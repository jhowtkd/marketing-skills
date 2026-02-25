from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from vm_webapp.db import build_engine, init_db
from vm_webapp.memory import MemoryIndex
from vm_webapp.workflow_runtime_v2 import WorkflowRuntimeV2
from vm_webapp.workspace import Workspace


class FlakyDependencyWorker:
    def __init__(self) -> None:
        self.calls = 0

    def pump(self, *, max_events: int = 50) -> int:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary dependency outage")
        return 2


def test_runtime_remains_available_when_dependency_is_temporarily_unreachable(
    tmp_path: Path,
) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    runtime = WorkflowRuntimeV2(
        engine=engine,
        workspace=Workspace(root=tmp_path / "ws"),
        memory=MagicMock(spec=MemoryIndex),
        llm=MagicMock(),
    )
    worker = FlakyDependencyWorker()

    first = runtime.pump_worker_dependency(worker=worker, max_events=30)
    second = runtime.pump_worker_dependency(worker=worker, max_events=30)

    assert first == 0
    assert second == 2
    assert runtime.metrics.snapshot()["counts"]["dependency_failures"] == 1
