"""Tests for v39 Fast Lane telemetry and recommendation functionality."""

import pytest
from datetime import datetime
from typing import Dict, Any

from vm_webapp.onboarding_fast_lane import (
    # Core functions
    calculate_risk_score,
    determine_fast_lane_eligibility,
    get_fast_lane_path,
    get_fast_lane_for_user,
    # v39: Telemetry functions
    track_fast_lane_event,
    get_fast_lane_events,
    clear_fast_lane_events,
    get_fast_lane_recommendation,
    # Constants and enums
    RiskLevel,
    UserSegment,
    MINIMUM_CHECKLIST,
    SKIPPABLE_STEPS,
    TRUSTED_DOMAINS,
    HIGH_RISK_DOMAINS,
    FastLaneConfig,
)


class TestTrackFastLaneEvent:
    """Tests for track_fast_lane_event function."""
    
    def setup_method(self):
        """Clear events before each test."""
        clear_fast_lane_events()
    
    def teardown_method(self):
        """Clear events after each test."""
        clear_fast_lane_events()
    
    def test_track_presented_event(self):
        """Test tracking 'presented' event."""
        track_fast_lane_event(
            user_id="user_123",
            event_type="presented",
            context={"page": "onboarding", "timestamp": datetime.now().isoformat()},
        )
        
        events = get_fast_lane_events()
        assert len(events) == 1
        assert events[0]["user_id"] == "user_123"
        assert events[0]["event_type"] == "presented"
        assert "timestamp" in events[0]
        assert "context" in events[0]
    
    def test_track_accepted_event(self):
        """Test tracking 'accepted' event."""
        track_fast_lane_event(
            user_id="user_456",
            event_type="accepted",
            context={"path": "fast_lane", "confidence": 0.85},
        )
        
        events = get_fast_lane_events(user_id="user_456")
        assert len(events) == 1
        assert events[0]["event_type"] == "accepted"
        assert events[0]["context"]["path"] == "fast_lane"
    
    def test_track_rejected_event(self):
        """Test tracking 'rejected' event."""
        track_fast_lane_event(
            user_id="user_789",
            event_type="rejected",
            context={"reason": "user_prefers_standard", "confidence": 0.45},
        )
        
        events = get_fast_lane_events(event_type="rejected")
        assert len(events) == 1
        assert events[0]["user_id"] == "user_789"
        assert events[0]["event_type"] == "rejected"
    
    def test_multiple_events_same_user(self):
        """Test tracking multiple events for same user."""
        track_fast_lane_event("user_001", "presented", {})
        track_fast_lane_event("user_001", "accepted", {})
        
        events = get_fast_lane_events(user_id="user_001")
        assert len(events) == 2
        assert events[0]["event_type"] == "presented"
        assert events[1]["event_type"] == "accepted"
    
    def test_get_events_filter_by_user(self):
        """Test filtering events by user_id."""
        track_fast_lane_event("user_a", "presented", {})
        track_fast_lane_event("user_b", "presented", {})
        track_fast_lane_event("user_a", "accepted", {})
        
        user_a_events = get_fast_lane_events(user_id="user_a")
        assert len(user_a_events) == 2
        
        user_b_events = get_fast_lane_events(user_id="user_b")
        assert len(user_b_events) == 1
    
    def test_get_events_filter_by_type(self):
        """Test filtering events by event_type."""
        track_fast_lane_event("user_1", "presented", {})
        track_fast_lane_event("user_2", "accepted", {})
        track_fast_lane_event("user_3", "presented", {})
        
        presented_events = get_fast_lane_events(event_type="presented")
        assert len(presented_events) == 2
        
        accepted_events = get_fast_lane_events(event_type="accepted")
        assert len(accepted_events) == 1
    
    def test_get_events_filter_combined(self):
        """Test filtering events by both user_id and event_type."""
        track_fast_lane_event("user_x", "presented", {})
        track_fast_lane_event("user_x", "accepted", {})
        track_fast_lane_event("user_y", "presented", {})
        
        events = get_fast_lane_events(user_id="user_x", event_type="presented")
        assert len(events) == 1
        assert events[0]["user_id"] == "user_x"
        assert events[0]["event_type"] == "presented"
    
    def test_event_context_preservation(self):
        """Test that event context is preserved correctly."""
        context = {
            "page": "onboarding",
            "template_type": "blog-post",
            "confidence": 0.9,
            "metadata": {"source": "referral"},
        }
        track_fast_lane_event("user_123", "presented", context)
        
        events = get_fast_lane_events()
        assert events[0]["context"] == context


