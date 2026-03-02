"""Hybrid ROI engine with quality guardrails for v36.

Combines financial and operational metrics into a hybrid ROI score,
with guardrails to prevent optimization that degrades quality or stability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
import uuid

from vm_webapp.outcome_attribution import OutcomeType, TouchpointType


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FinancialMetrics:
    """Financial metrics for ROI calculation."""
    revenue_per_activation: float = 0.0
    cost_per_activation: float = 0.0
    time_to_revenue_days: float = 30.0
    
    @property
    def roi(self) -> float:
        """Calculate financial ROI: (revenue - cost) / cost."""
        if self.cost_per_activation <= 0:
            return 0.0
        return (self.revenue_per_activation - self.cost_per_activation) / self.cost_per_activation
    
    @property
    def payback_time_days(self) -> float:
        """Calculate payback time in days."""
        if self.revenue_per_activation <= 0:
            return float('inf')
        return self.time_to_revenue_days * (self.cost_per_activation / self.revenue_per_activation)
    
    def to_hybrid_contribution(self, weight: float = 0.6) -> float:
        """Convert to hybrid ROI index contribution (weighted)."""
        return self.roi * weight


@dataclass
class OperationalMetrics:
    """Operational metrics for ROI calculation."""
    human_minutes_per_activation: float = 0.0
    success_rate: float = 0.0
    
    @property
    def efficiency_score(self) -> float:
        """Calculate efficiency: success_rate / (human_hours)."""
        human_hours = self.human_minutes_per_activation / 60.0
        if human_hours <= 0:
            return 0.0
        return self.success_rate / human_hours
    
    def to_hybrid_contribution(self, weight: float = 0.4) -> float:
        """Convert to hybrid ROI index contribution (weighted)."""
        return self.efficiency_score * weight


@dataclass
class QualityPenalty:
    """Quality penalty applied to hybrid score."""
    factor: float  # 0-1, where 1 = 100% penalty
    reason: str
    
    @classmethod
    def for_incident(cls, severity: str = "medium") -> QualityPenalty:
        """Create penalty for incident."""
        severity_factors = {
            "low": 0.1,
            "medium": 0.25,
            "high": 0.5,
            "critical": 1.0,
        }
        return cls(
            factor=severity_factors.get(severity, 0.25),
            reason=f"{severity}_severity_incident",
        )
    
    @classmethod
    def for_quality_degradation(
        cls, 
        metric_name: str, 
        drop_percentage: float
    ) -> QualityPenalty:
        """Create penalty for quality degradation."""
        # Factor proportional to drop percentage (max 0.5)
        factor = min(0.5, drop_percentage / 100.0)
        return cls(
            factor=factor,
            reason=f"{metric_name}_degraded_{drop_percentage:.1f}pct",
        )


class ProposalRiskLevel(str, Enum):
    """Risk level for proposals based on hybrid score."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    
    @classmethod
    def from_hybrid_score(cls, score: float) -> ProposalRiskLevel:
        """Classify risk level from hybrid score."""
        if score >= 0.15:
            return cls.LOW
        elif score >= 0.08:
            return cls.MEDIUM
        else:
            return cls.HIGH


@dataclass
class HybridScore:
    """Hybrid ROI score combining financial and operational components."""
    financial_component: float = 0.0
    operational_component: float = 0.0
    quality_penalty: Optional[QualityPenalty] = None
    
    @property
    def hybrid_index(self) -> float:
        """Calculate hybrid ROI index."""
        financial = self.financial_component * 0.6
        operational = self.operational_component * 0.4
        return financial + operational
    
    @property
    def penalized_index(self) -> float:
        """Calculate hybrid index after penalty."""
        base = self.hybrid_index
        if self.quality_penalty:
            return base * (1 - self.quality_penalty.factor)
        return base
    
    def explain(self) -> str:
        """Generate human-readable explanation."""
        parts = [
            f"Financial component: {self.financial_component:.2f} (60% weight)",
            f"Operational component: {self.operational_component:.2f} (40% weight)",
            f"Base hybrid index: {self.hybrid_index:.2f}",
        ]
        if self.quality_penalty:
            parts.append(
                f"Quality penalty: -{self.quality_penalty.factor * 100:.0f}% "
                f"({self.quality_penalty.reason})"
            )
            parts.append(f"Final index: {self.penalized_index:.2f}")
        return "; ".join(parts)


