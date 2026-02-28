"""
Task A: Weekly KPI Scoreboard - Tests
Covers: API contract, delta calculations, empty scenarios
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch

from vm_webapp.kpi_scoreboard import (
    KpiTarget,
    KpiStatus,
    KpiWeeklyDelta,
    SegmentKpiSummary,
    calculate_kpi_status,
    calculate_delta_vs_target,
    aggregate_weekly_kpis,
    get_kpi_scoreboard,
)


class TestKpiTarget:
    """Test KPI target constants."""
    
    def test_approval_without_regen_target(self):
        """Target for approval_without_regen_24h is +5 p.p."""
        assert KpiTarget.APPROVAL_WITHOUT_REGEN_24H_DELTA == 0.05
    
    def test_v1_score_avg_target(self):
        """Target for V1 score avg is +6 points."""
        assert KpiTarget.V1_SCORE_AVG_DELTA == 6.0
    
    def test_regenerations_per_job_target(self):
        """Target for regenerations/job is -15%."""
        assert KpiTarget.REGENERATIONS_PER_JOB_DELTA == -0.15


class TestCalculateKpiStatus:
    """Test KPI status calculation based on delta vs target."""
    
    def test_on_track_positive_target(self):
        """For positive target, delta >= target is on_track."""
        # Target +5%, achieved +6% → on_track
        status = calculate_kpi_status(
            current=0.56,
            baseline=0.50,
            target_delta=0.05,
            tolerance=0.02
        )
        assert status == KpiStatus.ON_TRACK
    
    def test_attention_positive_target(self):
        """For positive target, within tolerance is attention."""
        # Target +5%, achieved +4% → attention (within 2% tolerance)
        status = calculate_kpi_status(
            current=0.54,
            baseline=0.50,
            target_delta=0.05,
            tolerance=0.02
        )
        assert status == KpiStatus.ATTENTION
    
    def test_off_track_positive_target(self):
        """For positive target, below tolerance is off_track."""
        # Target +5%, achieved +2% → off_track
        status = calculate_kpi_status(
            current=0.52,
            baseline=0.50,
            target_delta=0.05,
            tolerance=0.02
        )
        assert status == KpiStatus.OFF_TRACK
    
    def test_on_track_negative_target(self):
        """For negative target (reduction), delta <= target is on_track."""
        # Target -15%, achieved -16% → on_track
        status = calculate_kpi_status(
            current=0.84,
            baseline=1.00,
            target_delta=-0.15,
            tolerance=0.05
        )
        assert status == KpiStatus.ON_TRACK
    
    def test_off_track_negative_target(self):
        """For negative target, not enough reduction is off_track."""
        # Target -15%, achieved -5% → off_track
        status = calculate_kpi_status(
            current=0.95,
            baseline=1.00,
            target_delta=-0.15,
            tolerance=0.05
        )
        assert status == KpiStatus.OFF_TRACK
    
    def test_zero_baseline_handling(self):
        """Handle zero baseline gracefully."""
        status = calculate_kpi_status(
            current=0.10,
            baseline=0.0,
            target_delta=0.05,
            tolerance=0.02
        )
        assert status == KpiStatus.ON_TRACK  # Any improvement is good


class TestCalculateDeltaVsTarget:
    """Test delta calculation between current and baseline."""
    
    def test_positive_delta(self):
        """Calculate positive delta correctly."""
        delta = calculate_delta_vs_target(
            current=0.55,
            baseline=0.50,
            target_delta=0.05
        )
        assert delta.actual_delta == pytest.approx(0.05)
        assert delta.target_delta == pytest.approx(0.05)
        assert delta.gap_to_target == pytest.approx(0.0)
        assert delta.is_on_target is True
    
    def test_negative_delta(self):
        """Calculate negative delta (regression) correctly."""
        delta = calculate_delta_vs_target(
            current=0.45,
            baseline=0.50,
            target_delta=0.05
        )
        assert delta.actual_delta == pytest.approx(-0.05)
        assert delta.gap_to_target == pytest.approx(0.10)  # Need 10% more to reach target
        assert delta.is_on_target is False
    
    def test_reduction_metric_delta(self):
        """Calculate delta for metrics that should decrease."""
        delta = calculate_delta_vs_target(
            current=0.85,  # 15% reduction
            baseline=1.00,
            target_delta=-0.15
        )
        assert delta.actual_delta == pytest.approx(-0.15)
        assert delta.gap_to_target == pytest.approx(0.0)
        assert delta.is_on_target is True


class TestSegmentKpiSummary:
    """Test segment KPI summary data structure."""
    
    def test_summary_creation(self):
        """Can create a segment KPI summary."""
        summary = SegmentKpiSummary(
            segment_key="brand1:conversion",
            runs_count=150,
            approval_without_regen_24h=KpiWeeklyDelta(
                metric_name="approval_without_regen_24h",
                current_value=0.56,
                baseline_value=0.50,
                actual_delta=0.06,
                target_delta=0.05,
                gap_to_target=0.0,
                status=KpiStatus.ON_TRACK
            ),
            v1_score_avg=KpiWeeklyDelta(
                metric_name="v1_score_avg",
                current_value=82.0,
                baseline_value=76.0,
                actual_delta=6.0,
                target_delta=6.0,
                gap_to_target=0.0,
                status=KpiStatus.ON_TRACK
            ),
            regenerations_per_job=KpiWeeklyDelta(
                metric_name="regenerations_per_job",
                current_value=0.85,
                baseline_value=1.00,
                actual_delta=-0.15,
                target_delta=-0.15,
                gap_to_target=0.0,
                status=KpiStatus.ON_TRACK
            ),
            overall_status=KpiStatus.ON_TRACK
        )
        
        assert summary.segment_key == "brand1:conversion"
        assert summary.overall_status == KpiStatus.ON_TRACK


class TestAggregateWeeklyKpis:
    """Test aggregation of weekly KPIs."""
    
    def test_aggregate_single_segment(self):
        """Aggregate KPIs for a single segment."""
        segment_data = {
            "segment_key": "brand1:awareness",
            "runs_count": 100,
            "approval_without_regen_24h": 0.56,
            "v1_score_avg": 82.0,
            "regenerations_per_job": 0.85,
        }
        
        result = aggregate_weekly_kpis(
            segment_data_list=[segment_data],
            baseline_data={"brand1:awareness": {
                "approval_without_regen_24h": 0.50,
                "v1_score_avg": 76.0,
                "regenerations_per_job": 1.00,
            }}
        )
        
        assert len(result) == 1
        assert result[0].segment_key == "brand1:awareness"
        assert result[0].approval_without_regen_24h.status == KpiStatus.ON_TRACK
    
    def test_aggregate_multiple_segments(self):
        """Aggregate KPIs for multiple segments."""
        segments = [
            {
                "segment_key": "brand1:awareness",
                "runs_count": 100,
                "approval_without_regen_24h": 0.56,
                "v1_score_avg": 82.0,
                "regenerations_per_job": 0.85,
            },
            {
                "segment_key": "brand2:conversion",
                "runs_count": 80,
                "approval_without_regen_24h": 0.52,
                "v1_score_avg": 78.0,
                "regenerations_per_job": 0.95,
            }
        ]
        
        baseline = {
            "brand1:awareness": {
                "approval_without_regen_24h": 0.50,
                "v1_score_avg": 76.0,
                "regenerations_per_job": 1.00,
            },
            "brand2:conversion": {
                "approval_without_regen_24h": 0.50,
                "v1_score_avg": 76.0,
                "regenerations_per_job": 1.00,
            }
        }
        
        result = aggregate_weekly_kpis(segments, baseline)
        
        assert len(result) == 2
        # brand1 on track (52% vs 50% target +5% → +2% is within tolerance)
        # Actually +2% vs target +5% → gap -3% → off_track
        # brand2: 52% vs 50% baseline, target +5%, actual +2% → off_track (needs > 3%)
        assert result[0].overall_status == KpiStatus.ON_TRACK
        assert result[1].overall_status == KpiStatus.OFF_TRACK
    
    def test_missing_baseline_defaults(self):
        """Handle missing baseline with sensible defaults."""
        segment_data = [{
            "segment_key": "brand1:new_segment",
            "runs_count": 50,
            "approval_without_regen_24h": 0.50,
            "v1_score_avg": 76.0,
            "regenerations_per_job": 1.00,
        }]
        
        result = aggregate_weekly_kpis(segment_data, baseline_data={})
        
        assert len(result) == 1
        # Uses v13 baseline defaults
        assert result[0].approval_without_regen_24h.baseline_value == 0.50


class TestGetKpiScoreboard:
    """Test the main KPI scoreboard retrieval function."""
    
    @patch("vm_webapp.kpi_scoreboard._fetch_segment_metrics")
    @patch("vm_webapp.kpi_scoreboard._fetch_baseline_metrics")
    def test_get_scoreboard_returns_global_and_segments(
        self, mock_baseline, mock_metrics
    ):
        """Scoreboard includes global summary and segment details."""
        mock_metrics.return_value = [
            {
                "segment_key": "brand1:awareness",
                "runs_count": 100,
                "approval_without_regen_24h": 0.55,
                "v1_score_avg": 80.0,
                "regenerations_per_job": 0.90,
            }
        ]
        mock_baseline.return_value = {
            "brand1:awareness": {
                "approval_without_regen_24h": 0.50,
                "v1_score_avg": 76.0,
                "regenerations_per_job": 1.00,
            }
        }
        
        scoreboard = get_kpi_scoreboard(brand_id="brand1")
        
        assert "global" in scoreboard
        assert "segments" in scoreboard
        assert "week_ending" in scoreboard
        assert len(scoreboard["segments"]) == 1
    
    @patch("vm_webapp.kpi_scoreboard._fetch_segment_metrics")
    @patch("vm_webapp.kpi_scoreboard._fetch_baseline_metrics")
    def test_global_summary_aggregates_all_segments(
        self, mock_baseline, mock_metrics
    ):
        """Global summary is weighted average across segments."""
        mock_metrics.return_value = [
            {
                "segment_key": "brand1:awareness",
                "runs_count": 100,
                "approval_without_regen_24h": 0.56,
                "v1_score_avg": 82.0,
                "regenerations_per_job": 0.85,
            },
            {
                "segment_key": "brand1:conversion",
                "runs_count": 50,
                "approval_without_regen_24h": 0.52,
                "v1_score_avg": 78.0,
                "regenerations_per_job": 0.95,
            }
        ]
        mock_baseline.return_value = {
            "brand1:awareness": {
                "approval_without_regen_24h": 0.50,
                "v1_score_avg": 76.0,
                "regenerations_per_job": 1.00,
            },
            "brand1:conversion": {
                "approval_without_regen_24h": 0.50,
                "v1_score_avg": 76.0,
                "regenerations_per_job": 1.00,
            }
        }
        
        scoreboard = get_kpi_scoreboard()
        
        global_summary = scoreboard["global"]
        # Weighted: (100*0.56 + 50*0.52) / 150 = 0.547 → delta +4.7%
        assert global_summary.approval_without_regen_24h.current_value == pytest.approx(0.547, 0.01)
    
    @patch("vm_webapp.kpi_scoreboard._fetch_segment_metrics")
    @patch("vm_webapp.kpi_scoreboard._fetch_baseline_metrics")
    def test_empty_metrics_returns_empty_scoreboard(
        self, mock_baseline, mock_metrics
    ):
        """Empty metrics returns empty but valid scoreboard."""
        mock_metrics.return_value = []
        mock_baseline.return_value = {}
        
        scoreboard = get_kpi_scoreboard()
        
        assert scoreboard["segments"] == []
        assert scoreboard["global"] is None
        assert "week_ending" in scoreboard


class TestKpiScoreboardApiContract:
    """Test API response contract for KPI scoreboard endpoint."""
    
    def test_kpi_weekly_delta_serialization(self):
        """KpiWeeklyDelta serializes to expected JSON structure."""
        delta = KpiWeeklyDelta(
            metric_name="approval_without_regen_24h",
            current_value=0.56,
            baseline_value=0.50,
            actual_delta=0.06,
            target_delta=0.05,
            gap_to_target=0.0,
            status=KpiStatus.ON_TRACK
        )
        
        # Simulate JSON serialization
        import json
        from dataclasses import asdict
        
        data = asdict(delta)
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        
        assert parsed["metric_name"] == "approval_without_regen_24h"
        assert parsed["status"] == "on_track"
        assert parsed["current_value"] == 0.56