class TestGetFastLaneRecommendation:
    """Tests for get_fast_lane_recommendation function."""
    
    def test_recommendation_structure(self):
        """Test that recommendation has required structure."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={"confidence": "medium", "source": "utm"},
            context={"email_domain": "gmail.com", "signup_source": "organic"},
        )
        
        assert "recommended_path" in result
        assert result["recommended_path"] in ["fast_lane", "standard"]
        assert "confidence" in result
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1
        assert "reasons" in result
        assert isinstance(result["reasons"], list)
        assert "skipped_steps" in result
        assert isinstance(result["skipped_steps"], list)
        assert "estimated_time_saved_minutes" in result
        assert isinstance(result["estimated_time_saved_minutes"], float)
    
    def test_high_confidence_recommends_fast_lane(self):
        """Test that high confidence factors recommend fast lane."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={"confidence": "high", "source": "utm"},
            context={
                "email_domain": "microsoft.com",
                "signup_source": "referral",
                "segment": UserSegment.ENTERPRISE,
                "has_payment_method": True,
                "previous_completions": 3,
                "ip_reputation_score": 0.9,
            },
        )
        
        assert result["recommended_path"] == "fast_lane"
        assert result["confidence"] >= 0.6
        assert len(result["skipped_steps"]) > 0
        assert result["estimated_time_saved_minutes"] > 0
    
    def test_low_confidence_recommends_standard(self):
        """Test that low confidence factors recommend standard path."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={"confidence": "low", "source": "unknown"},
            context={
                "email_domain": "tempmail.com",
                "signup_source": "unknown",
                "ip_reputation_score": 0.2,
            },
        )
        
        assert result["recommended_path"] == "standard"
        assert result["confidence"] < 0.6
        assert len(result["skipped_steps"]) == 0
        assert result["estimated_time_saved_minutes"] == 0.0
    
    def test_trusted_domain_boosts_confidence(self):
        """Test that trusted domain increases confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"email_domain": "google.com"},
        )
        
        # Should have reason mentioning trusted domain
        domain_reasons = [r for r in result["reasons"] if "Trusted domain" in r]
        assert len(domain_reasons) > 0
    
    def test_high_risk_domain_reduces_confidence(self):
        """Test that high-risk domain reduces confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"email_domain": "tempmail.com"},
        )
        
        # Should have reason mentioning high-risk domain
        risk_reasons = [r for r in result["reasons"] if "High-risk" in r]
        assert len(risk_reasons) > 0
    
    def test_edu_domain_recognition(self):
        """Test that .edu domains are recognized."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"email_domain": "student.harvard.edu"},
        )
        
        edu_reasons = [r for r in result["reasons"] if "Educational" in r]
        assert len(edu_reasons) > 0
    
    def test_referral_source_boosts_confidence(self):
        """Test that referral signup source increases confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"signup_source": "referral"},
        )
        
        referral_reasons = [r for r in result["reasons"] if "referral" in r.lower()]
        assert len(referral_reasons) > 0
    
    def test_enterprise_segment_boosts_confidence(self):
        """Test that enterprise segment increases confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"segment": UserSegment.ENTERPRISE},
        )
        
        enterprise_reasons = [r for r in result["reasons"] if "Enterprise" in r]
        assert len(enterprise_reasons) > 0
    
    def test_power_user_segment_boosts_confidence(self):
        """Test that power user segment increases confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"segment": UserSegment.POWER_USER},
        )
        
        power_reasons = [r for r in result["reasons"] if "Power user" in r]
        assert len(power_reasons) > 0
    
    def test_payment_method_boosts_confidence(self):
        """Test that having payment method increases confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"has_payment_method": True},
        )
        
        payment_reasons = [r for r in result["reasons"] if "Payment method" in r]
        assert len(payment_reasons) > 0
    
    def test_previous_completions_boosts_confidence(self):
        """Test that previous completions increase confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"previous_completions": 3},
        )
        
        completion_reasons = [r for r in result["reasons"] if "completions" in r.lower()]
        assert len(completion_reasons) > 0
    
    def test_high_ip_reputation_boosts_confidence(self):
        """Test that high IP reputation increases confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"ip_reputation_score": 0.9},
        )
        
        ip_reasons = [r for r in result["reasons"] if "IP reputation" in r]
        assert len(ip_reasons) > 0
    
    def test_low_ip_reputation_reduces_confidence(self):
        """Test that low IP reputation reduces confidence."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={"ip_reputation_score": 0.2},
        )
        
        ip_reasons = [r for r in result["reasons"] if "IP reputation" in r]
        assert len(ip_reasons) > 0
        assert "Low IP reputation" in result["reasons"]
    
    def test_confidence_clamped_to_zero(self):
        """Test that confidence is clamped to minimum of 0."""
        # Create a scenario with very negative confidence factors
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={"confidence": "low"},
            context={
                "email_domain": "tempmail.com",
                "signup_source": "unknown",
                "ip_reputation_score": 0.1,
            },
        )
        
        assert result["confidence"] >= 0.0
    
    def test_confidence_clamped_to_one(self):
        """Test that confidence is clamped to maximum of 1."""
        # Create a scenario with very high confidence factors
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={"confidence": "high"},
            context={
                "email_domain": "microsoft.com",
                "signup_source": "referral",
                "segment": UserSegment.ENTERPRISE,
                "has_payment_method": True,
                "previous_completions": 5,
                "ip_reputation_score": 0.95,
            },
        )
        
        assert result["confidence"] <= 1.0
    
    def test_skipped_steps_for_fast_lane(self):
        """Test that skipped steps are returned for fast lane recommendation."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={"confidence": "high"},
            context={
                "email_domain": "google.com",
                "signup_source": "referral",
            },
        )
        
        if result["recommended_path"] == "fast_lane":
            assert len(result["skipped_steps"]) > 0
            # All skipped steps should be from SKIPPABLE_STEPS
            for step in result["skipped_steps"]:
                assert step in SKIPPABLE_STEPS
    
    def test_time_saved_calculation(self):
        """Test that time saved is calculated correctly."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={"confidence": "high"},
            context={
                "email_domain": "google.com",
                "signup_source": "referral",
            },
        )
        
        if result["recommended_path"] == "fast_lane":
            assert result["estimated_time_saved_minutes"] > 0
        else:
            assert result["estimated_time_saved_minutes"] == 0.0
    
    def test_reasons_not_empty(self):
        """Test that reasons list is never empty."""
        result = get_fast_lane_recommendation(
            user_id="user_123",
            prefill_data={},
            context={},
        )
        
        assert len(result["reasons"]) > 0


class TestExistingFastLaneFunctions:
    """Tests for existing fast lane functions to ensure backward compatibility."""
    
    def test_calculate_risk_score_trusted_domain(self):
        """Test risk score calculation with trusted domain."""
        context = {"email_domain": "google.com"}
        score = calculate_risk_score(context)
        # Should be lower due to trusted domain
        assert score < 50
    
    def test_calculate_risk_score_high_risk_domain(self):
        """Test risk score calculation with high-risk domain."""
        context = {"email_domain": "tempmail.com"}
        score = calculate_risk_score(context)
        # Should be higher due to high-risk domain
        assert score > 30
    
    def test_determine_eligibility_with_complete_checklist(self):
        """Test eligibility with complete checklist."""
        checklist = {item: True for item in MINIMUM_CHECKLIST}
        context = {"email_domain": "google.com"}
        
        result = determine_fast_lane_eligibility("user_123", context, checklist)
        
        assert result.is_eligible is True
        assert result.risk_level == RiskLevel.LOW
    
    def test_determine_eligibility_with_incomplete_checklist(self):
        """Test eligibility with incomplete checklist."""
        checklist = {item: False for item in MINIMUM_CHECKLIST}
        context = {}
        
        result = determine_fast_lane_eligibility("user_123", context, checklist)
        
        assert result.is_eligible is False
        assert len(result.missing_checklist_items) > 0
    
    def test_get_fast_lane_path_eligible(self):
        """Test getting fast lane path for eligible user."""
        from vm_webapp.onboarding_fast_lane import FastLaneEligibility
        
        eligibility = FastLaneEligibility(
            user_id="user_123",
            is_eligible=True,
            risk_level=RiskLevel.LOW,
            skip_steps=["advanced_settings", "integrations"],
            required_checklist={item: True for item in MINIMUM_CHECKLIST},
            estimated_time_saved_minutes=8.0,
        )
        
        path = get_fast_lane_path("user_123", eligibility)
        
        assert path["is_fast_lane"] is True
        assert len(path["skipped_steps"]) == 2
        assert path["estimated_time_saved_minutes"] == 8.0
    
    def test_get_fast_lane_path_not_eligible(self):
        """Test getting fast lane path for ineligible user."""
        from vm_webapp.onboarding_fast_lane import FastLaneEligibility
        
        eligibility = FastLaneEligibility(
            user_id="user_123",
            is_eligible=False,
            risk_level=RiskLevel.HIGH,
            reason="Risk score too high",
            required_checklist={item: True for item in MINIMUM_CHECKLIST},
        )
        
        path = get_fast_lane_path("user_123", eligibility)
        
        assert path["is_fast_lane"] is False
        assert len(path["skipped_steps"]) == 0
        assert path["estimated_time_saved_minutes"] == 0.0


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def setup_method(self):
        """Clear events before each test."""
        clear_fast_lane_events()
    
    def teardown_method(self):
        """Clear events after each test."""
        clear_fast_lane_events()
    
    def test_full_fast_lane_workflow(self):
        """Test complete fast lane workflow with telemetry."""
        user_id = "user_workflow_001"
        
        # 1. Get recommendation
        recommendation = get_fast_lane_recommendation(
            user_id=user_id,
            prefill_data={"confidence": "high", "template_type": "blog-post"},
            context={
                "email_domain": "microsoft.com",
                "signup_source": "referral",
                "segment": UserSegment.ENTERPRISE,
            },
        )
        
        # 2. Track that recommendation was presented
        track_fast_lane_event(
            user_id=user_id,
            event_type="presented",
            context={
                "recommended_path": recommendation["recommended_path"],
                "confidence": recommendation["confidence"],
            },
        )
        
        # 3. User accepts fast lane
        if recommendation["recommended_path"] == "fast_lane":
            track_fast_lane_event(
                user_id=user_id,
                event_type="accepted",
                context={"time_saved": recommendation["estimated_time_saved_minutes"]},
            )
        
        # 4. Verify events were tracked
        events = get_fast_lane_events(user_id=user_id)
        assert len(events) == 2
        assert events[0]["event_type"] == "presented"
        assert events[1]["event_type"] == "accepted"
    
    def test_rejection_workflow(self):
        """Test workflow when user rejects fast lane."""
        user_id = "user_rejection_001"
        
        # Get recommendation (might recommend fast lane)
        recommendation = get_fast_lane_recommendation(
            user_id=user_id,
            prefill_data={"confidence": "medium"},
            context={"email_domain": "gmail.com"},
        )
        
        # Track presentation
        track_fast_lane_event(
            user_id=user_id,
            event_type="presented",
            context={"recommended_path": recommendation["recommended_path"]},
        )
        
        # User rejects (chooses standard)
        track_fast_lane_event(
            user_id=user_id,
            event_type="rejected",
            context={"user_choice": "standard", "reason": "prefers_full_onboarding"},
        )
        
        # Verify rejection was tracked
        rejection_events = get_fast_lane_events(user_id=user_id, event_type="rejected")
        assert len(rejection_events) == 1
        assert rejection_events[0]["context"]["user_choice"] == "standard"
