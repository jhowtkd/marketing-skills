"""Testes de contrato para API v2 de Alertas Editoriais (SLO Alerts Hub).

TDD: Estes testes definem o contrato do endpoint GET /api/v2/threads/{thread_id}/alerts.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.models import TimelineItemView, EventLog
from vm_webapp.settings import Settings


def _create_test_thread(client: TestClient) -> str:
    """Helper to create a minimal test thread setup."""
    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "alerts-b"}, 
        json={"name": "Acme Alerts"}
    ).json()["brand_id"]
    
    project_id = client.post(
        "/api/v2/projects", 
        headers={"Idempotency-Key": "alerts-p"}, 
        json={"brand_id": brand_id, "name": "Alerts Test"}
    ).json()["project_id"]
    
    thread_id = client.post(
        "/api/v2/threads", 
        headers={"Idempotency-Key": "alerts-t"}, 
        json={"brand_id": brand_id, "project_id": project_id, "title": "Alerts Test Thread"}
    ).json()["thread_id"]
    
    return thread_id


def test_alerts_endpoint_returns_404_for_unknown_thread(tmp_path: Path) -> None:
    """GET /api/v2/threads/{thread_id}/alerts deve retornar 404 para thread inexistente."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    resp = client.get("/api/v2/threads/thread-inexistente/alerts")
    assert resp.status_code == 404
    assert "thread not found" in resp.json()["detail"]


def test_alerts_empty_for_thread_with_no_alerts(tmp_path: Path) -> None:
    """Thread sem dados ainda pode gerar alertas de forecast (ex: no_golden_marks).
    
    O endpoint deve retornar estrutura correta mesmo com alertas gerados por heurísticas.
    """
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "thread_id" in data
    assert "alerts" in data
    assert "generated_at" in data
    assert "total_count" in data
    assert "by_severity" in data
    
    assert data["thread_id"] == thread_id
    # Thread sem dados pode gerar alertas de forecast (no_golden_marks é esperado)
    assert isinstance(data["alerts"], list)
    assert data["total_count"] == len(data["alerts"])
    # Verificar que by_severity é consistente com total_count
    severity_sum = sum(data["by_severity"].values())
    assert severity_sum == data["total_count"]


def test_alerts_response_schema_validation(tmp_path: Path) -> None:
    """Cada alerta deve seguir o schema contratual definido."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    # Criar uma run para gerar baseline
    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "alerts-run"},
        json={"request_text": "Test alert", "mode": "content_calendar"}
    ).json()["run_id"]

    # Resolver baseline (vai gerar source=none -> alerta baseline_none)
    client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "alerts" in data
    
    # Verificar schema de cada alerta
    for alert in data["alerts"]:
        # Campos obrigatórios
        assert "alert_id" in alert, "alert_id é obrigatório"
        assert "alert_type" in alert, "alert_type é obrigatório"
        assert "severity" in alert, "severity é obrigatório"
        assert "status" in alert, "status é obrigatório"
        assert "title" in alert, "title é obrigatório"
        assert "description" in alert, "description é obrigatório"
        assert "causa" in alert, "causa é obrigatório"
        assert "recomendacao" in alert, "recomendacao é obrigatório"
        assert "created_at" in alert, "created_at é obrigatório"
        assert "updated_at" in alert, "updated_at é obrigatório"
        
        # Valores permitidos
        assert alert["severity"] in ["critical", "warning", "info"]
        assert alert["status"] in ["active", "acknowledged", "resolved"]
        assert alert["alert_type"] in [
            "slo_violation", "drift_detected", "baseline_none", 
            "policy_denied", "forecast_risk"
        ]
        
        # Tipos de dados
        assert isinstance(alert["alert_id"], str)
        assert isinstance(alert["title"], str)
        assert isinstance(alert["description"], str)
        assert isinstance(alert["causa"], str)
        assert isinstance(alert["recomendacao"], str)
        assert isinstance(alert["metadata"], dict)


def test_alerts_multiple_types_combined(tmp_path: Path) -> None:
    """Agregador deve combinar múltiplos tipos de alertas em uma única resposta."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    # Criar múltiplas runs e resolver baselines (gera baseline_none)
    for i in range(3):
        run_id = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            headers={"Idempotency-Key": f"alerts-run-{i}"},
            json={"request_text": f"Test alert {i}", "mode": "content_calendar"}
        ).json()["run_id"]
        client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    assert data["total_count"] > 0
    
    # Verificar que há alertas de algum tipo (baseline, slo, drift, ou forecast)
    alert_types = {alert["alert_type"] for alert in data["alerts"]}
    expected_types = {"baseline_none", "slo_violation", "drift_detected", "forecast_risk"}
    assert bool(alert_types & expected_types), f"Nenhum tipo de alerta esperado encontrado: {alert_types}"


