"""v38 Onboarding Fast Lane - reduces TTFV by skipping non-essential steps for eligible users.

v39: Added telemetry tracking for fast lane events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json

# In-memory event store for fast lane telemetry (replace with DB in production)
_fast_lane_events: List[Dict[str, Any]] = []


class FastLaneEventType(str, Enum):
    """Types of fast lane interaction events."""
    PRESENTED = "presented"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    """Risk assessment levels for fast lane eligibility."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserSegment(str, Enum):
    """User segments for eligibility determination."""
    NEW_USER = "new_user"
    RETURNING = "returning"
    ENTERPRISE = "enterprise"
    POWER_USER = "power_user"


# Minimum required checklist items that cannot be skipped
MINIMUM_CHECKLIST = [
    "terms_accepted",
    "email_verified",
    "privacy_policy",
]

# Default onboarding steps
DEFAULT_ONBOARDING_STEPS = [
    "welcome",
    "workspace_setup",
    "template_selection",
    "customization",
    "advanced_settings",
    "integrations",
    "first_run",
    "completion",
]

# Steps that can be skipped in fast lane (in order of skip priority)
SKIPPABLE_STEPS = [
    "advanced_settings",
    "integrations",
    "customization",
]

# Enterprise/trusted domains that reduce risk
TRUSTED_DOMAINS = {
    "microsoft.com", "google.com", "apple.com", "amazon.com",
    "salesforce.com", "hubspot.com", "shopify.com", "adobe.com",
    "ibm.com", "oracle.com", "sap.com", "slack.com",
}

# High-risk domains that increase risk score
HIGH_RISK_DOMAINS = {
    "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "throwaway.com", "mailinator.com", "yopmail.com",
}


@dataclass
class FastLaneEligibility:
    """Result of fast lane eligibility check."""
    user_id: str
    is_eligible: bool
    risk_level: RiskLevel
    skip_steps: List[str] = field(default_factory=list)
    required_checklist: Dict[str, bool] = field(default_factory=dict)
    missing_checklist_items: List[str] = field(default_factory=list)
    justification: str = ""
    reason: str = ""  # Reason for ineligibility
    estimated_time_saved_minutes: float = 0.0


@dataclass
class FastLaneConfig:
    """Configuration for fast lane feature."""
    enabled: bool = True
    min_risk_score: int = 0
    max_risk_score: int = 40  # Max risk score for fast lane eligibility
    skippable_steps: List[str] = field(default_factory=lambda: SKIPPABLE_STEPS.copy())
    require_all_checklist: bool = True
    enterprise_always_eligible: bool = True


def calculate_risk_score(context: Dict[str, Any]) -> int:
    """Calculate risk score based on user context.
    
    Score ranges:
    - 0-30: Low risk (eligible for fast lane)
    - 31-70: Medium risk (standard path)
    - 71-100: High risk (enhanced verification required)
    
    Factors considered:
    - Email domain reputation
    - Signup source
    - IP reputation
    - Payment method presence
    - VPN/proxy detection
    - Signup velocity
    """
    score = 0
    
    # Email domain risk
    email_domain = context.get("email_domain", "").lower()
    if email_domain in TRUSTED_DOMAINS:
        score -= 20  # Trusted domain reduces risk
    elif email_domain in HIGH_RISK_DOMAINS:
        score += 20  # Disposable email increases risk
    elif ".edu" in email_domain:
        score -= 10  # Educational domains slightly trusted
    elif any(x in email_domain for x in ["temp", "throw", "disposable"]):
        score += 15
    
    # IP reputation
    ip_reputation = context.get("ip_reputation_score", 0.5)
    if ip_reputation < 0.3:
        score += 25
    elif ip_reputation < 0.6:
        score += 10
    elif ip_reputation > 0.8:
        score -= 10
    
    # Signup source
    signup_source = context.get("signup_source", "unknown")
    if signup_source == "organic":
        score -= 5
    elif signup_source in ["referral", "partner"]:
        score -= 10
    elif signup_source == "unknown":
        score += 10
    
    # Payment method presence indicates commitment
    if context.get("has_payment_method"):
        score -= 15
    
    # VPN/Proxy detection
    if context.get("vpn_detected"):
        score += 20
    if context.get("proxy_detected"):
        score += 15
    
    # Rapid signup (bot indicator)
    if context.get("rapid_signup"):
        score += 25
    
    # Previous history
    if context.get("previous_completions", 0) > 0:
        score -= 10
    
    # Normalize score to 0-100 range
    score = max(0, min(100, score + 25))  # Base score of 25
    
    return score


