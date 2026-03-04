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
    infer_prefill_data,
    merge_prefill_with_explicit,
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


# =============================================================================
# v38 SPECIFICATION COMPLIANT TESTS
# =============================================================================

class TestInferPrefillData:
    """Test the specification-compliant infer_prefill_data function."""

    # --- UTM Campaign Rules ---
    
    def test_utm_campaign_blog_returns_blog_post(self):
        """UTM campaign 'blog' → template_type: 'blog_post'"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="blog",
        )
        assert result["template_type"] == "blog_post"
        assert result["confidence"] == "high"
        assert result["source"] == "utm_campaign"

    def test_utm_campaign_landing_returns_landing_page(self):
        """UTM campaign 'landing' → template_type: 'landing_page'"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="landing",
        )
        assert result["template_type"] == "landing_page"
        assert result["confidence"] == "high"
        assert result["source"] == "utm_campaign"

    def test_utm_campaign_social_returns_social_media(self):
        """UTM campaign 'social' → template_type: 'social_media'"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="social",
        )
        assert result["template_type"] == "social_media"
        assert result["confidence"] == "high"
        assert result["source"] == "utm_campaign"

    def test_utm_campaign_email_returns_email_marketing(self):
        """UTM campaign 'email' → template_type: 'email_marketing'"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="email",
        )
        assert result["template_type"] == "email_marketing"
        assert result["confidence"] == "high"
        assert result["source"] == "utm_campaign"

    def test_utm_campaign_case_insensitive(self):
        """UTM campaign matching should be case-insensitive"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="BLOG",
        )
        assert result["template_type"] == "blog_post"

    def test_utm_campaign_partial_match(self):
        """UTM campaign with partial match"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="my_blog_campaign",
        )
        assert result["template_type"] == "blog_post"

    # --- Referrer Rules ---

    def test_referrer_google_returns_paid_search(self):
        """Referrer contains 'google' → channel: 'paid_search'"""
        result = infer_prefill_data(
            source="test",
            referrer="https://google.com/search",
        )
        assert result["channel"] == "paid_search"
        assert result["source"] == "referrer"
        assert result["confidence"] == "medium"

    def test_referrer_facebook_returns_social_ads(self):
        """Referrer contains 'facebook' → channel: 'social_ads'"""
        result = infer_prefill_data(
            source="test",
            referrer="https://facebook.com/groups/marketing",
        )
        assert result["channel"] == "social_ads"
        assert result["source"] == "referrer"
        assert result["confidence"] == "medium"

    def test_referrer_meta_returns_social_ads(self):
        """Referrer contains 'meta' → channel: 'social_ads'"""
        result = infer_prefill_data(
            source="test",
            referrer="https://meta.com/business",
        )
        assert result["channel"] == "social_ads"
        assert result["source"] == "referrer"

    def test_referrer_case_insensitive(self):
        """Referrer matching should be case-insensitive"""
        result = infer_prefill_data(
            source="test",
            referrer="https://GOOGLE.com/search",
        )
        assert result["channel"] == "paid_search"

    # --- Email Domain Rules ---

    def test_email_enterprise_com_returns_enterprise(self):
        """Email domain contains '@enterprise.com' → segment: 'enterprise'"""
        result = infer_prefill_data(
            source="test",
            email="user@enterprise.com",
        )
        assert result["segment"] == "enterprise"
        assert result["source"] == "email_domain"
        assert result["confidence"] == "medium"

    def test_email_corp_domain_returns_enterprise(self):
        """Email domain contains '@corp.' → segment: 'enterprise'"""
        result = infer_prefill_data(
            source="test",
            email="user@corp.example.com",
        )
        assert result["segment"] == "enterprise"

    def test_email_gmail_returns_smb(self):
        """Email domain contains '@gmail.com' → segment: 'smb'"""
        result = infer_prefill_data(
            source="test",
            email="user@gmail.com",
        )
        assert result["segment"] == "smb"
        assert result["source"] == "email_domain"
        assert result["confidence"] == "medium"

    def test_email_outlook_returns_smb(self):
        """Email domain contains '@outlook.com' → segment: 'smb'"""
        result = infer_prefill_data(
            source="test",
            email="user@outlook.com",
        )
        assert result["segment"] == "smb"

    def test_email_case_insensitive(self):
        """Email domain matching should be case-insensitive"""
        result = infer_prefill_data(
            source="test",
            email="user@GMAIL.COM",
        )
        assert result["segment"] == "smb"

    # --- Fallback Tests ---

    def test_fallback_when_no_signals(self):
        """Test fallback when no signals are provided"""
        result = infer_prefill_data(
            source="test",
        )
        assert result["template_type"] is None
        assert result["channel"] is None
        assert result["segment"] is None
        assert result["confidence"] == "low"
        assert result["source"] == "default"

    def test_fallback_with_unmatched_signals(self):
        """Test fallback when signals don't match any rules"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="unknown_campaign",
            referrer="https://example.com",
            email="user@unknown-domain.com",
        )
        assert result["template_type"] is None
        assert result["channel"] is None
        assert result["segment"] is None
        assert result["confidence"] == "low"
        assert result["source"] == "default"

    # --- Multiple Signals Tests ---

    def test_multiple_signals_priority(self):
        """UTM campaign has highest priority when multiple signals present"""
        result = infer_prefill_data(
            source="test",
            utm_campaign="blog",
            referrer="https://google.com",
            email="user@enterprise.com",
        )
        # UTM campaign should determine the source
        assert result["template_type"] == "blog_post"
        assert result["channel"] == "paid_search"
        assert result["segment"] == "enterprise"
        assert result["confidence"] == "high"
        assert "utm_campaign" in result["source"]


class TestMergePrefillWithExplicit:
    """Test that prefill never overrides explicit user input."""

    def test_explicit_values_preserved(self):
        """NUNCA sobrescrever input explícito do usuário"""
        prefill_data = {
            "template_type": "blog_post",
            "channel": "paid_search",
            "segment": "smb",
            "confidence": "high",
            "source": "utm_campaign",
        }
        explicit_fields = {
            "template_type": "landing_page",  # User explicitly chose this
        }
        
        result = merge_prefill_with_explicit(prefill_data, explicit_fields)
        
        # Explicit value should be preserved
        assert result["template_type"] == "landing_page"
        # Other prefill values should remain
        assert result["channel"] == "paid_search"
        assert result["segment"] == "smb"

    def test_explicit_none_does_not_override(self):
        """Explicit None values should not override prefill"""
        prefill_data = {
            "template_type": "blog_post",
            "confidence": "high",
        }
        explicit_fields = {
            "template_type": None,
        }
        
        result = merge_prefill_with_explicit(prefill_data, explicit_fields)
        
        # Prefill value should be preserved
        assert result["template_type"] == "blog_post"

    def test_explicit_empty_string_does_not_override(self):
        """Explicit empty string should not override prefill"""
        prefill_data = {
            "template_type": "blog_post",
            "confidence": "high",
        }
        explicit_fields = {
            "template_type": "",
        }
        
        result = merge_prefill_with_explicit(prefill_data, explicit_fields)
        
        # Prefill value should be preserved
        assert result["template_type"] == "blog_post"

    def test_merged_prefill_and_explicit(self):
        """Test merging prefill with explicit fields without conflict"""
        prefill_data = {
            "template_type": "blog_post",
            "channel": "paid_search",
            "confidence": "high",
            "source": "utm_campaign",
        }
        explicit_fields = {
            "brand_name": "My Brand",  # New field not in prefill
        }
        
        result = merge_prefill_with_explicit(prefill_data, explicit_fields)
        
        # Both should be present
        assert result["template_type"] == "blog_post"
        assert result["channel"] == "paid_search"
        assert result["brand_name"] == "My Brand"
