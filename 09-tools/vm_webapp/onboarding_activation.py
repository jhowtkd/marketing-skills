"""v31 Onboarding Activation Engine - Rule-based learning loop for onboarding optimization."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid


class RiskLevel(str, Enum):
    """Risk levels for adjustment proposals."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProposalStatus(str, Enum):
    """Status of a proposal."""
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class AdjustmentProposal:
    """A proposal for adjusting onboarding parameters."""
    id: str
    rule_name: str
    description: str
    risk_level: RiskLevel
    current_value: float
    target_value: float
    adjustment_percent: float
    expected_impact: str
    status: ProposalStatus = ProposalStatus.PENDING
    brand_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    applied_at: Optional[str] = None
    auto_applied: bool = False


class OnboardingActivationEngine:
    """Rule-based engine for optimizing onboarding activation."""
    
    # Max adjustment per cycle: ±10%
    MAX_ADJUSTMENT_PERCENT = 10.0
    
    # Rule definitions with risk levels
    RULES = [
        {
            "name": "reduce_step_1_complexity",
            "description": "Simplify workspace setup form",
            "condition": lambda m: m.get("step_1_dropoff_rate", 0) > 0.30,
            "risk_level": RiskLevel.LOW,
            "adjustment": -10,  # Reduce complexity by 10%
            "target_metric": "step_1_dropoff_rate",
            "expected_impact": "Reduce step 1 dropoff by 5-8%",
        },
        {
            "name": "add_nudge_to_template_selection",
            "description": "Add contextual nudge for template selection",
            "condition": lambda m: m.get("template_to_first_run_conversion", 1.0) < 0.50,
            "risk_level": RiskLevel.LOW,
            "adjustment": -8,  # Small nudge adjustment
            "target_metric": "template_to_first_run_conversion",
            "expected_impact": "Improve template selection conversion by 10-15%",
        },
        {
            "name": "reduce_time_to_first_action",
            "description": "Pre-fill common values to reduce initial friction",
            "condition": lambda m: m.get("average_time_to_first_action_ms", 0) > 90000,
            "risk_level": RiskLevel.LOW,
            "adjustment": -10,
            "target_metric": "average_time_to_first_action_ms",
            "expected_impact": "Reduce time to first action by 15-20%",
        },
        {
            "name": "reorder_onboarding_steps",
            "description": "Move template selection before workspace setup",
            "condition": lambda m: (
                m.get("abandon_by_step", {}).get("workspace_setup", 0) > 
                m.get("abandon_by_step", {}).get("template_selection", 0) * 2
            ),
            "risk_level": RiskLevel.MEDIUM,
            "adjustment": 0,  # Structural change, not percentage
            "target_metric": "completion_rate",
            "expected_impact": "Improve completion rate by 8-12%",
        },
        {
            "name": "add_progress_rewards",
            "description": "Add gamification elements for step completion",
            "condition": lambda m: m.get("completion_rate", 1.0) < 0.50,
            "risk_level": RiskLevel.MEDIUM,
            "adjustment": 5,
            "target_metric": "completion_rate",
            "expected_impact": "Increase completion rate by 10-15%",
        },
        {
            "name": "major_onboarding_redesign",
            "description": "Complete redesign of onboarding flow based on friction analysis",
            "condition": lambda m: (
                m.get("completion_rate", 1.0) < 0.30 or
                m.get("total_abandons", 0) > 50
            ),
            "risk_level": RiskLevel.HIGH,
            "adjustment": 0,
            "target_metric": "completion_rate",
            "expected_impact": "Potential 20-30% improvement in completion rate",
        },
        {
            "name": "enable_skip_options",
            "description": "Allow skipping optional steps with clear CTAs",
            "condition": lambda m: m.get("abandon_reasons", {}).get("too_complex", 0) > 15,
            "risk_level": RiskLevel.MEDIUM,
            "adjustment": -5,
            "target_metric": "step_1_dropoff_rate",
            "expected_impact": "Reduce complexity-related dropoff by 10%",
        },
    ]
    
    def __init__(self):
        """Initialize the engine with empty state."""
        self._proposals: Dict[str, List[AdjustmentProposal]] = {}
        self._applied_history: Dict[str, List[AdjustmentProposal]] = {}
        self._frozen_brands: set = set()
    
    def evaluate_rules(self, brand_id: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all rules against metrics and generate proposals."""
        if brand_id in self._frozen_brands:
            return []
        
        proposals = []
        
        for rule in self.RULES:
            if rule["condition"](metrics):
                proposal = self._create_proposal(brand_id, rule, metrics)
                proposals.append(proposal)
                
                # Store for later retrieval
                if brand_id not in self._proposals:
                    self._proposals[brand_id] = []
                self._proposals[brand_id].append(proposal)
        
        return [self._proposal_to_dict(p) for p in proposals]
    
    def _create_proposal(
        self,
        brand_id: str,
        rule: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> AdjustmentProposal:
        """Create a proposal from a rule."""
        target_metric = rule["target_metric"]
        current_value = metrics.get(target_metric, 0.0)
        
        # If current value is a dict (like abandon_by_step), use max value
        if isinstance(current_value, dict):
            current_value = max(current_value.values()) if current_value else 0.0
        
        adjustment = rule["adjustment"]
        
        # Clamp adjustment to max ±10%
        adjustment = max(-self.MAX_ADJUSTMENT_PERCENT, min(self.MAX_ADJUSTMENT_PERCENT, adjustment))
        
        # Calculate target value
        if current_value > 0 and adjustment != 0:
            target_value = current_value * (1 + adjustment / 100)
        else:
            target_value = current_value
        
        return AdjustmentProposal(
            id=f"prop-{uuid.uuid4().hex[:8]}",
            rule_name=rule["name"],
            description=rule["description"],
            risk_level=rule["risk_level"],
            current_value=current_value,
            target_value=target_value,
            adjustment_percent=adjustment,
            expected_impact=rule["expected_impact"],
            brand_id=brand_id,
        )
    
    def _proposal_to_dict(self, proposal: AdjustmentProposal) -> Dict[str, Any]:
        """Convert proposal to dictionary."""
        return {
            "id": proposal.id,
            "rule_name": proposal.rule_name,
            "description": proposal.description,
            "risk_level": proposal.risk_level.value,
            "current_value": proposal.current_value,
            "target_value": proposal.target_value,
            "adjustment_percent": proposal.adjustment_percent,
            "expected_impact": proposal.expected_impact,
            "status": proposal.status.value,
            "brand_id": proposal.brand_id,
            "created_at": proposal.created_at,
        }
    
    def apply_proposal(self, brand_id: str, proposal_id: str) -> Dict[str, Any]:
        """Apply a proposal. Auto-apply for low risk."""
        proposals = self._proposals.get(brand_id, [])
        proposal = next((p for p in proposals if p.id == proposal_id), None)
        
        if not proposal:
            return {"error": "Proposal not found", "status": "error"}
        
        # Auto-apply only for low risk
        auto_applied = proposal.risk_level == RiskLevel.LOW
        
        proposal.status = ProposalStatus.APPLIED
        proposal.applied_at = datetime.utcnow().isoformat()
        proposal.auto_applied = auto_applied
        
        # Track in history
        if brand_id not in self._applied_history:
            self._applied_history[brand_id] = []
        self._applied_history[brand_id].append(proposal)
        
        return {
            "id": proposal_id,
            "status": ProposalStatus.APPLIED.value,
            "auto_applied": auto_applied,
            "applied_at": proposal.applied_at,
        }
    
    def reject_proposal(self, brand_id: str, proposal_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a proposal."""
        proposals = self._proposals.get(brand_id, [])
        proposal = next((p for p in proposals if p.id == proposal_id), None)
        
        if not proposal:
            return {"error": "Proposal not found", "status": "error"}
        
        proposal.status = ProposalStatus.REJECTED
        
        return {
            "id": proposal_id,
            "status": ProposalStatus.REJECTED.value,
            "reason": reason,
        }
    
    def freeze_proposals(self, brand_id: str) -> Dict[str, Any]:
        """Freeze proposals for a brand."""
        self._frozen_brands.add(brand_id)
        
        return {
            "brand_id": brand_id,
            "frozen": True,
            "frozen_at": datetime.utcnow().isoformat(),
        }
    
    def rollback_last(self, brand_id: str) -> Dict[str, Any]:
        """Rollback the last applied proposal."""
        history = self._applied_history.get(brand_id, [])
        
        if not history:
            return {"error": "No proposals to rollback", "status": "error"}
        
        last_proposal = history[-1]
        last_proposal.status = ProposalStatus.ROLLED_BACK
        
        return {
            "brand_id": brand_id,
            "proposal_id": last_proposal.id,
            "rolled_back": True,
            "rolled_back_at": datetime.utcnow().isoformat(),
        }
    
    def get_proposals(self, brand_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get proposals for a brand, optionally filtered by status."""
        proposals = self._proposals.get(brand_id, [])
        
        if status:
            proposals = [p for p in proposals if p.status.value == status]
        
        return [self._proposal_to_dict(p) for p in proposals]
    
    def identify_top_frictions(
        self,
        brand_id: str,
        metrics: Dict[str, Any],
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Identify top friction points from metrics."""
        frictions = []
        
        # Analyze abandon by step
        abandon_by_step = metrics.get("abandon_by_step", {})
        for step, count in abandon_by_step.items():
            frictions.append({
                "type": "step_abandon",
                "step": step,
                "count": count,
                "severity": "high" if count > 20 else "medium" if count > 10 else "low",
            })
        
        # Analyze abandon reasons
        abandon_reasons = metrics.get("abandon_reasons", {})
        for reason, count in abandon_reasons.items():
            frictions.append({
                "type": "reason",
                "reason": reason,
                "count": count,
                "severity": "high" if count > 15 else "medium" if count > 8 else "low",
            })
        
        # Sort by count descending and limit
        frictions.sort(key=lambda x: x["count"], reverse=True)
        return frictions[:limit]
