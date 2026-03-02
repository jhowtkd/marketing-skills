"""Tests for onboarding policy serving engine and safe rollout manager."""

from __future__ import annotations

import pytest

from vm_webapp.onboarding_personalization import (
    PersonalizationPolicy,
    PolicyStatus,
    RiskLevel,
    SegmentKey,
    SegmentProfiler,
)
from vm_webapp.onboarding_policy_rollout import (
    CanaryConfig,
    GuardrailResult,
    PolicyServingEngine,
    RolloutDecision,
    RolloutManager,
    ValidationResult,
)


class TestCanaryConfig:
    """Test canary configuration."""

    def test_canary_config_defaults(self):
        """Test canary config with default values."""
        config = CanaryConfig(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
        )
        assert config.policy_id == "policy-001"
        assert config.traffic_percentage == 10  # Default
        assert config.duration_hours == 24  # Default
        assert config.success_criteria["conversion_rate_lift"] == 0.05

    def test_canary_config_custom_values(self):
        """Test canary config with custom values."""
        config = CanaryConfig(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            traffic_percentage=25,
            duration_hours=48,
            success_criteria={"conversion_rate_lift": 0.10},
        )
        assert config.traffic_percentage == 25
        assert config.duration_hours == 48
        assert config.success_criteria["conversion_rate_lift"] == 0.10


