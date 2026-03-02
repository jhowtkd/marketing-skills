"""Tests for onboarding personalization segment profiler and policy model."""

from __future__ import annotations

import pytest

from vm_webapp.onboarding_personalization import (
    PersonalizationPolicy,
    PolicyStatus,
    RiskLevel,
    SegmentKey,
    SegmentProfiler,
)


class TestSegmentKey:
    """Test segment key derivation."""

    def test_segment_key_creation(self):
        """Test creating a segment key from user attributes."""
        key = SegmentKey(
            company_size="small",
            industry="tech",
            experience_level="beginner",
            traffic_source="organic",
        )
        assert key.company_size == "small"
        assert key.industry == "tech"
        assert key.experience_level == "beginner"
        assert key.traffic_source == "organic"

    def test_segment_key_from_user_profile(self):
        """Test deriving segment key from user profile."""
        profile = {
            "company_size": "enterprise",
            "industry": "finance",
            "experience_level": "advanced",
            "traffic_source": "paid",
        }
        key = SegmentKey.from_profile(profile)
        assert key.company_size == "enterprise"
        assert key.industry == "finance"
        assert key.experience_level == "advanced"
        assert key.traffic_source == "paid"

    def test_segment_key_from_profile_with_defaults(self):
        """Test deriving segment key with missing attributes uses defaults."""
        profile = {"company_size": "medium"}
        key = SegmentKey.from_profile(profile)
        assert key.company_size == "medium"
        assert key.industry == "unknown"
        assert key.experience_level == "unknown"
        assert key.traffic_source == "unknown"

    def test_segment_key_string_representation(self):
        """Test segment key string representation."""
        key = SegmentKey(
            company_size="small",
            industry="tech",
            experience_level="beginner",
            traffic_source="organic",
        )
        assert str(key) == "small:tech:beginner:organic"

    def test_segment_key_equality(self):
        """Test segment key equality comparison."""
        key1 = SegmentKey("small", "tech", "beginner", "organic")
        key2 = SegmentKey("small", "tech", "beginner", "organic")
        key3 = SegmentKey("large", "tech", "beginner", "organic")
        assert key1 == key2
        assert key1 != key3


