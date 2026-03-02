"""Onboarding resume orchestrator with consistency guardrails.

v35: Resume orchestration with conflict detection and rollback support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional

from vm_webapp.onboarding_continuity import (
    CheckpointStatus,
    HandoffStatus,
    SourcePriority,
    ContinuityGraph,
)


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class ConflictType(str, Enum):
    """Types of conflicts during resume validation."""
    DATA_MISMATCH = "data_mismatch"
    STEP_REGRESSION = "step_regression"
    FORM_INCONSISTENCY = "form_inconsistency"
    VERSION_GAP = "version_gap"


class ConflictResolution(str, Enum):
    """Strategies for resolving conflicts."""
    USE_HIGHER_PRIORITY = "use_higher_priority"
    USE_LATEST = "use_latest"
    MERGE = "merge"
    REJECT = "reject"


@dataclass
class ValidationResult:
    """Result of resume validation."""
    valid: bool
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    reason: Optional[str] = field(default=None)
    risk_level: str = field(default="low")  # low, medium, high


class ConsistencyGuardrails:
    """Guardrails for validating resume consistency."""

    def __init__(
        self,
        max_version_gap: int = 5,
        max_step_regression: int = 2,
        require_form_consistency: bool = True,
    ) -> None:
        """Initialize guardrails.
        
        Args:
            max_version_gap: Maximum allowed version difference
            max_step_regression: Maximum allowed step regression
            require_form_consistency: Whether to enforce form data consistency
        """
        self.max_version_gap = max_version_gap
        self.max_step_regression = max_step_regression
        self.require_form_consistency = require_form_consistency

    def validate_version_gap(
        self,
        source_version: int,
        target_version: int,
    ) -> ValidationResult:
        """Validate version gap between source and target.
        
        Args:
            source_version: Version of source context
            target_version: Version of target/current context
            
        Returns:
            ValidationResult with conflicts if any
        """
        gap = abs(target_version - source_version)
        
        if gap > self.max_version_gap:
            return ValidationResult(
                valid=False,
                conflicts=[{
                    "type": ConflictType.VERSION_GAP,
                    "gap": gap,
                    "max_allowed": self.max_version_gap,
                }],
                reason=f"Version gap ({gap}) exceeds maximum ({self.max_version_gap})",
                risk_level="high" if gap > self.max_version_gap * 2 else "medium",
            )
        
        return ValidationResult(valid=True)

    def validate_step_progression(
        self,
        source_step: int,
        target_step: int,
    ) -> ValidationResult:
        """Validate step progression.
        
        Args:
            source_step: Step from source context
            target_step: Current/target step
            
        Returns:
            ValidationResult with conflicts if any
        """
        regression = target_step - source_step
        
        if regression < 0 and abs(regression) > self.max_step_regression:
            return ValidationResult(
                valid=False,
                conflicts=[{
                    "type": ConflictType.STEP_REGRESSION,
                    "from_step": target_step,
                    "to_step": source_step,
                    "regression": abs(regression),
                }],
                reason=f"Step regression ({abs(regression)}) exceeds maximum ({self.max_step_regression})",
                risk_level="high",
            )
        
        return ValidationResult(valid=True)

    def validate_form_consistency(
        self,
        source_form: Dict[str, Any],
        target_form: Dict[str, Any],
    ) -> ValidationResult:
        """Validate form data consistency.
        
        Args:
            source_form: Form data from source
            target_form: Form data from target/current
            
        Returns:
            ValidationResult with conflicts if any
        """
        if not self.require_form_consistency:
            return ValidationResult(valid=True)
        
        conflicts = []
        
        # Check for mismatches in common fields
        common_fields = set(source_form.keys()) & set(target_form.keys())
        for field in common_fields:
            if source_form[field] != target_form[field]:
                conflicts.append({
                    "type": ConflictType.FORM_INCONSISTENCY,
                    "field": field,
                    "source_value": source_form[field],
                    "target_value": target_form[field],
                })
        
        if conflicts:
            return ValidationResult(
                valid=False,
                conflicts=conflicts,
                reason="Form data inconsistencies detected",
                risk_level="medium",
            )
        
        return ValidationResult(valid=True)

    def validate_full(
        self,
        source_context: Dict[str, Any],
        target_context: Dict[str, Any],
    ) -> ValidationResult:
        """Run full validation.
        
        Args:
            source_context: Source context payload
            target_context: Target/current context payload
            
        Returns:
            Combined ValidationResult
        """
        all_conflicts = []
        max_risk = "low"
        reasons = []

        # Version gap validation
        source_version = source_context.get("version", 0)
        target_version = target_context.get("version", 0)
        version_result = self.validate_version_gap(source_version, target_version)
        
        if not version_result.valid:
            all_conflicts.extend(version_result.conflicts)
            reasons.append(version_result.reason)
            max_risk = self._higher_risk(max_risk, version_result.risk_level)

        # Step progression validation
        source_step = source_context.get("current_step_number", 0)
        target_step = target_context.get("current_step_number", 0)
        step_result = self.validate_step_progression(source_step, target_step)
        
        if not step_result.valid:
            all_conflicts.extend(step_result.conflicts)
            reasons.append(step_result.reason)
            max_risk = self._higher_risk(max_risk, step_result.risk_level)

        # Form consistency validation
        source_form = source_context.get("form_data", {})
        target_form = target_context.get("form_data", {})
        form_result = self.validate_form_consistency(source_form, target_form)
        
        if not form_result.valid:
            all_conflicts.extend(form_result.conflicts)
            reasons.append(form_result.reason)
            max_risk = self._higher_risk(max_risk, form_result.risk_level)

        if all_conflicts:
            return ValidationResult(
                valid=False,
                conflicts=all_conflicts,
                reason="; ".join(reasons),
                risk_level=max_risk,
            )
        
        return ValidationResult(valid=True, risk_level="low")

    def _higher_risk(self, risk1: str, risk2: str) -> str:
        """Return the higher of two risk levels."""
        order = ["low", "medium", "high"]
        idx1 = order.index(risk1)
        idx2 = order.index(risk2)
        return order[max(idx1, idx2)]


class ResumeOrchestrator:
    """Orchestrates cross-session resume with consistency validation."""

    def __init__(
        self,
        graph: ContinuityGraph,
        guardrails: Optional[ConsistencyGuardrails] = None,
    ) -> None:
        """Initialize orchestrator.
        
        Args:
            graph: ContinuityGraph instance
            guardrails: Optional custom guardrails
        """
        self._graph = graph
        self._guardrails = guardrails or ConsistencyGuardrails()
        self._metrics: Dict[str, int] = {
            "resumes_attempted": 0,
            "resumes_succeeded": 0,
            "resumes_failed": 0,
            "resumes_auto_applied": 0,
            "resumes_needing_approval": 0,
            "resumes_rolled_back": 0,
        }

    def resolve_conflict(
        self,
        contexts: Dict[SourcePriority, Dict[str, Any]],
        resolution: ConflictResolution = ConflictResolution.USE_HIGHER_PRIORITY,
    ) -> Dict[str, Any]:
        """Resolve conflicts between multiple context sources.
        
        Args:
            contexts: Map of source priority to context
            resolution: Conflict resolution strategy
            
        Returns:
            Resolved context
        """
        if resolution == ConflictResolution.USE_HIGHER_PRIORITY:
            # Use highest priority context available
            for priority in [SourcePriority.SESSION, SourcePriority.RECOVERY, SourcePriority.DEFAULT]:
                if priority in contexts:
                    return contexts[priority].copy()
            return {}
        
        elif resolution == ConflictResolution.USE_LATEST:
            # Use context with highest version
            latest_context = {}
            latest_version = -1
            for context in contexts.values():
                version = context.get("version", 0)
                if version > latest_version:
                    latest_version = version
                    latest_context = context.copy()
            return latest_context
        
        elif resolution == ConflictResolution.MERGE:
            # Merge contexts (higher priority wins conflicts)
            merged: Dict[str, Any] = {}
            for priority in [SourcePriority.DEFAULT, SourcePriority.RECOVERY, SourcePriority.SESSION]:
                if priority in contexts:
                    merged.update(contexts[priority])
            return merged
        
        else:  # REJECT
            return {}

    def validate_resume(self, bundle_id: str) -> ValidationResult:
        """Validate a resume operation.
        
        Args:
            bundle_id: Handoff bundle ID
            
        Returns:
            ValidationResult
        """
        bundle = self._graph.get_bundle(bundle_id)
        if not bundle:
            return ValidationResult(
                valid=False,
                reason="Bundle not found",
                risk_level="high",
            )

        # Get source context from bundle
        source_context = bundle.context_payload

        # Get current target context
        target_context = self._graph.generate_context_payload(bundle.user_id)
        
        # If no target context exists, resume is valid
        if not target_context:
            return ValidationResult(valid=True, risk_level="low")

        # Run full validation
        return self._guardrails.validate_full(source_context, target_context)

    def execute_resume(
        self,
        bundle_id: str,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Execute a resume operation.
        
        Args:
            bundle_id: Handoff bundle ID
            force: Whether to force execution despite conflicts
            
        Returns:
            Execution result
        """
        self._metrics["resumes_attempted"] += 1

        bundle = self._graph.get_bundle(bundle_id)
        if not bundle:
            self._metrics["resumes_failed"] += 1
            return {
                "success": False,
                "bundle_id": bundle_id,
                "error": "Bundle not found",
            }

        # Mark as in progress
        bundle.mark_in_progress()

        # Validate
        validation = self.validate_resume(bundle_id)

        if not validation.valid and not force:
            bundle.mark_failed(f"Validation failed: {validation.reason}")
            self._metrics["resumes_failed"] += 1
            
            if validation.risk_level in ["medium", "high"]:
                self._metrics["resumes_needing_approval"] += 1
                return {
                    "success": False,
                    "bundle_id": bundle_id,
                    "needs_approval": True,
                    "risk_level": validation.risk_level,
                    "conflicts": validation.conflicts,
                    "reason": validation.reason,
                }
            
            return {
                "success": False,
                "bundle_id": bundle_id,
                "conflicts": validation.conflicts,
                "reason": validation.reason,
            }

        # Commit checkpoints
        for cp_id in bundle.checkpoint_ids:
            cp = self._graph.get_checkpoint(cp_id)
            if cp:
                cp.commit()

        # Mark bundle completed
        bundle.mark_completed()
        
        self._metrics["resumes_succeeded"] += 1
        
        # Determine if auto-applied
        auto_applied = validation.risk_level == "low" and not force
        if auto_applied:
            self._metrics["resumes_auto_applied"] += 1

        return {
            "success": True,
            "bundle_id": bundle_id,
            "context": bundle.context_payload,
            "auto_applied": auto_applied,
            "risk_level": validation.risk_level,
        }

    def rollback_resume(self, bundle_id: str) -> Dict[str, Any]:
        """Rollback a completed resume.
        
        Args:
            bundle_id: Handoff bundle ID
            
        Returns:
            Rollback result
        """
        bundle = self._graph.get_bundle(bundle_id)
        if not bundle:
            return {
                "success": False,
                "bundle_id": bundle_id,
                "error": "Bundle not found",
            }

        # Rollback checkpoints
        for cp_id in bundle.checkpoint_ids:
            cp = self._graph.get_checkpoint(cp_id)
            if cp:
                cp.rollback()

        # Mark bundle as failed
        bundle.mark_failed("Rolled back by orchestrator")
        
        self._metrics["resumes_rolled_back"] += 1

        return {
            "success": True,
            "bundle_id": bundle_id,
            "rolled_back_at": _now_iso(),
        }

    def get_resume_metrics(self) -> Dict[str, Any]:
        """Get resume orchestration metrics."""
        return self._metrics.copy()
