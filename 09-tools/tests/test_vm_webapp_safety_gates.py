"""
Task A: Safety Gates Policy Engine - Tests
Governança v16 - Safety gates fortes para automação de decisões

Principles:
- Safety-first
- Determinístico
- Auditável
- Reversível
- Sem automação cega
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from vm_webapp.safety_gates import (
    SafetyGate,
    SafetyGateResult,
    SafetyGateEngine,
    RiskLevel,
    GateType,
    SampleSizeGate,
    ConfidenceThresholdGate,
    RegressionGuardGate,
    CooldownGate,
    MaxActionsPerDayGate,
)

UTC = timezone.utc


class TestRiskLevel:
    """Test risk level enum."""
    
    def test_risk_levels(self):
        """Risk levels are correctly defined."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestGateType:
    """Test gate type enum."""
    
    def test_gate_types(self):
        """Gate types are correctly defined."""
        assert GateType.SAMPLE_SIZE.value == "sample_size"
        assert GateType.CONFIDENCE_THRESHOLD.value == "confidence_threshold"
        assert GateType.REGRESSION_GUARD.value == "regression_guard"
        assert GateType.COOLDOWN.value == "cooldown"
        assert GateType.MAX_ACTIONS_PER_DAY.value == "max_actions_per_day"


class TestSafetyGateResult:
    """Test safety gate result structure."""
    
    def test_allowed_result(self):
        """Can create allowed result."""
        result = SafetyGateResult(
            gate_type=GateType.SAMPLE_SIZE,
            allowed=True,
            risk_level=RiskLevel.LOW
        )
        assert result.allowed is True
        assert result.blocked_by == []
    
    def test_blocked_result(self):
        """Can create blocked result with reasons."""
        result = SafetyGateResult(
            gate_type=GateType.SAMPLE_SIZE,
            allowed=False,
            blocked_by=["insufficient_sample_size"],
            risk_level=RiskLevel.HIGH,
            recommended_action="collect_more_data"
        )
        assert result.allowed is False
        assert "insufficient_sample_size" in result.blocked_by
        assert result.recommended_action == "collect_more_data"


