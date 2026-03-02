"""Onboarding recovery reactivation strategy engine.

v34: Strategy selection and smart resume path generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional

from vm_webapp.onboarding_recovery import (
    DropoffReason,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryPriority,
)


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class ReactivationStrategy(str, Enum):
    """Available reactivation strategies."""
    REMINDER = "reminder"  # Simple email/app reminder
    FAST_LANE = "fast_lane"  # Skip some steps, streamlined flow
    TEMPLATE_BOOST = "template_boost"  # Highlight new/improved templates
    GUIDED_RESUME = "guided_resume"  # Human-guided or highly assisted flow


class StrategyType(str, Enum):
    """Classification of strategy touch intensity."""
    LOW_TOUCH = "low_touch"  # Can be auto-applied
    MEDIUM_TOUCH = "medium_touch"  # May need approval
    HIGH_TOUCH = "high_touch"  # Requires approval


@dataclass
class StrategySelection:
    """A selected strategy for a recovery case."""
    
    strategy: ReactivationStrategy
    strategy_type: StrategyType
    reason: str
    expected_impact: float  # 0.0 to 1.0 (estimated completion lift)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        """Convert selection to dictionary."""
        return {
            "strategy": self.strategy.value,
            "strategy_type": self.strategy_type.value,
            "reason": self.reason,
            "expected_impact": self.expected_impact,
            "created_at": self.created_at,
        }


@dataclass
class ResumePath:
    """Smart resume path for a recovery case."""
    
    case_id: str
    entry_point: str  # Step identifier where user resumes
    prefill_data: Dict[str, Any] = field(default_factory=dict)
    skip_steps: List[str] = field(default_factory=list)
    highlight_changes: List[str] = field(default_factory=list)
    estimated_completion_minutes: int = 10
    friction_score: float = 0.5  # 0.0 (low friction) to 1.0 (high friction)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        """Convert path to dictionary."""
        return {
            "case_id": self.case_id,
            "entry_point": self.entry_point,
            "prefill_data": self.prefill_data,
            "skip_steps": self.skip_steps,
            "highlight_changes": self.highlight_changes,
            "estimated_completion_minutes": self.estimated_completion_minutes,
            "friction_score": self.friction_score,
            "created_at": self.created_at,
        }


class SmartResumePath:
    """Generates intelligent resume paths for recovery cases."""

    def __init__(self) -> None:
        """Initialize resume path generator."""
        self._step_names = [
            "welcome",
            "company_profile",
            "team_setup",
            "template_selection",
            "integration_connect",
            "content_import",
            "review_launch",
        ]

    def generate(self, case: RecoveryCase) -> ResumePath:
        """Generate optimal resume path for a recovery case.
        
        Args:
            case: The recovery case to generate path for
            
        Returns:
            ResumePath with optimized entry point and settings
        """
        # Determine entry point
        entry_point = self._determine_entry_point(case)
        
        # Determine steps to skip
        skip_steps = self._determine_skip_steps(case)
        
        # Extract prefill data from metadata
        prefill_data = self._extract_prefill_data(case)
        
        # Calculate friction score
        friction_score = self._calculate_friction(case, skip_steps)
        
        # Estimate completion time
        estimated_minutes = self._estimate_completion_time(case, skip_steps)
        
        # Determine what to highlight
        highlight_changes = self._determine_highlights(case)

        return ResumePath(
            case_id=case.case_id,
            entry_point=entry_point,
            prefill_data=prefill_data,
            skip_steps=skip_steps,
            highlight_changes=highlight_changes,
            estimated_completion_minutes=estimated_minutes,
            friction_score=friction_score,
        )

    def _determine_entry_point(self, case: RecoveryCase) -> str:
        """Determine optimal entry point for resume."""
        # Late-stage dropoffs: resume from dropoff step
        if case.is_late_stage():
            return f"step_{case.current_step}"
        
        # Early-stage: might benefit from quick recap
        if case.current_step <= 2:
            return "quick_resume"
        
        # Mid-stage: resume from dropoff step
        return f"step_{case.current_step}"

    def _determine_skip_steps(self, case: RecoveryCase) -> List[str]:
        """Determine which steps can be skipped."""
        skip_steps = []
        
        # Always skip completed steps that don't need revisiting
        if case.current_step > 1:
            skip_steps.append("welcome")
        
        # Late-stage: skip most completed steps
        if case.is_late_stage():
            skip_steps.extend([
                "welcome",
                "company_profile_review",
                "tutorial_video",
            ])
        
        # Low priority early-stage: offer simplified path
        if case.priority == RecoveryPriority.LOW and case.current_step <= 2:
            skip_steps.extend([
                "detailed_onboarding",
                "advanced_options",
            ])
        
        return skip_steps

    def _extract_prefill_data(self, case: RecoveryCase) -> Dict[str, Any]:
        """Extract prefill data from case metadata."""
        prefill = {}
        
        # Common fields to prefill
        fields = ["company_name", "industry", "team_size", "use_case", "primary_goal"]
        
        for field in fields:
            if field in case.metadata:
                prefill[field] = case.metadata[field]
        
        return prefill

    def _calculate_friction(self, case: RecoveryCase, skip_steps: List[str]) -> float:
        """Calculate friction score (0.0 = low, 1.0 = high)."""
        # Base friction from remaining steps
        remaining_steps = case.total_steps - case.current_step
        base_friction = remaining_steps / case.total_steps
        
        # Reduce friction for skipped steps
        skip_reduction = len(skip_steps) * 0.05
        
        # Adjust for priority (high priority = more effort acceptable)
        priority_multiplier = {
            RecoveryPriority.HIGH: 0.8,
            RecoveryPriority.MEDIUM: 1.0,
            RecoveryPriority.LOW: 1.2,
        }.get(case.priority, 1.0)
        
        friction = (base_friction - skip_reduction) * priority_multiplier
        return max(0.0, min(1.0, friction))

    def _estimate_completion_time(self, case: RecoveryCase, skip_steps: List[str]) -> int:
        """Estimate minutes to complete from resume point."""
        # Base time per step
        base_minutes_per_step = 2
        
        remaining_steps = case.total_steps - case.current_step
        base_time = remaining_steps * base_minutes_per_step
        
        # Reduce for skipped steps
        skip_savings = len(skip_steps) * 1
        
        # Adjust for strategy type
        if case.priority == RecoveryPriority.HIGH:
            # High priority = more thorough = more time
            time = base_time - skip_savings + 2
        else:
            time = base_time - skip_savings
        
        return max(1, time)

    def _determine_highlights(self, case: RecoveryCase) -> List[str]:
        """Determine what changes/improvements to highlight."""
        highlights = []
        
        # Always highlight if returning after some time
        highlights.append("improved_flow")
        
        # Error cases: highlight fixes
        if case.reason == DropoffReason.ERROR:
            highlights.append("issues_resolved")
        
        # Late-stage: highlight progress preservation
        if case.is_late_stage():
            highlights.append("progress_preserved")
        
        # Template-related: highlight new options
        if case.reason in [DropoffReason.ABANDONED_STEP, DropoffReason.USER_INITIATED_EXIT]:
            highlights.append("new_templates")
        
        return highlights


class ReactivationStrategyEngine:
    """Engine for selecting and generating reactivation strategies."""

    def __init__(self) -> None:
        """Initialize strategy engine."""
        self._resume_generator = SmartResumePath()
        self._metrics: Dict[str, Any] = {
            "proposals_generated": 0,
            "auto_apply_count": 0,
            "needs_approval_count": 0,
            "strategy_distribution": {
                ReactivationStrategy.REMINDER: 0,
                ReactivationStrategy.FAST_LANE: 0,
                ReactivationStrategy.TEMPLATE_BOOST: 0,
                ReactivationStrategy.GUIDED_RESUME: 0,
            },
        }

    def select_strategy(self, case: RecoveryCase) -> StrategySelection:
        """Select optimal strategy for a recovery case.
        
        Args:
            case: The recovery case to select strategy for
            
        Returns:
            StrategySelection with chosen strategy and rationale
        """
        # Error cases: guided resume to rebuild confidence
        if case.reason == DropoffReason.ERROR:
            return StrategySelection(
                strategy=ReactivationStrategy.GUIDED_RESUME,
                strategy_type=StrategyType.HIGH_TOUCH,
                reason="Error-induced dropoff requires guided recovery to rebuild user confidence",
                expected_impact=0.45,
            )
        
        # High priority late-stage: fast lane or guided
        if case.priority == RecoveryPriority.HIGH and case.is_late_stage():
            if case.reason == DropoffReason.ABANDONED_STEP:
                return StrategySelection(
                    strategy=ReactivationStrategy.FAST_LANE,
                    strategy_type=StrategyType.MEDIUM_TOUCH,
                    reason="Late-stage abandonment with high intent - fast track to completion",
                    expected_impact=0.35,
                )
            else:
                return StrategySelection(
                    strategy=ReactivationStrategy.GUIDED_RESUME,
                    strategy_type=StrategyType.HIGH_TOUCH,
                    reason="High-priority case with significant progress invested",
                    expected_impact=0.40,
                )
        
        # Medium priority: template boost or fast lane
        if case.priority == RecoveryPriority.MEDIUM:
            if case.reason == DropoffReason.ABANDONED_STEP:
                return StrategySelection(
                    strategy=ReactivationStrategy.TEMPLATE_BOOST,
                    strategy_type=StrategyType.MEDIUM_TOUCH,
                    reason="Mid-stage abandonment - new templates may re-engage",
                    expected_impact=0.25,
                )
            else:
                return StrategySelection(
                    strategy=ReactivationStrategy.FAST_LANE,
                    strategy_type=StrategyType.MEDIUM_TOUCH,
                    reason="Streamlined path to reduce friction",
                    expected_impact=0.30,
                )
        
        # Low priority / early stage: simple reminder
        return StrategySelection(
            strategy=ReactivationStrategy.REMINDER,
            strategy_type=StrategyType.LOW_TOUCH,
            reason="Early-stage or low-engagement dropoff - gentle reminder",
            expected_impact=0.15,
        )

    def generate_proposal(self, case: RecoveryCase) -> Dict[str, Any]:
        """Generate complete recovery proposal.
        
        Args:
            case: The recovery case to generate proposal for
            
        Returns:
            Proposal dict with strategy, path, and approval requirements
        """
        # Select strategy
        selection = self.select_strategy(case)
        
        # Generate resume path
        resume_path = self._resume_generator.generate(case)
        
        # Determine approval requirement
        requires_approval = selection.strategy_type == StrategyType.HIGH_TOUCH
        
        # Update metrics
        self._metrics["proposals_generated"] += 1
        self._metrics["strategy_distribution"][selection.strategy] += 1
        
        if requires_approval:
            self._metrics["needs_approval_count"] += 1
        else:
            self._metrics["auto_apply_count"] += 1
        
        return {
            "case_id": case.case_id,
            "user_id": case.user_id,
            "brand_id": case.brand_id,
            "strategy": selection.to_dict(),
            "resume_path": resume_path.to_dict(),
            "requires_approval": requires_approval,
            "priority": case.priority.value,
            "reason": case.reason.value,
            "created_at": _now_iso(),
        }

    def batch_generate_proposals(self, cases: List[RecoveryCase]) -> List[Dict[str, Any]]:
        """Generate proposals for multiple cases.
        
        Args:
            cases: List of recovery cases
            
        Returns:
            List of proposals
        """
        return [self.generate_proposal(case) for case in cases]

    def get_strategy_metrics(self) -> Dict[str, Any]:
        """Get strategy generation metrics."""
        return {
            "proposals_generated": self._metrics["proposals_generated"],
            "auto_apply_count": self._metrics["auto_apply_count"],
            "needs_approval_count": self._metrics["needs_approval_count"],
            "strategy_distribution": {
                k.value: v for k, v in self._metrics["strategy_distribution"].items()
            },
        }
