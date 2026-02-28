"""First-run recommendation read model and ranking engine.

Provides aggregation of V1 outcomes and deterministic ranking with fallback
for profile/mode recommendations to improve approval_without_regen_24h KPI.
"""

from dataclasses import dataclass, field
from typing import Optional
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


@dataclass
class FirstRunOutcomeAggregate:
    """Aggregate of first-run outcomes for a specific profile/mode combination.
    
    Tracks success metrics over a 24-hour window to determine which
    profile/mode combinations are most effective.
    """
    
    profile: str
    mode: str
    total_runs: int = 0
    success_24h_count: int = 0
    approved_count: int = 0
    _quality_score_sum: float = field(default=0.0, repr=False)
    _duration_ms_sum: float = field(default=0.0, repr=False)
    
    @property
    def avg_quality_score(self) -> float:
        """Average quality score across all runs."""
        if self.total_runs == 0:
            return 0.0
        return self._quality_score_sum / self.total_runs
    
    @property
    def avg_duration_ms(self) -> float:
        """Average duration in milliseconds across all runs."""
        if self.total_runs == 0:
            return 0.0
        return self._duration_ms_sum / self.total_runs
    
    @property
    def success_rate(self) -> float:
        """Success rate within 24h (no regeneration)."""
        if self.total_runs == 0:
            return 0.0
        return self.success_24h_count / self.total_runs
    
    def update(
        self,
        *,
        approved: bool,
        success_24h: bool,
        quality_score: float,
        duration_ms: float,
    ) -> Self:
        """Update aggregate with a new outcome.
        
        Args:
            approved: Whether the run was approved
            success_24h: Whether no new run was created within 24h
            quality_score: Quality score of the run (0.0 - 1.0)
            duration_ms: Duration of the run in milliseconds
        
        Returns:
            Self for method chaining
        """
        self.total_runs += 1
        if approved:
            self.approved_count += 1
        if success_24h:
            self.success_24h_count += 1
        self._quality_score_sum += quality_score
        self._duration_ms_sum += duration_ms
        return self


@dataclass(frozen=True)
class ProfileModeOutcome:
    """Immutable outcome data for a profile/mode combination.
    
    Used as input for the ranking engine.
    """
    
    profile: str
    mode: str
    total_runs: int
    success_24h_count: int
    success_rate: float
    avg_quality_score: float
    avg_duration_ms: float


@dataclass(frozen=True)
class RankedRecommendation:
    """A ranked recommendation with confidence and reasoning.
    
    Output of the ranking engine.
    """
    
    profile: str
    mode: str
    score: float
    confidence: float
    reason_codes: list[str]
    
    # Threshold for auto-selection in UI
    CONFIDENCE_THRESHOLD: float = field(default=0.55, repr=False)
    
    @property
    def can_auto_select(self) -> bool:
        """Whether this recommendation can be auto-selected in the UI."""
        return self.confidence >= self.CONFIDENCE_THRESHOLD


