from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def test_prometheus_metrics_endpoint_exposes_runtime_counters(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    app.state.workflow_runtime.metrics.record_count("workflow_run_completed", 2)

    response = client.get("/api/v2/metrics/prometheus")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    body = response.text
    assert "vm_workflow_run_completed 2" in body
    assert "vm_http_request_total_metrics_prometheus 1" in body
