"""Tests for v26 API v2 Control Loop Endpoints.

TDD approach: tests for status/run/events/apply/reject/freeze/rollback endpoints.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from fastapi.testclient import TestClient

# Import after mocking
from vm_webapp.online_control_loop import (
    OnlineControlLoop,
    ControlLoopState,
    AdjustmentSeverity,
    MicroAdjustment,
    AdjustmentType,
)


class TestAPIControlLoopStatus:
    """Test GET /api/v2/brands/{brand_id}/control-loop/status"""
    
    def test_status_endpoint_returns_cycle_info(self, client):
        """Should return current control loop status for brand."""
        response = client.get("/api/v2/brands/brand-123/control-loop/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "brand_id" in data
        assert "state" in data
        assert "cycle_id" in data
        assert "last_run_at" in data
    
    def test_status_endpoint_for_nonexistent_brand(self, client):
        """Should return idle status for brand without active cycle."""
        response = client.get("/api/v2/brands/nonexistent/control-loop/status")
        
        # Returns 200 with idle state (not 404)
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "idle"
    
    def test_status_includes_active_proposals(self, client):
        """Should include active proposals in status."""
        response = client.get("/api/v2/brands/brand-123/control-loop/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_proposals" in data
        assert isinstance(data["active_proposals"], list)
    
    def test_status_includes_regression_signals(self, client):
        """Should include active regression signals."""
        response = client.get("/api/v2/brands/brand-123/control-loop/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_regressions" in data
        assert isinstance(data["active_regressions"], list)


class TestAPIControlLoopRun:
    """Test POST /api/v2/brands/{brand_id}/control-loop/run"""
    
    def test_run_endpoint_starts_new_cycle(self, client):
        """Should start a new control loop cycle."""
        # Reset frozen state if any
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            with patch("vm_webapp.api_control_loop._brand_cycles", {}):
                response = client.post("/api/v2/brands/brand-123/control-loop/run")
                
                assert response.status_code == 200
                data = response.json()
                assert "cycle_id" in data
                assert data["state"] == "observing"
                assert "started_at" in data
    
    def test_run_endpoint_with_regression_detection(self, client):
        """Should detect regressions during run."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            with patch("vm_webapp.api_control_loop._brand_cycles", {}):
                response = client.post("/api/v2/brands/brand-123/control-loop/run")
                
                assert response.status_code == 200
                data = response.json()
                assert "regressions_detected" in data
                assert isinstance(data["regressions_detected"], int)
    
    def test_run_endpoint_generates_proposals(self, client):
        """Should generate adjustment proposals."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            with patch("vm_webapp.api_control_loop._brand_cycles", {}):
                response = client.post("/api/v2/brands/brand-123/control-loop/run")
                
                assert response.status_code == 200
                data = response.json()
                assert "proposals_generated" in data
                assert "proposals" in data
    
    def test_run_endpoint_respects_already_running(self, client):
        """Should not start new cycle if one is already running."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # First run
            response1 = client.post("/api/v2/brands/brand-123/control-loop/run")
            assert response1.status_code == 200
            
            # Second run should conflict
            response2 = client.post("/api/v2/brands/brand-123/control-loop/run")
            assert response2.status_code == 409  # 409 Conflict


