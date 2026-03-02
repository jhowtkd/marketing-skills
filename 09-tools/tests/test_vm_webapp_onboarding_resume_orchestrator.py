"""Tests for v35 Onboarding Resume Orchestrator.

Resume orchestration with consistency guardrails and conflict detection.
"""

import pytest
from datetime import datetime, timezone, timedelta

from vm_webapp.onboarding_continuity import (
    CheckpointStatus,
    HandoffStatus,
    SourcePriority,
    ContinuityGraph,
)
from vm_webapp.onboarding_resume_orchestrator import (
    ConflictType,
    ConflictResolution,
    ValidationResult,
    ConsistencyGuardrails,
    ResumeOrchestrator,
)


class TestConflictType:
    """Test ConflictType enum."""

    def test_conflict_type_values(self):
        """ConflictType should have expected values."""
        assert ConflictType.DATA_MISMATCH == "data_mismatch"
        assert ConflictType.STEP_REGRESSION == "step_regression"
        assert ConflictType.FORM_INCONSISTENCY == "form_inconsistency"
        assert ConflictType.VERSION_GAP == "version_gap"


class TestConflictResolution:
    """Test ConflictResolution enum."""

    def test_conflict_resolution_values(self):
        """ConflictResolution should have expected values."""
        assert ConflictResolution.USE_HIGHER_PRIORITY == "use_higher_priority"
        assert ConflictResolution.USE_LATEST == "use_latest"
        assert ConflictResolution.MERGE == "merge"
        assert ConflictResolution.REJECT == "reject"


