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

    # Mark golden (needs admin for global scope)
    client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "prom-mark", "Authorization": "Bearer admin1:admin"},
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


def test_prometheus_metrics_expose_policy_denial_metrics(tmp_path: Path) -> None:
    """Metricas de negacao de policy devem ser expostas"""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Seed data
    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "deny-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "deny-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "deny-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "deny-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]

    # Attempt editor + global (should be denied)
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={"Idempotency-Key": "deny-attempt", "Authorization": "Bearer editor1:editor"},
        json={"run_id": run_id, "scope": "global", "justification": "tentativa"},
    )
    assert resp.status_code == 403

    # Get Prometheus metrics
    response = client.get("/api/v2/metrics/prometheus")
    assert response.status_code == 200
    body = response.text

    # Check policy denial metrics
    assert "vm_editorial_golden_policy_denied_total 1" in body
    assert "vm_editorial_golden_policy_denied_role_editor 1" in body
    assert "vm_editorial_golden_policy_denied_scope_global 1" in body


# TASK C: Alertas operacionais - Threshold validation

class ThresholdChecker:
    """Helper para validar thresholds de métricas editoriais"""
    
    def __init__(self, metrics_text: str):
        self.metrics = self._parse_metrics(metrics_text)
    
    def _parse_metrics(self, text: str) -> dict[str, float]:
        """Parse Prometheus metrics text into dict"""
        metrics = {}
        for line in text.strip().split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                try:
                    value = float(parts[1])
                    metrics[name] = value
                except ValueError:
                    continue
        return metrics
    
    def get_metric(self, name: str) -> float:
        return self.metrics.get(name, 0.0)
    
    def check_threshold(self, metric_name: str, threshold: float) -> tuple[bool, float]:
        """Check if metric is below threshold. Returns (ok, value)"""
        value = self.get_metric(metric_name)
        return value <= threshold, value


def test_threshold_checker_validates_policy_denial_spike(tmp_path: Path) -> None:
    """Checker deve detectar spike em negacoes de policy"""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Seed data
    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "thresh-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "thresh-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "thresh-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    
    # Multiple policy denials
    for i in range(5):
        run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": f"thresh-run{i}"}, json={"request_text": f"Campanha {i}", "mode": "content_calendar"}).json()["run_id"]
        client.post(
            f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
            headers={"Idempotency-Key": f"thresh-deny{i}", "Authorization": "Bearer editor1:editor"},
            json={"run_id": run_id, "scope": "global", "justification": f"tentativa {i}"},
        )

    # Get metrics
    response = client.get("/api/v2/metrics/prometheus")
    checker = ThresholdChecker(response.text)
    
    # Check policy denial threshold (limiar: 3)
    ok, value = checker.check_threshold("vm_editorial_golden_policy_denied_total", threshold=3.0)
    assert not ok, f"Expected threshold breach for policy denials, got {value}"
    assert value == 5.0, f"Expected 5 denials, got {value}"


def test_threshold_checker_validates_baseline_none_acceptable(tmp_path: Path) -> None:
    """Checker deve aceitar baseline_none em niveis normais"""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Single run (will have baseline=none)
    brand_id = client.post("/api/v2/brands", headers={"Idempotency-Key": "none-b"}, json={"name": "Acme"}).json()["brand_id"]
    project_id = client.post("/api/v2/projects", headers={"Idempotency-Key": "none-p"}, json={"brand_id": brand_id, "name": "Launch"}).json()["project_id"]
    thread_id = client.post("/api/v2/threads", headers={"Idempotency-Key": "none-t"}, json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}).json()["thread_id"]
    run_id = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", headers={"Idempotency-Key": "none-run"}, json={"request_text": "Campanha", "mode": "content_calendar"}).json()["run_id"]
    
    # Trigger baseline resolution
    client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    # Get metrics
    response = client.get("/api/v2/metrics/prometheus")
    checker = ThresholdChecker(response.text)
    
    # Check baseline_none threshold (limiar: 10)
    ok, value = checker.check_threshold("vm_editorial_baseline_source_none", threshold=10.0)
    assert ok, f"Expected baseline_none within threshold, got {value}"
    assert value == 1.0
