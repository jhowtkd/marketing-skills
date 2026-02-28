"""v14 Segmented Copilot - eligibility, adjustment and freeze logic.

This module extends the v13 editorial copilot with segment-based personalization
using brand + objective_key granularity.
"""

from dataclasses import dataclass
from enum import Enum


# Type alias for segment key
SegmentKey = str


class SegmentStatus(str, Enum):
    """Segment status values."""
    ELIGIBLE = "eligible"
    INSUFFICIENT_VOLUME = "insufficient_volume"
    FROZEN = "frozen"
    FALLBACK = "fallback"

# Eligibility threshold: minimum 20 runs per segment
SEGMENT_MINIMUM_RUNS_THRESHOLD = 20


@dataclass
class CopilotSegmentView:
    """Read-model for copilot segment data.
    
    Aggregated metrics per segment (brand + objective_key).
    """
    segment_key: str
    segment_runs_total: int
    segment_success_24h_rate: float
    segment_v1_score_avg: float
    segment_regen_rate: float
    segment_last_updated_at: str
    segment_status: str  # One of SegmentStatus values
    adjustment_factor: float  # -0.15 to +0.15 cap


def build_segment_key(brand_id: str, objective_key: str) -> SegmentKey:
    """Build segment key from brand and objective.
    
    Args:
        brand_id: The brand identifier
        objective_key: The objective key (e.g., 'awareness', 'conversion')
    
    Returns:
        Segment key in format "brand_id:objective_key"
    """
    return f"{brand_id}:{objective_key}"


def check_segment_eligibility(segment: CopilotSegmentView) -> tuple[bool, str]:
    """Check if segment is eligible for personalized copilot suggestions.
    
    Eligibility rules:
    - Must have at least SEGMENT_MINIMUM_RUNS_THRESHOLD runs (20)
    - Must not be frozen due to regression
    
    Args:
        segment: The segment view with aggregated metrics
    
    Returns:
        Tuple of (is_eligible, status)
    """
    # If already frozen, maintain frozen status
    if segment.segment_status == SegmentStatus.FROZEN.value:
        return False, SegmentStatus.FROZEN.value
    
    # Check minimum runs threshold
    if segment.segment_runs_total < SEGMENT_MINIMUM_RUNS_THRESHOLD:
        return False, SegmentStatus.INSUFFICIENT_VOLUME.value
    
    return True, SegmentStatus.ELIGIBLE.value


def check_segment_regression(
    segment: CopilotSegmentView,
    baseline_success_rate: float,
    baseline_v1_score: float,
    days_of_regression: int,
) -> bool:
    """Check if segment shows strong regression over 7 days.
    
    Regression criteria:
    - Success rate dropped >10 percentage points OR
    - V1 score dropped >5 points
    
    Args:
        segment: The segment view
        baseline_success_rate: Historical success rate
        baseline_v1_score: Historical V1 score average
        days_of_regression: Number of days regression has persisted
    
    Returns:
        True if segment should be frozen
    """
    if days_of_regression < 7:
        return False
    
    success_rate_drop = baseline_success_rate - segment.segment_success_24h_rate
    v1_score_drop = baseline_v1_score - segment.segment_v1_score_avg
    
    # Strong regression: >10pp success rate drop OR >5 points V1 score drop
    return success_rate_drop > 0.10 or v1_score_drop > 5.0


def calculate_adjustment_factor(
    segment: CopilotSegmentView,
    global_success_rate: float,
    global_v1_score: float,
) -> float:
    """Calculate capped adjustment factor for segment.
    
    The adjustment factor is capped at ±15% to prevent overfitting.
    
    Args:
        segment: The segment view
        global_success_rate: Global success rate across all segments
        global_v1_score: Global V1 score average
    
    Returns:
        Adjustment factor between -0.15 and +0.15
    """
    if not check_segment_eligibility(segment)[0]:
        return 0.0
    
    # Calculate raw adjustment based on segment performance vs global
    success_adjustment = segment.segment_success_24h_rate - global_success_rate
    score_adjustment = (segment.segment_v1_score_avg - global_v1_score) / 100.0
    
    # Combine adjustments (weighted average)
    raw_adjustment = (success_adjustment * 0.6) + (score_adjustment * 0.4)
    
    # Apply cap of ±15%
    return max(-0.15, min(0.15, raw_adjustment))


def freeze_segment(segment: CopilotSegmentView) -> CopilotSegmentView:
    """Freeze a segment due to regression.
    
    Args:
        segment: The segment to freeze
    
    Returns:
        Updated segment with frozen status and zero adjustment
    """
    return CopilotSegmentView(
        segment_key=segment.segment_key,
        segment_runs_total=segment.segment_runs_total,
        segment_success_24h_rate=segment.segment_success_24h_rate,
        segment_v1_score_avg=segment.segment_v1_score_avg,
        segment_regen_rate=segment.segment_regen_rate,
        segment_last_updated_at=segment.segment_last_updated_at,
        segment_status=SegmentStatus.FROZEN.value,
        adjustment_factor=0.0,
    )
