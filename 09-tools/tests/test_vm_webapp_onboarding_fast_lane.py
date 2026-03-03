"""Tests for v38 onboarding fast lane functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from vm_webapp.onboarding_fast_lane import (
    FastLaneEligibility,
    RiskLevel,
    UserSegment,
    FastLaneConfig,
    determine_fast_lane_eligibility,
    calculate_risk_score,
    get_fast_lane_path,
    MINIMUM_CHECKLIST,
)


class TestRiskLevel:
    """Test risk level enum."""

    def test_risk_level_values(self):
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"


class TestUserSegment:
    """Test user segment enum."""

    def test_user_segment_values(self):
        assert UserSegment.NEW_USER == "new_user"
        assert UserSegment.RETURNING == "returning"
        assert UserSegment.ENTERPRISE == "enterprise"
        assert UserSegment.POWER_USER == "power_user"


class TestMinimumChecklist:
    """Test minimum required checklist items."""

    def test_minimum_checklist_defined(self):
        assert "terms_accepted" in MINIMUM_CHECKLIST
        assert "email_verified" in MINIMUM_CHECKLIST
        assert "privacy_policy" in MINIMUM_CHECKLIST

    def test_minimum_checklist_cannot_be_skipped(self):
        # These items must always be required, even in fast lane
        required_items = ["terms_accepted", "email_verified"]
        for item in required_items:
            assert item in MINIMUM_CHECKLIST


class TestCalculateRiskScore:
    """Test risk score calculation."""

    def test_low_risk_new_user_with_email_domain(self):
        context = {
            "email_domain": "company.com",
            "signup_source": "organic",
            "has_payment_method": False,
            "ip_reputation_score": 0.8,
        }
        score = calculate_risk_score(context)
        assert 0 <= score <= 30  # Low risk range

    def test_medium_risk_suspicious_patterns(self):
        context = {
            "email_domain": "tempmail.com",
            "signup_source": "referral",
            "has_payment_method": False,
            "ip_reputation_score": 0.5,
            "rapid_signup": True,
        }
        score = calculate_risk_score(context)
        assert 31 <= score <= 70  # Medium risk range

    def test_high_risk_suspicious_indicators(self):
        context = {
            "email_domain": "suspicious.xyz",
            "signup_source": "unknown",
            "has_payment_method": False,
            "ip_reputation_score": 0.2,
            "rapid_signup": True,
            "vpn_detected": True,
        }
        score = calculate_risk_score(context)
        assert 71 <= score <= 100  # High risk range

    def test_enterprise_domain_reduces_risk(self):
        context = {
            "email_domain": "microsoft.com",
            "signup_source": "organic",
            "has_payment_method": True,
            "ip_reputation_score": 0.9,
        }
        score = calculate_risk_score(context)
        assert score < 30  # Enterprise domain should result in low risk


class TestDetermineFastLaneEligibility:
    """Test fast lane eligibility determination."""

    def test_eligible_low_risk_new_user(self):
        user_id = "user-123"
        context = {
            "email_domain": "company.com",
            "signup_source": "organic",
            "has_payment_method": False,
            "ip_reputation_score": 0.8,
        }
        checklist = {
            "terms_accepted": True,
            "email_verified": True,
            "privacy_policy": True,
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        assert eligibility.is_eligible is True
        assert eligibility.user_id == user_id
        assert eligibility.risk_level == RiskLevel.LOW
        assert eligibility.skip_steps is not None
        assert len(eligibility.skip_steps) > 0
        assert eligibility.required_checklist == checklist

    def test_not_eligible_high_risk(self):
        user_id = "user-456"
        context = {
            "email_domain": "tempmail.com",
            "ip_reputation_score": 0.2,
            "vpn_detected": True,
        }
        checklist = {
            "terms_accepted": True,
            "email_verified": True,
            "privacy_policy": True,
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        assert eligibility.is_eligible is False
        assert eligibility.risk_level == RiskLevel.HIGH
        assert eligibility.reason is not None
        assert "risk" in eligibility.reason.lower()

    def test_not_eligible_incomplete_checklist(self):
        user_id = "user-789"
        context = {
            "email_domain": "company.com",
            "ip_reputation_score": 0.9,
        }
        checklist = {
            "terms_accepted": True,
            "email_verified": False,  # Missing!
            "privacy_policy": True,
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        assert eligibility.is_eligible is False
        assert eligibility.reason is not None
        assert "checklist" in eligibility.reason.lower()

    def test_enterprise_user_always_eligible(self):
        user_id = "user-enterprise"
        context = {
            "segment": UserSegment.ENTERPRISE,
            "email_domain": "enterprise.com",
            "ip_reputation_score": 0.9,
        }
        checklist = {
            "terms_accepted": True,
            "email_verified": True,
            "privacy_policy": True,
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        assert eligibility.is_eligible is True
        assert eligibility.risk_level == RiskLevel.LOW

    def test_eligibility_includes_justification(self):
        user_id = "user-123"
        context = {
            "email_domain": "company.com",
            "ip_reputation_score": 0.8,
        }
        checklist = {
            "terms_accepted": True,
            "email_verified": True,
            "privacy_policy": True,
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        assert eligibility.justification is not None
        assert len(eligibility.justification) > 0


class TestGetFastLanePath:
    """Test getting fast lane path with skipped steps."""

    def test_fast_lane_skips_non_essential_steps(self):
        user_id = "user-123"
        eligibility = FastLaneEligibility(
            user_id=user_id,
            is_eligible=True,
            risk_level=RiskLevel.LOW,
            skip_steps=["customization", "advanced_settings"],
            required_checklist={"terms_accepted": True},
            justification="Low risk user",
        )

        path = get_fast_lane_path(user_id, eligibility)

        assert path["user_id"] == user_id
        assert path["is_fast_lane"] is True
        assert "customization" in path["skipped_steps"]
        assert "advanced_settings" in path["skipped_steps"]
        assert len(path["remaining_steps"]) < len(path["original_steps"])
        assert path["estimated_time_saved_minutes"] > 0

    def test_standard_path_for_ineligible_user(self):
        user_id = "user-456"
        eligibility = FastLaneEligibility(
            user_id=user_id,
            is_eligible=False,
            risk_level=RiskLevel.HIGH,
            skip_steps=[],
            required_checklist={},
            reason="High risk user",
        )

        path = get_fast_lane_path(user_id, eligibility)

        assert path["is_fast_lane"] is False
        assert len(path["skipped_steps"]) == 0
        assert path["estimated_time_saved_minutes"] == 0

    def test_path_includes_required_checklist(self):
        user_id = "user-123"
        checklist = {
            "terms_accepted": True,
            "email_verified": True,
            "privacy_policy": True,
        }
        eligibility = FastLaneEligibility(
            user_id=user_id,
            is_eligible=True,
            risk_level=RiskLevel.LOW,
            skip_steps=["customization"],
            required_checklist=checklist,
            justification="Low risk",
        )

        path = get_fast_lane_path(user_id, eligibility)

        assert path["required_checklist"] == checklist
        assert path["checklist_complete"] is True


class TestFastLaneConfig:
    """Test fast lane configuration."""

    def test_default_config_values(self):
        config = FastLaneConfig()
        assert config.enabled is True
        assert config.max_risk_score <= 100
        assert config.min_risk_score >= 0
        assert len(config.skippable_steps) > 0

    def test_config_can_disable_fast_lane(self):
        config = FastLaneConfig(enabled=False)
        assert config.enabled is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_context_defaults_to_standard_path(self):
        user_id = "user-empty"
        context = {}
        checklist = {
            "terms_accepted": True,
            "email_verified": True,
            "privacy_policy": True,
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        # Empty context should be treated conservatively
        assert eligibility.is_eligible is False or eligibility.risk_level == RiskLevel.MEDIUM

    def test_missing_checklist_items_detected(self):
        user_id = "user-123"
        context = {"ip_reputation_score": 0.9}
        checklist = {
            "terms_accepted": True,
            # Missing email_verified and privacy_policy
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        assert eligibility.is_eligible is False
        missing_items = eligibility.missing_checklist_items
        assert "email_verified" in missing_items or "privacy_policy" in missing_items

    def test_power_user_gets_more_skippable_steps(self):
        user_id = "user-power"
        context = {
            "segment": UserSegment.POWER_USER,
            "previous_completions": 5,
            "ip_reputation_score": 0.95,
        }
        checklist = {
            "terms_accepted": True,
            "email_verified": True,
            "privacy_policy": True,
        }

        eligibility = determine_fast_lane_eligibility(user_id, context, checklist)

        if eligibility.is_eligible:
            # Power users should skip more steps
            assert len(eligibility.skip_steps) >= 2
