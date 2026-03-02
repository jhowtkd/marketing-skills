"""Tests for v35 Onboarding Cross-Session Continuity Autopilot.

Session state graph, checkpoints, and handoff bundle management.
"""

import pytest
from datetime import datetime, timezone, timedelta

from vm_webapp.onboarding_continuity import (
    CheckpointStatus,
    HandoffStatus,
    SourcePriority,
    SessionCheckpoint,
    HandoffBundle,
    ContinuityGraph,
)


class TestCheckpointStatus:
    """Test CheckpointStatus enum."""

    def test_checkpoint_status_values(self):
        """CheckpointStatus should have expected values."""
        assert CheckpointStatus.ACTIVE == "active"
        assert CheckpointStatus.COMMITTED == "committed"
        assert CheckpointStatus.ROLLED_BACK == "rolled_back"
        assert CheckpointStatus.EXPIRED == "expired"


class TestHandoffStatus:
    """Test HandoffStatus enum."""

    def test_handoff_status_values(self):
        """HandoffStatus should have expected values."""
        assert HandoffStatus.PENDING == "pending"
        assert HandoffStatus.IN_PROGRESS == "in_progress"
        assert HandoffStatus.COMPLETED == "completed"
        assert HandoffStatus.FAILED == "failed"


class TestSourcePriority:
    """Test SourcePriority enum."""

    def test_source_priority_values(self):
        """SourcePriority should have expected values."""
        assert SourcePriority.SESSION == "session"
        assert SourcePriority.RECOVERY == "recovery"
        assert SourcePriority.DEFAULT == "default"

    def test_priority_order(self):
        """Session > Recovery > Default priority order."""
        assert SourcePriority.SESSION > SourcePriority.RECOVERY
        assert SourcePriority.RECOVERY > SourcePriority.DEFAULT


class TestSessionCheckpoint:
    """Test SessionCheckpoint model."""

    def test_checkpoint_creation(self):
        """Create a session checkpoint."""
        checkpoint = SessionCheckpoint(
            checkpoint_id="cp-001",
            user_id="user-123",
            brand_id="brand-456",
            step_id="step_3",
            step_data={"company_name": "Acme Inc"},
            form_data={"industry": "tech", "size": "10-50"},
        )
        
        assert checkpoint.checkpoint_id == "cp-001"
        assert checkpoint.user_id == "user-123"
        assert checkpoint.step_id == "step_3"
        assert checkpoint.status == CheckpointStatus.ACTIVE

    def test_checkpoint_version_increment(self):
        """Each checkpoint increments version."""
        # Versions are managed by ContinuityGraph, not auto-incremented
        graph = ContinuityGraph()
        
        cp1 = graph.create_checkpoint(
            "user-123", "brand-456", "step_2", {}
        )
        cp2 = graph.create_checkpoint(
            "user-123", "brand-456", "step_3", {}
        )
        
        assert cp2.version == cp1.version + 1

    def test_checkpoint_to_dict(self):
        """Convert checkpoint to dictionary."""
        checkpoint = SessionCheckpoint(
            checkpoint_id="cp-001",
            user_id="user-123",
            brand_id="brand-456",
            step_id="step_3",
            step_data={"key": "value"},
            form_data={"field": "data"},
        )
        
        data = checkpoint.to_dict()
        
        assert data["checkpoint_id"] == "cp-001"
        assert data["step_id"] == "step_3"
        assert data["status"] == "active"

    def test_commit_checkpoint(self):
        """Commit a checkpoint."""
        checkpoint = SessionCheckpoint(
            checkpoint_id="cp-001",
            user_id="user-123",
            brand_id="brand-456",
            step_id="step_3",
            step_data={},
        )
        
        checkpoint.commit()
        
        assert checkpoint.status == CheckpointStatus.COMMITTED
        assert checkpoint.committed_at is not None

    def test_rollback_checkpoint(self):
        """Rollback a checkpoint."""
        checkpoint = SessionCheckpoint(
            checkpoint_id="cp-001",
            user_id="user-123",
            brand_id="brand-456",
            step_id="step_3",
            step_data={},
        )
        
        checkpoint.rollback()
        
        assert checkpoint.status == CheckpointStatus.ROLLED_BACK
        assert checkpoint.rolled_back_at is not None


