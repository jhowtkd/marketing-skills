"""ROI-Weighted Policy Optimizer (v19).

Implements composite ROI score calculation with three weighted pillars:
- Business (40%): approval_without_regen_24h, revenue_attribution
- Quality (35%): regen_per_job, quality_score_avg
- Efficiency (25%): avg_latency_ms, cost_per_job

Features:
- Weekly semi-automatic policy optimization
- Hard guardrails (incident_rate cannot increase)
- ±10% adjustment clamp per cycle
- Low-risk autoapply eligibility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Optional


class RiskLevel(Enum):
    """Risk levels for proposals."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProposalStatus(Enum):
    """Status of an optimization proposal."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class RoiWeights:
    """Weight configuration for ROI pillars."""
    business: float = 0.40
    quality: float = 0.35
    efficiency: float = 0.25

    def __post_init__(self):
        total = self.business + self.quality + self.efficiency
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass(frozen=True)
class RoiPillarScores:
    """Individual pillar scores (0-1 range)."""
    business: float
    quality: float
    efficiency: float


@dataclass(frozen=True)
class RoiContributions:
    """Weighted contributions to total score."""
    business: float
    quality: float
    efficiency: float


@dataclass(frozen=True)
class RoiCompositeScore:
    """Complete ROI composite score with breakdown."""
    total_score: float
    pillar_scores: RoiPillarScores
    contributions: RoiContributions
    weights: RoiWeights
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RoiScoreInput:
    """Input metrics for ROI score calculation.
    
    All ratios should be in 0-1 range where applicable.
    """
    # Business proxies
    approval_without_regen_24h: float  # 0-1 ratio
    revenue_attribution_usd: float
    
    # Quality proxies
    regen_per_job: float  # 0+ (lower is better)
    quality_score_avg: float  # 0-1 (higher is better)
    
    # Efficiency proxies
    avg_latency_ms: float  # milliseconds (lower is better)
    cost_per_job_usd: float  # USD (lower is better)
    
    # Optional safety metric
    incident_rate: float = 0.0  # 0-1 ratio (lower is better)

    def __post_init__(self):
        # Validate ranges
        if not 0 <= self.approval_without_regen_24h <= 1:
            raise ValueError(f"approval_without_regen_24h must be in [0,1], got {self.approval_without_regen_24h}")
        if not 0 <= self.quality_score_avg <= 1:
            raise ValueError(f"quality_score_avg must be in [0,1], got {self.quality_score_avg}")
        if self.revenue_attribution_usd < 0:
            raise ValueError(f"revenue_attribution_usd must be >= 0")
        if self.regen_per_job < 0:
            raise ValueError(f"regen_per_job must be >= 0")
        if self.avg_latency_ms < 0:
            raise ValueError(f"avg_latency_ms must be >= 0")
        if self.cost_per_job_usd < 0:
            raise ValueError(f"cost_per_job_usd must be >= 0")
        if not 0 <= self.incident_rate <= 1:
            raise ValueError(f"incident_rate must be in [0,1]")


@dataclass
class RoiProposal:
    """An optimization proposal with ROI projections."""
    id: str
    description: str
    expected_roi_delta: float
    risk_level: RiskLevel
    status: ProposalStatus
    adjustments: dict[str, float] = field(default_factory=dict)
    autoapply_eligible: bool = False
    block_reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    applied_at: Optional[datetime] = None


class RoiScoreCalculator:
    """Calculate ROI composite scores from input metrics."""
    
    # Normalization constants for proxy values
    MAX_REVENUE = 500000  # USD - considered excellent
    MAX_REGEN = 2.0  # regen/job - above this is poor
    MAX_LATENCY = 500  # ms - above this is poor
    MAX_COST = 0.20  # USD - above this is poor
    
    def __init__(self, weights: Optional[RoiWeights] = None):
        self.weights = weights or RoiWeights()
    
    def calculate(self, input_data: RoiScoreInput) -> RoiCompositeScore:
        """Calculate composite ROI score from input metrics."""
        # Calculate pillar scores (normalized to 0-1)
        business_score = self._calculate_business_score(input_data)
        quality_score = self._calculate_quality_score(input_data)
        efficiency_score = self._calculate_efficiency_score(input_data)
        
        pillar_scores = RoiPillarScores(
            business=business_score,
            quality=quality_score,
            efficiency=efficiency_score,
        )
        
        # Calculate weighted contributions
        contributions = RoiContributions(
            business=business_score * self.weights.business,
            quality=quality_score * self.weights.quality,
            efficiency=efficiency_score * self.weights.efficiency,
        )
        
        # Total score is sum of weighted contributions
        total_score = (
            contributions.business +
            contributions.quality +
            contributions.efficiency
        )
        
        return RoiCompositeScore(
            total_score=total_score,
            pillar_scores=pillar_scores,
            contributions=contributions,
            weights=self.weights,
        )
    
    def _calculate_business_score(self, input_data: RoiScoreInput) -> float:
        """Calculate business pillar score (0-1, higher is better).
        
        Based on:
        - approval_without_regen_24h (primary): direct measure
        - revenue_attribution_usd (secondary): normalized
        """
        approval_component = input_data.approval_without_regen_24h
        
        # Normalize revenue (cap at MAX_REVENUE)
        revenue_normalized = min(input_data.revenue_attribution_usd / self.MAX_REVENUE, 1.0)
        
        # Weight: 70% approval, 30% revenue
        return (approval_component * 0.70) + (revenue_normalized * 0.30)
    
    def _calculate_quality_score(self, input_data: RoiScoreInput) -> float:
        """Calculate quality pillar score (0-1, higher is better).
        
        Based on:
        - regen_per_job: inverted and normalized (lower is better)
        - quality_score_avg: direct measure
        """
        # Invert regen (0 regen = 1.0 score, MAX_REGEN = 0.0 score)
        regen_normalized = max(0.0, 1.0 - (input_data.regen_per_job / self.MAX_REGEN))
        
        quality_component = input_data.quality_score_avg
        
        # Weight: 60% quality_score, 40% regen
        return (quality_component * 0.60) + (regen_normalized * 0.40)
    
    def _calculate_efficiency_score(self, input_data: RoiScoreInput) -> float:
        """Calculate efficiency pillar score (0-1, higher is better).
        
        Based on:
        - avg_latency_ms: inverted and normalized (lower is better)
        - cost_per_job_usd: inverted and normalized (lower is better)
        """
        # Invert latency (50ms = 1.0, MAX_LATENCY = 0.0)
        latency_normalized = max(0.0, 1.0 - (input_data.avg_latency_ms / self.MAX_LATENCY))
        
        # Invert cost ($0.01 = 1.0, MAX_COST = 0.0)
        cost_normalized = max(0.0, 1.0 - (input_data.cost_per_job_usd / self.MAX_COST))
        
        # Weight: 50% latency, 50% cost
        return (latency_normalized * 0.50) + (cost_normalized * 0.50)


class RoiOptimizer:
    """ROI-weighted policy optimizer with guardrails."""
    
    # Adjustment limits
    MAX_ADJUSTMENT_PER_CYCLE = 0.10  # ±10%
    
    def __init__(
        self,
        mode: str = "semi-automatic",
        cadence: str = "weekly",
        calculator: Optional[RoiScoreCalculator] = None,
    ):
        self.mode = mode
        self.cadence = cadence
        self.calculator = calculator or RoiScoreCalculator()
        self._proposal_counter = 0
    
    def generate_proposals(
        self,
        current_state: RoiScoreInput,
        target_improvement: Optional[float] = None,
        projected_incident_rate: Optional[float] = None,
    ) -> list[RoiProposal]:
        """Generate optimization proposals with ROI projections.
        
        Args:
            current_state: Current metrics state
            target_improvement: Desired ROI improvement (e.g., 0.10 for +10%)
            projected_incident_rate: Projected incident rate after changes
            
        Returns:
            List of proposals with status and eligibility
        """
        proposals = []
        current_score = self.calculator.calculate(current_state)
        
        # Check hard guardrail: incident rate cannot increase
        if projected_incident_rate is not None:
            if projected_incident_rate > current_state.incident_rate:
                # Block all proposals that would increase incidents
                proposal = self._create_blocked_proposal(
                    "Optimization blocked: would increase incident rate",
                    f"Current: {current_state.incident_rate:.3f}, Projected: {projected_incident_rate:.3f}",
                )
                proposals.append(proposal)
                return proposals
        
        # Generate adjustment proposals based on pillar weaknesses
        pillar_scores = current_score.pillar_scores
        
        # Identify lowest scoring pillar for improvement
        pillar_scores_dict = {
            "business": pillar_scores.business,
            "quality": pillar_scores.quality,
            "efficiency": pillar_scores.efficiency,
        }
        weakest_pillar = min(pillar_scores_dict, key=pillar_scores_dict.get)
        
        # Create proposal for weakest pillar
        proposal = self._create_pillar_proposal(
            weakest_pillar,
            current_state,
            current_score,
            target_improvement,
        )
        proposals.append(proposal)
        
        # Create balanced improvement proposal
        balanced_proposal = self._create_balanced_proposal(
            current_state,
            current_score,
            target_improvement,
        )
        proposals.append(balanced_proposal)
        
        return proposals
    
    def _create_pillar_proposal(
        self,
        pillar: str,
        current_state: RoiScoreInput,
        current_score: RoiCompositeScore,
        target_improvement: Optional[float],
    ) -> RoiProposal:
        """Create a proposal focused on improving a specific pillar."""
        self._proposal_counter += 1
        
        # Define adjustments based on pillar
        adjustments: dict[str, float] = {}
        
        if pillar == "business":
            adjustments = {
                "approval_boost": min(0.10, self.MAX_ADJUSTMENT_PER_CYCLE),
            }
            description = "Increase approval rate through policy refinement"
        elif pillar == "quality":
            adjustments = {
                "regen_reduction": -min(0.10, self.MAX_ADJUSTMENT_PER_CYCLE),
                "quality_threshold": min(0.05, self.MAX_ADJUSTMENT_PER_CYCLE),
            }
            description = "Improve quality through reduced regeneration"
        else:  # efficiency
            adjustments = {
                "latency_optimization": -min(0.10, self.MAX_ADJUSTMENT_PER_CYCLE),
                "cost_efficiency": -min(0.05, self.MAX_ADJUSTMENT_PER_CYCLE),
            }
            description = "Optimize efficiency through latency reduction"
        
        # Calculate expected ROI delta
        expected_delta = target_improvement or 0.05
        expected_delta = min(expected_delta, 0.10)  # Cap at 10%
        
        # Determine risk level
        risk_level = self._assess_risk(adjustments, current_state)
        
        # Autoapply eligibility: only low risk in semi-automatic mode
        autoapply_eligible = risk_level == RiskLevel.LOW
        
        return RoiProposal(
            id=f"proposal-{self._proposal_counter:03d}",
            description=description,
            expected_roi_delta=expected_delta,
            risk_level=risk_level,
            status=ProposalStatus.PENDING,
            adjustments=adjustments,
            autoapply_eligible=autoapply_eligible,
        )
    
    def _create_balanced_proposal(
        self,
        current_state: RoiScoreInput,
        current_score: RoiCompositeScore,
        target_improvement: Optional[float],
    ) -> RoiProposal:
        """Create a balanced proposal improving all pillars slightly."""
        self._proposal_counter += 1
        
        # Small adjustments across all dimensions
        adjustments = {
            "approval_boost": min(0.05, self.MAX_ADJUSTMENT_PER_CYCLE),
            "regen_reduction": -min(0.05, self.MAX_ADJUSTMENT_PER_CYCLE),
            "latency_optimization": -min(0.05, self.MAX_ADJUSTMENT_PER_CYCLE),
        }
        
        expected_delta = target_improvement or 0.03
        expected_delta = min(expected_delta, 0.10)
        
        risk_level = self._assess_risk(adjustments, current_state)
        autoapply_eligible = risk_level == RiskLevel.LOW
        
        return RoiProposal(
            id=f"proposal-{self._proposal_counter:03d}",
            description="Balanced optimization across all pillars",
            expected_roi_delta=expected_delta,
            risk_level=risk_level,
            status=ProposalStatus.PENDING,
            adjustments=adjustments,
            autoapply_eligible=autoapply_eligible,
        )
    
    def _create_blocked_proposal(self, reason: str, details: str) -> RoiProposal:
        """Create a blocked proposal due to guardrail violation."""
        self._proposal_counter += 1
        
        return RoiProposal(
            id=f"proposal-{self._proposal_counter:03d}",
            description="Optimization blocked by hard guardrail",
            expected_roi_delta=0.0,
            risk_level=RiskLevel.CRITICAL,
            status=ProposalStatus.BLOCKED,
            block_reason=f"{reason}: {details}",
            autoapply_eligible=False,
        )
    
    def _assess_risk(
        self,
        adjustments: dict[str, float],
        current_state: RoiScoreInput,
    ) -> RiskLevel:
        """Assess risk level of proposed adjustments."""
        # Check if any adjustment is near the limit
        max_adjustment = max(abs(v) for v in adjustments.values()) if adjustments else 0
        
        # Risk based on current state and adjustment size
        if current_state.incident_rate > 0.03:  # High current incidents
            return RiskLevel.HIGH
        elif max_adjustment > 0.08:  # Large adjustment
            return RiskLevel.MEDIUM
        elif current_state.quality_score_avg < 0.60:  # Poor quality
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
