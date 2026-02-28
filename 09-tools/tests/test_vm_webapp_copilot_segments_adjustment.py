"""Tests for v14 segmented copilot - adjustment cap and freeze logic."""

import pytest
from datetime import datetime, timezone
from vm_webapp.copilot_segments import (
    CopilotSegmentView,
    SegmentStatus,
    calculate_adjustment_factor,
    check_segment_regression,
    freeze_segment,
    SEGMENT_MINIMUM_RUNS_THRESHOLD,
)


class TestAdjustmentCap:
    """Test adjustment factor capping at ±15%."""

    def test_segment_adjustment_is_capped_at_15_percent(self):
        """Adjustment factor cannot exceed ±15%."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.85,  # Very high success
            segment_v1_score_avg=95.0,  # Very high score
            segment_regen_rate=0.1,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.0,
        )
        # Global averages are lower, so this would suggest a big adjustment
        adjustment = calculate_adjustment_factor(
            segment,
            global_success_rate=0.50,
            global_v1_score=70.0,
        )
        # Should be capped at +0.15 (15%)
        assert adjustment <= 0.15
        assert adjustment >= 0  # Positive adjustment for outperforming segment

    def test_adjustment_is_capped_at_negative_15_percent(self):
        """Adjustment factor cannot be less than -15%."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.20,  # Very low success
            segment_v1_score_avg=45.0,  # Very low score
            segment_regen_rate=0.6,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.0,
        )
        adjustment = calculate_adjustment_factor(
            segment,
            global_success_rate=0.60,
            global_v1_score=75.0,
        )
        # Should be capped at -0.15 (-15%)
        assert adjustment >= -0.15
        assert adjustment <= 0  # Negative adjustment for underperforming segment

    def test_adjustment_is_zero_for_ineligible_segment(self):
        """Ineligible segments get zero adjustment (fallback to v13 global)."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=10,  # Below threshold
            segment_success_24h_rate=0.50,
            segment_v1_score_avg=75.0,
            segment_regen_rate=0.3,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.INSUFFICIENT_VOLUME.value,
            adjustment_factor=0.0,
        )
        adjustment = calculate_adjustment_factor(
            segment,
            global_success_rate=0.50,
            global_v1_score=75.0,
        )
        assert adjustment == 0.0

    def test_adjustment_within_cap_is_calculated_correctly(self):
        """Adjustment within ±15% is calculated correctly."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.60,  # 10pp above global
            segment_v1_score_avg=80.0,  # 5 points above global
            segment_regen_rate=0.2,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.0,
        )
        adjustment = calculate_adjustment_factor(
            segment,
            global_success_rate=0.50,
            global_v1_score=75.0,
        )
        # (0.10 * 0.6) + (0.05 * 0.4) = 0.06 + 0.02 = 0.08
        assert 0.07 <= adjustment <= 0.09


class TestRegressionFreeze:
    """Test segment freeze after strong regression."""

    def test_segment_freezes_after_strong_7d_regression_success_rate(self):
        """Segment freezes after 7 days of >10pp success rate drop."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.35,  # 15pp drop from baseline
            segment_v1_score_avg=75.0,
            segment_regen_rate=0.5,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.05,
        )
        should_freeze = check_segment_regression(
            segment,
            baseline_success_rate=0.50,  # 15pp higher
            baseline_v1_score=75.0,
            days_of_regression=7,
        )
        assert should_freeze is True

    def test_segment_freezes_after_strong_7d_regression_v1_score(self):
        """Segment freezes after 7 days of >5 points V1 score drop."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.50,
            segment_v1_score_avg=65.0,  # 10 points drop from baseline
            segment_regen_rate=0.5,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.05,
        )
        should_freeze = check_segment_regression(
            segment,
            baseline_success_rate=0.50,
            baseline_v1_score=75.0,  # 10 points higher
            days_of_regression=7,
        )
        assert should_freeze is True

    def test_segment_does_not_freeze_before_7_days(self):
        """Segment doesn't freeze before 7 days of regression."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.30,  # Big drop
            segment_v1_score_avg=65.0,  # Big drop
            segment_regen_rate=0.5,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.05,
        )
        should_freeze = check_segment_regression(
            segment,
            baseline_success_rate=0.60,
            baseline_v1_score=80.0,
            days_of_regression=5,  # Only 5 days
        )
        assert should_freeze is False

    def test_segment_does_not_freeze_on_minor_regression(self):
        """Segment doesn't freeze on minor regression (<10pp, <5 points)."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.45,  # 5pp drop
            segment_v1_score_avg=72.0,  # 3 points drop
            segment_regen_rate=0.35,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.05,
        )
        should_freeze = check_segment_regression(
            segment,
            baseline_success_rate=0.50,
            baseline_v1_score=75.0,
            days_of_regression=7,
        )
        assert should_freeze is False


class TestFreezeFunction:
    """Test freeze_segment function."""

    def test_freeze_segment_returns_frozen_status(self):
        """freeze_segment returns segment with frozen status."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.40,
            segment_v1_score_avg=70.0,
            segment_regen_rate=0.4,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.05,
        )
        frozen = freeze_segment(segment)
        assert frozen.segment_status == SegmentStatus.FROZEN.value
        assert frozen.adjustment_factor == 0.0

    def test_frozen_segment_preserves_metrics(self):
        """freeze_segment preserves segment metrics."""
        now = datetime.now(timezone.utc).isoformat()
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.40,
            segment_v1_score_avg=70.0,
            segment_regen_rate=0.4,
            segment_last_updated_at=now,
            segment_status=SegmentStatus.ELIGIBLE.value,
            adjustment_factor=0.05,
        )
        frozen = freeze_segment(segment)
        assert frozen.segment_key == segment.segment_key
        assert frozen.segment_runs_total == segment.segment_runs_total
        assert frozen.segment_success_24h_rate == segment.segment_success_24h_rate
        assert frozen.segment_v1_score_avg == segment.segment_v1_score_avg
        assert frozen.segment_regen_rate == segment.segment_regen_rate
        assert frozen.segment_last_updated_at == segment.segment_last_updated_at


class TestFrozenSegmentFallback:
    """Test frozen segment fallback to v13 global."""

    def test_frozen_segment_falls_back_to_v13_global(self):
        """Frozen segment uses fallback (zero adjustment)."""
        frozen_segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.40,
            segment_v1_score_avg=70.0,
            segment_regen_rate=0.4,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.FROZEN.value,
            adjustment_factor=0.0,
        )
        # Even with different global values, frozen segment returns zero adjustment
        adjustment = calculate_adjustment_factor(
            frozen_segment,
            global_success_rate=0.60,
            global_v1_score=80.0,
        )
        assert adjustment == 0.0