@dataclass
class Proposal:
    """Optimization proposal with hybrid ROI score."""
    proposal_id: str
    brand_id: str
    touchpoint_type: TouchpointType
    action: str
    expected_impact: Dict[str, Any]
    score: HybridScore
    created_at: str = field(default_factory=_now_iso)
    status: str = "pending"  # pending, applied, rejected, rolled_back
    
    @property
    def risk_level(self) -> ProposalRiskLevel:
        """Get risk level from score."""
        return ProposalRiskLevel.from_hybrid_score(self.score.penalized_index)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert proposal to dictionary."""
        return {
            "proposal_id": self.proposal_id,
            "brand_id": self.brand_id,
            "touchpoint_type": self.touchpoint_type.value,
            "action": self.action,
            "expected_impact": self.expected_impact,
            "hybrid_index": self.score.penalized_index,
            "risk_level": self.risk_level.value,
            "status": self.status,
            "created_at": self.created_at,
            "score_explanation": self.score.explain(),
        }


@dataclass
class GuardrailRule:
    """Guardrail rule to check proposal quality."""
    name: str
    check: Callable[[Dict[str, Any]], bool]
    message: str
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate rule against context."""
        try:
            return self.check(context)
        except Exception:
            return False


@dataclass
class BlockCheckResult:
    """Result of block rule check."""
    blocked: bool
    reason: Optional[str] = None


@dataclass
class BlockRule:
    """Block rule that can prevent proposal application."""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    block_message: str
    
    def check(self, context: Dict[str, Any]) -> BlockCheckResult:
        """Check if proposal should be blocked."""
        try:
            if self.condition(context):
                return BlockCheckResult(blocked=False)
            else:
                return BlockCheckResult(blocked=True, reason=self.block_message)
        except Exception as e:
            return BlockCheckResult(blocked=True, reason=f"Error checking rule: {e}")


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    passed: bool
    violations: List[str]


@dataclass
class ProposalEvaluation:
    """Result of proposal evaluation."""
    proposal_id: str
    autoapply: bool
    approval_required: bool
    blocked: bool
    reason: Optional[str] = None
    guardrail_violations: List[str] = field(default_factory=list)


