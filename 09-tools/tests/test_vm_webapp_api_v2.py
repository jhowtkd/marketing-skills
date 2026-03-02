"""Tests for v28 Recovery Orchestration API Endpoints.

TDD: Testes para run/status/events/approve/reject/freeze/rollback.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.api_recovery import router as recovery_router
from fastapi import FastAPI


# Create test app
app = FastAPI()
app.include_router(recovery_router)
client = TestClient(app)


def _reset_state():
    """Reset global state between tests."""
    from vm_webapp.api_recovery import (
        _recovery_runs,
        _recovery_events,
        _approval_requests,
        _frozen_incidents,
        _recovery_metrics,
    )
    _recovery_runs.clear()
    _recovery_events.clear()
    _approval_requests.clear()
    _frozen_incidents.clear()
    _recovery_metrics["total_runs"] = 0
    _recovery_metrics["successful_runs"] = 0
    _recovery_metrics["failed_runs"] = 0


class TestRecoveryStatusEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/recovery/status."""

    def test_status_returns_basic_info(self):
        """Status deve retornar informações básicas."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "state" in data
        assert "version" in data
        assert data["version"] == "v28"

    def test_status_includes_recovery_metrics(self):
        """Status deve incluir métricas de recovery."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "total_runs" in data["metrics"]
        assert "successful_runs" in data["metrics"]
        assert "failed_runs" in data["metrics"]

    def test_status_includes_active_incidents(self):
        """Status deve incluir incidentes ativos."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_incidents" in data
        assert isinstance(data["active_incidents"], list)

    def test_status_includes_pending_approvals(self):
        """Status deve incluir aprovações pendentes."""
        response = client.get("/api/v2/brands/brand-001/recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "pending_approvals" in data
        assert isinstance(data["pending_approvals"], list)


class TestRecoveryRunEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/run."""

    def test_run_starts_new_recovery(self):
        """Run deve iniciar novo recovery."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["brand_id"] == "brand-001"
        assert "plan" in data
        assert data["status"] in ["started", "pending_approval"]

    def test_run_low_severity_auto_executes(self):
        """Run com severidade LOW deve auto-executar."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["auto_executed"] is True

    def test_run_high_severity_requires_approval(self):
        """Run com severidade HIGH deve requerer aprovação."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_approval"
        assert data["requires_approval"] is True
        assert "approval_request_id" in data


class TestRecoveryEventsEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para GET /api/v2/brands/{brand_id}/recovery/events."""

    def test_events_returns_list(self):
        """Events deve retornar lista de eventos."""
        response = client.get("/api/v2/brands/brand-001/recovery/events")
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)
        assert "total" in data

    def test_events_supports_pagination(self):
        """Events deve suportar paginação."""
        response = client.get("/api/v2/brands/brand-001/recovery/events?limit=10&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0


class TestRecoveryApproveEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/approve/{request_id}."""

    def test_approve_starts_recovery(self):
        """Approve deve iniciar recovery pendente."""
        # First create a pending recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        run_data = run_response.json()
        approval_request_id = run_data["approval_request_id"]
        
        # Now approve it
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/approve/{approval_request_id}",
            json={"approved_by": "user-001", "reason": "Approved for execution"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["approval_request_id"] == approval_request_id
        assert data["status"] == "approved"
        assert data["recovery_status"] == "started"

    def test_approve_nonexistent_returns_404(self):
        """Approve de request inexistente deve retornar 404."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/approve/nonexistent",
            json={"approved_by": "user-001"}
        )
        
        assert response.status_code == 404


class TestRecoveryRejectEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/reject/{request_id}."""

    def test_reject_cancels_recovery(self):
        """Reject deve cancelar recovery pendente."""
        # First create a pending recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "high"}
        )
        run_data = run_response.json()
        approval_request_id = run_data["approval_request_id"]
        
        # Now reject it
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/reject/{approval_request_id}",
            json={"rejected_by": "user-001", "reason": "Risk too high"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["approval_request_id"] == approval_request_id
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Risk too high"


class TestRecoveryFreezeEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/freeze/{incident_id}."""

    def test_freeze_stops_recovery(self):
        """Freeze deve parar recovery em execução."""
        # First start a recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        run_data = run_response.json()
        incident_id = run_data["incident_id"]
        
        # Now freeze it
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/freeze/{incident_id}",
            json={"reason": "Investigating side effects"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["incident_id"] == incident_id
        assert data["status"] == "frozen"
        assert data["frozen_at"] is not None

    def test_freeze_nonexistent_returns_404(self):
        """Freeze de incidente inexistente deve retornar 404."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/freeze/nonexistent",
            json={"reason": "Test"}
        )
        
        assert response.status_code == 404


class TestRecoveryRollbackEndpoint:
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    """Testes para POST /api/v2/brands/{brand_id}/recovery/rollback/{run_id}."""

    def test_rollback_reverts_recovery(self):
        """Rollback deve reverter ações do recovery."""
        # First complete a recovery
        run_response = client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        run_data = run_response.json()
        run_id = run_data["run_id"]
        
        # Now rollback
        response = client.post(
            f"/api/v2/brands/brand-001/recovery/rollback/{run_id}",
            json={"reason": "Recovery caused issues"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["status"] == "rolled_back"
        assert "rolled_back_at" in data
        assert "affected_steps" in data

    def test_rollback_nonexistent_returns_404(self):
        """Rollback de run inexistente deve retornar 404."""
        response = client.post(
            "/api/v2/brands/brand-001/recovery/rollback/nonexistent",
            json={"reason": "Test"}
        )
        
        assert response.status_code == 404


class TestRecoveryMetrics:
    """Testes para métricas de recovery."""
    
    def setup_method(self):
        """Reset state before each test."""
        _reset_state()

    def test_metrics_tracked_after_run(self):
        """Métricas devem ser atualizadas após run."""
        # Initial state
        status_response = client.get("/api/v2/brands/brand-001/recovery/status")
        initial_metrics = status_response.json()["metrics"]
        initial_total = initial_metrics["total_runs"]
        
        # Run recovery
        client.post(
            "/api/v2/brands/brand-001/recovery/run",
            json={"incident_type": "handoff_timeout", "severity": "low"}
        )
        
        # Check metrics updated
        status_response = client.get("/api/v2/brands/brand-001/recovery/status")
        updated_metrics = status_response.json()["metrics"]
        
        assert updated_metrics["total_runs"] == initial_total + 1