def determine_fast_lane_eligibility(
    user_id: str,
    context: Dict[str, Any],
    checklist: Dict[str, bool],
    config: Optional[FastLaneConfig] = None,
) -> FastLaneEligibility:
    """Determine if user is eligible for fast lane onboarding.
    
    Eligibility criteria:
    1. Complete minimum checklist
    2. Risk score below threshold
    3. Not flagged for enhanced verification
    """
    config = config or FastLaneConfig()
    
    if not config.enabled:
        return FastLaneEligibility(
            user_id=user_id,
            is_eligible=False,
            risk_level=RiskLevel.HIGH,
            reason="Fast lane is currently disabled",
            required_checklist=checklist,
        )
    
    # Check minimum checklist completion
    missing_items = [
        item for item in MINIMUM_CHECKLIST
        if not checklist.get(item, False)
    ]
    
    if missing_items:
        return FastLaneEligibility(
            user_id=user_id,
            is_eligible=False,
            risk_level=RiskLevel.HIGH,
            missing_checklist_items=missing_items,
            reason=f"Incomplete checklist: missing {', '.join(missing_items)}",
            required_checklist=checklist,
        )
    
    # Calculate risk score
    risk_score = calculate_risk_score(context)
    
    # Determine risk level
    if risk_score <= 30:
        risk_level = RiskLevel.LOW
    elif risk_score <= 70:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.HIGH
    
    # Check enterprise override
    segment = context.get("segment")
    if config.enterprise_always_eligible and segment == UserSegment.ENTERPRISE:
        skip_steps = _determine_skip_steps(context, config)
        return FastLaneEligibility(
            user_id=user_id,
            is_eligible=True,
            risk_level=RiskLevel.LOW,
            skip_steps=skip_steps,
            required_checklist=checklist,
            justification="Enterprise user - automatically eligible",
            estimated_time_saved_minutes=_estimate_time_saved(skip_steps),
        )
    
    # Check risk threshold
    if risk_score > config.max_risk_score:
        return FastLaneEligibility(
            user_id=user_id,
            is_eligible=False,
            risk_level=risk_level,
            reason=f"Risk score {risk_score} exceeds threshold {config.max_risk_score}",
            required_checklist=checklist,
        )
    
    # User is eligible for fast lane
    skip_steps = _determine_skip_steps(context, config)
    
    return FastLaneEligibility(
        user_id=user_id,
        is_eligible=True,
        risk_level=risk_level,
        skip_steps=skip_steps,
        required_checklist=checklist,
        justification=f"Low risk user (score: {risk_score}) with complete checklist",
        estimated_time_saved_minutes=_estimate_time_saved(skip_steps),
    )


def _determine_skip_steps(context: Dict[str, Any], config: FastLaneConfig) -> List[str]:
    """Determine which steps can be skipped based on user context."""
    skip_steps = []
    
    # Base skippable steps
    skip_steps.extend(config.skippable_steps)
    
    # Power users can skip more
    segment = context.get("segment")
    previous_completions = context.get("previous_completions", 0)
    
    if segment == UserSegment.POWER_USER or previous_completions >= 3:
        # Power users might skip customization if they have history
        if "customization" not in skip_steps:
            skip_steps.append("customization")
    
    # Enterprise users get maximum fast lane
    if segment == UserSegment.ENTERPRISE:
        # Can skip even more steps
        pass  # Already have all skippable steps
    
    return skip_steps