class HybridROIEngine:
    """Engine for calculating hybrid ROI and managing proposals."""
    
    # Default thresholds
    AUTOAPPLY_THRESHOLD = 0.15  # hybrid_index >= 0.15
    APPROVAL_THRESHOLD = 0.08   # hybrid_index >= 0.08 needs approval
    
    def __init__(self):
        """Initialize engine with default guardrails and block rules."""
        self.proposals: Dict[str, Proposal] = {}
        self.guardrail_rules: List[GuardrailRule] = self._default_guardrails()
        self.block_rules: List[BlockRule] = self._default_block_rules()
    
    def _default_guardrails(self) -> List[GuardrailRule]:
        """Create default guardrail rules."""
        return [
            GuardrailRule(
                name="min_success_rate",
                check=lambda ctx: ctx.get("success_rate", 0) >= 0.8,
                message="Success rate below 80%",
            ),
            GuardrailRule(
                name="max_incident_rate",
                check=lambda ctx: ctx.get("incident_rate", 1) <= 0.05,
                message="Incident rate above 5%",
            ),
            GuardrailRule(
                name="min_user_satisfaction",
                check=lambda ctx: ctx.get("user_satisfaction", 0) >= 0.7,
                message="User satisfaction below 70%",
            ),
        ]
    
    def _default_block_rules(self) -> List[BlockRule]:
        """Create default block rules."""
        return [
            BlockRule(
                name="no_incident_spike",
                condition=lambda ctx: ctx.get("incident_rate", 0) < 0.05,
                block_message="Blocked: incident rate spike detected (>= 5%)",
            ),
            BlockRule(
                name="no_critical_errors",
                condition=lambda ctx: ctx.get("critical_error_rate", 0) < 0.01,
                block_message="Blocked: critical error rate too high (>= 1%)",
            ),
        ]
    
    def calculate_financial_metrics(self, data: Dict[str, Any]) -> FinancialMetrics:
        """Calculate financial metrics from raw data."""
        activations = data.get("activations", 1)
        if activations <= 0:
            activations = 1
        
        return FinancialMetrics(
            revenue_per_activation=data.get("revenue", 0) / activations,
            cost_per_activation=data.get("cost", 0) / activations,
            time_to_revenue_days=data.get("time_to_revenue_days", 30.0),
        )
    
    def calculate_operational_metrics(self, data: Dict[str, Any]) -> OperationalMetrics:
        """Calculate operational metrics from raw data."""
        activations = data.get("activations", 1)
        if activations <= 0:
            activations = 1
        
        successes = data.get("successes", 0)
        success_rate = successes / activations if activations > 0 else 0.0
        
        return OperationalMetrics(
            human_minutes_per_activation=data.get("human_minutes", 0) / activations,
            success_rate=success_rate,
        )
    
    def calculate_hybrid_score(
        self,
        financial: FinancialMetrics,
        operational: OperationalMetrics,
        penalty: Optional[QualityPenalty] = None,
    ) -> HybridScore:
        """Calculate hybrid score from metrics."""
        return HybridScore(
            financial_component=financial.roi,
            operational_component=operational.efficiency_score,
            quality_penalty=penalty,
        )
    
    def generate_proposal(
        self,
        brand_id: str,
        touchpoint_type: TouchpointType,
        action: str,
        expected_impact: Dict[str, Any],
        financial_data: Dict[str, Any],
        operational_data: Dict[str, Any],
        penalty: Optional[QualityPenalty] = None,
    ) -> Proposal:
        """Generate optimization proposal."""
        financial = self.calculate_financial_metrics(financial_data)
        operational = self.calculate_operational_metrics(operational_data)
        score = self.calculate_hybrid_score(financial, operational, penalty)
        
        proposal = Proposal(
            proposal_id=str(uuid.uuid4()),
            brand_id=brand_id,
            touchpoint_type=touchpoint_type,
            action=action,
            expected_impact=expected_impact,
            score=score,
        )
        
        self.proposals[proposal.proposal_id] = proposal
        return proposal
    
    def check_guardrails(self, context: Dict[str, Any]) -> GuardrailResult:
        """Check guardrail rules against context."""
        violations = []
        for rule in self.guardrail_rules:
            if not rule.evaluate(context):
                violations.append(rule.message)
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
        )
    
    def check_blocks(self, context: Dict[str, Any]) -> BlockCheckResult:
        """Check block rules against context."""
        for rule in self.block_rules:
            result = rule.check(context)
            if result.blocked:
                return result
        return BlockCheckResult(blocked=False)
    
    def evaluate_proposal(
        self,
        proposal: Proposal,
        context: Dict[str, Any],
    ) -> ProposalEvaluation:
        """Evaluate proposal against guardrails and blocks."""
        # Check block rules first
        block_result = self.check_blocks(context)
        if block_result.blocked:
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                autoapply=False,
                approval_required=False,
                blocked=True,
                reason=block_result.reason,
            )
        
        # Check guardrails
        guardrail_result = self.check_guardrails(context)
        
        # Determine action based on score
        score = proposal.score.penalized_index
        
        if score >= self.AUTOAPPLY_THRESHOLD and guardrail_result.passed:
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                autoapply=True,
                approval_required=False,
                blocked=False,
                guardrail_violations=guardrail_result.violations,
            )
        elif score >= self.APPROVAL_THRESHOLD:
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                autoapply=False,
                approval_required=True,
                blocked=False,
                guardrail_violations=guardrail_result.violations,
            )
        else:
            return ProposalEvaluation(
                proposal_id=proposal.proposal_id,
                autoapply=False,
                approval_required=False,
                blocked=False,
                reason="Score below approval threshold",
                guardrail_violations=guardrail_result.violations,
            )
    
    def get_roi_summary(self, brand_id: Optional[str] = None) -> Dict[str, Any]:
        """Get ROI summary for proposals."""
        proposals = list(self.proposals.values())
        if brand_id:
            proposals = [p for p in proposals if p.brand_id == brand_id]
        
        if not proposals:
            return {
                "total_proposals": 0,
                "avg_hybrid_index": 0.0,
                "by_risk_level": {},
            }
        
        total = len(proposals)
        avg_index = sum(p.score.penalized_index for p in proposals) / total
        
        by_risk = {}
        for level in ProposalRiskLevel:
            count = len([p for p in proposals if p.risk_level == level])
            if count > 0:
                by_risk[level.value] = count
        
        return {
            "total_proposals": total,
            "avg_hybrid_index": round(avg_index, 4),
            "by_risk_level": by_risk,
        }
