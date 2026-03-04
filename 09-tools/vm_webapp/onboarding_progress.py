"""v40 Onboarding Progress Save/Resume - persistence and retrieval."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class OnboardingProgress(BaseModel):
    """Schema for onboarding progress persistence."""
    user_id: str
    thread_id: Optional[str] = None
    session_id: str
    current_step: str
    step_data: Dict[str, Any] = Field(default_factory=dict)
    completed_steps: List[str] = Field(default_factory=list)
    skipped_steps: List[str] = Field(default_factory=list)
    prefill_data: Optional[Dict] = None
    fast_lane_accepted: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "manual"  # manual, auto_save, resume
    version: int = 1


class ProgressStore:
    """In-memory store for progress (production would use DB)."""
    _progress: Dict[str, OnboardingProgress] = {}
    
    @classmethod
    def save(cls, progress: OnboardingProgress) -> None:
        cls._progress[progress.user_id] = progress
    
    @classmethod
    def get(cls, user_id: str) -> Optional[OnboardingProgress]:
        return cls._progress.get(user_id)
    
    @classmethod
    def delete(cls, user_id: str) -> bool:
        return cls._progress.pop(user_id, None) is not None
    
    @classmethod
    def clear(cls) -> None:
        """Clear all progress (useful for testing)."""
        cls._progress.clear()


def save_progress(
    user_id: str,
    current_step: str,
    step_data: Dict[str, Any],
    completed_steps: List[str],
    **kwargs
) -> OnboardingProgress:
    """Save onboarding progress.
    
    Args:
        user_id: Unique user identifier
        current_step: Current onboarding step identifier
        step_data: Data collected in current step
        completed_steps: List of completed step identifiers
        **kwargs: Optional fields (thread_id, session_id, skipped_steps, 
                  prefill_data, fast_lane_accepted, source)
    
    Returns:
        OnboardingProgress: The saved progress record
    """
    # Check for existing progress to preserve fields not provided
    existing = ProgressStore.get(user_id)
    
    # Use existing values as defaults if not provided in kwargs
    session_id = kwargs.get('session_id', existing.session_id if existing else f"session-{user_id}")
    thread_id = kwargs.get('thread_id', existing.thread_id if existing else None)
    skipped_steps = kwargs.get('skipped_steps', existing.skipped_steps if existing else [])
    prefill_data = kwargs.get('prefill_data', existing.prefill_data if existing else None)
    fast_lane_accepted = kwargs.get('fast_lane_accepted', existing.fast_lane_accepted if existing else False)
    source = kwargs.get('source', 'manual')
    
    # Increment version if updating existing record
    version = existing.version + 1 if existing else 1
    
    progress = OnboardingProgress(
        user_id=user_id,
        thread_id=thread_id,
        session_id=session_id,
        current_step=current_step,
        step_data=step_data,
        completed_steps=completed_steps,
        skipped_steps=skipped_steps,
        prefill_data=prefill_data,
        fast_lane_accepted=fast_lane_accepted,
        updated_at=datetime.now(timezone.utc),
        source=source,
        version=version,
    )
    
    ProgressStore.save(progress)
    return progress


def get_progress(user_id: str) -> Optional[OnboardingProgress]:
    """Retrieve saved progress.
    
    Args:
        user_id: Unique user identifier
    
    Returns:
        OnboardingProgress if found, None otherwise
    """
    return ProgressStore.get(user_id)


def resume_progress(user_id: str) -> Optional[OnboardingProgress]:
    """Mark progress as resumed and return it.
    
    Args:
        user_id: Unique user identifier
    
    Returns:
        OnboardingProgress if found, None otherwise
    """
    progress = ProgressStore.get(user_id)
    if progress is None:
        return None
    
    # Create updated progress with resume marker
    resumed_progress = OnboardingProgress(
        user_id=progress.user_id,
        thread_id=progress.thread_id,
        session_id=progress.session_id,
        current_step=progress.current_step,
        step_data=progress.step_data,
        completed_steps=progress.completed_steps,
        skipped_steps=progress.skipped_steps,
        prefill_data=progress.prefill_data,
        fast_lane_accepted=progress.fast_lane_accepted,
        updated_at=datetime.now(timezone.utc),
        source="resume",
        version=progress.version + 1,
    )
    
    ProgressStore.save(resumed_progress)
    return resumed_progress


def has_progress(user_id: str) -> bool:
    """Check if user has saved progress.
    
    Args:
        user_id: Unique user identifier
    
    Returns:
        True if progress exists, False otherwise
    """
    return ProgressStore.get(user_id) is not None


def auto_save_trigger(
    user_id: str,
    step: str,
    data: Dict[str, Any]
) -> None:
    """Auto-save progress when step is completed.
    
    Args:
        user_id: Unique user identifier
        step: Step identifier that was completed
        data: Data collected from the completed step
    """
    existing = ProgressStore.get(user_id)
    
    # Build completed steps list
    if existing:
        completed_steps = list(existing.completed_steps)
        if step not in completed_steps:
            completed_steps.append(step)
        
        # Merge step data
        step_data = {**existing.step_data, **data}
        session_id = existing.session_id
        thread_id = existing.thread_id
        skipped_steps = existing.skipped_steps
        prefill_data = existing.prefill_data
        fast_lane_accepted = existing.fast_lane_accepted
    else:
        completed_steps = [step]
        step_data = data
        session_id = f"session-{user_id}"
        thread_id = None
        skipped_steps = []
        prefill_data = None
        fast_lane_accepted = False
    
    progress = OnboardingProgress(
        user_id=user_id,
        thread_id=thread_id,
        session_id=session_id,
        current_step=step,
        step_data=step_data,
        completed_steps=completed_steps,
        skipped_steps=skipped_steps,
        prefill_data=prefill_data,
        fast_lane_accepted=fast_lane_accepted,
        updated_at=datetime.now(timezone.utc),
        source="auto_save",
        version=existing.version + 1 if existing else 1,
    )
    
    ProgressStore.save(progress)


def delete_progress(user_id: str) -> bool:
    """Delete progress for a user.
    
    Args:
        user_id: Unique user identifier
    
    Returns:
        True if progress was deleted, False if not found
    """
    return ProgressStore.delete(user_id)
