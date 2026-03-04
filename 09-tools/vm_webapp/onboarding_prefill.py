"""v38 Onboarding Smart Prefill - reduces setup time by inferring user intent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse


class PrefillSource(str, Enum):
    """Sources for prefill inference."""

    UTM_CAMPAIGN = "utm_campaign"
    REFERRER_DOMAIN = "referrer_domain"
    USER_SEGMENT = "user_segment"
    EMAIL_DOMAIN = "email_domain"
    DEFAULT = "default"


@dataclass
class PrefillRule:
    """Rule for applying prefill based on source matching."""

    source: PrefillSource
    match_pattern: str
    field_mappings: Dict[str, str]
    priority: int = 0


@dataclass
class UserContext:
    """User context for prefill inference."""

    user_id: str
    email: Optional[str] = None
    utm_params: Dict[str, str] = field(default_factory=dict)
    referrer: Optional[str] = None
    signup_timestamp: Optional[datetime] = None
    segment: Optional[str] = None


# Domain-to-category mappings for referrer-based prefill
DOMAIN_CATEGORY_MAP = {
    "facebook": "social",
    "instagram": "social",
    "twitter": "social",
    "linkedin": "social",
    "google": "content",
    "youtube": "video",
    "shopify": "ecommerce",
    "woocommerce": "ecommerce",
    "amazon": "ecommerce",
}

# Email domain-to-segment mappings
EMAIL_DOMAIN_SEGMENT_MAP = {
    "shopify": "ecommerce",
    "amazon": "ecommerce",
    "hubspot": "marketing",
    "salesforce": "enterprise",
    "microsoft": "enterprise",
    "google": "general",
}

# UTM campaign to template mappings
CAMPAIGN_TEMPLATE_MAP = {
    "blog": "blog-post",
    "content": "blog-post",
    "landing": "landing-page",
    "conversion": "landing-page",
    "social": "social-media",
    "instagram": "social-media",
    "email": "email-marketing",
    "newsletter": "email-marketing",
    "ads": "google-ads",
    "google-ads": "google-ads",
    "meta-ads": "meta-ads",
    "facebook-ads": "meta-ads",
}

# Segment to category mappings
SEGMENT_CATEGORY_MAP = {
    "ecommerce": "conversion",
    "enterprise": "ads",
    "smb": "content",
    "marketing": "social",
    "content_creator": "content",
}

# Default prefill values
DEFAULT_PREFILL = {
    "template_id": "blog-post",
    "category": "content",
}


def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix if present
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def get_domain_keyword(domain: str) -> str:
    """Extract keyword from domain for matching."""
    parts = domain.split(".")
    if parts:
        return parts[0].lower()
    return domain.lower()


def apply_prefill_rules(
    context: UserContext, rules: List[PrefillRule]
) -> Dict[str, str]:
    """Apply prefill rules in priority order.

    Higher priority rules are applied last, allowing them to override
    lower priority rules for the same fields.
    """
    result = {}

    # Sort rules by priority ascending, then apply in order
    sorted_rules = sorted(rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        # Check if rule matches context
        matches = False

        if rule.source == PrefillSource.UTM_CAMPAIGN:
            campaign = context.utm_params.get("campaign", "").lower()
            matches = rule.match_pattern.lower() in campaign or rule.match_pattern == "*"

        elif rule.source == PrefillSource.REFERRER_DOMAIN:
            if context.referrer:
                domain = extract_domain_from_url(context.referrer)
                keyword = get_domain_keyword(domain)
                matches = rule.match_pattern.lower() == keyword or rule.match_pattern == "*"

        elif rule.source == PrefillSource.USER_SEGMENT:
            segment = (context.segment or "").lower()
            matches = rule.match_pattern.lower() == segment or rule.match_pattern == "*"

        elif rule.source == PrefillSource.EMAIL_DOMAIN:
            if context.email:
                domain = context.email.split("@")[-1].lower()
                keyword = get_domain_keyword(domain)
                matches = rule.match_pattern.lower() == keyword or rule.match_pattern == "*"

        elif rule.source == PrefillSource.DEFAULT:
            matches = rule.match_pattern == "*"

        # Apply field mappings if matched
        if matches:
            result.update(rule.field_mappings)

    return result


def generate_prefill_payload(
    context: UserContext,
    explicit_values: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Generate prefill payload based on user context.

    Prefill logic (in priority order):
    1. UTM campaign (highest priority)
    2. Referrer domain
    3. User segment
    4. Email domain
    5. Default fallback
    """
    explicit_values = explicit_values or {}

    # Build rules based on context
    rules = []

    # Default rule (lowest priority)
    rules.append(
        PrefillRule(
            source=PrefillSource.DEFAULT,
            match_pattern="*",
            field_mappings=DEFAULT_PREFILL.copy(),
            priority=0,
        )
    )

    # Email domain rule
    if context.email:
        domain = context.email.split("@")[-1].lower()
        keyword = get_domain_keyword(domain)
        if keyword in EMAIL_DOMAIN_SEGMENT_MAP:
            segment = EMAIL_DOMAIN_SEGMENT_MAP[keyword]
            template = SEGMENT_CATEGORY_MAP.get(segment, "blog-post")
            rules.append(
                PrefillRule(
                    source=PrefillSource.EMAIL_DOMAIN,
                    match_pattern=keyword,
                    field_mappings={
                        "template_id": template if template != "blog-post" else "blog-post",
                        "category": segment,
                    },
                    priority=1,
                )
            )

    # User segment rule
    if context.segment:
        segment_lower = context.segment.lower()
        category = SEGMENT_CATEGORY_MAP.get(segment_lower, "content")
        rules.append(
            PrefillRule(
                source=PrefillSource.USER_SEGMENT,
                match_pattern=segment_lower,
                field_mappings={"category": category},
                priority=2,
            )
        )

    # Referrer domain rule
    if context.referrer:
        domain = extract_domain_from_url(context.referrer)
        keyword = get_domain_keyword(domain)
        if keyword in DOMAIN_CATEGORY_MAP:
            category = DOMAIN_CATEGORY_MAP[keyword]
            rules.append(
                PrefillRule(
                    source=PrefillSource.REFERRER_DOMAIN,
                    match_pattern=keyword,
                    field_mappings={"category": category},
                    priority=3,
                )
            )

    # UTM campaign rule (highest priority)
    if context.utm_params.get("campaign"):
        campaign = context.utm_params["campaign"].lower()
        for keyword, template in CAMPAIGN_TEMPLATE_MAP.items():
            if keyword in campaign:
                rules.append(
                    PrefillRule(
                        source=PrefillSource.UTM_CAMPAIGN,
                        match_pattern=keyword,
                        field_mappings={"template_id": template},
                        priority=4,
                    )
                )
                break

    # Apply rules
    prefill_fields = apply_prefill_rules(context, rules)

    # Determine prefill source with highest priority match
    prefill_source = PrefillSource.DEFAULT
    confidence = "low"

    if context.utm_params.get("campaign"):
        for keyword in CAMPAIGN_TEMPLATE_MAP:
            if keyword in context.utm_params["campaign"].lower():
                prefill_source = PrefillSource.UTM_CAMPAIGN
                confidence = "high"
                break
    elif context.referrer and get_domain_keyword(extract_domain_from_url(context.referrer)) in DOMAIN_CATEGORY_MAP:
        prefill_source = PrefillSource.REFERRER_DOMAIN
        confidence = "medium"
    elif context.segment:
        prefill_source = PrefillSource.USER_SEGMENT
        confidence = "medium"
    elif context.email and get_domain_keyword(context.email.split("@")[-1]) in EMAIL_DOMAIN_SEGMENT_MAP:
        prefill_source = PrefillSource.EMAIL_DOMAIN
        confidence = "medium"

    # Merge prefill with explicit values (explicit wins)
    final_fields = {**prefill_fields, **explicit_values}

    return {
        "user_id": context.user_id,
        "prefill_source": prefill_source,
        "confidence": confidence,
        "fields": final_fields,
        "context": {
            "has_utm": bool(context.utm_params),
            "has_referrer": bool(context.referrer),
            "has_segment": bool(context.segment),
        },
    }


