"""Tests for v38 onboarding smart prefill functionality."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from vm_webapp.onboarding_prefill import (
    PrefillSource,
    PrefillRule,
    UserContext,
    generate_prefill_payload,
    get_prefill_for_user,
    apply_prefill_rules,
)


class TestPrefillSource:
    """Test prefill source enum."""

    def test_prefill_source_values(self):
        assert PrefillSource.UTM_CAMPAIGN == "utm_campaign"
        assert PrefillSource.REFERRER_DOMAIN == "referrer_domain"
        assert PrefillSource.USER_SEGMENT == "user_segment"
        assert PrefillSource.EMAIL_DOMAIN == "email_domain"
        assert PrefillSource.DEFAULT == "default"


class TestPrefillRule:
    """Test prefill rule dataclass."""

    def test_prefill_rule_creation(self):
        rule = PrefillRule(
            source=PrefillSource.UTM_CAMPAIGN,
            match_pattern="blog",
            field_mappings={"template_id": "blog-post", "category": "content"},
            priority=1,
        )
        assert rule.source == PrefillSource.UTM_CAMPAIGN
        assert rule.match_pattern == "blog"
        assert rule.field_mappings == {"template_id": "blog-post", "category": "content"}
        assert rule.priority == 1

    def test_prefill_rule_default_priority(self):
        rule = PrefillRule(
            source=PrefillSource.DEFAULT,
            match_pattern="*",
            field_mappings={"template_id": "blog-post"},
        )
        assert rule.priority == 0


class TestUserContext:
    """Test user context dataclass."""

    def test_user_context_creation(self):
        context = UserContext(
            user_id="user-123",
            email="test@company.com",
            utm_params={"campaign": "blog", "source": "google"},
            referrer="https://google.com/search",
            signup_timestamp=datetime.now(timezone.utc),
            segment="enterprise",
        )
        assert context.user_id == "user-123"
        assert context.email == "test@company.com"
        assert context.utm_params["campaign"] == "blog"

    def test_user_context_minimal(self):
        context = UserContext(user_id="user-456")
        assert context.user_id == "user-456"
        assert context.email is None
        assert context.utm_params == {}


class TestGeneratePrefillPayload:
    """Test prefill payload generation."""

    def test_generate_prefill_from_utm_campaign(self):
        context = UserContext(
            user_id="user-123",
            utm_params={"campaign": "landing-page", "medium": "cpc"},
        )
        payload = generate_prefill_payload(context)

        assert payload["user_id"] == "user-123"
        assert payload["prefill_source"] == PrefillSource.UTM_CAMPAIGN
        assert payload["fields"]["template_id"] == "landing-page"
        assert payload["confidence"] == "high"

    def test_generate_prefill_from_referrer_domain(self):
        context = UserContext(
            user_id="user-123",
            referrer="https://facebook.com/groups/marketing",
        )
        payload = generate_prefill_payload(context)

        assert payload["prefill_source"] == PrefillSource.REFERRER_DOMAIN
        assert payload["fields"]["category"] == "social"
        assert payload["confidence"] in ["high", "medium"]

    def test_generate_prefill_from_email_domain(self):
        context = UserContext(
            user_id="user-123",
            email="user@shopify.com",
        )
        payload = generate_prefill_payload(context)

        assert payload["prefill_source"] == PrefillSource.EMAIL_DOMAIN
        assert "template_id" in payload["fields"]
        assert payload["confidence"] == "medium"

    def test_generate_prefill_from_user_segment(self):
        context = UserContext(
            user_id="user-123",
            segment="ecommerce",
        )
        payload = generate_prefill_payload(context)

        assert payload["prefill_source"] == PrefillSource.USER_SEGMENT
        assert payload["fields"]["category"] == "conversion"

    def test_generate_prefill_fallback_default(self):
        context = UserContext(user_id="user-123")
        payload = generate_prefill_payload(context)

        assert payload["prefill_source"] == PrefillSource.DEFAULT
        assert payload["fields"]["template_id"] == "blog-post"
        assert payload["confidence"] == "low"

    def test_prefill_does_not_override_explicit_input(self):
        context = UserContext(
            user_id="user-123",
            utm_params={"campaign": "blog"},
        )
        explicit_values = {"template_id": "custom-template"}
        payload = generate_prefill_payload(context, explicit_values=explicit_values)

        # Prefill should not override explicit values
        assert payload["fields"]["template_id"] == "custom-template"

    def test_prefill_applies_when_no_explicit_conflict(self):
        context = UserContext(
            user_id="user-123",
            utm_params={"campaign": "blog"},
        )
        explicit_values = {"category": "content"}
        payload = generate_prefill_payload(context, explicit_values=explicit_values)

        # Both prefill and explicit should be merged
        assert payload["fields"]["template_id"] == "blog-post"  # from prefill
        assert payload["fields"]["category"] == "content"  # from explicit


class TestApplyPrefillRules:
    """Test prefill rule application with priority."""

    def test_rule_priority_ordering(self):
        rules = [
            PrefillRule(
                source=PrefillSource.DEFAULT,
                match_pattern="*",
                field_mappings={"template_id": "default"},
                priority=0,
            ),
            PrefillRule(
                source=PrefillSource.UTM_CAMPAIGN,
                match_pattern="blog",
                field_mappings={"template_id": "blog-post"},
                priority=2,
            ),
            PrefillRule(
                source=PrefillSource.USER_SEGMENT,
                match_pattern="enterprise",
                field_mappings={"template_id": "enterprise"},
                priority=1,
            ),
        ]

        context = UserContext(
            user_id="user-123",
            utm_params={"campaign": "blog"},
            segment="enterprise",
        )

        result = apply_prefill_rules(context, rules)

        # Higher priority UTM_CAMPAIGN should win
        assert result["template_id"] == "blog-post"

    def test_partial_field_override(self):
        rules = [
            PrefillRule(
                source=PrefillSource.DEFAULT,
                match_pattern="*",
                field_mappings={"template_id": "default", "category": "general"},
                priority=0,
            ),
            PrefillRule(
                source=PrefillSource.USER_SEGMENT,
                match_pattern="ecommerce",
                field_mappings={"category": "conversion"},
                priority=1,
            ),
        ]

        context = UserContext(user_id="user-123", segment="ecommerce")
        result = apply_prefill_rules(context, rules)

        # Segment rule only overrides category, template_id stays from default
        assert result["template_id"] == "default"
        assert result["category"] == "conversion"


class TestGetPrefillForUser:
    """Test getting prefill for a user with database integration."""

    def test_get_prefill_for_new_user(self):
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "user-123"
        mock_user.email = "test@company.com"
        mock_user.signup_metadata = {"utm_campaign": "blog"}
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.segment = None

        mock_session.get.return_value = mock_user

        # Pass session directly - no need to mock session_scope
        payload = get_prefill_for_user("user-123", mock_session)

        assert payload["user_id"] == "user-123"
        assert "fields" in payload
        assert "prefill_source" in payload

    def test_get_prefill_user_not_found(self):
        mock_session = MagicMock()
        mock_session.get.return_value = None

        # Pass session directly
        payload = get_prefill_for_user("nonexistent-user", mock_session)

        # Should return default prefill for unknown user
        assert payload["user_id"] == "nonexistent-user"
        assert payload["prefill_source"] == PrefillSource.DEFAULT
