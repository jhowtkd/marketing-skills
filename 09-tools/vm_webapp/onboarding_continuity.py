"""Onboarding cross-session continuity state graph and handoff bundles.

v35: Deterministic continuity between sessions with versioned checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
import uuid


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class CheckpointStatus(str, Enum):
    """Status of a session checkpoint."""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    EXPIRED = "expired"


class HandoffStatus(str, Enum):
    """Status of a handoff bundle."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SourcePriority(str, Enum):
    """Priority of context source for conflict resolution.
    
    Priority order: SESSION > RECOVERY > DEFAULT
    """
    SESSION = "session"
    RECOVERY = "recovery"
    DEFAULT = "default"

    def __gt__(self, other: SourcePriority) -> bool:
        """Compare priorities."""
        order = [SourcePriority.DEFAULT, SourcePriority.RECOVERY, SourcePriority.SESSION]
        return order.index(self) > order.index(other)


@dataclass
class SessionCheckpoint:
    """A versioned checkpoint of user progress in onboarding."""
    
    checkpoint_id: str
    user_id: str
    brand_id: str
    step_id: str
    step_data: Dict[str, Any]
    form_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = field(default=1)
    status: CheckpointStatus = field(default=CheckpointStatus.ACTIVE)
    created_at: str = field(default_factory=_now_iso)
    committed_at: Optional[str] = field(default=None)
    rolled_back_at: Optional[str] = field(default=None)
    expires_at: Optional[str] = field(default=None)

    def commit(self) -> None:
        """Mark checkpoint as committed."""
        self.status = CheckpointStatus.COMMITTED
        self.committed_at = _now_iso()

    def rollback(self) -> None:
        """Mark checkpoint as rolled back."""
        self.status = CheckpointStatus.ROLLED_BACK
        self.rolled_back_at = _now_iso()

    def expire(self) -> None:
        """Mark checkpoint as expired."""
        self.status = CheckpointStatus.EXPIRED

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "user_id": self.user_id,
            "brand_id": self.brand_id,
            "step_id": self.step_id,
            "step_data": self.step_data,
            "form_data": self.form_data,
            "metadata": self.metadata,
            "version": self.version,
            "status": self.status.value,
            "created_at": self.created_at,
            "committed_at": self.committed_at,
            "rolled_back_at": self.rolled_back_at,
            "expires_at": self.expires_at,
        }


@dataclass
class HandoffBundle:
    """A bundle for handing off context between sessions."""
    
    bundle_id: str
    user_id: str
    brand_id: str
    source_session: str
    target_session: str
    checkpoint_ids: List[str]
    context_payload: Dict[str, Any] = field(default_factory=dict)
    source_priority: SourcePriority = field(default=SourcePriority.SESSION)
    status: HandoffStatus = field(default=HandoffStatus.PENDING)
    created_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = field(default=None)
    completed_at: Optional[str] = field(default=None)
    failure_reason: Optional[str] = field(default=None)

    def mark_in_progress(self) -> None:
        """Mark handoff as in progress."""
        self.status = HandoffStatus.IN_PROGRESS
        self.started_at = _now_iso()

    def mark_completed(self) -> None:
        """Mark handoff as completed."""
        self.status = HandoffStatus.COMPLETED
        self.completed_at = _now_iso()

    def mark_failed(self, reason: str) -> None:
        """Mark handoff as failed."""
        self.status = HandoffStatus.FAILED
        self.failure_reason = reason

    def to_dict(self) -> dict:
        """Convert bundle to dictionary."""
        return {
            "bundle_id": self.bundle_id,
            "user_id": self.user_id,
            "brand_id": self.brand_id,
            "source_session": self.source_session,
            "target_session": self.target_session,
            "checkpoint_ids": self.checkpoint_ids,
            "context_payload": self.context_payload,
            "source_priority": self.source_priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failure_reason": self.failure_reason,
        }