class RecommendationRanker:
    """Deterministic ranker for profile/mode recommendations.
    
    Implements a scoring formula that considers:
    - Success rate within 24h (primary metric)
    - Quality score (secondary metric)
    - Speed/inverse duration (tertiary metric)
    - Sample size confidence (penalty for low samples)
    
    Fallback chain: objective -> brand -> global -> default
    """
    
    # Minimum sample size for full confidence
    MIN_SAMPLE_SIZE: int = 10
    
    # Weight factors for scoring
    SUCCESS_RATE_WEIGHT: float = 0.6
    QUALITY_WEIGHT: float = 0.25
    SPEED_WEIGHT: float = 0.15
    
    def _calculate_score(self, outcome: ProfileModeOutcome) -> float:
        """Calculate score for an outcome.
        
        Formula weighted by:
        - 60% success rate (primary KPI)
        - 25% quality score
        - 15% speed (inverse of normalized duration)
        
        Penalized by sample size confidence.
        """
        # Base score components
        success_component = outcome.success_rate * self.SUCCESS_RATE_WEIGHT
        quality_component = outcome.avg_quality_score * self.QUALITY_WEIGHT
        
        # Speed component (faster is better, normalize to ~0-1 range)
        # Assume 1000ms is fast (score 1.0), 10000ms is slow (score 0.0)
        speed_normalized = max(0.0, 1.0 - (outcome.avg_duration_ms / 10000))
        speed_component = speed_normalized * self.SPEED_WEIGHT
        
        # Sample size confidence factor (0.5 to 1.0)
        if outcome.total_runs >= self.MIN_SAMPLE_SIZE:
            sample_confidence = 1.0
        else:
            # Linear scale from 0.5 at 0 samples to 1.0 at MIN_SAMPLE_SIZE
            sample_confidence = 0.5 + (0.5 * outcome.total_runs / self.MIN_SAMPLE_SIZE)
        
        raw_score = success_component + quality_component + speed_component
        return raw_score * sample_confidence
    
    def _calculate_confidence(self, outcome: ProfileModeOutcome) -> float:
        """Calculate confidence based on sample size.
        
        Returns value between 0.0 and 1.0.
        """
        if outcome.total_runs >= self.MIN_SAMPLE_SIZE:
            return min(1.0, 0.6 + (0.4 * outcome.total_runs / (self.MIN_SAMPLE_SIZE * 10)))
        else:
            return 0.3 + (0.3 * outcome.total_runs / self.MIN_SAMPLE_SIZE)
    
    def _generate_reason_codes(self, outcome: ProfileModeOutcome) -> list[str]:
        """Generate reason codes for the recommendation."""
        reasons = []
        
        if outcome.success_rate >= 0.7:
            reasons.append("high_success_rate")
        elif outcome.success_rate >= 0.5:
            reasons.append("success_rate")
        
        if outcome.avg_quality_score >= 0.8:
            reasons.append("high_quality")
        elif outcome.avg_quality_score >= 0.6:
            reasons.append("quality")
        
        if outcome.avg_duration_ms <= 4000:
            reasons.append("fast")
        
        if outcome.total_runs < self.MIN_SAMPLE_SIZE:
            reasons.append("low_sample_size")
        
        return reasons if reasons else ["default"]
    
    def rank(
        self,
        outcomes: list[ProfileModeOutcome],
        top_n: int = 3,
    ) -> list[RankedRecommendation]:
        """Rank outcomes and return top N recommendations.
        
        Args:
            outcomes: List of outcomes to rank
            top_n: Number of top recommendations to return
        
        Returns:
            List of ranked recommendations, sorted by score descending
        """
        scored = []
        for outcome in outcomes:
            score = self._calculate_score(outcome)
            confidence = self._calculate_confidence(outcome)
            reasons = self._generate_reason_codes(outcome)
            
            scored.append(
                RankedRecommendation(
                    profile=outcome.profile,
                    mode=outcome.mode,
                    score=round(score, 4),
                    confidence=round(confidence, 4),
                    reason_codes=reasons,
                )
            )
        
        # Sort by score descending
        scored.sort(key=lambda r: r.score, reverse=True)
        
        return scored[:top_n]


# Fallback chain constants for reference
FALLBACK_CHAIN = ["objective", "brand", "global", "default"]


def get_fallback_recommendation(
    scope: str,
    objective_key: Optional[str] = None,
) -> RankedRecommendation:
    """Get fallback recommendation when no data is available.
    
    Args:
        scope: Fallback scope (objective, brand, global, default)
        objective_key: Optional objective key for context
    
    Returns:
        Default recommendation with low confidence
    """
    return RankedRecommendation(
        profile="engagement",
        mode="balanced",
        score=0.5,
        confidence=0.3,
        reason_codes=[f"fallback_{scope}"],
    )