def get_prefill_for_user(user_id: str, session=None) -> Dict[str, Any]:
    """Get prefill payload for a user from database.

    Args:
        user_id: The user's ID
        session: Optional database session (for testing)

    Returns:
        Prefill payload with inferred values
    """
    # For production, this would fetch from user database
    # For now, return default prefill (tests use mocked sessions)
    if session is not None:
        # Try to get user-like object from session (for testing with mocks)
        user = None
        if hasattr(session, 'get'):
            # Try common model names
            for model_name in ['User', 'OnboardingState']:
                try:
                    model = getattr(__import__('vm_webapp.models_onboarding', fromlist=[model_name]), model_name, None)
                    if model:
                        user = session.get(model, user_id)
                        if user:
                            break
                except (ImportError, AttributeError):
                    continue
        
        if user:
            # Build context from user data
            utm_params = {}
            if hasattr(user, 'signup_metadata') and user.signup_metadata:
                utm_params = {
                    "campaign": user.signup_metadata.get("utm_campaign", ""),
                    "source": user.signup_metadata.get("utm_source", ""),
                    "medium": user.signup_metadata.get("utm_medium", ""),
                }

            context = UserContext(
                user_id=getattr(user, 'user_id', user_id),
                email=getattr(user, 'email', None),
                utm_params=utm_params,
                signup_timestamp=getattr(user, 'created_at', None),
                segment=getattr(user, 'segment', None),
            )
            return generate_prefill_payload(context)

    # Return default prefill for unknown user
    return {
        "user_id": user_id,
        "prefill_source": PrefillSource.DEFAULT,
        "confidence": "low",
        "fields": DEFAULT_PREFILL.copy(),
        "context": {
            "has_utm": False,
            "has_referrer": False,
            "has_segment": False,
        },
    }