class TestPersonalizationPolicy:
    """Test personalization policy model."""

    def test_policy_creation(self):
        """Test creating a personalization policy."""
        policy = PersonalizationPolicy(
            policy_id="policy-001",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple", "advanced", "custom"],
            welcome_message="Welcome! Let's get you started quickly.",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        assert policy.policy_id == "policy-001"
        assert policy.status == PolicyStatus.DRAFT
        assert policy.nudge_delay_ms == 3000
        assert policy.template_order == ["simple", "advanced", "custom"]

    def test_policy_status_transitions(self):
        """Test policy status transitions."""
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
        
        # Draft -> Active
        policy.activate()
        assert policy.status == PolicyStatus.ACTIVE
        
        # Active -> Frozen
        policy.freeze()
        assert policy.status == PolicyStatus.FROZEN
        
        # Frozen -> Active
        policy.activate()
        assert policy.status == PolicyStatus.ACTIVE
        
        # Active -> Rolled Back
        policy.rollback()
        assert policy.status == PolicyStatus.ROLLED_BACK

    def test_policy_risk_levels(self):
        """Test different risk levels."""
        for risk_level in RiskLevel:
            policy = PersonalizationPolicy(
                policy_id=f"policy-{risk_level.value}",
                segment_key=SegmentKey("small", "tech", "beginner", "organic"),
                nudge_delay_ms=3000,
                template_order=["simple"],
                welcome_message="Welcome!",
                show_video_tutorial=True,
                max_steps=3,
                risk_level=risk_level,
            )
            assert policy.risk_level == risk_level
            assert policy.requires_approval() == (risk_level != RiskLevel.LOW)


class TestSegmentProfiler:
    """Test segment profiler."""

    def test_profiler_initialization(self):
        """Test profiler initialization."""
        profiler = SegmentProfiler()
        assert profiler.get_policy_count() == 0

    def test_register_policy(self):
        """Test registering a policy."""
        profiler = SegmentProfiler()
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
        assert profiler.get_policy_count() == 1

    def test_get_policy_for_segment_exact_match(self):
        """Test getting policy with exact segment match."""
        profiler = SegmentProfiler()
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
        
        result = profiler.get_policy_for_segment(key)
        assert result is not None
        assert result.policy.policy_id == "policy-001"
        assert result.source == "segment"

    def test_get_policy_with_fallback_to_brand(self):
        """Test getting policy falls back to brand level."""
        profiler = SegmentProfiler()
        
        # Register brand-level policy
        brand_policy = PersonalizationPolicy(
            policy_id="policy-brand",
            segment_key=SegmentKey("*", "*", "*", "*"),  # Wildcard = brand level
            nudge_delay_ms=5000,
            template_order=["default"],
            welcome_message="Welcome to our platform!",
            show_video_tutorial=False,
            max_steps=5,
            risk_level=RiskLevel.MEDIUM,
        )
        brand_policy.activate()
        profiler.register_policy(brand_policy)
        
        # Request specific segment
        specific_key = SegmentKey("small", "tech", "beginner", "organic")
        result = profiler.get_policy_for_segment(specific_key)
        
        assert result is not None
        assert result.policy.policy_id == "policy-brand"
        assert result.source == "brand"

    def test_get_policy_with_fallback_to_global(self):
        """Test getting policy falls back to global level."""
        profiler = SegmentProfiler()
        
        # Register global policy
        global_policy = PersonalizationPolicy(
            policy_id="policy-global",
            segment_key=None,  # None = global level
            nudge_delay_ms=7000,
            template_order=["standard"],
            welcome_message="Hello!",
            show_video_tutorial=True,
            max_steps=7,
            risk_level=RiskLevel.LOW,
        )
        global_policy.activate()
        profiler.register_policy(global_policy)
        
        # Request any segment
        specific_key = SegmentKey("small", "tech", "beginner", "organic")
        result = profiler.get_policy_for_segment(specific_key)
        
        assert result is not None
        assert result.policy.policy_id == "policy-global"
        assert result.source == "global"

    def test_get_policy_priority_resolution(self):
        """Test priority resolution: segment > brand > global."""
        profiler = SegmentProfiler()
        
        # Register all three levels
        global_policy = PersonalizationPolicy(
            policy_id="policy-global",
            segment_key=None,
            nudge_delay_ms=7000,
            template_order=["standard"],
            welcome_message="Hello!",
            show_video_tutorial=True,
            max_steps=7,
            risk_level=RiskLevel.LOW,
        )
        global_policy.activate()
        profiler.register_policy(global_policy)
        
        brand_policy = PersonalizationPolicy(
            policy_id="policy-brand",
            segment_key=SegmentKey("*", "*", "*", "*"),
            nudge_delay_ms=5000,
            template_order=["default"],
            welcome_message="Welcome to our platform!",
            show_video_tutorial=False,
            max_steps=5,
            risk_level=RiskLevel.MEDIUM,
        )
        brand_policy.activate()
        profiler.register_policy(brand_policy)
        
        segment_key = SegmentKey("small", "tech", "beginner", "organic")
        segment_policy = PersonalizationPolicy(
            policy_id="policy-segment",
            segment_key=segment_key,
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        segment_policy.activate()
        profiler.register_policy(segment_policy)
        
        # Should get segment-level policy
        result = profiler.get_policy_for_segment(segment_key)
        assert result.policy.policy_id == "policy-segment"
        assert result.source == "segment"

    def test_get_policy_no_match_returns_none(self):
        """Test getting policy when no policies registered returns None."""
        profiler = SegmentProfiler()
        key = SegmentKey("small", "tech", "beginner", "organic")
        result = profiler.get_policy_for_segment(key)
        assert result is None

    def test_list_active_policies(self):
        """Test listing only active policies."""
        profiler = SegmentProfiler()
        
        # Active policy
        active_policy = PersonalizationPolicy(
            policy_id="policy-active",
            segment_key=SegmentKey("small", "tech", "beginner", "organic"),
            nudge_delay_ms=3000,
            template_order=["simple"],
            welcome_message="Welcome!",
            show_video_tutorial=True,
            max_steps=3,
            risk_level=RiskLevel.LOW,
        )
        active_policy.activate()
        profiler.register_policy(active_policy)
        
        # Draft policy
        draft_policy = PersonalizationPolicy(
            policy_id="policy-draft",
            segment_key=SegmentKey("large", "finance", "advanced", "paid"),
            nudge_delay_ms=5000,
            template_order=["advanced"],
            welcome_message="Welcome!",
            show_video_tutorial=False,
            max_steps=5,
            risk_level=RiskLevel.MEDIUM,
        )
        profiler.register_policy(draft_policy)
        
        active_policies = profiler.list_active_policies()
        assert len(active_policies) == 1
        assert active_policies[0].policy_id == "policy-active"

    def test_compile_segment_metrics(self):
        """Test compiling metrics for a segment."""
        profiler = SegmentProfiler()
        key = SegmentKey("small", "tech", "beginner", "organic")
        
        metrics = profiler.compile_segment_metrics(key, {
            "conversion_rate": 0.15,
            "time_to_first_value_ms": 45000,
            "nudge_acceptance_rate": 0.72,
            "dropoff_rate": 0.25,
        })
        
        assert metrics.segment_key == str(key)
        assert metrics.conversion_rate == 0.15
        assert metrics.time_to_first_value_ms == 45000
        assert metrics.nudge_acceptance_rate == 0.72
        assert metrics.dropoff_rate == 0.25
