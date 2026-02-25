from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_readiness_reports_db_and_worker_dependency_state(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    live = client.get("/api/v2/health/live")
    assert live.status_code == 200
    assert live.json() == {"status": "live"}

    ready = client.get("/api/v2/health/ready")
    assert ready.status_code == 200

    payload = ready.json()
    assert payload["status"] == "ready"
    assert payload["dependencies"]["database"]["status"] == "ok"
    assert payload["dependencies"]["worker"]["status"] == "ok"
    assert payload["dependencies"]["worker"]["mode"] == "in_process"