class TestHandoffBundle:
    """Test HandoffBundle model."""

    def test_bundle_creation(self):
        """Create a handoff bundle."""
        bundle = HandoffBundle(
            bundle_id="bundle-001",
            user_id="user-123",
            brand_id="brand-456",
            source_session="session-abc",
            target_session="session-xyz",
            checkpoint_ids=["cp-001", "cp-002"],
            context_payload={
                "current_step": 3,
                "completed_steps": ["step_1", "step_2"],
                "form_data": {"company_name": "Acme"},
            },
        )
        
        assert bundle.bundle_id == "bundle-001"
        assert bundle.user_id == "user-123"
        assert bundle.status == HandoffStatus.PENDING

    def test_bundle_source_priority(self):
        """Bundle tracks source priority."""
        bundle = HandoffBundle(
            bundle_id="bundle-001",
            user_id="user-123",
            brand_id="brand-456",
            source_session="session-abc",
            target_session="session-xyz",
            checkpoint_ids=["cp-001"],
            context_payload={},
            source_priority=SourcePriority.SESSION,
        )
        
        assert bundle.source_priority == SourcePriority.SESSION

    def test_bundle_to_dict(self):
        """Convert bundle to dictionary."""
        bundle = HandoffBundle(
            bundle_id="bundle-001",
            user_id="user-123",
            brand_id="brand-456",
            source_session="session-abc",
            target_session="session-xyz",
            checkpoint_ids=["cp-001"],
            context_payload={"step": 3},
        )
        
        data = bundle.to_dict()
        
        assert data["bundle_id"] == "bundle-001"
        assert data["source_session"] == "session-abc"
        assert data["status"] == "pending"

    def test_mark_in_progress(self):
        """Mark bundle as in progress."""
        bundle = HandoffBundle(
            bundle_id="bundle-001",
            user_id="user-123",
            brand_id="brand-456",
            source_session="session-abc",
            target_session="session-xyz",
            checkpoint_ids=["cp-001"],
            context_payload={},
        )
        
        bundle.mark_in_progress()
        
        assert bundle.status == HandoffStatus.IN_PROGRESS

    def test_mark_completed(self):
        """Mark bundle as completed."""
        bundle = HandoffBundle(
            bundle_id="bundle-001",
            user_id="user-123",
            brand_id="brand-456",
            source_session="session-abc",
            target_session="session-xyz",
            checkpoint_ids=["cp-001"],
            context_payload={},
        )
        
        bundle.mark_completed()
        
        assert bundle.status == HandoffStatus.COMPLETED
        assert bundle.completed_at is not None

    def test_mark_failed(self):
        """Mark bundle as failed."""
        bundle = HandoffBundle(
            bundle_id="bundle-001",
            user_id="user-123",
            brand_id="brand-456",
            source_session="session-abc",
            target_session="session-xyz",
            checkpoint_ids=["cp-001"],
            context_payload={},
        )
        
        bundle.mark_failed("Context validation failed")
        
        assert bundle.status == HandoffStatus.FAILED
        assert bundle.failure_reason == "Context validation failed"


class TestContinuityGraph:
    """Test ContinuityGraph functionality."""

    def test_graph_initialization(self):
        """Initialize continuity graph."""
        graph = ContinuityGraph()
        assert graph._checkpoints == {}
        assert graph._bundles == {}

    def test_create_checkpoint(self):
        """Create a checkpoint in the graph."""
        graph = ContinuityGraph()
        
        checkpoint = graph.create_checkpoint(
            user_id="user-123",
            brand_id="brand-456",
            step_id="step_3",
            step_data={"key": "value"},
        )
        
        assert checkpoint.checkpoint_id in graph._checkpoints
        assert checkpoint.user_id == "user-123"
        assert checkpoint.step_id == "step_3"

    def test_get_user_checkpoints(self):
        """Get all checkpoints for a user."""
        graph = ContinuityGraph()
        
        cp1 = graph.create_checkpoint("user-123", "brand-456", "step_2", {})
        cp2 = graph.create_checkpoint("user-123", "brand-456", "step_3", {})
        cp3 = graph.create_checkpoint("user-456", "brand-456", "step_1", {})
        
        user_checkpoints = graph.get_user_checkpoints("user-123")
        
        assert len(user_checkpoints) == 2
        assert all(cp.user_id == "user-123" for cp in user_checkpoints)

    def test_get_latest_checkpoint(self):
        """Get latest checkpoint for a user."""
        graph = ContinuityGraph()
        
        graph.create_checkpoint("user-123", "brand-456", "step_1", {})
        graph.create_checkpoint("user-123", "brand-456", "step_2", {})
        latest = graph.create_checkpoint("user-123", "brand-456", "step_3", {})
        
        result = graph.get_latest_checkpoint("user-123")
        
        assert result.checkpoint_id == latest.checkpoint_id

    def test_create_handoff_bundle(self):
        """Create a handoff bundle."""
        graph = ContinuityGraph()
        
        cp = graph.create_checkpoint("user-123", "brand-456", "step_3", {})
        
        bundle = graph.create_handoff_bundle(
            user_id="user-123",
            brand_id="brand-456",
            source_session="session-abc",
            target_session="session-xyz",
            checkpoint_ids=[cp.checkpoint_id],
        )
        
        assert bundle.bundle_id in graph._bundles
        assert bundle.user_id == "user-123"

    def test_generate_context_payload(self):
        """Generate context payload from checkpoints."""
        graph = ContinuityGraph()
        
        graph.create_checkpoint(
            "user-123", "brand-456", "step_1",
            {"step": 1}, {"company": "Acme"}
        )
        graph.create_checkpoint(
            "user-123", "brand-456", "step_2",
            {"step": 2}, {"industry": "tech"}
        )
        
        payload = graph.generate_context_payload("user-123")
        
        assert payload["current_step"] == "step_2"
        assert "completed_steps" in payload
        assert "form_data" in payload

    def test_get_handoff_metrics(self):
        """Get handoff metrics."""
        graph = ContinuityGraph()
        
        cp = graph.create_checkpoint("user-123", "brand-456", "step_3", {})
        graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id]
        )
        
        metrics = graph.get_handoff_metrics()
        
        assert metrics["bundles_total"] == 1
        assert metrics["bundles_pending"] == 1
        assert metrics["checkpoints_total"] == 1