class TestSampleSizeGate:
    """Test sample size gate - minimum sample size por segmento."""
    
    def test_pass_with_sufficient_samples(self):
        """Gate passes with sufficient samples."""
        gate = SampleSizeGate(min_samples=100)
        
        context = {
            "segment_key": "brand1:awareness",
            "sample_size": 150,
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
        assert result.gate_type == GateType.SAMPLE_SIZE
        assert result.risk_level == RiskLevel.LOW
    
    def test_block_with_insufficient_samples(self):
        """Gate blocks with insufficient samples."""
        gate = SampleSizeGate(min_samples=100)
        
        context = {
            "segment_key": "brand1:awareness",
            "sample_size": 50,
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "insufficient_sample_size" in result.blocked_by
        assert result.risk_level == RiskLevel.HIGH
    
    def test_block_with_zero_samples(self):
        """Gate blocks with zero samples."""
        gate = SampleSizeGate(min_samples=100)
        
        context = {
            "segment_key": "brand1:awareness",
            "sample_size": 0,
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert result.risk_level == RiskLevel.CRITICAL
    
    def test_different_requirements_per_decision_type(self):
        """Different sample requirements for different decision types."""
        gate = SampleSizeGate(min_samples=100)
        
        # ROLLBACK needs less data than EXPAND (50 vs 100)
        expand_ctx = {"segment_key": "b:a", "sample_size": 110, "decision_type": "expand"}
        rollback_ctx = {"segment_key": "b:a", "sample_size": 60, "decision_type": "rollback"}
        
        expand_result = gate.evaluate(expand_ctx)
        rollback_result = gate.evaluate(rollback_ctx)
        
        # Both should pass with their respective thresholds
        assert expand_result.allowed is True  # 110 >= 100
        assert rollback_result.allowed is True  # 60 >= 50 (50% of 100)


class TestConfidenceThresholdGate:
    """Test confidence threshold gate."""
    
    def test_pass_with_high_confidence(self):
        """Gate passes with sufficient confidence."""
        gate = ConfidenceThresholdGate(min_confidence=0.8)
        
        context = {
            "segment_key": "brand1:awareness",
            "confidence_score": 0.85,
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
        assert result.risk_level == RiskLevel.LOW
    
    def test_block_with_low_confidence(self):
        """Gate blocks with low confidence."""
        gate = ConfidenceThresholdGate(min_confidence=0.8)
        
        context = {
            "segment_key": "brand1:awareness",
            "confidence_score": 0.75,  # Between 0.7 and 0.8 = MEDIUM risk
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "confidence_below_threshold" in result.blocked_by
        assert result.risk_level == RiskLevel.MEDIUM
    
    def test_block_with_missing_confidence(self):
        """Gate blocks when confidence is missing."""
        gate = ConfidenceThresholdGate(min_confidence=0.8)
        
        context = {
            "segment_key": "brand1:awareness",
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "missing_confidence_score" in result.blocked_by


class TestRegressionGuardGate:
    """Test regression guard gate - janela curta vs longa."""
    
    def test_pass_without_regression(self):
        """Gate passes without regression signals."""
        gate = RegressionGuardGate(
            short_window_hours=1,
            long_window_hours=24
        )
        
        context = {
            "segment_key": "brand1:awareness",
            "short_window_regression": False,
            "long_window_regression": False,
            "active_alerts": []
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
        assert result.risk_level == RiskLevel.LOW
    
    def test_block_with_short_window_regression(self):
        """Gate blocks with short window regression."""
        gate = RegressionGuardGate(
            short_window_hours=1,
            long_window_hours=24
        )
        
        context = {
            "segment_key": "brand1:awareness",
            "short_window_regression": True,
            "long_window_regression": False,
            "active_alerts": [{"severity": "warning"}]
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "short_window_regression" in result.blocked_by
        assert result.risk_level == RiskLevel.HIGH
    
    def test_block_with_long_window_regression(self):
        """Gate blocks with long window regression."""
        gate = RegressionGuardGate(
            short_window_hours=1,
            long_window_hours=24
        )
        
        context = {
            "segment_key": "brand1:awareness",
            "short_window_regression": False,
            "long_window_regression": True,
            "active_alerts": [{"severity": "critical"}]
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "long_window_regression" in result.blocked_by
        assert result.risk_level == RiskLevel.CRITICAL
    
    def test_block_with_critical_alert(self):
        """Gate blocks with critical alert regardless of window."""
        gate = RegressionGuardGate(
            short_window_hours=1,
            long_window_hours=24
        )
        
        context = {
            "segment_key": "brand1:awareness",
            "short_window_regression": False,
            "long_window_regression": False,
            "active_alerts": [{"severity": "critical", "reason_code": "approval_rate_drop"}]
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "critical_alert_active" in result.blocked_by


class TestCooldownGate:
    """Test cooldown gate - cooldown por segmento."""
    
    def test_pass_when_no_recent_action(self):
        """Gate passes when no recent action on segment."""
        gate = CooldownGate(cooldown_hours=4)
        
        now = datetime.now(UTC)
        last_action = now - timedelta(hours=5)
        
        context = {
            "segment_key": "brand1:awareness",
            "last_action_at": last_action.isoformat(),
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
        assert result.risk_level == RiskLevel.LOW
    
    def test_block_during_cooldown(self):
        """Gate blocks during cooldown period."""
        gate = CooldownGate(cooldown_hours=4)
        
        now = datetime.now(UTC)
        last_action = now - timedelta(hours=2)
        
        context = {
            "segment_key": "brand1:awareness",
            "last_action_at": last_action.isoformat(),
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "cooldown_active" in result.blocked_by
        assert result.risk_level == RiskLevel.MEDIUM
    
    def test_pass_when_no_previous_action(self):
        """Gate passes when no previous action recorded."""
        gate = CooldownGate(cooldown_hours=4)
        
        context = {
            "segment_key": "brand1:awareness",
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
    
    def test_rollback_bypasses_cooldown(self):
        """ROLLBACK decisions bypass cooldown."""
        gate = CooldownGate(cooldown_hours=4)
        
        now = datetime.now(UTC)
        last_action = now - timedelta(minutes=30)
        
        context = {
            "segment_key": "brand1:awareness",
            "last_action_at": last_action.isoformat(),
            "decision_type": "rollback"  # Emergency override
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
        assert result.risk_level == RiskLevel.LOW


class TestMaxActionsPerDayGate:
    """Test max actions per day gate por brand."""
    
    def test_pass_under_limit(self):
        """Gate passes when under daily limit."""
        gate = MaxActionsPerDayGate(max_actions=10)
        
        context = {
            "brand_id": "brand1",
            "actions_today": 5,
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
        assert result.risk_level == RiskLevel.LOW
    
    def test_block_at_limit(self):
        """Gate blocks when at daily limit."""
        gate = MaxActionsPerDayGate(max_actions=10)
        
        context = {
            "brand_id": "brand1",
            "actions_today": 10,
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert "max_actions_per_day_reached" in result.blocked_by
        assert result.risk_level == RiskLevel.MEDIUM
    
    def test_block_over_limit(self):
        """Gate blocks when over daily limit."""
        gate = MaxActionsPerDayGate(max_actions=10)
        
        context = {
            "brand_id": "brand1",
            "actions_today": 12,
            "decision_type": "expand"
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
        assert result.risk_level == RiskLevel.HIGH


class TestSafetyGateEngine:
    """Test safety gate engine - orquestra todos os gates."""
    
    def test_all_gates_pass(self):
        """Engine allows when all gates pass."""
        engine = SafetyGateEngine()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 150,
            "confidence_score": 0.85,
            "short_window_regression": False,
            "long_window_regression": False,
            "active_alerts": [],
            "actions_today": 3,
            "decision_type": "expand"
        }
        
        result = engine.evaluate(context)
        
        assert result.allowed is True
        assert result.risk_level == RiskLevel.LOW
        assert result.blocked_by == []
    
    def test_blocks_when_any_gate_fails(self):
        """Engine blocks when any gate fails."""
        engine = SafetyGateEngine()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 50,  # FAIL: too few samples
            "confidence_score": 0.85,
            "short_window_regression": False,
            "long_window_regression": False,
            "active_alerts": [],
            "actions_today": 3,
            "decision_type": "expand"
        }
        
        result = engine.evaluate(context)
        
        assert result.allowed is False
        assert "insufficient_sample_size" in result.blocked_by
        assert result.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    def test_multiple_gate_failures(self):
        """Engine reports all blocking gates."""
        engine = SafetyGateEngine()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 50,  # FAIL
            "confidence_score": 0.65,  # FAIL
            "short_window_regression": False,
            "long_window_regression": True,  # FAIL - CRITICAL
            "active_alerts": [{"severity": "critical"}],  # FAIL - CRITICAL
            "actions_today": 15,  # FAIL
            "decision_type": "expand"
        }
        
        result = engine.evaluate(context)
        
        assert result.allowed is False
        assert len(result.blocked_by) >= 3  # Multiple failures
        assert result.risk_level == RiskLevel.CRITICAL
    
    def test_recommended_action_on_block(self):
        """Engine provides recommended action when blocked."""
        engine = SafetyGateEngine()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 50,
            "confidence_score": 0.85,
            "short_window_regression": False,
            "long_window_regression": False,
            "active_alerts": [],
            "actions_today": 3,
            "decision_type": "expand"
        }
        
        result = engine.evaluate(context)
        
        assert result.allowed is False
        assert result.recommended_action is not None
        assert len(result.recommended_action) > 0
    
    def test_evaluate_with_custom_thresholds(self):
        """Engine accepts custom thresholds per brand."""
        engine = SafetyGateEngine()
        
        # Brand with stricter requirements
        custom_config = {
            "min_samples": 200,
            "min_confidence": 0.9,
            "max_actions_per_day": 5
        }
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 150,  # Would pass default (100) but fail custom (200)
            "confidence_score": 0.85,
            "custom_config": custom_config,
            "decision_type": "expand"
        }
        
        result = engine.evaluate(context)
        
        assert result.allowed is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_context(self):
        """Engine handles empty context gracefully."""
        engine = SafetyGateEngine()
        
        result = engine.evaluate({})
        
        assert result.allowed is False
        assert len(result.blocked_by) > 0
    
    def test_missing_segment_key(self):
        """Engine blocks when segment key is missing."""
        engine = SafetyGateEngine()
        
        context = {
            "sample_size": 100,
            # Missing segment_key
        }
        
        result = engine.evaluate(context)
        
        assert result.allowed is False
    
    def test_null_values_in_context(self):
        """Engine handles null values gracefully."""
        gate = SampleSizeGate(min_samples=100)
        
        context = {
            "segment_key": "brand1:awareness",
            "sample_size": None
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
    
    def test_very_high_confidence(self):
        """Gate handles confidence score of 1.0."""
        gate = ConfidenceThresholdGate(min_confidence=0.8)
        
        context = {
            "segment_key": "brand1:awareness",
            "confidence_score": 1.0
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is True
    
    def test_zero_confidence(self):
        """Gate blocks with zero confidence."""
        gate = ConfidenceThresholdGate(min_confidence=0.8)
        
        context = {
            "segment_key": "brand1:awareness",
            "confidence_score": 0.0
        }
        
        result = gate.evaluate(context)
        
        assert result.allowed is False
