"""Tests for outcome attribution core (v36).

TDD: fail -> implement -> pass -> commit
"""

import pytest
from datetime import datetime, timezone, timedelta
from vm_webapp.outcome_attribution import (
    OutcomeType,
    TouchpointType,
    AttributionWindow,
    ContributionWeight,
    AttributionNode,
    AttributionGraph,
    OutcomeAttributionEngine,
)


class TestOutcomeType:
    """Test outcome type enumeration."""

    def test_outcome_type_values(self):
        """Outcome types should have expected values."""
        assert OutcomeType.ACTIVATION.value == "activation"
        assert OutcomeType.RECOVERY.value == "recovery"
        assert OutcomeType.RESUME.value == "resume"
        assert OutcomeType.FIRST_RUN.value == "first_run"
        assert OutcomeType.FEATURE_ADOPTION.value == "feature_adoption"


class TestTouchpointType:
    """Test touchpoint type enumeration."""

    def test_touchpoint_type_values(self):
        """Touchpoint types should have expected values."""
        assert TouchpointType.ONBOARDING_STEP.value == "onboarding_step"
        assert TouchpointType.RECOVERY_ACTION.value == "recovery_action"
        assert TouchpointType.CONTINUITY_RESUME.value == "continuity_resume"
        assert TouchpointType.NUDGE.value == "nudge"
        assert TouchpointType.SUPPORT_INTERACTION.value == "support_interaction"
        assert TouchpointType.SELF_SERVICE.value == "self_service"


class TestAttributionWindow:
    """Test attribution window configuration."""

    def test_default_window_days(self):
        """Default window should be 30 days."""
        window = AttributionWindow()
        assert window.days == 30

    def test_custom_window_days(self):
        """Custom window should accept different values."""
        window = AttributionWindow(days=7)
        assert window.days == 7

    def test_window_contains_recent_timestamp(self):
        """Window should contain timestamps within range."""
        window = AttributionWindow(days=30)
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        assert window.contains(recent) is True

    def test_window_excludes_old_timestamp(self):
        """Window should exclude timestamps outside range."""
        window = AttributionWindow(days=30)
        old = datetime.now(timezone.utc) - timedelta(days=35)
        assert window.contains(old) is False


class TestContributionWeight:
    """Test contribution weight calculation."""

    def test_weight_creation(self):
        """Weight should store value and confidence."""
        weight = ContributionWeight(value=0.5, confidence=0.8)
        assert weight.value == 0.5
        assert weight.confidence == 0.8

    def test_weight_validation_range(self):
        """Weight value should be between 0 and 1."""
        with pytest.raises(ValueError):
            ContributionWeight(value=1.5, confidence=0.5)
        with pytest.raises(ValueError):
            ContributionWeight(value=-0.1, confidence=0.5)

    def test_weight_adjustment(self):
        """Weight should be adjustable by factor."""
        weight = ContributionWeight(value=0.5, confidence=0.8)
        adjusted = weight.adjust(0.5)
        assert adjusted.value == 0.25


class TestAttributionNode:
    """Test attribution node structure."""

    def test_node_creation(self):
        """Node should be created with required fields."""
        node = AttributionNode(
            node_id="node_001",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id="step_01",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={"step_name": "brand_setup"},
        )
        assert node.node_id == "node_001"
        assert node.touchpoint_type == TouchpointType.ONBOARDING_STEP

    def test_node_to_dict(self):
        """Node should convert to dictionary."""
        node = AttributionNode(
            node_id="node_001",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id="step_01",
            timestamp="2026-03-01T10:00:00+00:00",
            metadata={},
        )
        data = node.to_dict()
        assert data["node_id"] == "node_001"
        assert data["touchpoint_type"] == "onboarding_step"