class TestValidationResult:
    """Test ValidationResult model."""

    def test_validation_success(self):
        """Create a successful validation."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.conflicts == []

    def test_validation_with_conflicts(self):
        """Create validation with conflicts."""
        result = ValidationResult(
            valid=False,
            conflicts=[
                {"type": "data_mismatch", "field": "company_name"},
                {"type": "step_regression", "from": 5, "to": 3},
            ],
            reason="Multiple conflicts detected",
        )
        assert result.valid is False
        assert len(result.conflicts) == 2


class TestConsistencyGuardrails:
    """Test ConsistencyGuardrails."""

    def test_guardrails_initialization(self):
        """Initialize guardrails with defaults."""
        guardrails = ConsistencyGuardrails()
        assert guardrails.max_version_gap == 5
        assert guardrails.max_step_regression == 2
        assert guardrails.require_form_consistency is True

    def test_validate_version_gap_within_limit(self):
        """Version gap within limit passes."""
        guardrails = ConsistencyGuardrails()
        result = guardrails.validate_version_gap(source_version=5, target_version=3)
        assert result.valid is True

    def test_validate_version_gap_exceeds_limit(self):
        """Version gap exceeds limit fails."""
        guardrails = ConsistencyGuardrails(max_version_gap=3)
        result = guardrails.validate_version_gap(source_version=10, target_version=1)
        assert result.valid is False
        assert result.conflicts[0]["type"] == "version_gap"

    def test_validate_step_progression_forward(self):
        """Forward step progression passes."""
        guardrails = ConsistencyGuardrails()
        result = guardrails.validate_step_progression(source_step=3, target_step=5)
        assert result.valid is True

    def test_validate_step_progression_minor_regression(self):
        """Minor step regression within limit passes."""
        guardrails = ConsistencyGuardrails(max_step_regression=2)
        result = guardrails.validate_step_progression(source_step=5, target_step=4)
        assert result.valid is True

    def test_validate_step_progression_major_regression(self):
        """Major step regression fails."""
        guardrails = ConsistencyGuardrails(max_step_regression=1)
        result = guardrails.validate_step_progression(source_step=5, target_step=2)
        assert result.valid is False
        assert result.conflicts[0]["type"] == "step_regression"

    def test_validate_form_consistency_match(self):
        """Matching form data passes."""
        guardrails = ConsistencyGuardrails()
        source_form = {"company": "Acme", "size": "10-50"}
        target_form = {"company": "Acme", "size": "10-50"}
        result = guardrails.validate_form_consistency(source_form, target_form)
        assert result.valid is True

    def test_validate_form_consistency_mismatch(self):
        """Mismatched form data fails when required."""
        guardrails = ConsistencyGuardrails(require_form_consistency=True)
        source_form = {"company": "Acme"}
        target_form = {"company": "Different"}
        result = guardrails.validate_form_consistency(source_form, target_form)
        assert result.valid is False
        assert result.conflicts[0]["type"] == "form_inconsistency"


class TestResumeOrchestrator:
    """Test ResumeOrchestrator."""

    def test_orchestrator_initialization(self):
        """Initialize orchestrator."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)
        assert orchestrator._graph == graph
        assert orchestrator._guardrails is not None

    def test_resolve_conflict_by_priority(self):
        """Resolve conflict using source priority."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        source_context = {"step": 5, "company": "Acme"}
        recovery_context = {"step": 3, "company": "Old"}
        default_context = {"step": 1}

        result = orchestrator.resolve_conflict(
            contexts={
                SourcePriority.SESSION: source_context,
                SourcePriority.RECOVERY: recovery_context,
                SourcePriority.DEFAULT: default_context,
            },
            resolution=ConflictResolution.USE_HIGHER_PRIORITY,
        )

        assert result["step"] == 5  # Session wins
        assert result["company"] == "Acme"

    def test_resolve_conflict_use_latest(self):
        """Resolve conflict using latest version."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        contexts = {
            SourcePriority.SESSION: {"version": 1, "step": 3},
            SourcePriority.RECOVERY: {"version": 2, "step": 5},
        }

        result = orchestrator.resolve_conflict(
            contexts=contexts,
            resolution=ConflictResolution.USE_LATEST,
        )

        assert result["version"] == 2
        assert result["step"] == 5

    def test_validate_resume_session_to_session(self):
        """Validate session-to-session resume."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        # Create source checkpoint
        cp = graph.create_checkpoint("user-123", "brand-456", "step_5", {}, {})
        cp.commit()

        bundle = graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id]
        )

        validation = orchestrator.validate_resume(bundle.bundle_id)

        assert validation.valid is True

    def test_validate_resume_with_conflicts(self):
        """Validate resume with conflicts detected."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        # Create checkpoint with old version
        cp = graph.create_checkpoint("user-123", "brand-456", "step_2", {}, {})
        # Manually set old version to simulate version gap
        cp.version = 1
        cp.commit()

        # Create many newer checkpoints
        for i in range(10):
            new_cp = graph.create_checkpoint("user-123", "brand-456", f"step_{i+3}", {}, {})
            new_cp.commit()

        bundle = graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id]
        )

        validation = orchestrator.validate_resume(bundle.bundle_id)

        # Should detect version gap
        assert validation.valid is False
        assert any(c["type"] == "version_gap" for c in validation.conflicts)

    def test_execute_resume_success(self):
        """Execute successful resume."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        cp = graph.create_checkpoint("user-123", "brand-456", "step_5", {}, {})
        cp.commit()

        bundle = graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id]
        )

        result = orchestrator.execute_resume(bundle.bundle_id)

        assert result["success"] is True
        assert result["bundle_id"] == bundle.bundle_id
        assert "context" in result

    def test_execute_resume_with_validation_failure(self):
        """Execute resume with validation failure."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        # Create checkpoint at step 1
        cp = graph.create_checkpoint("user-123", "brand-456", "step_1", {}, {})
        cp.commit()

        # Create many checkpoints at step 10 (creates version gap > 5)
        for i in range(10):
            new_cp = graph.create_checkpoint("user-123", "brand-456", "step_10", {}, {})
            new_cp.commit()

        bundle = graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id]
        )

        result = orchestrator.execute_resume(bundle.bundle_id)

        assert result["success"] is False
        assert "conflicts" in result

    def test_execute_resume_auto_apply_low_risk(self):
        """Auto-apply for low-risk resumes."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        # Sequential progression - low risk
        cp = graph.create_checkpoint("user-123", "brand-456", "step_4", {}, {})
        cp.commit()

        bundle = graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id],
            source_priority=SourcePriority.SESSION,
        )

        result = orchestrator.execute_resume(bundle.bundle_id)

        assert result["success"] is True
        assert result["auto_applied"] is True

    def test_execute_resume_needs_approval_high_risk(self):
        """Require approval for high-risk resumes."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        # Large version gap - high risk
        cp = graph.create_checkpoint("user-123", "brand-456", "step_5", {}, {})
        cp.commit()

        # Create many checkpoints
        for i in range(15):
            new_cp = graph.create_checkpoint("user-123", "brand-456", f"step_{i+1}", {}, {})
            new_cp.commit()

        bundle = graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id],
            source_priority=SourcePriority.RECOVERY,
        )

        result = orchestrator.execute_resume(bundle.bundle_id)

        assert result["success"] is False or result.get("needs_approval") is True

    def test_rollback_resume(self):
        """Rollback a completed resume."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        cp = graph.create_checkpoint("user-123", "brand-456", "step_5", {}, {})
        cp.commit()

        bundle = graph.create_handoff_bundle(
            "user-123", "brand-456", "session-abc", "session-xyz", [cp.checkpoint_id]
        )

        # Execute then rollback
        orchestrator.execute_resume(bundle.bundle_id)
        result = orchestrator.rollback_resume(bundle.bundle_id)

        assert result["success"] is True
        assert result["bundle_id"] == bundle.bundle_id

        bundle_refreshed = graph.get_bundle(bundle.bundle_id)
        assert bundle_refreshed.status == HandoffStatus.FAILED

    def test_get_resume_metrics(self):
        """Get resume orchestration metrics."""
        graph = ContinuityGraph()
        orchestrator = ResumeOrchestrator(graph)

        # Execute some resumes
        for i in range(3):
            cp = graph.create_checkpoint(f"user-{i}", "brand-456", "step_3", {}, {})
            cp.commit()
            bundle = graph.create_handoff_bundle(
                f"user-{i}", "brand-456", f"session-{i}", f"session-new-{i}", [cp.checkpoint_id]
            )
            orchestrator.execute_resume(bundle.bundle_id)

        metrics = orchestrator.get_resume_metrics()

        assert metrics["resumes_attempted"] >= 3
        assert metrics["resumes_succeeded"] >= 0
        assert "resumes_needing_approval" in metrics
        assert "resumes_rolled_back" in metrics
