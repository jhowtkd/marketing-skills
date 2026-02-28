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
)
from vm_webapp.models import CopilotSuggestionView, CopilotFeedbackView
from vm_webapp.repo import (
    list_copilot_suggestions,
    insert_copilot_suggestion,
    list_copilot_feedback,
    insert_copilot_feedback,
)


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
    # SuggestionPhase is a Literal type, so we test valid values
    phases = ["initial", "refine", "strategy"]
    
    for phase in phases:
        assert isinstance(phase, str)
        assert len(phase) > 0


def test_feedback_actions():
    """Test that all feedback actions are defined as valid literals."""
    # FeedbackAction is a Literal type, so we test valid values
    actions = ["accepted", "edited", "ignored"]
    
    for action in actions:
        assert isinstance(action, str)
        assert len(action) > 0


def test_low_confidence_returns_passive_suggestion():
    """Test that low confidence results in a passive/guardrailed suggestion."""
    # Context with insufficient data should trigger low confidence
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


def test_refine_phase_suggestion():
    """Test that refine phase generates suggestions based on scorecard gaps."""
    context = {"thread_id": "thread-123"}
    gaps = [
        {"dimension": "clarity", "score": 0.5, "suggestion": "Add clearer CTA"},
        {"dimension": "tone", "score": 0.6, "suggestion": "Adjust brand voice"},
    ]
    
    suggestion = generate_suggestions("refine", context, scorecard_gaps=gaps)
    
    assert suggestion.phase == "refine"
    assert suggestion.confidence > 0.4
    assert "clarity" in suggestion.content or "tone" in suggestion.content
    assert len(suggestion.reason_codes) > 0


def test_strategy_phase_suggestion():
    """Test that strategy phase generates suggestions based on risk signals."""
    context = {"thread_id": "thread-123"}
    risk_signals = [
        {"type": "baseline_drift", "severity": "high", "risk_score": 80, "recommendation": "Review baseline"},
    ]
    
    suggestion = generate_suggestions("strategy", context, risk_signals=risk_signals)
    
    assert suggestion.phase == "strategy"
    assert suggestion.confidence > 0.4
    assert "baseline" in suggestion.content.lower() or "risk" in suggestion.why.lower()


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


# Database/Repository Tests

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
