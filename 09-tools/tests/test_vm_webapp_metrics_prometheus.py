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


def test_prometheus_metrics_endpoint_exposes_editorial_metrics(tmp_path: Path) -> None:
    """O endpoint /metrics/prometheus deve expor as metricas de editorial golden e baseline"""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Seed data
    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "prom-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "prom-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "prom-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run1_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "prom-run1"}, json={"request_text": "Campanha 1", "mode": "content_calendar"}).json()["run_id"]
    run2_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "prom-run2"}, json={"request_text": "Campanha 2", "mode": "content_calendar"}).json()["run_id"]

    # Mark golden
    client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "prom-mark"},
        json={"run_id": run1_id, "scope": "global", "justification": "melhor resultado"},
    )

    # Call baseline
    client.get(f"/api/v2/workflow-runs/{run2_id}/baseline")

    # Call list decisions
    client.get(f"/api/v2/threads/{thread_id}/editorial-decisions")

    # Get Prometheus metrics
    response = client.get("/api/v2/metrics/prometheus")
    assert response.status_code == 200

    body = response.text

    # Check editorial metrics are exposed
    assert "vm_editorial_golden_marked_total 1" in body
    assert "vm_editorial_golden_marked_scope_global 1" in body
    assert "vm_editorial_baseline_resolved_total 1" in body
    assert "vm_editorial_baseline_source_global_golden 1" in body
    assert "vm_editorial_decisions_list_total 1" in body
