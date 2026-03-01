"""Tests for v26 Online Control Loop - Adaptive Controller.

TDD approach: tests for propose/apply/verify with clamp per cycle.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from vm_webapp.online_control_loop import (
    ControlLoopState,
    AdjustmentType,
    AdjustmentSeverity,
    MicroAdjustment,
    ControlLoopCycle,
    OnlineControlLoop,
)
from vm_webapp.control_loop_sentinel import RegressionSeverity, RegressionSignal


class TestControlLoopEnums:
    """Test enum definitions."""
    
    def test_control_loop_state_values(self):
        """ControlLoopState should have all required states."""
        assert ControlLoopState.IDLE.value == "idle"
        assert ControlLoopState.OBSERVING.value == "observing"
        assert ControlLoopState.DETECTING.value == "detecting"
        assert ControlLoopState.PROPOSING.value == "proposing"
        assert ControlLoopState.APPLYING.value == "applying"
        assert ControlLoopState.VERIFYING.value == "verifying"
        assert ControlLoopState.COMPLETED.value == "completed"
        assert ControlLoopState.BLOCKED.value == "blocked"
        assert ControlLoopState.ROLLING_BACK.value == "rolling_back"
    
    def test_adjustment_type_values(self):
        """AdjustmentType should have all adjustment types."""
        assert AdjustmentType.GATE_THRESHOLD.value == "gate_threshold"
        assert AdjustmentType.TEMPERATURE.value == "temperature"
        assert AdjustmentType.MAX_TOKENS.value == "max_tokens"
        assert AdjustmentType.TIMEOUT.value == "timeout"
        assert AdjustmentType.RETRY_COUNT.value == "retry_count"
    
    def test_adjustment_severity_values(self):
        """AdjustmentSeverity should have all severity levels."""
        assert AdjustmentSeverity.LOW.value == "low"
        assert AdjustmentSeverity.MEDIUM.value == "medium"
        assert AdjustmentSeverity.HIGH.value == "high"


class TestMicroAdjustment:
    """Test MicroAdjustment dataclass."""
    
    def test_micro_adjustment_creation(self):
        """Should create MicroAdjustment with all fields."""
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=72.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
            estimated_impact={"v1_score": +2.0, "approval_rate": -0.01},
        )
        assert adj.adjustment_id == "adj-001"
        assert adj.adjustment_type == AdjustmentType.GATE_THRESHOLD
        assert adj.target_gate == "v1_score_min"
        assert adj.current_value == 70.0
        assert adj.proposed_value == 72.0
        assert adj.delta == 2.0
        assert adj.severity == AdjustmentSeverity.LOW
        assert adj.requires_approval is False
    
    def test_micro_adjustment_delta_calculation(self):
        """Delta should be calculated as proposed - current."""
        adj = MicroAdjustment(
            adjustment_id="adj-002",
            adjustment_type=AdjustmentType.TEMPERATURE,
            target_gate="generation",
            current_value=0.7,
            proposed_value=0.65,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        assert abs(adj.delta - (-0.05)) < 0.0001  # Float comparison with tolerance


class TestControlLoopCycle:
    """Test ControlLoopCycle dataclass."""
    
    def test_cycle_creation(self):
        """Should create cycle with defaults."""
        cycle = ControlLoopCycle(
            cycle_id="cycle-001",
            brand_id="brand-123",
        )
        assert cycle.cycle_id == "cycle-001"
        assert cycle.brand_id == "brand-123"
        assert cycle.state == ControlLoopState.IDLE
        assert cycle.adjustments == []
        assert cycle.applied_adjustments == []
        assert cycle.rolled_back_adjustments == []
    
    def test_cycle_state_transitions(self):
        """Should track state transitions."""
        cycle = ControlLoopCycle(
            cycle_id="cycle-002",
            brand_id="brand-123",
        )
        assert cycle.state == ControlLoopState.IDLE
        
        cycle.state = ControlLoopState.OBSERVING
        assert cycle.state == ControlLoopState.OBSERVING


class TestOnlineControlLoopBasics:
    """Test basic OnlineControlLoop functionality."""
    
    def test_version_constant(self):
        """Should have correct version."""
        loop = OnlineControlLoop()
        assert loop.VERSION == "v26"
    
    def test_initial_state(self):
        """Should initialize with empty state."""
        loop = OnlineControlLoop()
        assert loop._cycles == {}
        assert loop._proposals == {}
        assert loop._active_cycle is None
    
    def test_clamp_limits_constant(self):
        """Should have clamp limits defined."""
        assert OnlineControlLoop.CLAMP_MAX_DELTA_PER_CYCLE == 0.05  # 5%
        assert OnlineControlLoop.CLAMP_MAX_WEEKLY_DELTA == 0.15  # 15%


class TestOnlineControlLoopPropose:
    """Test propose method."""
    
    def test_propose_generates_adjustments(self):
        """Should generate micro-adjustments from regression signals."""
        loop = OnlineControlLoop()
        
        # Create mock regression signals
        signals = [
            RegressionSignal(
                signal_id="sig-001",
                metric_name="v1_score",
                severity="medium",
                detected_at="2026-03-01T12:00:00Z",
                value=65.0,
                baseline=75.0,
                delta_pct=-10.0,
                window_minutes=15,
            ),
        ]
        
        current_params = {
            "v1_score_min": 70.0,
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        
        adjustments = loop.propose(
            brand_id="brand-123",
            signals=signals,
            current_params=current_params,
        )
        
        assert len(adjustments) > 0
        # At least one adjustment should target v1_score_min
        gate_adjustments = [a for a in adjustments if a.target_gate == "v1_score_min"]
        assert len(gate_adjustments) > 0
    
    def test_propose_lowers_gate_for_v1_regression(self):
        """Should propose lowering gate threshold when v1_score regresses."""
        loop = OnlineControlLoop()
        
        signals = [
            RegressionSignal(
                signal_id="sig-002",
                metric_name="v1_score",
                severity="medium",
                detected_at="2026-03-01T12:00:00Z",
                value=65.0,
                baseline=75.0,
                delta_pct=-10.0,
                window_minutes=15,
            ),
        ]
        
        current_params = {"v1_score_min": 70.0}
        
        adjustments = loop.propose(
            brand_id="brand-123",
            signals=signals,
            current_params=current_params,
        )
        
        gate_adj = [a for a in adjustments if a.target_gate == "v1_score_min"][0]
        # Should lower the threshold (reduce gate strictness)
        assert gate_adj.proposed_value < gate_adj.current_value
    
    def test_propose_increases_gate_for_approval_rate_drop(self):
        """Should propose increasing gate strictness when approval_rate drops too much."""
        loop = OnlineControlLoop()
        
        signals = [
            RegressionSignal(
                signal_id="sig-003",
                metric_name="approval_rate",
                severity="medium",
                detected_at="2026-03-01T12:00:00Z",
                value=0.60,
                baseline=0.75,
                delta_pct=-15.0,
                window_minutes=15,
            ),
        ]
        
        current_params = {"v1_score_min": 65.0}
        
        adjustments = loop.propose(
            brand_id="brand-123",
            signals=signals,
            current_params=current_params,
        )
        
        # Should generate adjustments
        assert len(adjustments) > 0
    
    def test_propose_with_incident_rate_increase(self):
        """Should propose adjustments when incident_rate increases."""
        loop = OnlineControlLoop()
        
        signals = [
            RegressionSignal(
                signal_id="sig-004",
                metric_name="incident_rate",
                severity="high",
                detected_at="2026-03-01T12:00:00Z",
                value=0.08,
                baseline=0.03,
                delta_pct=166.0,  # 166% increase
                window_minutes=15,
            ),
        ]
        
        current_params = {"temperature": 0.8, "max_tokens": 2500}
        
        adjustments = loop.propose(
            brand_id="brand-123",
            signals=signals,
            current_params=current_params,
        )
        
        # Should propose lowering temperature or other safety measures
        temp_adj = [a for a in adjustments if a.adjustment_type == AdjustmentType.TEMPERATURE]
        if temp_adj:
            assert temp_adj[0].proposed_value < temp_adj[0].current_value
    
    def test_propose_respects_clamp_limits(self):
        """Proposed adjustments should respect per-cycle clamp limits."""
        loop = OnlineControlLoop()
        
        signals = [
            RegressionSignal(
                signal_id="sig-005",
                metric_name="v1_score",
                severity="high",
                detected_at="2026-03-01T12:00:00Z",
                value=50.0,
                baseline=80.0,
                delta_pct=-37.5,
                window_minutes=15,
            ),
        ]
        
        current_params = {"v1_score_min": 75.0}
        
        adjustments = loop.propose(
            brand_id="brand-123",
            signals=signals,
            current_params=current_params,
        )
        
        # Check that no adjustment exceeds 5% delta
        for adj in adjustments:
            delta_pct = abs(adj.delta / adj.current_value) if adj.current_value != 0 else 0
            assert delta_pct <= OnlineControlLoop.CLAMP_MAX_DELTA_PER_CYCLE + 0.001, \
                f"Adjustment {adj.adjustment_id} exceeds clamp limit"
    
    def test_propose_sets_severity_based_on_regression(self):
        """Should set adjustment severity based on regression severity."""
        loop = OnlineControlLoop()
        
        # Test with HIGH severity regression
        signals_high = [
            RegressionSignal(
                signal_id="sig-006",
                metric_name="v1_score",
                severity="high",
                detected_at="2026-03-01T12:00:00Z",
                value=60.0,
                baseline=80.0,
                delta_pct=-25.0,
                window_minutes=15,
            ),
        ]
        
        adjustments = loop.propose(
            brand_id="brand-123",
            signals=signals_high,
            current_params={"v1_score_min": 75.0},
        )
        
        # HIGH regression should produce MEDIUM or HIGH adjustments
        for adj in adjustments:
            assert adj.severity in [AdjustmentSeverity.MEDIUM, AdjustmentSeverity.HIGH]
            assert adj.requires_approval is True


class TestOnlineControlLoopApply:
    """Test apply method."""
    
    def test_apply_low_severity_auto_applies(self):
        """LOW severity adjustments should auto-apply."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-low-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        result = loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        
        assert result is True
        assert adj.state == "applied"
    
    def test_apply_medium_severity_requires_approval(self):
        """MEDIUM severity should require approval."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-med-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.MEDIUM,
            requires_approval=True,
        )
        
        # Without approval, should fail
        result = loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        assert result is False
        
        # With approval, should succeed
        result = loop.apply(
            adjustment_id=adj.adjustment_id,
            adjustment=adj,
            approved=True,
        )
        assert result is True
        assert adj.state == "applied"
    
    def test_apply_high_severity_requires_approval(self):
        """HIGH severity should require approval."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-high-001",
            adjustment_type=AdjustmentType.TEMPERATURE,
            target_gate="generation",
            current_value=0.8,
            proposed_value=0.7,
            severity=AdjustmentSeverity.HIGH,
            requires_approval=True,
        )
        
        # Without approval, should fail
        result = loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        assert result is False
        
        # With approval, should succeed
        result = loop.apply(
            adjustment_id=adj.adjustment_id,
            adjustment=adj,
            approved=True,
        )
        assert result is True
    
    def test_apply_creates_proposal_record(self):
        """Apply should create proposal record for tracking."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        
        assert adj.adjustment_id in loop._proposals
        proposal = loop._proposals[adj.adjustment_id]
        assert proposal.state == "applied"
        assert proposal.applied_at is not None


class TestOnlineControlLoopVerify:
    """Test verify method."""
    
    def test_verify_detects_successful_mitigation(self):
        """Should detect when regression is mitigated."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        # Apply adjustment
        loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        
        # Verify with improved metrics (regression fixed)
        current_metrics = {"v1_score": 78.0}  # Back to normal
        baseline_metrics = {"v1_score": 75.0}
        
        result = loop.verify(
            adjustment_id=adj.adjustment_id,
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
        )
        
        assert result["success"] is True
        assert result["needs_rollback"] is False
    
    def test_verify_detects_failed_mitigation_needs_rollback(self):
        """Should detect when adjustment failed and rollback needed."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        # Apply adjustment
        loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        
        # Verify with still-bad metrics (regression not fixed)
        current_metrics = {"v1_score": 60.0}  # Still bad
        baseline_metrics = {"v1_score": 75.0}
        
        result = loop.verify(
            adjustment_id=adj.adjustment_id,
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
        )
        
        assert result["success"] is False
        assert result["needs_rollback"] is True
    
    def test_verify_updates_proposal_state(self):
        """Should update proposal state after verification."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        
        current_metrics = {"v1_score": 78.0}
        baseline_metrics = {"v1_score": 75.0}
        
        loop.verify(
            adjustment_id=adj.adjustment_id,
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
        )
        
        proposal = loop._proposals[adj.adjustment_id]
        assert proposal.verified is True
        assert proposal.mitigation_successful is True