class TestValidationResult:
    """Test validation result."""

    def test_validation_success(self):
        """Test successful validation."""
        result = ValidationResult(
            policy_id="policy-001",
            is_valid=True,
            checks={"schema": True, "constraints": True},
        )
        assert result.is_valid is True
        assert result.errors == []

    def test_validation_failure(self):
        """Test failed validation."""
        result = ValidationResult(
            policy_id="policy-001",
            is_valid=False,
            checks={"schema": True, "constraints": False},
            errors=["Invalid nudge_delay_ms: must be positive"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 1


class TestGuardrailResult:
    """Test guardrail result."""

    def test_guardrail_pass(self):
        """Test guardrail passing."""
        result = GuardrailResult(
            policy_id="policy-001",
            blocked=False,
            checks={"latency": True, "error_rate": True},
        )
        assert result.blocked is False
        assert result.reason == ""

    def test_guardrail_block(self):
        """Test guardrail blocking."""
        result = GuardrailResult(
            policy_id="policy-001",
            blocked=True,
            checks={"latency": False, "error_rate": True},
            reason="Latency threshold exceeded: 500ms > 300ms",
        )
        assert result.blocked is True
        assert "Latency threshold exceeded" in result.reason


class TestPolicyServingEngine:
    """Test policy serving engine."""

    def test_engine_initialization(self):
        """Test engine initialization."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        assert engine._profiler == profiler

    def test_serve_policy_for_segment_exact_match(self):
        """Test serving policy with exact segment match."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        
        key = SegmentKey("small", "tech", "beginner", "organic")
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=key,
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        policy.activate()
        profiler.register_policy(policy)
        
        result = engine.serve_policy_for_segment(key)
        assert result is not None
        assert result.policy.policy_id == "policy-001"
        assert result.source == "segment"
        assert result.fallback_used is False

    def test_serve_policy_with_fallback(self):
        """Test serving policy with fallback to brand level."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        
        # Register brand-level policy
        brand_policy = PersonalizationPolicy(
            policy_id="policy-brand",
            segment_key=SegmentKey("*", "*", "*", "*"),
            nudge_delay_ms=5000,
            template_order=["default"],
            welcome_message="Welcome!",
            show_video_tutorial=False,
            max_steps=5,
            risk_level=RiskLevel.MEDIUM,
        )
        brand_policy.activate()
        profiler.register_policy(brand_policy)
        
        # Request specific segment
        specific_key = SegmentKey("small", "tech", "beginner", "organic")
        result = engine.serve_policy_for_segment(specific_key)
        
        assert result is not None
        assert result.policy.policy_id == "policy-brand"
        assert result.source == "brand"
        assert result.fallback_used is True

    def test_serve_policy_tracks_latency(self):
        """Test that serving tracks latency metrics."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        
        key = SegmentKey("small", "tech", "beginner", "organic")
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=key,
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        policy.activate()
        profiler.register_policy(policy)
        
        # Serve policy
        engine.serve_policy_for_segment(key)
        
        # Check that latency was tracked
        assert len(engine._serve_latencies_ms) == 1
        assert engine._serve_latencies_ms[0] >= 0

    def test_serve_policy_no_match_returns_none(self):
        """Test serving when no policy matches."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        
        key = SegmentKey("small", "tech", "beginner", "organic")
        result = engine.serve_policy_for_segment(key)
        
        assert result is None

    def test_get_serve_metrics(self):
        """Test getting serve metrics."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        
        key = SegmentKey("small", "tech", "beginner", "organic")
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=key,
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        policy.activate()
        profiler.register_policy(policy)
        
        # Serve policy multiple times
        for _ in range(5):
            engine.serve_policy_for_segment(key)
        
        metrics = engine.get_serve_metrics()
        assert metrics["total_serves"] == 5
        assert metrics["segment_hits"] == 5
        assert metrics["fallback_uses"] == 0
        assert metrics["avg_latency_ms"] >= 0


class TestRolloutManager:
    """Test rollout manager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        assert manager._profiler == profiler
        assert manager._engine == engine

    def test_validate_policy_success(self):
        """Test policy validation success."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        
        result = manager.validate_policy(policy)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_policy_failure_negative_delay(self):
        """Test policy validation fails with negative delay."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=-100,  # Invalid
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        
        result = manager.validate_policy(policy)
        assert result.is_valid is False
        assert any("nudge_delay_ms" in error for error in result.errors)

    def test_validate_policy_failure_empty_templates(self):
        """Test policy validation fails with empty template order."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=[],  # Invalid
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        
        result = manager.validate_policy(policy)
        assert result.is_valid is False
        assert any("template_order" in error for error in result.errors)

    def test_check_guardrails_pass(self):
        """Test guardrails check passes."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        
        result = manager.check_guardrails(policy)
        assert result.blocked is False

    def test_check_guardrails_block_high_latency(self):
        """Test guardrails block high latency policy."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=50000,  # Too high (> 30s max)
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        
        result = manager.check_guardrails(policy)
        assert result.blocked is True
        assert "nudge_delay_ms" in result.reason.lower()

    def test_check_guardrails_block_too_many_steps(self):
        """Test guardrails block policy with too many steps."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=15,  # Too many (> 10 max)
            risk_level=RiskLevel.LOW,
        )
        
        result = manager.check_guardrails(policy)
        assert result.blocked is True
        assert "max_steps" in result.reason.lower()

    def test_decide_rollout_low_risk_auto_apply(self):
        """Test low risk policy gets auto-apply decision."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        
        decision = manager.decide_rollout(policy)
        assert decision.decision == "auto_apply"
        assert decision.requires_approval is False

    def test_decide_rollout_medium_risk_needs_approval(self):
        """Test medium risk policy needs approval."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.MEDIUM,
        )
        
        decision = manager.decide_rollout(policy)
        assert decision.decision == "approve"
        assert decision.requires_approval is True

    def test_decide_rollout_high_risk_needs_approval(self):
        """Test high risk policy needs approval."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.HIGH,
        )
        
        decision = manager.decide_rollout(policy)
        assert decision.decision == "approve"
        assert decision.requires_approval is True

    def test_decide_rollout_blocked_by_guardrails(self):
        """Test invalid policy is blocked by guardrails."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=50000,  # Too high
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        
        decision = manager.decide_rollout(policy)
        assert decision.decision == "block"
        assert decision.reason != ""

    def test_execute_rollout_auto_apply(self):
        """Test executing rollout for low risk policy."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        profiler.register_policy(policy)
        
        result = manager.execute_rollout("policy-001")
        assert result is True
        
        # Check policy is now active
        updated_policy = profiler.get_policy("policy-001")
        assert updated_policy.status == PolicyStatus.ACTIVE

    def test_execute_rollout_blocked(self):
        """Test executing rollout for blocked policy fails."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=50000,  # Too high - will be blocked
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        profiler.register_policy(policy)
        
        result = manager.execute_rollout("policy-001")
        assert result is False

    def test_rollback_policy(self):
        """Test rolling back a policy."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        policy.activate()
        profiler.register_policy(policy)
        
        result = manager.rollback_policy("policy-001", "Negative metrics detected")
        assert result is True
        
        # Check policy is now rolled back
        updated_policy = profiler.get_policy("policy-001")
        assert updated_policy.status == PolicyStatus.ROLLED_BACK

    def test_get_rollout_metrics(self):
        """Test getting rollout metrics."""
        profiler = SegmentProfiler()
        engine = PolicyServingEngine(profiler)
        manager = RolloutManager(profiler, engine)
        
        # Register and roll out a policy
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        profiler.register_policy(policy)
        manager.execute_rollout("policy-001")
        
        # Register a blocked policy
        blocked_policy = PersonalizationPolicy(
            policy_id="policy-002",
            segment_key=SegmentKey("large", "finance", "advanced", "paid"),
            nudge_delay_ms=50000,  # Too high
            template_order=["advanced"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        profiler.register_policy(blocked_policy)
        manager.execute_rollout("policy-002")  # Will be blocked
        
        metrics = manager.get_rollout_metrics()
        assert metrics["total_rollouts"] == 1
        assert metrics["blocked_rollouts"] == 1
        assert metrics["auto_applied"] == 1