class ContinuityGraph:
    """Graph for managing session continuity and handoffs."""

    def __init__(self) -> None:
        """Initialize continuity graph."""
        self._checkpoints: Dict[str, SessionCheckpoint] = {}
        self._bundles: Dict[str, HandoffBundle] = {}
        self._user_checkpoints: Dict[str, List[str]] = {}
        self._version_counter: Dict[str, int] = {}

    def create_checkpoint(
        self,
        user_id: str,
        brand_id: str,
        step_id: str,
        step_data: Dict[str, Any],
        form_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionCheckpoint:
        """Create a new checkpoint for a user.
        
        Args:
            user_id: User identifier
            brand_id: Brand identifier
            step_id: Current step identifier
            step_data: Step-specific data
            form_data: Form field values
            metadata: Additional metadata
            
        Returns:
            Created SessionCheckpoint
        """
        # Get next version for user
        current_version = self._version_counter.get(user_id, 0)
        next_version = current_version + 1
        self._version_counter[user_id] = next_version

        checkpoint = SessionCheckpoint(
            checkpoint_id=f"cp-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            brand_id=brand_id,
            step_id=step_id,
            step_data=step_data,
            form_data=form_data or {},
            metadata=metadata or {},
            version=next_version,
        )

        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

        # Index by user
        if user_id not in self._user_checkpoints:
            self._user_checkpoints[user_id] = []
        self._user_checkpoints[user_id].append(checkpoint.checkpoint_id)

        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[SessionCheckpoint]:
        """Get a specific checkpoint by ID."""
        return self._checkpoints.get(checkpoint_id)

    def get_user_checkpoints(self, user_id: str) -> List[SessionCheckpoint]:
        """Get all checkpoints for a user."""
        checkpoint_ids = self._user_checkpoints.get(user_id, [])
        return [
            self._checkpoints[cp_id]
            for cp_id in checkpoint_ids
            if cp_id in self._checkpoints
        ]

    def get_latest_checkpoint(self, user_id: str) -> Optional[SessionCheckpoint]:
        """Get the latest checkpoint for a user."""
        user_cps = self.get_user_checkpoints(user_id)
        if not user_cps:
            return None
        return max(user_cps, key=lambda cp: cp.version)

    def create_handoff_bundle(
        self,
        user_id: str,
        brand_id: str,
        source_session: str,
        target_session: str,
        checkpoint_ids: List[str],
        source_priority: SourcePriority = SourcePriority.SESSION,
    ) -> HandoffBundle:
        """Create a handoff bundle between sessions.
        
        Args:
            user_id: User identifier
            brand_id: Brand identifier
            source_session: Source session ID
            target_session: Target session ID
            checkpoint_ids: List of checkpoint IDs to include
            source_priority: Priority of the source context
            
        Returns:
            Created HandoffBundle
        """
        # Generate context payload from checkpoints
        context_payload = self._build_context_payload(checkpoint_ids)

        bundle = HandoffBundle(
            bundle_id=f"bundle-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            brand_id=brand_id,
            source_session=source_session,
            target_session=target_session,
            checkpoint_ids=checkpoint_ids,
            context_payload=context_payload,
            source_priority=source_priority,
        )

        self._bundles[bundle.bundle_id] = bundle
        return bundle

    def get_bundle(self, bundle_id: str) -> Optional[HandoffBundle]:
        """Get a specific handoff bundle."""
        return self._bundles.get(bundle_id)

    def get_user_bundles(self, user_id: str) -> List[HandoffBundle]:
        """Get all handoff bundles for a user."""
        return [
            bundle for bundle in self._bundles.values()
            if bundle.user_id == user_id
        ]

    def generate_context_payload(self, user_id: str) -> Dict[str, Any]:
        """Generate context payload from user's checkpoints."""
        checkpoint_ids = self._user_checkpoints.get(user_id, [])
        return self._build_context_payload(checkpoint_ids)

    def _build_context_payload(self, checkpoint_ids: List[str]) -> Dict[str, Any]:
        """Build context payload from checkpoint IDs."""
        checkpoints = [
            self._checkpoints[cp_id]
            for cp_id in checkpoint_ids
            if cp_id in self._checkpoints
        ]

        if not checkpoints:
            return {}

        # Sort by version
        checkpoints.sort(key=lambda cp: cp.version)

        # Get latest checkpoint
        latest = checkpoints[-1]

        # Build completed steps list
        completed_steps = [
            cp.step_id for cp in checkpoints
            if cp.status in [CheckpointStatus.COMMITTED, CheckpointStatus.ACTIVE]
        ]

        # Merge form data (latest wins for conflicts)
        merged_form_data: Dict[str, Any] = {}
        for cp in checkpoints:
            merged_form_data.update(cp.form_data)

        return {
            "current_step": latest.step_id,
            "current_step_number": self._extract_step_number(latest.step_id),
            "completed_steps": completed_steps,
            "form_data": merged_form_data,
            "latest_checkpoint_id": latest.checkpoint_id,
            "version": latest.version,
        }

    def _extract_step_number(self, step_id: str) -> int:
        """Extract step number from step ID."""
        # Handle formats like "step_3", "step-3", "3"
        import re
        match = re.search(r'(\d+)', step_id)
        return int(match.group(1)) if match else 0

    def get_handoff_metrics(self) -> Dict[str, Any]:
        """Get handoff and checkpoint metrics."""
        total_checkpoints = len(self._checkpoints)
        active_checkpoints = len([
            cp for cp in self._checkpoints.values()
            if cp.status == CheckpointStatus.ACTIVE
        ])
        committed_checkpoints = len([
            cp for cp in self._checkpoints.values()
            if cp.status == CheckpointStatus.COMMITTED
        ])
        rolled_back_checkpoints = len([
            cp for cp in self._checkpoints.values()
            if cp.status == CheckpointStatus.ROLLED_BACK
        ])

        total_bundles = len(self._bundles)
        pending_bundles = len([
            b for b in self._bundles.values()
            if b.status == HandoffStatus.PENDING
        ])
        in_progress_bundles = len([
            b for b in self._bundles.values()
            if b.status == HandoffStatus.IN_PROGRESS
        ])
        completed_bundles = len([
            b for b in self._bundles.values()
            if b.status == HandoffStatus.COMPLETED
        ])
        failed_bundles = len([
            b for b in self._bundles.values()
            if b.status == HandoffStatus.FAILED
        ])

        return {
            "checkpoints_total": total_checkpoints,
            "checkpoints_active": active_checkpoints,
            "checkpoints_committed": committed_checkpoints,
            "checkpoints_rolled_back": rolled_back_checkpoints,
            "bundles_total": total_bundles,
            "bundles_pending": pending_bundles,
            "bundles_in_progress": in_progress_bundles,
            "bundles_completed": completed_bundles,
            "bundles_failed": failed_bundles,
        }

    def expire_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """Expire checkpoints older than max_age_hours.
        
        Returns:
            Number of checkpoints expired
        """
        now = datetime.now(timezone.utc)
        expired_count = 0

        for checkpoint in self._checkpoints.values():
            if checkpoint.status == CheckpointStatus.ACTIVE:
                created = datetime.fromisoformat(checkpoint.created_at)
                age_hours = (now - created).total_seconds() / 3600
                if age_hours > max_age_hours:
                    checkpoint.expire()
                    expired_count += 1

        return expired_count