def _estimate_time_saved(skip_steps: List[str]) -> float:
    """Estimate time saved in minutes based on skipped steps."""
    # Average time per step (in minutes)
    step_time_estimates = {
        "advanced_settings": 3.0,
        "integrations": 5.0,
        "customization": 4.0,
    }
    
    total_saved = 0.0
    for step in skip_steps:
        total_saved += step_time_estimates.get(step, 2.0)
    
    return round(total_saved, 1)


def get_fast_lane_path(
    user_id: str,
    eligibility: FastLaneEligibility,
) -> Dict[str, Any]:
    """Generate fast lane path with skipped steps identified."""
    original_steps = DEFAULT_ONBOARDING_STEPS.copy()
    
    if not eligibility.is_eligible:
        return {
            "user_id": user_id,
            "is_fast_lane": False,
            "original_steps": original_steps,
            "remaining_steps": original_steps,
            "skipped_steps": [],
            "required_checklist": eligibility.required_checklist,
            "checklist_complete": len(eligibility.missing_checklist_items) == 0,
            "estimated_time_saved_minutes": 0,
            "reason": eligibility.reason,
        }
    
    # Calculate remaining steps
    skipped_steps = eligibility.skip_steps
    remaining_steps = [s for s in original_steps if s not in skipped_steps]
    
    # Calculate time saved if not already set
    time_saved = eligibility.estimated_time_saved_minutes
    if time_saved == 0 and skipped_steps:
        time_saved = _estimate_time_saved(skipped_steps)
    
    return {
        "user_id": user_id,
        "is_fast_lane": True,
        "original_steps": original_steps,
        "remaining_steps": remaining_steps,
        "skipped_steps": skipped_steps,
        "required_checklist": eligibility.required_checklist,
        "checklist_complete": True,
        "estimated_time_saved_minutes": time_saved,
        "justification": eligibility.justification,
        "risk_level": eligibility.risk_level,
    }


