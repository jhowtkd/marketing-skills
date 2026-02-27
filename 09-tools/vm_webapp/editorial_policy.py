"""Editorial policy evaluator module.

Isolated logic for editorial authorization decisions based on:
- Role (admin/editor/viewer)
- Scope (global/objective)
- Brand policy flags
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Role(str, Enum):
    """User roles for editorial actions."""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Scope(str, Enum):
    """Scopes for editorial golden marking."""
    GLOBAL = "global"
    OBJECTIVE = "objective"


@dataclass(frozen=True)
class PolicyDecision:
    """Result of a policy evaluation."""
    allowed: bool
    reason: str


@dataclass(frozen=True)
class BrandPolicy:
    """Editorial policy configuration for a brand."""
    editor_can_mark_objective: bool = True
    editor_can_mark_global: bool = False

    @classmethod
    def default(cls) -> "BrandPolicy":
        """Return default policy."""
        return cls()


class PolicyStore(Protocol):
    """Protocol for policy storage."""
    
    def get_policy(self, brand_id: str) -> BrandPolicy | None:
        """Get policy for a brand. Returns None if not found."""
        ...


class PolicyEvaluator:
    """Evaluates editorial policy decisions.
    
    Deterministic evaluation based on role, scope, and brand policy.
    """
    
    def __init__(self, store: PolicyStore | None = None) -> None:
        self._store = store
    
    def evaluate(
        self,
        *,
        role: Role | str,
        scope: Scope | str,
        brand_id: str | None = None,
    ) -> PolicyDecision:
        """Evaluate if a role can perform action on scope.
        
        Args:
            role: User role (admin/editor/viewer)
            scope: Action scope (global/objective)
            brand_id: Optional brand ID for brand-specific policy lookup
            
        Returns:
            PolicyDecision with allowed status and reason
        """
        # Normalize inputs
        role_str = role.value if isinstance(role, Role) else role
        scope_str = scope.value if isinstance(scope, Scope) else scope
        
        # Admin always can do everything
        if role_str == Role.ADMIN.value:
            return PolicyDecision(
                allowed=True,
                reason="admin has full editorial permissions"
            )
        
        # Viewer cannot mark golden at all
        if role_str == Role.VIEWER.value:
            return PolicyDecision(
                allowed=False,
                reason="viewer is not authorized for editorial actions"
            )
        
        # Editor: check scope permissions
        if role_str == Role.EDITOR.value:
            return self._evaluate_editor(scope_str, brand_id)
        
        # Unknown role: deny
        return PolicyDecision(
            allowed=False,
            reason=f"unknown role '{role_str}'"
        )
    
    def _evaluate_editor(self, scope: str, brand_id: str | None) -> PolicyDecision:
        """Evaluate editor permissions based on scope and brand policy."""
        # Get brand policy
        policy = self._get_policy_for_brand(brand_id)
        
        if scope == Scope.OBJECTIVE.value:
            if policy.editor_can_mark_objective:
                return PolicyDecision(
                    allowed=True,
                    reason="editor can mark objective (policy allows)"
                )
            return PolicyDecision(
                allowed=False,
                reason="editor cannot mark objective (policy denies)"
            )
        
        if scope == Scope.GLOBAL.value:
            if policy.editor_can_mark_global:
                return PolicyDecision(
                    allowed=True,
                    reason="editor can mark global (policy allows)"
                )
            return PolicyDecision(
                allowed=False,
                reason="editor cannot mark global (policy denies)"
            )
        
        # Unknown scope: deny
        return PolicyDecision(
            allowed=False,
            reason=f"unknown scope '{scope}'"
        )
    
    def _get_policy_for_brand(self, brand_id: str | None) -> BrandPolicy:
        """Get policy for a brand, returning defaults if not found.
        
        Safe fallback: returns default policy when:
        - brand_id is None
        - store is not configured
        - policy not found in store
        """
        if brand_id is None:
            return BrandPolicy.default()
        
        if self._store is None:
            return BrandPolicy.default()
        
        policy = self._store.get_policy(brand_id)
        return policy if policy is not None else BrandPolicy.default()


def create_evaluator_from_session(session, brand_id: str) -> PolicyEvaluator:
    """Factory function to create evaluator from database session.
    
    Args:
        session: SQLAlchemy session
        brand_id: Brand ID to lookup policy for
        
    Returns:
        PolicyEvaluator configured with database policy store
    """
    from vm_webapp.repo import get_editorial_policy
    
    class SessionPolicyStore:
        def get_policy(self, bid: str) -> BrandPolicy | None:
            row = get_editorial_policy(session, bid)
            if row is None:
                return None
            return BrandPolicy(
                editor_can_mark_objective=row.editor_can_mark_objective,
                editor_can_mark_global=row.editor_can_mark_global,
            )
    
    return PolicyEvaluator(store=SessionPolicyStore())
