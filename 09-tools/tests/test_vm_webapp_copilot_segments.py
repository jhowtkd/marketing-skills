"""Tests for v14 segmented copilot - eligibility and read models."""

import pytest
from datetime import datetime, timezone
from vm_webapp.copilot_segments import (
    SegmentKey,
    SegmentStatus,
    CopilotSegmentView,
    check_segment_eligibility,
    build_segment_key,
    SEGMENT_MINIMUM_RUNS_THRESHOLD,
)


class TestSegmentKeyBuilding:
    """Test segment key construction."""

    def test_build_segment_key_with_brand_and_objective(self):
        """Segment key combines brand and objective."""
        key = build_segment_key(brand_id="brand_abc", objective_key="awareness")
        assert key == "brand_abc:awareness"

    def test_build_segment_key_with_empty_objective(self):
        """Segment key handles empty objective."""
        key = build_segment_key(brand_id="brand_abc", objective_key="")
        assert key == "brand_abc:"


class TestSegmentEligibility:
    """Test segment eligibility rules (minimum 20 runs)."""

    def test_segment_is_ineligible_below_20_runs(self):
        """Segment with <20 runs is ineligible (insufficient_volume)."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=19,
            segment_success_24h_rate=0.5,
            segment_v1_score_avg=75.0,
            segment_regen_rate=0.3,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.INSUFFICIENT_VOLUME,
            adjustment_factor=0.0,
        )
        is_eligible, status = check_segment_eligibility(segment)
        assert not is_eligible
        assert status == SegmentStatus.INSUFFICIENT_VOLUME

    def test_segment_becomes_eligible_at_20_runs(self):
        """Segment with >=20 runs is eligible."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=20,
            segment_success_24h_rate=0.5,
            segment_v1_score_avg=75.0,
            segment_regen_rate=0.3,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE,
            adjustment_factor=0.0,
        )
        is_eligible, status = check_segment_eligibility(segment)
        assert is_eligible
        assert status == SegmentStatus.ELIGIBLE

    def test_segment_eligible_at_100_runs(self):
        """Segment with high volume remains eligible."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=100,
            segment_success_24h_rate=0.6,
            segment_v1_score_avg=80.0,
            segment_regen_rate=0.2,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.ELIGIBLE,
            adjustment_factor=0.05,
        )
        is_eligible, status = check_segment_eligibility(segment)
        assert is_eligible
        assert status == SegmentStatus.ELIGIBLE

    def test_frozen_segment_is_not_eligible(self):
        """Frozen segment returns frozen status even with enough runs."""
        segment = CopilotSegmentView(
            segment_key="brand:test",
            segment_runs_total=50,
            segment_success_24h_rate=0.3,  # Low success
            segment_v1_score_avg=60.0,  # Low score
            segment_regen_rate=0.5,
            segment_last_updated_at=datetime.now(timezone.utc).isoformat(),
            segment_status=SegmentStatus.FROZEN,
            adjustment_factor=0.0,
        )
        is_eligible, status = check_segment_eligibility(segment)
        assert not is_eligible
        assert status == SegmentStatus.FROZEN

    def test_threshold_is_exactly_20(self):
        """Verify threshold constant is 20."""
        assert SEGMENT_MINIMUM_RUNS_THRESHOLD == 20


class TestSegmentViewModel:
    """Test CopilotSegmentView data structure."""

    def test_segment_view_creation(self):
        """Can create a segment view with all fields."""
        now = datetime.now(timezone.utc).isoformat()
        segment = CopilotSegmentView(
            segment_key="brand:conversion",
            segment_runs_total=25,
            segment_success_24h_rate=0.55,
            segment_v1_score_avg=78.0,
            segment_regen_rate=0.25,
            segment_last_updated_at=now,
            segment_status=SegmentStatus.ELIGIBLE,
            adjustment_factor=0.08,
        )
        assert segment.segment_key == "brand:conversion"
        assert segment.segment_runs_total == 25
        assert segment.adjustment_factor == 0.08

    def test_segment_view_default_adjustment(self):
        """Segment view can have zero adjustment."""
        now = datetime.now(timezone.utc).isoformat()
        segment = CopilotSegmentView(
            segment_key="brand:new",
            segment_runs_total=5,
            segment_success_24h_rate=0.0,
            segment_v1_score_avg=0.0,
            segment_regen_rate=0.0,
            segment_last_updated_at=now,
            segment_status=SegmentStatus.INSUFFICIENT_VOLUME,
            adjustment_factor=0.0,
        )
        assert segment.adjustment_factor == 0.0


class TestSegmentStatusEnum:
    """Test SegmentStatus values."""

    def test_eligible_status_exists(self):
        """ELIGIBLE status exists."""
        assert SegmentStatus.ELIGIBLE == "eligible"

    def test_insufficient_volume_status_exists(self):
        """INSUFFICIENT_VOLUME status exists."""
        assert SegmentStatus.INSUFFICIENT_VOLUME == "insufficient_volume"

    def test_frozen_status_exists(self):
        """FROZEN status exists."""
        assert SegmentStatus.FROZEN == "frozen"

    def test_fallback_status_exists(self):
        """FALLBACK status exists."""
        assert SegmentStatus.FALLBACK == "fallback"
