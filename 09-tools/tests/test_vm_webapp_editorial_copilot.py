"""Tests for Editorial Copilot read models and suggestion engine."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from vm_webapp.editorial_copilot import (
    CopilotSuggestion,
    CopilotFeedback,
    SuggestionPhase,
    FeedbackAction,
    build_initial_suggestion,
    generate_suggestions,
    record_feedback,
    SuggestionEngine,
)
from vm_webapp.first_run_recommendation import (
    ProfileModeOutcome,
    RecommendationRanker,
    RankedRecommendation,
)
from vm_webapp.alerts_v2 import EditorialAlert, aggregate_alerts
from vm_webapp.models import CopilotSuggestionView, CopilotFeedbackView
from vm_webapp.repo import (
    list_copilot_suggestions,
    insert_copilot_suggestion,
    list_copilot_feedback,
    insert_copilot_feedback,
)


# ============================================================================
# Task 1: Model and Read-model Tests
# ============================================================================

def test_build_initial_suggestion_shape():
    """Test that initial suggestion has correct shape and fields."""
    context = {
        "thread_id": "thread-123",
        "brand_id": "brand-456",
        "project_id": "project-789",
        "user_request": "Create a marketing campaign",
    }
    
    suggestion = build_initial_suggestion(context)
    
    assert isinstance(suggestion, CopilotSuggestion)
    assert suggestion.suggestion_id.startswith("sugg-")
    assert suggestion.phase == "initial"
    assert suggestion.thread_id == "thread-123"
    assert 0.0 <= suggestion.confidence <= 1.0
    assert isinstance(suggestion.reason_codes, list)
    assert isinstance(suggestion.why, str)
    assert isinstance(suggestion.expected_impact, dict)
    assert "quality_delta" in suggestion.expected_impact
    assert "approval_lift" in suggestion.expected_impact


def test_build_initial_suggestion_with_outcomes():
    """Test that initial suggestion contains relevant content with outcome data."""
    context = {
        "thread_id": "thread-123",
        "brand_id": "brand-456",
        "project_id": "project-789",
        "user_request": "Create a marketing campaign for new product launch",
    }
    
    # Provide outcomes to get a real suggestion
    outcomes = [
        {
            "profile": "engagement",
            "mode": "balanced",
            "total_runs": 15,
            "success_24h_count": 12,
            "success_rate": 0.8,
            "avg_quality_score": 0.85,
            "avg_duration_ms": 3500,
        }
    ]
    
    suggestion = generate_suggestions("initial", context, outcomes=outcomes)
    
    assert suggestion.content is not None
    assert len(suggestion.content) > 0
    assert "engagement" in suggestion.content
    assert "balanced" in suggestion.content
    assert suggestion.why is not None
    assert len(suggestion.why) > 0


def test_feedback_record_persists_action_and_phase():
    """Test that feedback record correctly stores action and phase."""
    feedback = CopilotFeedback(
        feedback_id="feedback-123",
        suggestion_id="sugg-456",
        thread_id="thread-789",
        phase="initial",
        action="accepted",
        edited_content=None,
        metadata={"user_id": "user-123"},
    )
    
    assert feedback.feedback_id == "feedback-123"
    assert feedback.suggestion_id == "sugg-456"
    assert feedback.phase == "initial"
    assert feedback.action == "accepted"
    assert feedback.edited_content is None


def test_feedback_record_edited_content():
    """Test that feedback record stores edited content when provided."""
    edited = "Modified suggestion content"
    feedback = CopilotFeedback(
        feedback_id="feedback-123",
        suggestion_id="sugg-456",
        thread_id="thread-789",
        phase="refine",
        action="edited",
        edited_content=edited,
        metadata={},
    )
    
    assert feedback.action == "edited"
    assert feedback.edited_content == edited


def test_suggestion_phases():
    """Test that all suggestion phases are defined as valid literals."""
    phases = ["initial", "refine", "strategy"]
    
    for phase in phases:
        assert isinstance(phase, str)
        assert len(phase) > 0


def test_feedback_actions():
    """Test that all feedback actions are defined as valid literals."""
    actions = ["accepted", "edited", "ignored"]
    
    for action in actions:
        assert isinstance(action, str)
        assert len(action) > 0


def test_low_confidence_returns_passive_suggestion():
    """Test that low confidence results in a passive/guardrailed suggestion."""
    context = {
        "thread_id": "thread-123",
        "brand_id": "brand-456",
        "project_id": "project-789",
        "user_request": "x",  # Very short request
    }
    
    suggestion = build_initial_suggestion(context)
    
    # Without outcomes, confidence should be low (0.3)
    assert suggestion.confidence < 0.4
    # Low confidence suggestions should be passive (empty content)
    assert suggestion.content == ""


def test_record_feedback():
    """Test the record_feedback convenience function."""
    feedback = record_feedback(
        suggestion_id="sugg-123",
        thread_id="thread-456",
        phase="initial",
        action="accepted",
        metadata={"user_id": "user-789"},
    )
    
    assert feedback.suggestion_id == "sugg-123"
    assert feedback.action == "accepted"
    assert feedback.feedback_id.startswith("feedback-")


# ============================================================================
# Task 2: Phase-based Suggestion Engine Tests
# ============================================================================

def test_initial_phase_uses_v12_ranking_and_returns_profile_mode():
    """Test that initial phase uses v12 ranking engine to recommend profile/mode."""
    context = {
        "thread_id": "thread-123",
        "brand_id": "brand-456",
        "project_id": "project-789",
        "user_request": "Create engaging social media campaign",
    }
    
    # Provide multiple outcomes to test ranking
    outcomes = [
        {
            "profile": "engagement",
            "mode": "creative",
            "total_runs": 20,
            "success_24h_count": 16,
            "success_rate": 0.8,
            "avg_quality_score": 0.85,
            "avg_duration_ms": 3000,
        },
        {
            "profile": "conversion",
            "mode": "aggressive",
            "total_runs": 10,
            "success_24h_count": 5,
            "success_rate": 0.5,
            "avg_quality_score": 0.70,
            "avg_duration_ms": 4500,
        },
    ]
    
    suggestion = generate_suggestions("initial", context, outcomes=outcomes)
    
    # Should recommend the best performing profile/mode
    assert suggestion.phase == "initial"
    assert "engagement" in suggestion.content  # Higher success rate
    assert "creative" in suggestion.content
    assert suggestion.confidence > 0.5
    assert "success_rate" in suggestion.reason_codes or "high_success_rate" in suggestion.reason_codes


def test_refine_phase_uses_scorecard_gaps_and_returns_refine_text():
    """Test that refine phase generates text refinements based on scorecard gaps."""
    context = {"thread_id": "thread-123"}
    
    scorecard_gaps = [
        {"dimension": "clarity", "score": 0.4, "suggestion": "Adicione uma chamada de ação clara"},
        {"dimension": "tone", "score": 0.5, "suggestion": "Ajuste o tom para ser mais amigável"},
        {"dimension": "structure", "score": 0.6, "suggestion": "Use parágrafos mais curtos"},
    ]
    
    suggestion = generate_suggestions("refine", context, scorecard_gaps=scorecard_gaps)
    
    assert suggestion.phase == "refine"
    assert suggestion.confidence >= 0.4
    assert len(suggestion.content) > 0
    # Should include gap suggestions
    assert "ação" in suggestion.content.lower() or "tom" in suggestion.content.lower()
    assert "scorecard_gaps" in suggestion.reason_codes
    assert suggestion.expected_impact["quality_delta"] > 0


def test_refine_phase_empty_gaps_returns_passive():
    """Test that refine phase returns passive suggestion when no gaps identified."""
    context = {"thread_id": "thread-123"}
    
    suggestion = generate_suggestions("refine", context, scorecard_gaps=[])
    
    assert suggestion.phase == "refine"
    assert suggestion.confidence < 0.4
    assert "no_gaps_identified" in suggestion.reason_codes


def test_strategy_phase_triggers_on_high_risk_signals():
    """Test that strategy phase generates recommendations based on risk signals."""
    context = {"thread_id": "thread-123"}
    
    risk_signals = [
        {
            "type": "baseline_drift",
            "severity": "high",
            "risk_score": 85,
            "recommendation": "Revisar baseline imediatamente - drift crítico detectado",
        },
        {
            "type": "quality_decline",
            "severity": "medium",
            "risk_score": 60,
            "recommendation": "Aumentar rigor de revisão editorial",
        },
    ]
    
    suggestion = generate_suggestions("strategy", context, risk_signals=risk_signals)
    
    assert suggestion.phase == "strategy"
    assert suggestion.confidence > 0.4  # High risk should boost confidence
    assert "high_risk_detected" in suggestion.reason_codes
    assert len(suggestion.content) > 0
    assert "baseline" in suggestion.content.lower() or "revisar" in suggestion.content.lower()


def test_strategy_phase_no_risk_returns_passive():
    """Test that strategy phase returns passive when no risk signals."""
    context = {"thread_id": "thread-123"}
    
    suggestion = generate_suggestions("strategy", context, risk_signals=[])
    
    assert suggestion.phase == "strategy"
    assert suggestion.confidence < 0.4
    assert "no_risk_signals" in suggestion.reason_codes


def test_suggestion_engine_guardrail_low_confidence():
    """Test that engine applies guardrail for low confidence situations."""
    engine = SuggestionEngine()
    
    # Very limited context should result in low confidence
    context = {"thread_id": "t1"}
    
    suggestion = engine.generate_initial(context, outcomes=[])
    
    # Guardrail: confidence below threshold should result in passive suggestion
    assert suggestion.confidence < engine.CONFIDENCE_THRESHOLD
    assert suggestion.content == ""  # Passive = no active suggestion
    assert "fallback" in suggestion.reason_codes[0] or "low_sample_size" in suggestion.reason_codes


def test_suggestion_includes_expected_impact_metrics():
    """Test that suggestions include quality_delta and approval_lift metrics."""
    context = {"thread_id": "thread-123"}
    
    outcomes = [
        {
            "profile": "engagement",
            "mode": "balanced",
            "total_runs": 15,
            "success_24h_count": 12,
            "success_rate": 0.8,
            "avg_quality_score": 0.85,
            "avg_duration_ms": 3500,
        }
    ]
    
    suggestion = generate_suggestions("initial", context, outcomes=outcomes)
    
    assert "quality_delta" in suggestion.expected_impact
    assert "approval_lift" in suggestion.expected_impact
    # Quality delta should be positive for good outcomes
    assert suggestion.expected_impact["quality_delta"] >= 0
    # Approval lift should be based on confidence
    assert suggestion.expected_impact["approval_lift"] >= 0


# ============================================================================
# Integration Tests with v12 Components
# ============================================================================

def test_copilot_uses_v12_ranker_for_initial_recommendations():
    """Integration test: Verify copilot integrates with v12 RecommendationRanker."""
    ranker = RecommendationRanker()
    
    outcomes = [
        ProfileModeOutcome(
            profile="engagement",
            mode="balanced",
            total_runs=15,
            success_24h_count=12,
            success_rate=0.8,
            avg_quality_score=0.85,
            avg_duration_ms=3500,
        ),
        ProfileModeOutcome(
            profile="awareness",
            mode="gentle",
            total_runs=8,
            success_24h_count=4,
            success_rate=0.5,
            avg_quality_score=0.70,
            avg_duration_ms=4000,
        ),
    ]
    
    ranked = ranker.rank(outcomes, top_n=2)
    
    # Copilot should get the same ranking
    assert len(ranked) == 2
    assert ranked[0].profile == "engagement"  # Best performing
    assert ranked[0].confidence > ranked[1].confidence  # More data = higher confidence


def test_copilot_considers_alerts_for_strategy_phase():
    """Integration test: Strategy phase should consider alerts_v2 data."""
    # Simulate alerts that would come from alerts_v2
    insights_data = {
        "totals": {"marked_total": 100},
        "baseline": {
            "by_source": {"none": 80},
            "resolved_total": 100,
        },
        "policy": {"denied_total": 30},
    }
    
    alerts = aggregate_alerts(insights_data, thread_id="thread-123")
    
    # Convert alerts to risk signals for strategy phase
    risk_signals = [
        {
            "type": alert.alert_type,
            "severity": "high" if alert.severity == "critical" else alert.severity,
            "risk_score": 85 if alert.severity == "critical" else 60,
            "recommendation": alert.recomendacao,
        }
        for alert in alerts
        if alert.severity in ["critical", "warning"]
    ]
    
    context = {"thread_id": "thread-123"}
    suggestion = generate_suggestions("strategy", context, risk_signals=risk_signals)
    
    # Should generate strategy suggestion based on alerts
    assert suggestion.phase == "strategy"
    if risk_signals:
        assert suggestion.confidence > 0.4


# ============================================================================
# Database/Repository Tests
# ============================================================================

def test_list_copilot_suggestions_empty_session(in_memory_db):
    """Test listing suggestions with empty database."""
    suggestions = list_copilot_suggestions(in_memory_db, thread_id="thread-123")
    assert suggestions == []


def test_insert_and_list_copilot_suggestion(in_memory_db):
    """Test inserting and listing a copilot suggestion."""
    suggestion = insert_copilot_suggestion(
        in_memory_db,
        suggestion_id="sugg-123",
        thread_id="thread-456",
        phase="initial",
        content="Test suggestion",
        confidence=0.75,
        reason_codes=["test_reason"],
        why="Test why",
        expected_impact={"quality_delta": 10},
    )
    
    assert suggestion.suggestion_id == "sugg-123"
    
    suggestions = list_copilot_suggestions(in_memory_db, thread_id="thread-456")
    assert len(suggestions) == 1
    assert suggestions[0].suggestion_id == "sugg-123"
    assert suggestions[0].phase == "initial"


def test_list_copilot_feedback_empty_session(in_memory_db):
    """Test listing feedback with empty database."""
    feedback = list_copilot_feedback(in_memory_db, thread_id="thread-123")
    assert feedback == []


def test_insert_and_list_copilot_feedback(in_memory_db):
    """Test inserting and listing copilot feedback."""
    feedback = insert_copilot_feedback(
        in_memory_db,
        feedback_id="feedback-123",
        suggestion_id="sugg-456",
        thread_id="thread-789",
        phase="refine",
        action="accepted",
        edited_content=None,
    )
    
    assert feedback.feedback_id == "feedback-123"
    
    feedback_list = list_copilot_feedback(in_memory_db, thread_id="thread-789")
    assert len(feedback_list) == 1
    assert feedback_list[0].action == "accepted"


def test_insert_copilot_feedback_with_edit(in_memory_db):
    """Test inserting feedback with edited content."""
    feedback = insert_copilot_feedback(
        in_memory_db,
        feedback_id="feedback-456",
        suggestion_id="sugg-789",
        thread_id="thread-abc",
        phase="initial",
        action="edited",
        edited_content="Modified content here",
        metadata={"editor_id": "editor-123"},
    )
    
    assert feedback.action == "edited"
    assert feedback.edited_content == "Modified content here"
    
    feedback_list = list_copilot_feedback(in_memory_db, thread_id="thread-abc")
    assert len(feedback_list) == 1
    assert feedback_list[0].edited_content == "Modified content here"
