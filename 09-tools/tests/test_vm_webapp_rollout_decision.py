"""
Task C: Rollout Decision Assistant - Tests
Covers: decision endpoint (expand/hold/rollback), confidence, reasons, required_actions
"""

import pytest
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from unittest.mock import MagicMock, patch

from vm_webapp.rollout_decision import (
    RolloutDecision,
    DecisionConfidence,
    DecisionReason,
    RequiredAction,
    RolloutDecisionEngine,
    get_rollout_decision,
    override_decision,
)


class TestRolloutDecision:
    """Test rollout decision enum."""
    
    def test_decision_values(self):
        """Decision values are correct."""
        assert RolloutDecision.EXPAND.value == "expand"
        assert RolloutDecision.HOLD.value == "hold"
        assert RolloutDecision.ROLLBACK.value == "rollback"


class TestDecisionConfidence:
    """Test confidence levels."""
    
    def test_confidence_values(self):
        """Confidence levels are correct."""
        assert DecisionConfidence.LOW.value == "low"
        assert DecisionConfidence.MEDIUM.value == "medium"
        assert DecisionConfidence.HIGH.value == "high"


class TestDecisionReason:
    """Test decision reason structure."""
    
    def test_reason_creation(self):
        """Can create decision reason."""
        reason = DecisionReason(
            code="kpi_on_track",
            description="All KPIs are meeting targets",
            severity="info"
        )
        
        assert reason.code == "kpi_on_track"
        assert reason.severity == "info"


class TestRequiredAction:
    """Test required action structure."""
    
    def test_action_creation(self):
        """Can create required action."""
        action = RequiredAction(
            action_id="action_001",
            description="Increase rollout to 50% of eligible segments",
            priority="high",
            due_hours=24,
            auto_applicable=True
        )
        
        assert action.action_id == "action_001"
        assert action.auto_applicable is True


