"""Hierarchical policy resolver for multi-brand governance (v18).

Policy resolution precedence: segment > brand > global
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy.orm import Session

from vm_webapp.models import Policy, PolicyLevel


class PolicySource(str, Enum):
    """Source of the effective policy."""

    GLOBAL = "global"
    BRAND = "brand"
    SEGMENT = "segment"
    DEFAULT = "default"


@dataclass
class EffectivePolicy:
    """Resolved effective policy with source tracking."""

    # Policy parameters (flattened from params_json)
    threshold: float = 0.5
    mode: str = "standard"
    timeout: int = 30
    
    # Source tracking
    source: PolicySource = PolicySource.DEFAULT
    source_brand_id: Optional[str] = None
    source_segment: Optional[str] = None
    source_objective_key: Optional[str] = None
    
    # Raw params for extensibility
    _raw_params: dict[str, Any] = field(default_factory=dict, repr=False)

    def __getattr__(self, name: str) -> Any:
        """Allow access to arbitrary params from _raw_params."""
        if name.startswith("_"):
            raise AttributeError(name)
        return self._raw_params.get(name)

    def to_snapshot(self) -> dict[str, Any]:
        """Create deterministic snapshot for audit/logging."""
        return {
            **self._raw_params,
            "_source": self.source.value,
            "_source_brand_id": self.source_brand_id,
            "_source_segment": self.source_segment,
            "_source_objective_key": self.source_objective_key,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _merge_params(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two param dicts, with override taking precedence."""
    return {**base, **override}


def resolve_effective_policy(
    session: Session,
    *,
    brand_id: str,
    segment: Optional[str] = None,
    objective_key: Optional[str] = None,
) -> EffectivePolicy:
    """Resolve effective policy with hierarchy: segment > brand > global.
    
    Args:
        session: Database session
        brand_id: Brand identifier
        segment: Optional segment identifier
        objective_key: Optional objective key for specific policies
        
    Returns:
        EffectivePolicy with resolved values and source tracking
    """
    # Start with default
    effective_params: dict[str, Any] = {}
    source = PolicySource.DEFAULT
    source_brand_id: Optional[str] = None
    source_segment: Optional[str] = None
    source_objective_key: Optional[str] = None

    # Query policies in priority order
    policies = (
        session.query(Policy)
        .filter(
            (Policy.brand_id.is_(None)) | (Policy.brand_id == brand_id)
        )
        .all()
    )

    # Organize by level for easier processing
    global_policies = [p for p in policies if p.level == PolicyLevel.GLOBAL]
    brand_policies = [
        p for p in policies 
        if p.level == PolicyLevel.BRAND and p.brand_id == brand_id
    ]
    segment_policies = [
        p for p in policies 
        if p.level == PolicyLevel.SEGMENT 
        and p.brand_id == brand_id 
        and p.segment == segment
    ]

    # Apply global (lowest priority)
    for policy in global_policies:
        if policy.objective_key is None or policy.objective_key == objective_key:
            params = json.loads(policy.params_json)
            effective_params = _merge_params(effective_params, params)
            source = PolicySource.GLOBAL

    # Apply brand (medium priority)
    for policy in brand_policies:
        if policy.objective_key is None or policy.objective_key == objective_key:
            params = json.loads(policy.params_json)
            effective_params = _merge_params(effective_params, params)
            source = PolicySource.BRAND
            source_brand_id = brand_id

    # Apply segment (highest priority)
    if segment:
        for policy in segment_policies:
            if policy.objective_key is None or policy.objective_key == objective_key:
                params = json.loads(policy.params_json)
                effective_params = _merge_params(effective_params, params)
                source = PolicySource.SEGMENT
                source_brand_id = brand_id
                source_segment = segment

    # Build EffectivePolicy from merged params
    return EffectivePolicy(
        threshold=effective_params.get("threshold", 0.5),
        mode=effective_params.get("mode", "standard"),
        timeout=effective_params.get("timeout", 30),
        source=source,
        source_brand_id=source_brand_id,
        source_segment=source_segment,
        source_objective_key=source_objective_key,
        _raw_params=effective_params,
    )


def upsert_policy(
    session: Session,
    *,
    level: PolicyLevel,
    brand_id: Optional[str] = None,
    segment: Optional[str] = None,
    objective_key: Optional[str] = None,
    params: dict[str, Any],
) -> Policy:
    """Create or update a policy.
    
    Args:
        session: Database session
        level: Policy level (global, brand, segment)
        brand_id: Required for brand/segment levels
        segment: Required for segment level
        objective_key: Optional objective-specific policy
        params: Policy parameters as dict
        
    Returns:
        Created or updated Policy
    """
    # Look for existing policy
    existing = (
        session.query(Policy)
        .filter(
            Policy.level == level,
            Policy.brand_id == brand_id,
            Policy.segment == segment,
            Policy.objective_key == objective_key,
        )
        .first()
    )

    if existing is not None:
        existing.params_json = json.dumps(params, ensure_ascii=False)
        existing.updated_at = _now_iso()
        session.flush()
        return existing

    # Create new policy
    policy = Policy(
        policy_id=str(uuid.uuid4()),
        level=level,
        brand_id=brand_id,
        segment=segment,
        objective_key=objective_key,
        params_json=json.dumps(params, ensure_ascii=False),
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )
    session.add(policy)
    session.flush()
    return policy


def get_policy(
    session: Session,
    *,
    level: PolicyLevel,
    brand_id: Optional[str] = None,
    segment: Optional[str] = None,
    objective_key: Optional[str] = None,
) -> Optional[Policy]:
    """Get a specific policy by its level and identifiers.
    
    Args:
        session: Database session
        level: Policy level
        brand_id: Brand identifier (for brand/segment levels)
        segment: Segment identifier (for segment level)
        objective_key: Optional objective key
        
    Returns:
        Policy if found, None otherwise
    """
    return (
        session.query(Policy)
        .filter(
            Policy.level == level,
            Policy.brand_id == brand_id,
            Policy.segment == segment,
            Policy.objective_key == objective_key,
        )
        .first()
    )


def list_policies(
    session: Session,
    *,
    brand_id: Optional[str] = None,
    level: Optional[PolicyLevel] = None,
) -> list[Policy]:
    """List policies with optional filtering.
    
    Args:
        session: Database session
        brand_id: Filter by brand (includes global)
        level: Filter by level
        
    Returns:
        List of matching policies
    """
    query = session.query(Policy)
    
    if brand_id is not None:
        query = query.filter(
            (Policy.brand_id.is_(None)) | (Policy.brand_id == brand_id)
        )
    
    if level is not None:
        query = query.filter(Policy.level == level)
    
    return list(query.order_by(Policy.created_at.desc()).all())
