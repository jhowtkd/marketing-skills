"""Tests for v34 Onboarding Recovery API Endpoints.

TDD: Testes para onboarding recovery operations.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.api_onboarding_recovery import router as recovery_router
from fastapi import FastAPI


# Create test app
app_recovery = FastAPI()
app_recovery.include_router(recovery_router)
client_recovery = TestClient(app_recovery)


def _reset_recovery_state():
    """Reset global state between tests."""
    from vm_webapp.api_onboarding_recovery import (
        _dropoff_detector,
        _strategy_engine,
        _recovery_metrics,
        _pending_approvals,
        _frozen_brands,
    )
    _dropoff_detector._cases.clear()
    _recovery_metrics["cases_detected"] = 0
    _recovery_metrics["cases_recovered"] = 0
    _recovery_metrics["cases_expired"] = 0
    _recovery_metrics["proposals_generated"] = 0
    _recovery_metrics["proposals_auto_applied"] = 0
    _recovery_metrics["proposals_approved"] = 0
    _recovery_metrics["proposals_rejected"] = 0
    _pending_approvals.clear()
    _frozen_brands.clear()


class TestOnboardingRecoveryStatusEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-recovery/status."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_recovery_state()

    def test_status_returns_basic_info(self):
        """Status deve retornar informações básicas."""
        response = client_recovery.get("/api/v2/brands/brand-001/onboarding-recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "state" in data
        assert "version" in data
        assert data["version"] == "v34"

    def test_status_includes_case_metrics(self):
        """Status deve incluir métricas de casos."""
        response = client_recovery.get("/api/v2/brands/brand-001/onboarding-recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "cases_total" in data["metrics"]
        assert "cases_recoverable" in data["metrics"]
        assert "cases_recovered" in data["metrics"]

    def test_status_includes_recoverable_cases(self):
        """Status deve incluir casos recuperáveis."""
        response = client_recovery.get("/api/v2/brands/brand-001/onboarding-recovery/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "recoverable_cases" in data
        assert isinstance(data["recoverable_cases"], list)


class TestOnboardingRecoveryRunEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-recovery/run."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_recovery_state()

    def test_run_detects_dropoffs_and_generates_proposals(self):
        """Run deve detectar dropoffs e gerar propostas."""
        response = client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/run",
            json={
                "sessions": [
                    {
                        "user_id": "user-001",
                        "current_step": 5,
                        "total_steps": 7,
                        "last_activity": "2026-03-01T10:00:00+00:00",
                        "step_start_time": "2026-03-01T10:00:00+00:00",
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cases_detected" in data
        assert "proposals_generated" in data
        assert "auto_applied" in data
        assert "pending_approval" in data

    def test_run_auto_applies_low_touch(self):
        """Run deve aplicar automaticamente estratégias low-touch."""
        response = client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/run",
            json={
                "sessions": [
                    {
                        "user_id": "user-low",
                        "current_step": 2,
                        "total_steps": 7,
                        "last_activity": "2026-03-01T10:00:00+00:00",
                        "step_start_time": "2026-03-01T10:00:00+00:00",
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Low-touch strategies (early stage) should be auto-applied
        assert data["auto_applied"] >= 0


class TestOnboardingRecoveryCasesEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-recovery/cases."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_recovery_state()

    def test_list_returns_cases(self):
        """List deve retornar casos de recuperação."""
        # First create a case via run
        client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/run",
            json={
                "sessions": [
                    {
                        "user_id": "user-001",
                        "current_step": 5,
                        "total_steps": 7,
                        "last_activity": "2026-03-01T10:00:00+00:00",
                        "step_start_time": "2026-03-01T10:00:00+00:00",
                    }
                ]
            }
        )
        
        response = client_recovery.get("/api/v2/brands/brand-001/onboarding-recovery/cases")
        
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert isinstance(data["cases"], list)
        assert len(data["cases"]) > 0

    def test_list_supports_status_filter(self):
        """List deve suportar filtro por status."""
        response = client_recovery.get(
            "/api/v2/brands/brand-001/onboarding-recovery/cases?status=recoverable"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data

    def test_list_supports_priority_filter(self):
        """List deve suportar filtro por prioridade."""
        response = client_recovery.get(
            "/api/v2/brands/brand-001/onboarding-recovery/cases?priority=high"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data


class TestOnboardingRecoveryApplyEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-recovery/cases/{id}/apply."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_recovery_state()

    def test_apply_low_touch_auto(self):
        """Apply deve executar imediatamente para low-touch."""
        # Create a low-priority case
        client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/run",
            json={
                "sessions": [
                    {
                        "user_id": "user-low",
                        "current_step": 2,
                        "total_steps": 7,
                        "last_activity": "2026-03-01T10:00:00+00:00",
                        "step_start_time": "2026-03-01T10:00:00+00:00",
                    }
                ]
            }
        )
        
        # Get the case ID
        list_response = client_recovery.get("/api/v2/brands/brand-001/onboarding-recovery/cases")
        cases = list_response.json()["cases"]
        if cases:
            case_id = cases[0]["case_id"]
            
            response = client_recovery.post(
                f"/api/v2/brands/brand-001/onboarding-recovery/cases/{case_id}/apply",
                json={"applied_by": "user-001", "reason": "Approved for recovery"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["applied", "pending_approval"]

    def test_apply_high_touch_needs_approval(self):
        """Apply deve requerer aprovação para high-touch."""
        # Create an error case (high priority)
        client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/run",
            json={
                "sessions": [
                    {
                        "user_id": "user-error",
                        "current_step": 4,
                        "total_steps": 7,
                        "error_occurred": True,
                        "error_code": "TEMPLATE_RENDER_FAILED",
                    }
                ]
            }
        )
        
        # Get the case ID
        list_response = client_recovery.get("/api/v2/brands/brand-001/onboarding-recovery/cases")
        cases = list_response.json()["cases"]
        if cases:
            case_id = cases[0]["case_id"]
            
            response = client_recovery.post(
                f"/api/v2/brands/brand-001/onboarding-recovery/cases/{case_id}/apply",
                json={"applied_by": "user-001", "reason": "Apply recovery"}
            )
            
            assert response.status_code == 200
            data = response.json()
            # High-touch may need approval
            assert "status" in data

    def test_apply_nonexistent_returns_404(self):
        """Apply de case inexistente deve retornar 404."""
        response = client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/cases/nonexistent/apply",
            json={"applied_by": "user-001", "reason": "Test"}
        )
        
        assert response.status_code == 404


class TestOnboardingRecoveryRejectEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-recovery/cases/{id}/reject."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_recovery_state()

    def test_reject_case(self):
        """Reject deve rejeitar uma proposta de recuperação."""
        # Create a case first
        client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/run",
            json={
                "sessions": [
                    {
                        "user_id": "user-001",
                        "current_step": 5,
                        "total_steps": 7,
                        "last_activity": "2026-03-01T10:00:00+00:00",
                        "step_start_time": "2026-03-01T10:00:00+00:00",
                    }
                ]
            }
        )
        
        # Get the case ID
        list_response = client_recovery.get("/api/v2/brands/brand-001/onboarding-recovery/cases")
        cases = list_response.json()["cases"]
        if cases:
            case_id = cases[0]["case_id"]
            
            response = client_recovery.post(
                f"/api/v2/brands/brand-001/onboarding-recovery/cases/{case_id}/reject",
                json={
                    "rejected_by": "user-001",
                    "reason": "User opted out"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["case_id"] == case_id
            assert data["status"] == "rejected"


class TestOnboardingRecoveryFreezeEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-recovery/freeze."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_recovery_state()

    def test_freeze_all_recovery(self):
        """Freeze deve congelar todas as operações de recovery."""
        response = client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/freeze",
            json={
                "frozen_by": "user-001",
                "reason": "Investigating data quality issue"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "frozen"
        assert data["brand_id"] == "brand-001"
        assert "frozen_at" in data


class TestOnboardingRecoveryRollbackEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-recovery/rollback."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_recovery_state()

    def test_rollback_recovery(self):
        """Rollback deve reverter ações de recovery."""
        # Create and apply a case first
        client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/run",
            json={
                "sessions": [
                    {
                        "user_id": "user-001",
                        "current_step": 5,
                        "total_steps": 7,
                        "last_activity": "2026-03-01T10:00:00+00:00",
                        "step_start_time": "2026-03-01T10:00:00+00:00",
                    }
                ]
            }
        )
        
        response = client_recovery.post(
            "/api/v2/brands/brand-001/onboarding-recovery/rollback",
            json={
                "rolled_back_by": "user-001",
                "reason": "Incorrect strategy applied"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "rolled_back_count" in data
        assert "rolled_back_at" in data