class TestAttributionGraph:
    """Test attribution graph operations."""

    def test_graph_creation(self):
        """Graph should be created for a user/brand."""
        graph = AttributionGraph(
            graph_id="graph_001",
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        assert graph.graph_id == "graph_001"
        assert graph.user_id == "user_123"

    def test_add_node_to_graph(self):
        """Nodes should be addable to graph."""
        graph = AttributionGraph(
            graph_id="graph_001",
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        node = AttributionNode(
            node_id="node_001",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id="step_01",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={},
        )
        graph.add_node(node)
        assert len(graph.nodes) == 1

    def test_calculate_contributions_linear(self):
        """Linear attribution should distribute evenly."""
        graph = AttributionGraph(
            graph_id="graph_001",
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        for i in range(3):
            node = AttributionNode(
                node_id=f"node_{i}",
                touchpoint_type=TouchpointType.ONBOARDING_STEP,
                touchpoint_id=f"step_{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={},
            )
            graph.add_node(node)
        
        contributions = graph.calculate_contributions(method="linear")
        assert len(contributions) == 3
        assert contributions[0].value == pytest.approx(0.333, rel=0.01)

    def test_calculate_contributions_first_touch(self):
        """First touch attribution should credit first node."""
        graph = AttributionGraph(
            graph_id="graph_001",
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        for i in range(3):
            node = AttributionNode(
                node_id=f"node_{i}",
                touchpoint_type=TouchpointType.ONBOARDING_STEP,
                touchpoint_id=f"step_{i}",
                timestamp=(datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(),
                metadata={},
            )
            graph.add_node(node)
        
        contributions = graph.calculate_contributions(method="first_touch")
        assert contributions[0].value == 1.0
        assert contributions[1].value == 0.0

    def test_calculate_contributions_last_touch(self):
        """Last touch attribution should credit last node."""
        graph = AttributionGraph(
            graph_id="graph_001",
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        for i in range(3):
            node = AttributionNode(
                node_id=f"node_{i}",
                touchpoint_type=TouchpointType.ONBOARDING_STEP,
                touchpoint_id=f"step_{i}",
                timestamp=(datetime.now(timezone.utc) - timedelta(hours=2-i)).isoformat(),
                metadata={},
            )
            graph.add_node(node)
        
        contributions = graph.calculate_contributions(method="last_touch")
        assert contributions[2].value == 1.0
        assert contributions[0].value == 0.0


class TestOutcomeAttributionEngine:
    """Test outcome attribution engine."""

    def test_engine_creation(self):
        """Engine should be created with default window."""
        engine = OutcomeAttributionEngine()
        assert engine is not None

    def test_create_graph(self):
        """Engine should create attribution graphs."""
        engine = OutcomeAttributionEngine()
        graph = engine.create_graph(
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        assert graph.user_id == "user_123"
        assert graph.outcome_type == OutcomeType.ACTIVATION

    def test_record_touchpoint(self):
        """Engine should record touchpoints."""
        engine = OutcomeAttributionEngine()
        engine.record_touchpoint(
            user_id="user_123",
            brand_id="brand_456",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id="step_01",
            metadata={"step_name": "brand_setup"},
        )
        assert len(engine.touchpoints) == 1

    def test_attribute_outcome(self):
        """Engine should attribute outcome to touchpoints."""
        engine = OutcomeAttributionEngine()
        
        # Record touchpoints
        for i in range(3):
            engine.record_touchpoint(
                user_id="user_123",
                brand_id="brand_456",
                touchpoint_type=TouchpointType.ONBOARDING_STEP,
                touchpoint_id=f"step_{i}",
                metadata={},
            )
        
        # Attribute outcome
        result = engine.attribute_outcome(
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
            method="linear",
        )
        
        assert result["user_id"] == "user_123"
        assert result["outcome_type"] == "activation"
        assert len(result["contributions"]) == 3

    def test_get_attribution_summary(self):
        """Engine should provide attribution summary."""
        engine = OutcomeAttributionEngine()
        
        engine.record_touchpoint(
            user_id="user_123",
            brand_id="brand_456",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id="step_01",
            metadata={},
        )
        
        engine.attribute_outcome(
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        
        summary = engine.get_attribution_summary(brand_id="brand_456")
        assert "total_outcomes" in summary
        assert "total_touchpoints" in summary

    def test_filter_by_window(self):
        """Engine should filter touchpoints by window."""
        engine = OutcomeAttributionEngine(window=AttributionWindow(days=7))
        
        # Add old touchpoint
        engine.record_touchpoint(
            user_id="user_123",
            brand_id="brand_456",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id="old_step",
            timestamp=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            metadata={},
        )
        
        # Add recent touchpoint
        engine.record_touchpoint(
            user_id="user_123",
            brand_id="brand_456",
            touchpoint_type=TouchpointType.ONBOARDING_STEP,
            touchpoint_id="recent_step",
            metadata={},
        )
        
        result = engine.attribute_outcome(
            user_id="user_123",
            brand_id="brand_456",
            outcome_type=OutcomeType.ACTIVATION,
        )
        
        # Should only include recent touchpoint
        assert len(result["contributions"]) == 1
        assert result["contributions"][0]["touchpoint_id"] == "recent_step"