class TestOnlineControlLoopRollback:
    """Test rollback method."""
    
    def test_rollback_restores_previous_params(self):
        """Should restore parameters to previous values."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        # Apply then rollback
        loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        result = loop.rollback(adjustment_id=adj.adjustment_id)
        
        assert result is True
        assert adj.state == "rolled_back"
    
    def test_rollback_updates_proposal_state(self):
        """Should update proposal state to rolled_back."""
        loop = OnlineControlLoop()
        
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        loop.apply(adjustment_id=adj.adjustment_id, adjustment=adj)
        loop.rollback(adjustment_id=adj.adjustment_id)
        
        proposal = loop._proposals[adj.adjustment_id]
        assert proposal.state == "rolled_back"
        assert proposal.rolled_back_at is not None
    
    def test_rollback_nonexistent_adjustment_fails(self):
        """Should fail when trying to rollback non-existent adjustment."""
        loop = OnlineControlLoop()
        
        result = loop.rollback(adjustment_id="nonexistent")
        
        assert result is False


class TestOnlineControlLoopCycleManagement:
    """Test cycle management."""
    
    def test_start_cycle_creates_new_cycle(self):
        """Should create new cycle when starting."""
        loop = OnlineControlLoop()
        
        cycle = loop.start_cycle(brand_id="brand-123")
        
        assert cycle.cycle_id is not None
        assert cycle.brand_id == "brand-123"
        assert cycle.state == ControlLoopState.OBSERVING
        assert cycle.cycle_id in loop._cycles
    
    def test_get_cycle_returns_cycle(self):
        """Should return cycle by ID."""
        loop = OnlineControlLoop()
        
        cycle = loop.start_cycle(brand_id="brand-123")
        retrieved = loop.get_cycle(cycle.cycle_id)
        
        assert retrieved is not None
        assert retrieved.cycle_id == cycle.cycle_id
    
    def test_get_cycle_returns_none_for_nonexistent(self):
        """Should return None for non-existent cycle."""
        loop = OnlineControlLoop()
        
        result = loop.get_cycle("nonexistent")
        
        assert result is None
    
    def test_update_cycle_state(self):
        """Should update cycle state."""
        loop = OnlineControlLoop()
        
        cycle = loop.start_cycle(brand_id="brand-123")
        loop.update_cycle_state(cycle.cycle_id, ControlLoopState.PROPOSING)
        
        updated = loop.get_cycle(cycle.cycle_id)
        assert updated.state == ControlLoopState.PROPOSING
    
    def test_add_adjustment_to_cycle(self):
        """Should add adjustment to cycle."""
        loop = OnlineControlLoop()
        
        cycle = loop.start_cycle(brand_id="brand-123")
        
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        loop.add_adjustment_to_cycle(cycle.cycle_id, adj)
        
        updated = loop.get_cycle(cycle.cycle_id)
        assert len(updated.adjustments) == 1
        assert updated.adjustments[0].adjustment_id == "adj-001"


class TestOnlineControlLoopWeeklyClamp:
    """Test weekly clamp tracking."""
    
    def test_get_weekly_delta_tracks_adjustments(self):
        """Should track accumulated weekly delta."""
        loop = OnlineControlLoop()
        
        # Apply some adjustments
        adj1 = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,  # -2
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        adj2 = MicroAdjustment(
            adjustment_id="adj-002",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=68.0,
            proposed_value=66.0,  # -2 more
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        loop.apply(adjustment_id=adj1.adjustment_id, adjustment=adj1)
        loop.apply(adjustment_id=adj2.adjustment_id, adjustment=adj2)
        
        weekly_delta = loop.get_weekly_delta("v1_score_min")
        assert weekly_delta == -4.0  # Total -4 from original
    
    def test_weekly_clamp_prevents_excessive_adjustments(self):
        """Should not allow adjustments that exceed weekly clamp."""
        loop = OnlineControlLoop()
        
        # First, apply a large adjustment (close to weekly limit)
        adj1 = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=100.0,
            proposed_value=86.0,  # -14%, close to 15% limit
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        result = loop.apply(adjustment_id=adj1.adjustment_id, adjustment=adj1)
        assert result is True
        
        # Second adjustment would exceed weekly limit
        adj2 = MicroAdjustment(
            adjustment_id="adj-002",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=86.0,
            proposed_value=80.0,  # Would exceed 15% weekly limit
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        
        result = loop.apply(adjustment_id=adj2.adjustment_id, adjustment=adj2)
        assert result is False  # Should be rejected


class TestOnlineControlLoopStatus:
    """Test status reporting."""
    
    def test_get_status_returns_full_status(self):
        """Should return complete status."""
        loop = OnlineControlLoop()
        
        # Start a cycle and add adjustments
        cycle = loop.start_cycle(brand_id="brand-123")
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        loop.add_adjustment_to_cycle(cycle.cycle_id, adj)
        
        status = loop.get_status()
        
        assert "version" in status
        assert status["version"] == "v26"
        assert "active_cycles" in status
        assert "total_adjustments_proposed" in status
        assert "total_adjustments_applied" in status
    
    def test_get_cycle_status_returns_cycle_details(self):
        """Should return detailed cycle status."""
        loop = OnlineControlLoop()
        
        cycle = loop.start_cycle(brand_id="brand-123")
        adj = MicroAdjustment(
            adjustment_id="adj-001",
            adjustment_type=AdjustmentType.GATE_THRESHOLD,
            target_gate="v1_score_min",
            current_value=70.0,
            proposed_value=68.0,
            severity=AdjustmentSeverity.LOW,
            requires_approval=False,
        )
        loop.add_adjustment_to_cycle(cycle.cycle_id, adj)
        
        status = loop.get_cycle_status(cycle.cycle_id)
        
        assert status is not None
        assert status["cycle_id"] == cycle.cycle_id
        assert status["brand_id"] == "brand-123"
        assert status["state"] == "observing"
        assert len(status["adjustments"]) == 1