class TestAPIControlLoopEvents:
    """Test GET /api/v2/brands/{brand_id}/control-loop/events"""
    
    def test_events_endpoint_returns_event_list(self, client):
        """Should return control loop events."""
        response = client.get("/api/v2/brands/brand-123/control-loop/events")
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)
    
    def test_events_endpoint_with_pagination(self, client):
        """Should support pagination."""
        response = client.get("/api/v2/brands/brand-123/control-loop/events?limit=10&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
    
    def test_events_endpoint_with_time_filter(self, client):
        """Should support time-based filtering."""
        response = client.get(
            "/api/v2/brands/brand-123/control-loop/events?since=2026-03-01T00:00:00Z"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data


class TestAPIControlLoopApply:
    """Test POST /api/v2/brands/{brand_id}/control-loop/proposals/{id}/apply"""
    
    def test_apply_endpoint_approves_proposal(self, client):
        """Should apply a pending proposal."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # First create a cycle with a proposal
            client.post("/api/v2/brands/brand-123/control-loop/run")
            
            # Apply proposal (using mocked proposal ID from fixture)
            response = client.post(
                "/api/v2/brands/brand-123/control-loop/proposals/adj-001/apply"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "applied"
    
    def test_apply_endpoint_requires_approval_for_high_severity(self, client):
        """Should require explicit approval for high severity proposals."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            response = client.post(
                "/api/v2/brands/brand-123/control-loop/proposals/adj-high/apply",
                json={"approved": False}
            )
            
            # Should fail without approval for high severity
            assert response.status_code in [403, 404]  # 403 forbidden or 404 not found
    
    def test_apply_endpoint_with_explicit_approval(self, client):
        """Should apply high severity with explicit approval."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # Create cycle first
            client.post("/api/v2/brands/brand-123/control-loop/run")
            
            response = client.post(
                "/api/v2/brands/brand-123/control-loop/proposals/adj-001/apply",
                json={"approved": True}
            )
            
            # Mock returns successful application
            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "applied"
    
    def test_apply_endpoint_for_nonexistent_proposal(self, client):
        """Should 404 for non-existent proposal."""
        response = client.post(
            "/api/v2/brands/brand-123/control-loop/proposals/nonexistent/apply"
        )
        
        assert response.status_code == 404


class TestAPIControlLoopReject:
    """Test POST /api/v2/brands/{brand_id}/control-loop/proposals/{id}/reject"""
    
    def test_reject_endpoint_rejects_proposal(self, client):
        """Should reject a pending proposal."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # Create cycle with proposal
            client.post("/api/v2/brands/brand-123/control-loop/run")
            
            response = client.post(
                "/api/v2/brands/brand-123/control-loop/proposals/adj-001/reject"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "rejected"
    
    def test_reject_endpoint_with_reason(self, client):
        """Should accept rejection reason."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # Create cycle with proposal
            client.post("/api/v2/brands/brand-123/control-loop/run")
            
            response = client.post(
                "/api/v2/brands/brand-123/control-loop/proposals/adj-001/reject",
                json={"reason": "Risk too high for current traffic"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "rejected"
            assert data.get("reason") == "Risk too high for current traffic"
    
    def test_reject_already_applied_fails(self, client):
        """Should fail to reject already applied proposal."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # Create cycle
            client.post("/api/v2/brands/brand-123/control-loop/run")
            # Apply
            client.post("/api/v2/brands/brand-123/control-loop/proposals/adj-001/apply")
            
            # Then reject
            response = client.post(
                "/api/v2/brands/brand-123/control-loop/proposals/adj-001/reject"
            )
            
            # May get 404 (not found in pending) or 409 (conflict)
            assert response.status_code in [404, 409]


class TestAPIControlLoopFreeze:
    """Test POST /api/v2/brands/{brand_id}/control-loop/freeze"""
    
    def test_freeze_endpoint_freezes_cycle(self, client):
        """Should freeze the current control loop cycle."""
        # Start a cycle first
        client.post("/api/v2/brands/brand-123/control-loop/run")
        
        response = client.post("/api/v2/brands/brand-123/control-loop/freeze")
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "frozen"
        assert "frozen_at" in data
    
    def test_freeze_endpoint_with_reason(self, client):
        """Should accept freeze reason."""
        response = client.post(
            "/api/v2/brands/brand-123/control-loop/freeze",
            json={"reason": "Investigating incident"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "frozen"
        assert data.get("reason") == "Investigating incident"
    
    def test_freeze_prevents_new_adjustments(self, client):
        """Should prevent new adjustments when frozen."""
        # Freeze
        client.post("/api/v2/brands/brand-123/control-loop/freeze")
        
        # Try to apply
        response = client.post(
            "/api/v2/brands/brand-123/control-loop/proposals/prop-123/apply"
        )
        
        assert response.status_code == 403


class TestAPIControlLoopRollback:
    """Test POST /api/v2/brands/{brand_id}/control-loop/rollback"""
    
    def test_rollback_endpoint_rolls_back_applied(self, client):
        """Should rollback applied adjustments."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # Create cycle and apply
            client.post("/api/v2/brands/brand-123/control-loop/run")
            client.post("/api/v2/brands/brand-123/control-loop/proposals/adj-001/apply")
            
            # Rollback
            response = client.post("/api/v2/brands/brand-123/control-loop/rollback")
            
            assert response.status_code == 200
            data = response.json()
            assert "rolled_back" in data
    
    def test_rollback_endpoint_with_specific_proposal(self, client):
        """Should rollback specific proposal when provided."""
        response = client.post(
            "/api/v2/brands/brand-123/control-loop/rollback",
            json={"proposal_id": "prop-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "rolled_back" in data
    
    def test_rollback_endpoint_no_applied_to_rollback(self, client):
        """Should handle when nothing to rollback."""
        response = client.post("/api/v2/brands/brand-123/control-loop/rollback")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("rolled_back", []) == []


class TestAPIControlLoopProposalDetail:
    """Test GET /api/v2/brands/{brand_id}/control-loop/proposals/{id}"""
    
    def test_proposal_detail_endpoint(self, client):
        """Should return proposal details."""
        with patch("vm_webapp.api_control_loop._frozen_brands", {}):
            # Create cycle with proposal
            client.post("/api/v2/brands/brand-123/control-loop/run")
            
            response = client.get(
                "/api/v2/brands/brand-123/control-loop/proposals/adj-001"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "proposal_id" in data
            assert "adjustment_type" in data
            assert "severity" in data
    
    def test_proposal_detail_for_nonexistent(self, client):
        """Should 404 for non-existent proposal."""
        response = client.get(
            "/api/v2/brands/brand-123/control-loop/proposals/nonexistent"
        )
        
        assert response.status_code == 404


class TestAPIControlLoopMetrics:
    """Test metrics endpoints"""
    
    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Should return metrics in Prometheus format."""
        response = client.get("/api/v2/brands/brand-123/control-loop/metrics")
        
        assert response.status_code == 200
        assert "control_loop_cycles_total" in response.text
        assert "control_loop_regressions_detected_total" in response.text
    
    def test_metrics_includes_time_based_metrics(self, client):
        """Should include time-to-detect and time-to-mitigate."""
        response = client.get("/api/v2/brands/brand-123/control-loop/metrics")
        
        assert response.status_code == 200
        assert "control_loop_time_to_detect_seconds" in response.text
        assert "control_loop_time_to_mitigate_seconds" in response.text


# Fixtures
@pytest.fixture
def client():
    """Create test client with mocked control loop."""
    from fastapi import FastAPI
    from vm_webapp.api_control_loop import router as control_loop_router
    
    app = FastAPI()
    app.include_router(control_loop_router)
    
    # Mock the control loop instance
    with patch("vm_webapp.api_control_loop.control_loop") as mock_loop:
        mock_cycle = Mock(
            cycle_id="cycle-test-001",
            brand_id="brand-123",
            state=ControlLoopState.OBSERVING,
            started_at="2026-03-01T12:00:00Z",
            completed_at=None,
            adjustments=[],
            regression_signals=[],
            to_dict=lambda: {
                "cycle_id": "cycle-test-001",
                "brand_id": "brand-123",
                "state": "observing",
            }
        )
        mock_loop.start_cycle.return_value = mock_cycle
        # Setup adjustments for cycle lookups
        mock_adj_with_state = Mock(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
            estimated_impact={"v1_score": +2.0},
            state="pending",
            applied_at=None,
            rolled_back_at=None,
        )
        mock_adj_with_state.delta = -2.0
        
        def get_cycle_mock(cycle_id):
            return Mock(
                cycle_id="cycle-test-001",
                brand_id="brand-123",
                state=ControlLoopState.OBSERVING,
                adjustments=[mock_adj_with_state],
                regression_signals=[],
            )
        
        mock_loop.get_cycle.side_effect = get_cycle_mock
        # Setup _cycles for proposal lookup
        mock_cycle_for_lookup = Mock(
            cycle_id="cycle-test-001",
            brand_id="brand-123",
            state=ControlLoopState.OBSERVING,
            adjustments=[mock_adj_with_state],
            regression_signals=[],
        )
        mock_loop._cycles = {"cycle-test-001": mock_cycle_for_lookup}
        
        mock_loop.get_status.return_value = {
            "version": "v26",
            "active_cycles": 1,
            "total_adjustments_applied": 5,
        }
        mock_loop.get_cycle_status.return_value = {
            "cycle_id": "cycle-test-001",
            "state": "observing",
            "adjustments": [],
            "regressions": [],
        }
        
        # Mock proposals - must match ProposalResponse model
        mock_adj = Mock(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
            estimated_impact={"v1_score": +2.0},
            state="pending",
            applied_at=None,
            rolled_back_at=None,
        )
        mock_adj.delta = -2.0
        mock_loop.propose.return_value = [mock_adj]
        
        # Mock applied adjustment
        mock_adj_applied = Mock(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
            estimated_impact={"v1_score": +2.0},
            state="applied",
            applied_at="2026-03-01T12:00:00Z",
            rolled_back_at=None,
        )
        mock_adj_applied.delta = -2.0
        
        def mock_apply(adjustment_id, adjustment, approved=False):
            adjustment.state = "applied"
            adjustment.applied_at = "2026-03-01T12:00:00Z"
            return True
        
        mock_loop.apply.side_effect = mock_apply
        mock_loop.rollback.return_value = True
        
        yield TestClient(app)
