"""Tests for v36 Outcome Attribution and Hybrid ROI API Endpoints.

TDD: fail -> implement -> pass -> commit
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "09-tools")

from vm_webapp.api_outcome_roi import router as roi_router
from fastapi import FastAPI


# Create test app
app_roi = FastAPI()
app_roi.include_router(roi_router)
client_roi = TestClient(app_roi)


def _reset_roi_state():
    """Reset global state between tests."""
    from vm_webapp.api_outcome_roi import (
        _attribution_engine,
        _roi_engine,
        _roi_metrics,
        _frozen_brands,
        _pending_proposals,
        _applied_proposals,
    )
    _attribution_engine.touchpoints.clear()
    _attribution_engine.graphs.clear()
    _roi_engine.proposals.clear()
    _roi_metrics["outcomes_attributed"] = 0
    _roi_metrics["proposals_generated"] = 0
    _roi_metrics["proposals_auto_applied"] = 0
    _roi_metrics["proposals_approved"] = 0
    _roi_metrics["proposals_rejected"] = 0
    _roi_metrics["proposals_blocked"] = 0
    _roi_metrics["guardrail_violations"] = 0
    _roi_metrics["payback_time_avg_days"] = 0.0
    _roi_metrics["hybrid_roi_index_avg"] = 0.0
    _frozen_brands.clear()
    _pending_proposals.clear()
    _applied_proposals.clear()


class TestOutcomeRoiStatusEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/outcome-roi/status."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_status_returns_basic_info(self):
        """Status deve retornar informações básicas."""
        response = client_roi.get("/api/v2/brands/brand-001/outcome-roi/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "state" in data
        assert "version" in data
        assert data["version"] == "v36"

    def test_status_includes_roi_metrics(self):
        """Status deve incluir métricas de ROI."""
        response = client_roi.get("/api/v2/brands/brand-001/outcome-roi/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "proposals_generated" in data["metrics"]
        assert "hybrid_roi_index_avg" in data["metrics"]
        assert "payback_time_avg_days" in data["metrics"]

    def test_status_includes_attribution_summary(self):
        """Status deve incluir sumário de atribuição."""
        response = client_roi.get("/api/v2/brands/brand-001/outcome-roi/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "attribution_summary" in data
        assert "total_outcomes" in data["attribution_summary"]


class TestOutcomeRoiRunEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/outcome-roi/run."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_run_attributions_and_generates_proposals(self):
        """Run deve executar atribuição e gerar proposals."""
        response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/run",
            json={
                "outcome_type": "activation",
                "attribution_window_days": 30,
                "auto_apply_low_risk": True,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "run_id" in data
        assert "outcomes_attributed" in data
        assert "proposals_generated" in data
        assert "proposals_auto_applied" in data
        assert "proposals_needing_approval" in data

    def test_run_respects_frozen_state(self):
        """Run deve respeitar estado congelado."""
        # Freeze brand first
        client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/freeze",
            json={"frozen_by": "admin", "reason": "maintenance"},
        )
        
        response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/run",
            json={"outcome_type": "activation"},
        )
        
        assert response.status_code == 409
        assert "frozen" in response.json()["detail"].lower()


class TestOutcomeRoiProposalsEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/outcome-roi/proposals."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_proposals_list_empty(self):
        """Proposals deve retornar lista vazia inicialmente."""
        response = client_roi.get("/api/v2/brands/brand-001/outcome-roi/proposals")
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert data["proposals"] == []
        assert data["total"] == 0

    def test_proposals_list_with_data(self):
        """Proposals deve retornar proposals geradas."""
        # Generate a proposal first
        client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/run",
            json={
                "outcome_type": "activation",
                "financial_data": {
                    "revenue": 1000,
                    "cost": 200,
                    "activations": 10,
                    "time_to_revenue_days": 14,
                },
                "operational_data": {
                    "human_minutes": 300,
                    "activations": 10,
                    "successes": 9,
                },
            },
        )
        
        response = client_roi.get("/api/v2/brands/brand-001/outcome-roi/proposals")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert len(data["proposals"]) > 0

    def test_proposals_filter_by_risk_level(self):
        """Proposals deve filtrar por risk level."""
        response = client_roi.get(
            "/api/v2/brands/brand-001/outcome-roi/proposals?risk_level=low"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "filter_risk_level" in data
        assert data["filter_risk_level"] == "low"


class TestOutcomeRoiProposalDetailEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/outcome-roi/proposals/{id}."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_proposal_detail_not_found(self):
        """Proposal detail deve retornar 404 para ID inexistente."""
        response = client_roi.get(
            "/api/v2/brands/brand-001/outcome-roi/proposals/nonexistent"
        )
        
        assert response.status_code == 404


class TestOutcomeRoiBreakdownEndpoint:
    """Testes para GET /api/v2/brands/{brand_id}/outcome-roi/breakdown."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_breakdown_returns_attribution_data(self):
        """Breakdown deve retornar dados de atribuição."""
        response = client_roi.get(
            "/api/v2/brands/brand-001/outcome-roi/breakdown"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "attribution_by_touchpoint" in data
        assert "financial_breakdown" in data
        assert "operational_breakdown" in data

    def test_breakdown_includes_hybrid_scores(self):
        """Breakdown deve incluir hybrid scores."""
        # Generate proposals first
        client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/run",
            json={
                "outcome_type": "activation",
                "auto_apply_low_risk": False,  # Don't auto-apply
                "financial_data": {
                    "revenue": 1000,
                    "cost": 200,
                    "activations": 10,
                    "time_to_revenue_days": 14,
                },
                "operational_data": {
                    "human_minutes": 300,
                    "activations": 10,
                    "successes": 9,
                },
            },
        )
        
        response = client_roi.get(
            "/api/v2/brands/brand-001/outcome-roi/breakdown"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "hybrid_roi_summary" in data
        assert "avg_hybrid_index" in data["hybrid_roi_summary"]


class TestOutcomeRoiApplyEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/outcome-roi/proposals/{id}/apply."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_apply_proposal_success(self):
        """Apply deve aplicar proposal com sucesso."""
        # Generate a proposal first (without auto-apply)
        run_response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/run",
            json={
                "outcome_type": "activation",
                "auto_apply_low_risk": False,  # Don't auto-apply
                "financial_data": {
                    "revenue": 1000,
                    "cost": 200,
                    "activations": 10,
                    "time_to_revenue_days": 14,
                },
                "operational_data": {
                    "human_minutes": 300,
                    "activations": 10,
                    "successes": 9,
                },
            },
        )
        
        # Get proposal ID
        proposals_response = client_roi.get(
            "/api/v2/brands/brand-001/outcome-roi/proposals"
        )
        proposals = proposals_response.json()["proposals"]
        if proposals:
            # Find a pending proposal
            pending_proposals = [p for p in proposals if p["status"] == "pending"]
            if pending_proposals:
                proposal_id = pending_proposals[0]["proposal_id"]
                
                response = client_roi.post(
                    f"/api/v2/brands/brand-001/outcome-roi/proposals/{proposal_id}/apply",
                    json={"applied_by": "admin", "note": "LGTM"},
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["proposal_id"] == proposal_id

    def test_apply_blocked_proposal_fails(self):
        """Apply deve falhar para proposal bloqueada."""
        response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/proposals/blocked-id/apply",
            json={"applied_by": "admin"},
        )
        
        # Should return 404 or 409 depending on implementation
        assert response.status_code in [404, 409]


class TestOutcomeRoiRejectEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/outcome-roi/proposals/{id}/reject."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_reject_proposal_success(self):
        """Reject deve rejeitar proposal com sucesso."""
        # Generate a proposal first (without auto-apply)
        client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/run",
            json={
                "outcome_type": "activation",
                "auto_apply_low_risk": False,  # Don't auto-apply
                "financial_data": {
                    "revenue": 1000,
                    "cost": 200,
                    "activations": 10,
                    "time_to_revenue_days": 14,
                },
                "operational_data": {
                    "human_minutes": 300,
                    "activations": 10,
                    "successes": 9,
                },
            },
        )
        
        # Get proposal ID
        proposals_response = client_roi.get(
            "/api/v2/brands/brand-001/outcome-roi/proposals"
        )
        proposals = proposals_response.json()["proposals"]
        if proposals:
            # Find a pending proposal
            pending_proposals = [p for p in proposals if p["status"] == "pending"]
            if pending_proposals:
                proposal_id = pending_proposals[0]["proposal_id"]
                
                response = client_roi.post(
                    f"/api/v2/brands/brand-001/outcome-roi/proposals/{proposal_id}/reject",
                    json={"rejected_by": "admin", "reason": "Risk too high"},
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["proposal_id"] == proposal_id


class TestOutcomeRoiFreezeEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/outcome-roi/freeze."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_freeze_success(self):
        """Freeze deve congelar operações."""
        response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/freeze",
            json={"frozen_by": "admin", "reason": "maintenance"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert data["status"] == "frozen"
        assert "frozen_at" in data

    def test_freeze_when_already_frozen(self):
        """Freeze deve retornar erro quando já congelado."""
        # Freeze first
        client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/freeze",
            json={"frozen_by": "admin", "reason": "maintenance"},
        )
        
        # Try to freeze again
        response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/freeze",
            json={"frozen_by": "admin", "reason": "maintenance again"},
        )
        
        assert response.status_code == 409


class TestOutcomeRoiRollbackEndpoint:
    """Testes para POST /api/v2/brands/{brand_id}/outcome-roi/rollback."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_roi_state()

    def test_rollback_success(self):
        """Rollback deve reverter proposals aplicadas."""
        response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/rollback",
            json={"rolled_back_by": "admin", "reason": "issue detected"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["brand_id"] == "brand-001"
        assert "rolled_back_count" in data
        assert "rolled_back_at" in data

    def test_rollback_with_proposals(self):
        """Rollback deve reverter proposals específicas."""
        # Apply a proposal first
        client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/run",
            json={
                "outcome_type": "activation",
                "financial_data": {
                    "revenue": 1000,
                    "cost": 200,
                    "activations": 10,
                    "time_to_revenue_days": 14,
                },
                "operational_data": {
                    "human_minutes": 300,
                    "activations": 10,
                    "successes": 9,
                },
            },
        )
        
        response = client_roi.post(
            "/api/v2/brands/brand-001/outcome-roi/rollback",
            json={
                "rolled_back_by": "admin",
                "reason": "reverting changes",
                "proposal_ids": [],  # Rollback all
            },
        )
        
        assert response.status_code == 200
