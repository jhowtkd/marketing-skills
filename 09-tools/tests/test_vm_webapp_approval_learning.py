"""
Tests for Approval Optimizer Learning Loop - v24
"""

import pytest
from datetime import datetime, timezone


def test_learning_core_collects_signals():
    """Test that learning core collects approval outcome signals."""
    from vm_webapp.approval_learning import LearningCore
    
    core = LearningCore()
    
    # Record an approval outcome
    outcome = {
        "request_id": "req-001",
        "batch_id": "batch-001",
        "brand_id": "brand-001",
        "approved": True,
        "risk_level": "medium",
        "predicted_risk": 0.6,
        "actual_time_minutes": 5.0,
        "batch_size": 3,
    }
    
    result = core.record_outcome(outcome)
    assert result["recorded"] is True
    assert result["request_id"] == "req-001"


def test_learning_core_calculates_deltas():
    """Test that learning core calculates performance deltas."""
    from vm_webapp.approval_learning import LearningCore
    
    core = LearningCore()
    
    # Record baseline
    core.record_outcome({
        "request_id": "req-001",
        "batch_id": "batch-001",
        "brand_id": "brand-001",
        "approved": True,
        "risk_level": "medium",
        "predicted_risk": 0.6,
        "actual_time_minutes": 5.0,
        "batch_size": 3,
    })
    
    # Calculate delta
    delta = core.calculate_delta("brand-001", days=7)
    assert "time_delta_percent" in delta
    assert "precision_delta_percent" in delta


def test_learning_core_generates_suggestions():
    """Test that learning core generates adjustment suggestions."""
    from vm_webapp.approval_learning import LearningCore
    
    core = LearningCore()
    
    # Record multiple outcomes to have data
    for i in range(5):
        core.record_outcome({
            "request_id": f"req-{i:03d}",
            "batch_id": f"batch-{i:03d}",
            "brand_id": "brand-001",
            "approved": True,
            "risk_level": "medium",
            "predicted_risk": 0.6,
            "actual_time_minutes": 4.0 + i,
            "batch_size": 3,
        })
    
    suggestions = core.generate_suggestions("brand-001")
    assert len(suggestions) > 0
    
    suggestion = suggestions[0]
    assert "adjustment_type" in suggestion
    assert "current_value" in suggestion
    assert "proposed_value" in suggestion
    assert "confidence" in suggestion
    assert "expected_savings_percent" in suggestion
    assert "risk_score" in suggestion


def test_suggestion_has_confidence_score():
    """Test that suggestions include confidence score 0-1."""
    from vm_webapp.approval_learning import LearningCore, AdjustmentSuggestion
    
    core = LearningCore()
    
    # Record outcomes
    for i in range(10):
        core.record_outcome({
            "request_id": f"req-{i:03d}",
            "batch_id": f"batch-{i:03d}",
            "brand_id": "brand-001",
            "approved": True,
            "risk_level": "low" if i < 7 else "medium",
            "predicted_risk": 0.4,
            "actual_time_minutes": 3.0,
            "batch_size": 3,
        })
    
    suggestions = core.generate_suggestions("brand-001")
    
    for suggestion in suggestions:
        assert 0.0 <= suggestion["confidence"] <= 1.0


def test_suggestion_has_expected_savings():
    """Test that suggestions include expected savings percentage."""
    from vm_webapp.approval_learning import LearningCore
    
    core = LearningCore()
    
    # Record outcomes with varying times
    for i in range(10):
        core.record_outcome({
            "request_id": f"req-{i:03d}",
            "batch_id": f"batch-{i:03d}",
            "brand_id": "brand-001",
            "approved": True,
            "risk_level": "medium",
            "predicted_risk": 0.6,
            "actual_time_minutes": 5.0,
            "batch_size": 3,
        })
    
    suggestions = core.generate_suggestions("brand-001")
    
    for suggestion in suggestions:
        assert "expected_savings_percent" in suggestion
        assert -50 <= suggestion["expected_savings_percent"] <= 50


def test_suggestion_has_risk_score():
    """Test that suggestions include risk score for the adjustment."""
    from vm_webapp.approval_learning import LearningCore
    
    core = LearningCore()
    
    for i in range(5):
        core.record_outcome({
            "request_id": f"req-{i:03d}",
            "batch_id": f"batch-{i:03d}",
            "brand_id": "brand-001",
            "approved": True,
            "risk_level": "high",
            "predicted_risk": 0.8,
            "actual_time_minutes": 10.0,
            "batch_size": 3,
        })
    
    suggestions = core.generate_suggestions("brand-001")
    
    for suggestion in suggestions:
        assert "risk_score" in suggestion
        assert 0.0 <= suggestion["risk_score"] <= 1.0


def test_learning_core_tracks_batch_precision():
    """Test tracking of batch approval precision over time."""
    from vm_webapp.approval_learning import LearningCore
    
    core = LearningCore()
    
    # Record batch outcomes - some approved, some rejected
    outcomes = [
        {"approved": True, "predicted": True},  # True positive
        {"approved": True, "predicted": True},  # True positive
        {"approved": False, "predicted": True}, # False positive
        {"approved": True, "predicted": True},  # True positive
        {"approved": False, "predicted": False}, # True negative
    ]
    
    for i, outcome in enumerate(outcomes):
        core.record_outcome({
            "request_id": f"req-{i:03d}",
            "batch_id": f"batch-{i:03d}",
            "brand_id": "brand-001",
            "approved": outcome["approved"],
            "predicted_outcome": outcome["predicted"],
            "risk_level": "medium",
            "predicted_risk": 0.6,
            "actual_time_minutes": 5.0,
            "batch_size": 3,
        })
    
    precision = core.get_batch_precision("brand-001", days=7)
    assert 0.0 <= precision <= 1.0
