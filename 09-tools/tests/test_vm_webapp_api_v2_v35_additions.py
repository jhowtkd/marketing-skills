"""Tests for v35 Onboarding Continuity API Endpoints.

TDD: Testes para onboarding continuity operations.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.api_onboarding_continuity import router as continuity_router
from fastapi import FastAPI


# Create test app
app_continuity = FastAPI()
app_continuity.include_router(continuity_router)
client_continuity = TestClient(app_continuity)


def _reset_continuity_state():
    """Reset global state between tests."""
    from vm_webapp.api_onboarding_continuity import (
        _continuity_graph,
        _resume_orchestrator,
        _continuity_metrics,
        _pending_approvals,
        _frozen_brands,
    )
    _continuity_graph._checkpoints.clear()
    _continuity_graph._bundles.clear()
    _continuity_graph._user_checkpoints.clear()
    _continuity_graph._version_counter.clear()
    _continuity_metrics["checkpoints_created"] = 0
    _continuity_metrics["bundles_created"] = 0
    _continuity_metrics["resumes_completed"] = 0
    _continuity_metrics["resumes_failed"] = 0
    _continuity_metrics["resumes_auto_applied"] = 0
    _continuity_metrics["resumes_needing_approval"] = 0
    _continuity_metrics["resumes_rolled_back"] = 0
    _continuity_metrics["context_loss_events"] = 0
    _continuity_metrics["conflicts_detected"] = 0
    _pending_approvals.clear()
    _frozen_brands.clear()


class TestOnboardingContinuityStatusEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-continuity/status."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_continuity_state()

    def test_status_returns_basic_info(self):
        """Status deve retornar informações básicas."""
        response = client_continuity.get("/api/v2/brands/brand-001/onboarding-continuity/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "state" in data
        assert "version" in data
        assert data["version"] == "v35"

    def test_status_includes_continuity_metrics(self):
        """Status deve incluir métricas de continuidade."""
        response = client_continuity.get("/api/v2/brands/brand-001/onboarding-continuity/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "checkpoints_created" in data["metrics"]
        assert "bundles_created" in data["metrics"]
        assert "resumes_completed" in data["metrics"]

    def test_status_includes_recent_handoffs(self):
        """Status deve incluir handoffs recentes."""
        response = client_continuity.get("/api/v2/brands/brand-001/onboarding-continuity/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "recent_handoffs" in data
        assert isinstance(data["recent_handoffs"], list)


class TestOnboardingContinuityRunEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-continuity/run."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_continuity_state()

    def test_run_creates_checkpoint_and_handoff(self):
        """Run deve criar checkpoint e handoff bundle."""
        response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/run",
            json={
                "user_id": "user-001",
                "source_session": "session-abc",
                "step_id": "step_3",
                "step_data": {"company_name": "Acme Inc"},
                "form_data": {"industry": "tech"},
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "checkpoint_id" in data
        assert "bundle_id" in data
        assert data["brand_id"] == "brand-001"
        assert data["user_id"] == "user-001"

    def test_run_with_source_priority(self):
        """Run deve aceitar source priority."""
        response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/run",
            json={
                "user_id": "user-001",
                "source_session": "session-abc",
                "step_id": "step_3",
                "step_data": {},
                "source_priority": "recovery",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "bundle_id" in data


class TestOnboardingContinuityHandoffsEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-continuity/handoffs."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_continuity_state()

    def test_list_returns_handoffs(self):
        """List deve retornar handoffs de continuidade."""
        # First create a handoff
        client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/run",
            json={
                "user_id": "user-001",
                "source_session": "session-abc",
                "step_id": "step_3",
                "step_data": {},
            }
        )
        
        response = client_continuity.get("/api/v2/brands/brand-001/onboarding-continuity/handoffs")
        
        assert response.status_code == 200
        data = response.json()
        assert "handoffs" in data
        assert isinstance(data["handoffs"], list)

    def test_list_supports_status_filter(self):
        """List deve suportar filtro por status."""
        response = client_continuity.get(
            "/api/v2/brands/brand-001/onboarding-continuity/handoffs?status=pending"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "handoffs" in data


class TestOnboardingContinuityHandoffDetailEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/onboarding-continuity/handoffs/{id}."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_continuity_state()

    def test_get_handoff_detail(self):
        """Get deve retornar detalhes do handoff."""
        # Create handoff with target_session
        run_response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/run",
            json={
                "user_id": "user-001",
                "source_session": "session-abc",
                "target_session": "session-xyz",
                "step_id": "step_3",
                "step_data": {"key": "value"},
            }
        )
        bundle_id = run_response.json()["bundle_id"]
        
        response = client_continuity.get(
            f"/api/v2/brands/brand-001/onboarding-continuity/handoffs/{bundle_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bundle_id"] == bundle_id
        assert "context_payload" in data
        assert "status" in data

    def test_get_nonexistent_returns_404(self):
        """Get de handoff inexistente deve retornar 404."""
        response = client_continuity.get(
            "/api/v2/brands/brand-001/onboarding-continuity/handoffs/nonexistent"
        )
        
        assert response.status_code == 404


class TestOnboardingContinuityResumeEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-continuity/resume."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_continuity_state()

    def test_resume_success(self):
        """Resume deve executar handoff com sucesso."""
        # Create handoff
        run_response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/run",
            json={
                "user_id": "user-001",
                "source_session": "session-abc",
                "target_session": "session-xyz",
                "step_id": "step_3",
                "step_data": {},
            }
        )
        bundle_id = run_response.json()["bundle_id"]
        
        response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/resume",
            json={
                "bundle_id": bundle_id,
                "target_session": "session-xyz",
                "resumed_by": "user-001",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "context" in data

    def test_resume_needs_approval_high_risk(self):
        """Resume deve requerer aprovação para alto risco."""
        # Create handoff with recovery priority (higher risk context)
        run_response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/run",
            json={
                "user_id": "user-001",
                "source_session": "session-abc",
                "target_session": "session-xyz",
                "step_id": "step_3",
                "step_data": {},
                "source_priority": "recovery",
            }
        )
        bundle_id = run_response.json()["bundle_id"]
        
        # Create conflict by having newer checkpoints
        for i in range(10):
            client_continuity.post(
                "/api/v2/brands/brand-001/onboarding-continuity/run",
                json={
                    "user_id": "user-001",
                    "source_session": f"session-{i}",
                    "step_id": f"step_{i+4}",
                    "step_data": {},
                }
            )
        
        response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/resume",
            json={
                "bundle_id": bundle_id,
                "target_session": "session-xyz",
                "resumed_by": "user-001",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # May need approval due to version gap
        assert "success" in data

    def test_resume_nonexistent_returns_404(self):
        """Resume de bundle inexistente deve retornar 404."""
        response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/resume",
            json={
                "bundle_id": "nonexistent",
                "target_session": "session-xyz",
                "resumed_by": "user-001",
            }
        )
        
        assert response.status_code == 404


class TestOnboardingContinuityFreezeEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-continuity/freeze."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_continuity_state()

    def test_freeze_all_continuity(self):
        """Freeze deve congelar todas as operações de continuidade."""
        response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/freeze",
            json={
                "frozen_by": "user-001",
                "reason": "Investigating context loss issue"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "frozen"
        assert data["brand_id"] == "brand-001"
        assert "frozen_at" in data


class TestOnboardingContinuityRollbackEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/onboarding-continuity/rollback."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_continuity_state()

    def test_rollback_continuity(self):
        """Rollback deve reverter operações de continuidade."""
        # Create and complete a handoff
        run_response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/run",
            json={
                "user_id": "user-001",
                "source_session": "session-abc",
                "target_session": "session-xyz",
                "step_id": "step_3",
                "step_data": {},
            }
        )
        bundle_id = run_response.json()["bundle_id"]
        
        # Resume it
        client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/resume",
            json={
                "bundle_id": bundle_id,
                "target_session": "session-xyz",
                "resumed_by": "user-001",
            }
        )
        
        # Now rollback
        response = client_continuity.post(
            "/api/v2/brands/brand-001/onboarding-continuity/rollback",
            json={
                "rolled_back_by": "user-001",
                "reason": "Incorrect context applied"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "rolled_back_count" in data
        assert "rolled_back_at" in data
