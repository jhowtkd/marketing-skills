"""Onboarding experiment registry and deterministic assignment core.

This module provides the core infrastructure for running A/B experiments
in the onboarding flow with deterministic, sticky variant assignment.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


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
class Variant:
    """A variant in an experiment.
    
    Attributes:
        variant_id: Unique identifier for the variant
        name: Human-readable name
        config: Configuration dictionary for the variant
        weight: Traffic allocation weight (proportional to total weights)
    """
    variant_id: str
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def __post_init__(self):
        if self.weight < 0:
            raise ValueError("Weight must be non-negative")


@dataclass
class Experiment:
    """An onboarding experiment definition.
    
    Attributes:
        experiment_id: Unique identifier for the experiment
        name: Human-readable name
        variants: List of variants in the experiment
        is_active: Whether the experiment is active
    """
    experiment_id: str
    name: str
    variants: list[Variant] = field(default_factory=list)
    is_active: bool = True


@dataclass
class ExperimentVariant:
    """A variant in an experiment (legacy compatibility)."""
    variant_id: str
    name: str
    config: dict[str, Any]
    traffic_allocation: int

    def __post_init__(self):
        if not 0 <= self.traffic_allocation <= 100:
            raise ValueError("Traffic allocation must be between 0 and 100")


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
        self._experiments: dict[str, Any] = {}
        self._assignments: dict[tuple[str, str, str], VariantAssignment] = {}

    def register(self, experiment: Any) -> None:
        """Register a new experiment."""
        experiment_id = getattr(experiment, 'experiment_id', None)
        if experiment_id is None:
            raise ValueError("Experiment must have experiment_id")
        if experiment_id in self._experiments:
            raise ValueError(f"Experiment already registered: {experiment_id}")
        self._experiments[experiment_id] = experiment

    def get_experiment(self, experiment_id: str) -> Any:
        """Get an experiment by ID."""
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment not found: {experiment_id}")
        return self._experiments[experiment_id]

    def list_experiments(self) -> list[Any]:
        """List all registered experiments."""
        return list(self._experiments.values())

    def get_assignment(self, experiment_id: str, user_id: str, workspace_id: str) -> VariantAssignment:
        """Get or create a deterministic variant assignment for a user."""
        experiment = self.get_experiment(experiment_id)
        
        # Check if experiment is active/running
        status = getattr(experiment, 'status', None)
        is_active = getattr(experiment, 'is_active', True)
        
        if status is not None and status != ExperimentStatus.RUNNING:
            raise ValueError(f"Experiment not running: {experiment_id}")
        if not is_active:
            raise ValueError(f"Experiment not active: {experiment_id}")

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
        self, experiment: Any, user_id: str, workspace_id: str
    ) -> VariantAssignment:
        """Create a deterministic variant assignment using hashing."""
        # Create deterministic hash based on experiment + user + workspace
        hash_input = f"{experiment.experiment_id}:{user_id}:{workspace_id}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        
        # Get variants (support both old and new format)
        variants = getattr(experiment, 'variants', [])
        
        # Map hash to variant based on traffic allocation or weights
        bucket = hash_value % 100
        cumulative = 0
        
        for variant in variants:
            # Support both traffic_allocation (int) and weight (float)
            allocation = getattr(variant, 'traffic_allocation', None)
            if allocation is None:
                # Convert weight to percentage based on total weights
                total_weight = sum(getattr(v, 'weight', 1.0) for v in variants)
                allocation = int((getattr(variant, 'weight', 1.0) / total_weight) * 100) if total_weight > 0 else 0
            
            cumulative += allocation
            if bucket < cumulative:
                variant_id = getattr(variant, 'variant_id', 'control')
                return VariantAssignment(
                    experiment_id=experiment.experiment_id,
                    variant_id=variant_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
        
        # Fallback to last variant
        if variants:
            variant_id = getattr(variants[-1], 'variant_id', 'control')
        else:
            variant_id = 'control'
            
        return VariantAssignment(
            experiment_id=experiment.experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )

    def get_variant_config(self, experiment_id: str, variant_id: str) -> dict[str, Any]:
        """Get the configuration for a specific variant."""
        experiment = self.get_experiment(experiment_id)
        for variant in experiment.variants:
            if getattr(variant, 'variant_id', None) == variant_id:
                return getattr(variant, 'config', {})
        raise ValueError(f"Variant not found: {variant_id}")

    def get_assignment_count(self, experiment_id: str | None = None, variant_id: str | None = None) -> int:
        """Get the number of assignments for an experiment/variant."""
        count = 0
        for key, assignment in self._assignments.items():
            if experiment_id is None or key[0] == experiment_id:
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


def assign_variant(user_id: str, experiment_id: str, variants: list[Variant]) -> str:
    """Deterministically assign a user to a variant.
    
    Uses SHA256 hash of (user_id + experiment_id) to ensure:
    - Same user always gets same variant for same experiment
    - Distribution is proportional to variant weights
    
    Args:
        user_id: Unique identifier for the user
        experiment_id: Unique identifier for the experiment
        variants: List of Variant objects with weights
        
    Returns:
        variant_id of the assigned variant, or "control" on error
    """
    # Validate inputs
    if not variants:
        logger.debug(f"[assign_variant] No variants provided for {experiment_id}, returning control")
        return "control"
    
    # Validate all variants
    valid_variants = []
    total_weight = 0.0
    for v in variants:
        if not hasattr(v, 'variant_id') or not v.variant_id:
            logger.debug(f"[assign_variant] Invalid variant (no variant_id), skipping")
            continue
        weight = getattr(v, 'weight', 1.0)
        if weight < 0:
            logger.debug(f"[assign_variant] Negative weight for {v.variant_id}, skipping")
            continue
        valid_variants.append(v)
        total_weight += weight
    
    if not valid_variants:
        logger.debug(f"[assign_variant] No valid variants for {experiment_id}, returning control")
        return "control"
    
    if total_weight <= 0:
        logger.debug(f"[assign_variant] Total weight is zero for {experiment_id}, returning control")
        return "control"
    
    try:
        # Create deterministic hash
        hash_input = f"{user_id}:{experiment_id}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        
        # Map hash to variant based on weights
        # Use modulo to get value in range [0, total_weight)
        bucket = (hash_value % 10000) / 10000.0 * total_weight
        cumulative = 0.0
        
        for variant in valid_variants:
            cumulative += variant.weight
            if bucket < cumulative:
                return variant.variant_id
        
        # Fallback to last variant (shouldn't happen due to math)
        return valid_variants[-1].variant_id
        
    except Exception as e:
        logger.debug(f"[assign_variant] Error assigning variant: {e}, returning control")
        return "control"


def assign_variant_from_experiment(user_id: str, experiment: Experiment) -> str:
    """Assign a user to a variant using an Experiment object.
    
    Args:
        user_id: Unique identifier for the user
        experiment: Experiment object containing variants
        
    Returns:
        variant_id of the assigned variant, or "control" on error/inactive
    """
    # Check if experiment is active
    is_active = getattr(experiment, 'is_active', True)
    if not is_active:
        logger.debug(f"[assign_variant_from_experiment] Experiment {experiment.experiment_id} is inactive")
        return "control"
    
    variants = getattr(experiment, 'variants', [])
    return assign_variant(user_id, experiment.experiment_id, variants)