def get_fast_lane_for_user(
    user_id: str,
    session=None,
    context: Optional[Dict[str, Any]] = None,
    checklist: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """Get fast lane configuration for a user.
    
    In production, this would fetch user data from database.
    For now, uses provided context or returns default standard path.
    """
    # Default checklist (all required items not completed)
    default_checklist = {item: False for item in MINIMUM_CHECKLIST}
    
    if checklist:
        default_checklist.update(checklist)
    
    # Default context
    default_context = {
        "ip_reputation_score": 0.5,
        "signup_source": "unknown",
    }
    
    if context:
        default_context.update(context)
    
    # Determine eligibility
    eligibility = determine_fast_lane_eligibility(
        user_id=user_id,
        context=default_context,
        checklist=default_checklist,
    )
    
    return get_fast_lane_path(user_id, eligibility)


# v39: Telemetry tracking functions
def track_fast_lane_event(
    user_id: str,
    event_type: str,  # "presented", "accepted", "rejected"
    context: Dict[str, Any],
) -> None:
    """Track fast lane interaction event.
    
    Args:
        user_id: Unique identifier for the user
        event_type: Type of event ("presented", "accepted", "rejected")
        context: Additional context data for the event
    
    Events tracked:
    - presented: Fast lane option was shown to user
    - accepted: User chose fast lane path
    - rejected: User chose standard onboarding path
    """
    event = {
        "user_id": user_id,
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "context": context,
    }
    _fast_lane_events.append(event)


def get_fast_lane_events(
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get fast lane events, optionally filtered.
    
    Args:
        user_id: Filter by user ID
        event_type: Filter by event type
    
    Returns:
        List of matching events
    """
    events = _fast_lane_events
    
    if user_id:
        events = [e for e in events if e["user_id"] == user_id]
    
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    
    return events.copy()


def clear_fast_lane_events() -> None:
    """Clear all fast lane events (useful for testing)."""
    _fast_lane_events.clear()


def get_fast_lane_recommendation(
    user_id: str,
    prefill_data: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return recommendation for fast lane with confidence score and reasons.
    
    This function analyzes user context and prefill data to determine
    whether fast lane is recommended and provides confidence scoring.
    
    Args:
        user_id: Unique identifier for the user
        prefill_data: Data inferred from prefill (template_type, channel, segment)
        context: User context including email_domain, signup_source, etc.
    
    Returns:
        {
            "recommended_path": "fast_lane" | "standard",
            "confidence": float,  # 0-1
            "reasons": List[str],
            "skipped_steps": List[str],
            "estimated_time_saved_minutes": float,
        }
    """
    reasons = []
    confidence_factors = []
    
    # Analyze prefill confidence
    prefill_confidence = prefill_data.get("confidence", "low")
    prefill_source = prefill_data.get("source", "unknown")
    
    # Factor 1: Prefill data quality
    if prefill_confidence == "high":
        confidence_factors.append(0.3)
        reasons.append("High confidence prefill data available")
    elif prefill_confidence == "medium":
        confidence_factors.append(0.2)
        reasons.append("Medium confidence prefill data available")
    else:
        confidence_factors.append(0.05)
        reasons.append("Low confidence prefill data")
    
    # Factor 2: Email domain reputation
    email_domain = context.get("email_domain", "").lower()
    if email_domain in TRUSTED_DOMAINS:
        confidence_factors.append(0.25)
        reasons.append(f"Trusted domain: {email_domain}")
    elif email_domain in HIGH_RISK_DOMAINS:
        confidence_factors.append(-0.2)
        reasons.append("High-risk email domain detected")
    elif ".edu" in email_domain:
        confidence_factors.append(0.15)
        reasons.append("Educational institution domain")
    else:
        confidence_factors.append(0.1)
        reasons.append("Standard email domain")
    
    # Factor 3: Signup source
    signup_source = context.get("signup_source", "unknown")
    if signup_source in ["referral", "partner"]:
        confidence_factors.append(0.2)
        reasons.append(f"Trusted signup source: {signup_source}")
    elif signup_source == "organic":
        confidence_factors.append(0.15)
        reasons.append("Organic signup source")
    else:
        confidence_factors.append(0.05)
        reasons.append("Unknown signup source")
    
    # Factor 4: User segment
    segment = context.get("segment")
    if segment == UserSegment.ENTERPRISE:
        confidence_factors.append(0.25)
        reasons.append("Enterprise user segment")
    elif segment == UserSegment.POWER_USER:
        confidence_factors.append(0.2)
        reasons.append("Power user segment")
    elif segment == UserSegment.RETURNING:
        confidence_factors.append(0.15)
        reasons.append("Returning user")
    
    # Factor 5: Payment method (indicates commitment)
    if context.get("has_payment_method"):
        confidence_factors.append(0.15)
        reasons.append("Payment method on file")
    
    # Factor 6: Previous completions
    previous_completions = context.get("previous_completions", 0)
    if previous_completions >= 3:
        confidence_factors.append(0.2)
        reasons.append("Multiple previous completions")
    elif previous_completions >= 1:
        confidence_factors.append(0.1)
        reasons.append("Previous completion history")
    
    # Factor 7: IP reputation
    ip_reputation = context.get("ip_reputation_score", 0.5)
    if ip_reputation > 0.8:
        confidence_factors.append(0.1)
        reasons.append("High IP reputation")
    elif ip_reputation < 0.3:
        confidence_factors.append(-0.15)
        reasons.append("Low IP reputation")
    
    # Calculate final confidence (sum of factors, clamped to 0-1)
    confidence = sum(confidence_factors)
    confidence = max(0.0, min(1.0, confidence))
    
    # Determine recommendation threshold
    # Confidence >= 0.6: recommend fast_lane
    # Confidence < 0.6: recommend standard
    recommended_path = "fast_lane" if confidence >= 0.6 else "standard"
    
    # Determine which steps would be skipped
    if recommended_path == "fast_lane":
        skip_steps = _determine_skip_steps(context, FastLaneConfig())
        time_saved = _estimate_time_saved(skip_steps)
    else:
        skip_steps = []
        time_saved = 0.0
        reasons.append("Confidence below threshold for fast lane")
    
    return {
        "recommended_path": recommended_path,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "skipped_steps": skip_steps,
        "estimated_time_saved_minutes": time_saved,
    }
