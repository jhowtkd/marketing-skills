"""Onboarding experiment registry and deterministic assignment core.

This module provides the core infrastructure for running A/B experiments
in the onboarding flow with deterministic, sticky variant assignment.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RiskLevel(str, Enum):
    """Risk level for experiment promotion decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExperimentStatus(str, Enum):
    """Status of an experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ExperimentVariant:
    """A variant in an experiment."""
    variant_id: str
    name: str
    config: dict[str, Any]
    traffic_allocation: int

    def __post_init__(self):
        if not 0 <= self.traffic_allocation <= 100:
            raise ValueError("Traffic allocation must be between 0 and 100")


@dataclass
class Experiment:
    """An onboarding experiment definition."""
    experiment_id: str
    name: str
    description: str
    hypothesis: str
    primary_metric: str
    variants: list[ExperimentVariant]
    risk_level: RiskLevel
    min_sample_size: int
    min_confidence: float
    max_lift_threshold: float
    status: ExperimentStatus = field(default=ExperimentStatus.DRAFT)
    created_at: str = field(default_factory=_now_iso)
    started_at: str | None = field(default=None)
    paused_at: str | None = field(default=None)
    completed_at: str | None = field(default=None)
    rolled_back_at: str | None = field(default=None)

    def __post_init__(self):
        if len(self.variants) < 2:
            raise ValueError("At least 2 variants required")
        total_allocation = sum(v.traffic_allocation for v in self.variants)
        if total_allocation != 100:
            raise ValueError(f"Variant traffic allocations must sum to 100, got {total_allocation}")


@dataclass
class VariantAssignment:
    """Assignment of a user to a variant."""
    experiment_id: str
    variant_id: str
    user_id: str
    workspace_id: str
    assigned_at: str = field(default_factory=_now_iso)


class ExperimentRegistry:
    """Registry for onboarding experiments with deterministic assignment."""

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}
        self._assignments: dict[tuple[str, str, str], VariantAssignment] = {}

    def register(self, experiment: Experiment) -> None:
        """Register a new experiment."""
        if experiment.experiment_id in self._experiments:
            raise ValueError(f"Experiment already registered: {experiment.experiment_id}")
        self._experiments[experiment.experiment_id] = experiment

    def get_experiment(self, experiment_id: str) -> Experiment:
        """Get an experiment by ID."""
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment not found: {experiment_id}")
        return self._experiments[experiment_id]

    def list_experiments(self) -> list[Experiment]:
        """List all registered experiments."""
        return list(self._experiments.values())

    def start_experiment(self, experiment_id: str) -> None:
        """Start an experiment."""
        experiment = self.get_experiment(experiment_id)
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = _now_iso()

    def pause_experiment(self, experiment_id: str) -> None:
        """Pause a running experiment."""
        experiment = self.get_experiment(experiment_id)
        experiment.status = ExperimentStatus.PAUSED
        experiment.paused_at = _now_iso()

    def complete_experiment(self, experiment_id: str) -> None:
        """Mark an experiment as completed."""
        experiment = self.get_experiment(experiment_id)
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = _now_iso()

    def rollback_experiment(self, experiment_id: str) -> None:
        """Mark an experiment as rolled back."""
        experiment = self.get_experiment(experiment_id)
        experiment.status = ExperimentStatus.ROLLED_BACK
        experiment.rolled_back_at = _now_iso()

    def get_assignment(self, experiment_id: str, user_id: str, workspace_id: str) -> VariantAssignment:
        """Get or create a deterministic variant assignment for a user.
        
        Assignment is sticky - once assigned, always returns the same variant.
        Uses deterministic hashing based on experiment_id + user_id + workspace_id.
        """
        experiment = self.get_experiment(experiment_id)
        
        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError(f"Experiment not running: {experiment_id}")

        # Check for existing assignment
        key = (experiment_id, user_id, workspace_id)
        if key in self._assignments:
            return self._assignments[key]

        # Create deterministic assignment
        assignment = self._create_deterministic_assignment(
            experiment, user_id, workspace_id
        )
        self._assignments[key] = assignment
        return assignment

    def _create_deterministic_assignment(
        self, experiment: Experiment, user_id: str, workspace_id: str
    ) -> VariantAssignment:
        """Create a deterministic variant assignment using hashing."""
        # Create deterministic hash based on experiment + user + workspace
        hash_input = f"{experiment.experiment_id}:{user_id}:{workspace_id}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        
        # Map hash to variant based on traffic allocation
        bucket = hash_value % 100
        cumulative = 0
        
        for variant in experiment.variants:
            cumulative += variant.traffic_allocation
            if bucket < cumulative:
                return VariantAssignment(
                    experiment_id=experiment.experiment_id,
                    variant_id=variant.variant_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
        
        # Fallback to last variant (shouldn't happen if allocations sum to 100)
        return VariantAssignment(
            experiment_id=experiment.experiment_id,
            variant_id=experiment.variants[-1].variant_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )

    def get_variant_config(self, experiment_id: str, variant_id: str) -> dict[str, Any]:
        """Get the configuration for a specific variant."""
        experiment = self.get_experiment(experiment_id)
        for variant in experiment.variants:
            if variant.variant_id == variant_id:
                return variant.config
        raise ValueError(f"Variant not found: {variant_id}")

    def get_assignment_count(self, experiment_id: str, variant_id: str | None = None) -> int:
        """Get the number of assignments for an experiment/variant."""
        count = 0
        for key, assignment in self._assignments.items():
            if key[0] == experiment_id:
                if variant_id is None or assignment.variant_id == variant_id:
                    count += 1
        return count

    def clear_assignments(self, experiment_id: str | None = None) -> None:
        """Clear assignments (useful for testing)."""
        if experiment_id is None:
            self._assignments.clear()
        else:
            keys_to_remove = [
                key for key in self._assignments.keys()
                if key[0] == experiment_id
            ]
            for key in keys_to_remove:
                del self._assignments[key]