# =============================================================================
# v38 SPECIFICATION COMPLIANT API
# =============================================================================

def infer_prefill_data(
    source: str,
    utm_campaign: str | None = None,
    referrer: str | None = None,
    email: str | None = None,
) -> dict:
    """Infer prefill data from available user signals.
    
    v38: Friction Killer #1 - Smart Prefill
    Reduces onboarding setup time by inferring user intent from UTM params,
    referrer, and email domain.
    
    Args:
        source: Identifier for the inference source/context
        utm_campaign: UTM campaign parameter (optional)
        referrer: Referrer URL (optional)
        email: User email address (optional)
        
    Returns:
        Dictionary with inferred prefill data including:
        - template_type: Inferred template type
        - channel: Inferred marketing channel
        - segment: Inferred user segment
        - confidence: "high", "medium", or "low"
        - source: Which signal was used for inference
        
    Inference Rules:
        - UTM campaign "blog" → template_type: "blog_post"
        - UTM campaign "landing" → template_type: "landing_page"
        - UTM campaign "social" → template_type: "social_media"
        - UTM campaign "email" → template_type: "email_marketing"
        - Referrer contains "google" → channel: "paid_search"
        - Referrer contains "facebook" or "meta" → channel: "social_ads"
        - Email domain contains "@enterprise.com" or "@corp." → segment: "enterprise"
        - Email domain contains "@gmail.com" or "@outlook.com" → segment: "smb"
    """
    result = {
        "template_type": None,
        "channel": None,
        "segment": None,
        "confidence": "low",
        "source": "default",
    }
    
    signals_used = []
    
    # UTM Campaign rules (highest priority for template_type)
    if utm_campaign:
        campaign_lower = utm_campaign.lower()
        if "blog" in campaign_lower:
            result["template_type"] = "blog_post"
            result["confidence"] = "high"
            result["source"] = "utm_campaign"
            signals_used.append("utm_campaign")
        elif "landing" in campaign_lower:
            result["template_type"] = "landing_page"
            result["confidence"] = "high"
            result["source"] = "utm_campaign"
            signals_used.append("utm_campaign")
        elif "social" in campaign_lower:
            result["template_type"] = "social_media"
            result["confidence"] = "high"
            result["source"] = "utm_campaign"
            signals_used.append("utm_campaign")
        elif "email" in campaign_lower:
            result["template_type"] = "email_marketing"
            result["confidence"] = "high"
            result["source"] = "utm_campaign"
            signals_used.append("utm_campaign")
    
    # Referrer rules for channel
    if referrer:
        referrer_lower = referrer.lower()
        if "google" in referrer_lower:
            result["channel"] = "paid_search"
            if result["source"] == "default":
                result["source"] = "referrer"
                result["confidence"] = "medium"
            signals_used.append("referrer")
        elif "facebook" in referrer_lower or "meta" in referrer_lower:
            result["channel"] = "social_ads"
            if result["source"] == "default":
                result["source"] = "referrer"
                result["confidence"] = "medium"
            signals_used.append("referrer")
    
    # Email domain rules for segment
    if email:
        email_lower = email.lower()
        if "@enterprise.com" in email_lower or "@corp." in email_lower:
            result["segment"] = "enterprise"
            if result["source"] == "default":
                result["source"] = "email_domain"
                result["confidence"] = "medium"
            signals_used.append("email_domain")
        elif "@gmail.com" in email_lower or "@outlook.com" in email_lower:
            result["segment"] = "smb"
            if result["source"] == "default":
                result["source"] = "email_domain"
                result["confidence"] = "medium"
            signals_used.append("email_domain")
    
    # Update source to reflect all signals used
    if len(signals_used) > 1:
        result["source"] = "+".join(signals_used)
    
    return result


def merge_prefill_with_explicit(
    prefill_data: dict,
    explicit_fields: dict,
) -> dict:
    """Merge prefill data with explicit user input.
    
    NUNCA sobrescreve input explícito do usuário.
    Explicit values always take precedence over inferred values.
    
    Args:
        prefill_data: Inferred prefill data from infer_prefill_data()
        explicit_fields: User-provided explicit field values
        
    Returns:
        Merged dictionary with explicit values preserved
    """
    merged = prefill_data.copy()
    
    for key, value in explicit_fields.items():
        if value is not None and value != "":
            merged[key] = value
    
    return merged