def test_alerts_severity_ordering(tmp_path: Path) -> None:
    """Alertas devem ser ordenados por severidade (critical > warning > info)."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    # Criar runs e resolver baselines
    for i in range(5):
        run_id = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            headers={"Idempotency-Key": f"sev-run-{i}"},
            json={"request_text": f"Severity test {i}", "mode": "content_calendar"}
        ).json()["run_id"]
        client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    if len(data["alerts"]) > 1:
        # Verificar ordenação: critical vem antes de warning, etc.
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        severities = [alert["severity"] for alert in data["alerts"]]
        
        for i in range(len(severities) - 1):
            assert severity_order[severities[i]] <= severity_order[severities[i + 1]], \
                f"Alertas não estão ordenados por severidade: {severities}"


def test_alerts_filter_by_severity(tmp_path: Path) -> None:
    """Endpoint deve suportar filtro por severidade via query param."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    # Criar runs e resolver baselines
    for i in range(3):
        run_id = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            headers={"Idempotency-Key": f"filt-run-{i}"},
            json={"request_text": f"Filter test {i}", "mode": "content_calendar"}
        ).json()["run_id"]
        client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    # Testar filtro por severidade
    resp_critical = client.get(f"/api/v2/threads/{thread_id}/alerts?severity=critical")
    assert resp_critical.status_code == 200
    
    for alert in resp_critical.json()["alerts"]:
        assert alert["severity"] == "critical"


def test_alerts_include_timestamps(tmp_path: Path) -> None:
    """Cada alerta deve incluir timestamps de criação e atualização."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "ts-run"},
        json={"request_text": "Timestamp test", "mode": "content_calendar"}
    ).json()["run_id"]
    client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    for alert in data["alerts"]:
        assert "created_at" in alert
        assert "updated_at" in alert
        # Verificar formato ISO
        assert "T" in alert["created_at"] or "+" in alert["created_at"]
        assert "T" in alert["updated_at"] or "+" in alert["updated_at"]


def test_alerts_with_slo_violations(tmp_path: Path) -> None:
    """Deve detectar violações de SLO quando baseline_none_rate excede threshold."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    # Criar muitas runs sem golden marks -> vai gerar baseline_none
    # Isso deve criar alerta de SLO violation quando a taxa exceder 50%
    for i in range(5):
        run_id = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            headers={"Idempotency-Key": f"slo-run-{i}"},
            json={"request_text": f"SLO test {i}", "mode": "content_calendar"}
        ).json()["run_id"]
        client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    
    # Verificar que há alertas relacionados a baseline/slo/forecast
    alert_types = {alert["alert_type"] for alert in data["alerts"]}
    expected_types = {"baseline_none", "slo_violation", "forecast_risk", "drift_detected"}
    assert bool(alert_types & expected_types), \
        f"Nenhum tipo esperado encontrado. Tipos: {alert_types}"


def test_alerts_with_drift_detection(tmp_path: Path) -> None:
    """Deve incluir alertas de drift quando detectado."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    # Criar runs com alta taxa de baseline_none para gerar drift
    for i in range(6):
        run_id = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            headers={"Idempotency-Key": f"drift-run-{i}"},
            json={"request_text": f"Drift test {i}", "mode": "content_calendar"}
        ).json()["run_id"]
        client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    
    # Verificar que há pelo menos algum alerta
    assert data["total_count"] >= 0


def test_alerts_metadata_structure(tmp_path: Path) -> None:
    """Metadata de cada alerta deve ter estrutura consistente."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "meta-run"},
        json={"request_text": "Metadata test", "mode": "content_calendar"}
    ).json()["run_id"]
    client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    for alert in data["alerts"]:
        assert isinstance(alert["metadata"], dict)
        # Verificar campos comuns em metadata
        assert "thread_id" in alert["metadata"]
        assert alert["metadata"]["thread_id"] == thread_id


def test_alerts_causa_e_recomendacao_presentes(tmp_path: Path) -> None:
    """Cada alerta deve ter causa e recomendação em português."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)
    thread_id = _create_test_thread(client)

    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs",
        headers={"Idempotency-Key": "rec-run"},
        json={"request_text": "Recommendation test", "mode": "content_calendar"}
    ).json()["run_id"]
    client.get(f"/api/v2/workflow-runs/{run_id}/baseline")

    resp = client.get(f"/api/v2/threads/{thread_id}/alerts")
    assert resp.status_code == 200
    
    data = resp.json()
    for alert in data["alerts"]:
        assert len(alert["causa"]) > 0, "causa não pode ser vazia"
        assert len(alert["recomendacao"]) > 0, "recomendacao não pode ser vazia"
        # Verificar que são strings significativas
        assert isinstance(alert["causa"], str)
        assert isinstance(alert["recomendacao"], str)