class TestRolloutDecisionEngine:
    """Test decision engine logic."""
    
    def test_recommend_expand_kpi_on_track(self):
        """Recommend EXPAND when all KPIs are on track."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
            "v1_score_avg": {"status": "on_track", "delta": 7.0},
            "regenerations_per_job": {"status": "on_track", "delta": -0.18},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[],
            days_in_current_phase=14
        )
        
        assert result["decision"] == RolloutDecision.EXPAND
        assert result["confidence"] in [DecisionConfidence.HIGH, DecisionConfidence.MEDIUM]
        assert len(result["reasons"]) > 0
        assert any(r.code == "kpi_on_track" for r in result["reasons"])
    
    def test_recommend_hold_mixed_kpis(self):
        """Recommend HOLD when KPIs are mixed."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
            "v1_score_avg": {"status": "attention", "delta": 4.0},  # Below target
            "regenerations_per_job": {"status": "on_track", "delta": -0.18},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[],
            days_in_current_phase=7
        )
        
        assert result["decision"] == RolloutDecision.HOLD
        assert result["confidence"] == DecisionConfidence.MEDIUM
        assert any("attention" in r.code for r in result["reasons"])
    
    def test_recommend_rollback_critical_regression(self):
        """Recommend ROLLBACK on critical regression."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "off_track", "delta": -0.05},  # Regression
            "v1_score_avg": {"status": "off_track", "delta": -5.0},
            "regenerations_per_job": {"status": "off_track", "delta": 0.30},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[{"severity": "critical"}],
            days_in_current_phase=3
        )
        
        assert result["decision"] == RolloutDecision.ROLLBACK
        assert result["confidence"] == DecisionConfidence.HIGH
        assert any("off_track" in r.code.lower() for r in result["reasons"])
    
    def test_recommend_hold_with_active_alerts(self):
        """Recommend HOLD when there are active alerts."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
            "v1_score_avg": {"status": "on_track", "delta": 7.0},
            "regenerations_per_job": {"status": "on_track", "delta": -0.18},
        }
        
        active_alerts = [
            {"severity": "warning", "reason_code": "approval_rate_drop"}
        ]
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=active_alerts,
            days_in_current_phase=10
        )
        
        assert result["decision"] == RolloutDecision.HOLD
        assert any("alert" in r.code.lower() for r in result["reasons"])
    
    def test_recommend_hold_insufficient_data(self):
        """Recommend HOLD when insufficient data (< 7 days)."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[],
            days_in_current_phase=3  # Less than 7 days
        )
        
        assert result["decision"] == RolloutDecision.HOLD
        assert any("insufficient" in r.code.lower() or "data" in r.code.lower() 
                   for r in result["reasons"])
    
    def test_required_actions_for_expand(self):
        """EXPAND decision includes appropriate actions."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
            "v1_score_avg": {"status": "on_track", "delta": 7.0},
            "regenerations_per_job": {"status": "on_track", "delta": -0.18},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[],
            days_in_current_phase=14
        )
        
        assert result["decision"] == RolloutDecision.EXPAND
        assert len(result["required_actions"]) > 0
        # Should have action to increase rollout
        assert any("expand" in a.description.lower() or "increase" in a.description.lower() 
                   for a in result["required_actions"])
    
    def test_required_actions_for_rollback(self):
        """ROLLBACK decision includes urgent actions."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "off_track", "delta": -0.10},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[{"severity": "critical"}],
            days_in_current_phase=5
        )
        
        assert result["decision"] == RolloutDecision.ROLLBACK
        # Should have urgent action
        assert any(a.priority == "critical" or a.priority == "high" 
                   for a in result["required_actions"])


class TestGetRolloutDecision:
    """Test high-level decision API."""
    
    @patch("vm_webapp.rollout_decision._fetch_kpi_summary")
    @patch("vm_webapp.rollout_decision._fetch_active_alerts")
    @patch("vm_webapp.rollout_decision._fetch_segment_phase_info")
    def test_get_decision_integration(self, mock_phase, mock_alerts, mock_kpi):
        """Integration test for get_rollout_decision."""
        mock_kpi.return_value = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
            "v1_score_avg": {"status": "on_track", "delta": 7.0},
            "regenerations_per_job": {"status": "on_track", "delta": -0.18},
        }
        mock_alerts.return_value = []
        mock_phase.return_value = {"days_in_phase": 14, "current_phase": "pilot"}
        
        result = get_rollout_decision("brand1:awareness")
        
        assert "decision" in result
        assert "confidence" in result
        assert "reasons" in result
        assert "required_actions" in result
        assert "segment_key" in result
        assert result["segment_key"] == "brand1:awareness"
    
    def test_decision_response_structure(self):
        """Decision response has expected structure."""
        with patch("vm_webapp.rollout_decision._fetch_kpi_summary") as mock_kpi, \
             patch("vm_webapp.rollout_decision._fetch_active_alerts") as mock_alerts, \
             patch("vm_webapp.rollout_decision._fetch_segment_phase_info") as mock_phase:
            
            mock_kpi.return_value = {
                "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
            }
            mock_alerts.return_value = []
            mock_phase.return_value = {"days_in_phase": 14, "current_phase": "pilot"}
            
            result = get_rollout_decision("brand1:awareness")
            
            # Response structure validation
            assert isinstance(result["decision"], RolloutDecision)
            assert isinstance(result["confidence"], DecisionConfidence)
            assert isinstance(result["reasons"], list)
            assert isinstance(result["required_actions"], list)
            assert "generated_at" in result


class TestOverrideDecision:
    """Test manual decision override."""
    
    @patch("vm_webapp.rollout_decision._store_decision_override")
    @patch("vm_webapp.rollout_decision._fetch_original_decision")
    def test_override_decision_success(self, mock_fetch, mock_store):
        """Can override decision with valid reason."""
        mock_fetch.return_value = {
            "decision": RolloutDecision.HOLD,
            "confidence": DecisionConfidence.MEDIUM,
            "segment_key": "brand1:awareness"
        }
        
        result = override_decision(
            segment_key="brand1:awareness",
            new_decision=RolloutDecision.EXPAND,
            reason="Business priority - Q4 campaign",
            overridden_by="operator@example.com"
        )
        
        assert result["overridden"] is True
        assert result["original_decision"] == RolloutDecision.HOLD
        assert result["new_decision"] == RolloutDecision.EXPAND
        assert result["override_reason"] == "Business priority - Q4 campaign"
        mock_store.assert_called_once()
    
    @patch("vm_webapp.rollout_decision._fetch_original_decision")
    def test_override_rollback_requires_approval(self, mock_fetch):
        """Overriding to ROLLBACK may require additional approval."""
        mock_fetch.return_value = {
            "decision": RolloutDecision.EXPAND,
            "confidence": DecisionConfidence.HIGH,
        }
        
        result = override_decision(
            segment_key="brand1:awareness",
            new_decision=RolloutDecision.ROLLBACK,
            reason="Critical issue detected",
            overridden_by="operator@example.com"
        )
        
        assert result["overridden"] is True
        # ROLLBACK should have warning about severity
        assert "requires_notification" in result


class TestConfidenceCalculation:
    """Test confidence calculation logic."""
    
    def test_high_confidence_all_green(self):
        """HIGH confidence when all signals positive."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.08},
            "v1_score_avg": {"status": "on_track", "delta": 8.0},
            "regenerations_per_job": {"status": "on_track", "delta": -0.20},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[],
            days_in_current_phase=21
        )
        
        assert result["confidence"] == DecisionConfidence.HIGH
    
    def test_low_confidence_mixed_signals(self):
        """LOW confidence with contradictory signals."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "on_track", "delta": 0.06},
            "v1_score_avg": {"status": "off_track", "delta": -2.0},  # Contradiction
            "regenerations_per_job": {"status": "attention", "delta": -0.10},
        }
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=[{"severity": "warning"}],
            days_in_current_phase=5
        )
        
        assert result["confidence"] == DecisionConfidence.LOW


class TestEdgeCases:
    """Test edge cases."""
    
    def test_no_kpi_data(self):
        """Handle missing KPI data gracefully."""
        engine = RolloutDecisionEngine()
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary={},
            active_alerts=[],
            days_in_current_phase=0
        )
        
        assert result["decision"] == RolloutDecision.HOLD
        assert result["confidence"] == DecisionConfidence.LOW
        assert any("insufficient" in r.code.lower() for r in result["reasons"])
    
    def test_multiple_critical_alerts(self):
        """Multiple critical alerts trigger ROLLBACK."""
        engine = RolloutDecisionEngine()
        
        kpi_summary = {
            "approval_without_regen_24h": {"status": "attention", "delta": 0.04},
        }
        
        active_alerts = [
            {"severity": "critical", "reason_code": "approval_rate_drop"},
            {"severity": "critical", "reason_code": "v1_score_decline"},
        ]
        
        result = engine.recommend(
            segment_key="brand1:awareness",
            kpi_summary=kpi_summary,
            active_alerts=active_alerts,
            days_in_current_phase=10
        )
        
        assert result["decision"] == RolloutDecision.ROLLBACK
        assert result["confidence"] == DecisionConfidence.HIGH
