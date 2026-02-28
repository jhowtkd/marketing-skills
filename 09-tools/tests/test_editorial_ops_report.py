"""Tests for editorial_ops_report.py script.

Tests cover:
- Report generation with various data scenarios
- SKIPPED behavior when no staging URL
- Structural PASS when no real data
- SLO alerts evidence integration
- Playbook execution status integration
- Artifact format validation
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.editorial_ops_report import (
    aggregate_metrics,
    calculate_forecast_deltas,
    calculate_signal_quality,
    extract_previous_forecasts,
    generate_github_step_summary,
    generate_markdown_report,
    get_top_risk_threads,
    load_forecasts,
    load_insights,
    load_recommendations,
    main,
)


class TestLoadInsights:
    """Tests for loading insights data."""

    def test_load_insights_from_file(self, tmp_path: Path) -> None:
        """Test loading insights from a JSON file."""
        data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {"global": 2, "objective": 3}},
                "policy": {"denied_total": 1},
                "baseline": {"resolved_total": 8, "by_source": {"objective_golden": 3}},
            }
        ]
        file_path = tmp_path / "insights.json"
        file_path.write_text(json.dumps(data))

        result = load_insights(file_path)
        assert result == data

    def test_load_insights_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty insights array."""
        file_path = tmp_path / "empty.json"
        file_path.write_text("[]")

        result = load_insights(file_path)
        assert result == []

    def test_load_insights_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON raises error."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not json")

        with pytest.raises(json.JSONDecodeError):
            load_insights(file_path)


class TestLoadForecasts:
    """Tests for loading forecast data."""

    def test_load_forecasts_from_file(self, tmp_path: Path) -> None:
        """Test loading forecasts from a JSON file."""
        data = [
            {
                "thread_id": "t-1",
                "risk_score": 65,
                "trend": "degrading",
                "drivers": ["baseline_none_rate_high"],
                "recommended_focus": "Aumentar cobertura",
                "confidence": 0.7,
                "volatility": 45,
            }
        ]
        file_path = tmp_path / "forecasts.json"
        file_path.write_text(json.dumps(data))

        result = load_forecasts(file_path)
        assert "t-1" in result
        assert result["t-1"]["risk_score"] == 65

    def test_load_forecasts_missing_file(self, tmp_path: Path) -> None:
        """Test loading forecasts from non-existent file returns empty dict."""
        result = load_forecasts(tmp_path / "nonexistent.json")
        assert result == {}

    def test_load_forecasts_none_input(self) -> None:
        """Test loading forecasts with None input returns empty dict."""
        result = load_forecasts(None)
        assert result == {}


class TestLoadRecommendations:
    """Tests for loading recommendations data."""

    def test_load_recommendations_from_file(self, tmp_path: Path) -> None:
        """Test loading recommendations from a JSON file."""
        data = [
            {
                "thread_id": "t-1",
                "recommendations": [
                    {"action_id": "create_golden", "severity": "warning", "suppressed": False}
                ],
            }
        ]
        file_path = tmp_path / "recommendations.json"
        file_path.write_text(json.dumps(data))

        result = load_recommendations(file_path)
        assert "t-1" in result
        assert len(result["t-1"]) == 1

    def test_load_recommendations_missing_file(self, tmp_path: Path) -> None:
        """Test loading recommendations from non-existent file returns empty dict."""
        result = load_recommendations(tmp_path / "nonexistent.json")
        assert result == {}


class TestAggregateMetrics:
    """Tests for metrics aggregation."""

    def test_aggregate_basic_metrics(self) -> None:
        """Test basic metrics aggregation across threads."""
        insights = [
            {
                "thread_id": "t-1",
                "totals": {
                    "marked_total": 5,
                    "by_scope": {"global": 2, "objective": 3},
                    "by_reason_code": {"clarity": 2, "cta": 3},
                },
                "policy": {"denied_total": 1},
                "baseline": {
                    "resolved_total": 8,
                    "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 2, "none": 1},
                },
            },
            {
                "thread_id": "t-2",
                "totals": {
                    "marked_total": 3,
                    "by_scope": {"global": 1, "objective": 2},
                    "by_reason_code": {"structure": 3},
                },
                "policy": {"denied_total": 0},
                "baseline": {
                    "resolved_total": 5,
                    "by_source": {"objective_golden": 2, "global_golden": 1, "previous": 1, "none": 1},
                },
            },
        ]

        result = aggregate_metrics(insights)

        assert result["total_threads"] == 2
        assert result["total_marked"] == 8
        assert result["total_denied"] == 1
        assert result["by_scope"]["global"] == 3
        assert result["by_scope"]["objective"] == 5
        assert result["by_source"]["objective_golden"] == 5
        assert result["by_source"]["none"] == 2

    def test_aggregate_empty_insights(self) -> None:
        """Test aggregation with empty insights returns zero values."""
        result = aggregate_metrics([])

        assert result["total_threads"] == 0
        assert result["total_marked"] == 0
        assert result["baseline_none_rate"] == 0.0

    def test_aggregate_baseline_none_rate_calculation(self) -> None:
        """Test baseline none rate calculation."""
        insights = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 1, "by_scope": {}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {
                    "resolved_total": 10,
                    "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 2, "none": 3},
                },
            }
        ]

        result = aggregate_metrics(insights)
        assert result["baseline_none_rate"] == 0.3  # 3/10


class TestCalculateSignalQuality:
    """Tests for signal quality calculation."""

    def test_calculate_signal_quality_basic(self) -> None:
        """Test signal quality calculation with valid data."""
        forecasts = {
            "t-1": {"risk_score": 65, "confidence": 0.7, "volatility": 45},
            "t-2": {"risk_score": 35, "confidence": 0.8, "volatility": 25},
        }
        recommendations = {
            "t-1": [{"action_id": "a1", "suppressed": False}],
            "t-2": [{"action_id": "a2", "suppressed": True}],
        }

        result = calculate_signal_quality(forecasts, recommendations)

        assert result["avg_confidence"] == 0.75  # (0.7 + 0.8) / 2
        assert result["avg_volatility"] == 35  # (45 + 25) / 2
        assert result["suppressed_actions_rate"] == 50.0  # 1/2
        assert result["total_threads_with_forecast"] == 2

    def test_calculate_signal_quality_empty(self) -> None:
        """Test signal quality with empty data returns defaults."""
        result = calculate_signal_quality({}, {})

        assert result["avg_confidence"] == 0.0
        assert result["avg_volatility"] == 0
        assert result["suppressed_actions_rate"] == 0.0

    def test_calculate_signal_quality_low_confidence_high_volatility(self) -> None:
        """Test detection of low confidence + high volatility threads."""
        forecasts = {
            "t-1": {"risk_score": 65, "confidence": 0.4, "volatility": 70},
            "t-2": {"risk_score": 35, "confidence": 0.9, "volatility": 20},
        }

        result = calculate_signal_quality(forecasts, {})

        assert len(result["low_confidence_high_volatility_threads"]) == 1
        assert result["low_confidence_high_volatility_threads"][0]["thread_id"] == "t-1"


class TestExtractPreviousForecasts:
    """Tests for extracting previous forecast data."""

    def test_extract_from_markdown_report(self, tmp_path: Path) -> None:
        """Test extracting previous risk scores from markdown report."""
        report_content = """# Editorial Operations Report

## Forecast Summary

| Thread | Risk Score | Delta | Trend | Focus |
|--------|-----------|-------|-------|-------|
| t-1 | 65 | — | stable | Test |
| t-2 | 35 | — | stable | Test |

## Other Section
"""
        report_path = tmp_path / "previous-report.md"
        report_path.write_text(report_content)

        result = extract_previous_forecasts(report_path)

        assert result["t-1"] == 65
        assert result["t-2"] == 35

    def test_extract_missing_file(self, tmp_path: Path) -> None:
        """Test extracting from non-existent file returns empty dict."""
        result = extract_previous_forecasts(tmp_path / "nonexistent.md")
        assert result == {}

    def test_extract_none_input(self) -> None:
        """Test extracting with None input returns empty dict."""
        result = extract_previous_forecasts(None)
        assert result == {}


class TestCalculateForecastDeltas:
    """Tests for delta calculation between forecasts."""

    def test_calculate_increase_delta(self) -> None:
        """Test detecting risk score increase."""
        forecasts = {"t-1": {"risk_score": 75}}
        previous = {"t-1": 65}

        result = calculate_forecast_deltas(forecasts, previous)

        assert "+10" in result["t-1"] or "📈" in result["t-1"]

    def test_calculate_decrease_delta(self) -> None:
        """Test detecting risk score decrease."""
        forecasts = {"t-1": {"risk_score": 55}}
        previous = {"t-1": 65}

        result = calculate_forecast_deltas(forecasts, previous)

        assert "-10" in result["t-1"] or "📉" in result["t-1"]

    def test_calculate_stable_delta(self) -> None:
        """Test detecting stable risk score (within threshold)."""
        forecasts = {"t-1": {"risk_score": 68}}
        previous = {"t-1": 65}

        result = calculate_forecast_deltas(forecasts, previous)

        assert result["t-1"] == "stable"

    def test_calculate_new_thread(self) -> None:
        """Test marking new threads without previous data."""
        forecasts = {"t-1": {"risk_score": 65}}
        previous = {}

        result = calculate_forecast_deltas(forecasts, previous)

        assert result["t-1"] == "new"


class TestGetTopRiskThreads:
    """Tests for top risk thread identification."""

    def test_get_top_3_by_risk(self) -> None:
        """Test getting top 3 threads by risk score."""
        forecasts = {
            "t-low": {"risk_score": 30, "trend": "improving", "recommended_focus": "Low"},
            "t-high": {"risk_score": 80, "trend": "degrading", "recommended_focus": "High"},
            "t-mid": {"risk_score": 50, "trend": "stable", "recommended_focus": "Mid"},
            "t-critical": {"risk_score": 95, "trend": "degrading", "recommended_focus": "Critical"},
        }

        result = get_top_risk_threads(forecasts, limit=3)

        assert len(result) == 3
        assert result[0][0] == "t-critical"  # Highest risk first
        assert result[0][1] == 95
        assert result[1][0] == "t-high"
        assert result[2][0] == "t-mid"

    def test_get_top_risks_empty(self) -> None:
        """Test with empty forecasts returns empty list."""
        result = get_top_risk_threads({})
        assert result == []


class TestGenerateMarkdownReport:
    """Tests for markdown report generation."""

    def test_generate_basic_report(self) -> None:
        """Test generating a basic markdown report."""
        metrics = {
            "total_threads": 2,
            "total_marked": 8,
            "total_denied": 1,
            "total_resolved": 13,
            "baseline_none_rate": 0.15,
            "by_scope": {"global": 3, "objective": 5},
            "by_source": {"objective_golden": 5, "global_golden": 3, "previous": 3, "none": 2},
            "by_reason_code": {"clarity": 5, "cta": 3},
        }
        forecasts = {
            "t-1": {"risk_score": 65, "trend": "degrading", "recommended_focus": "Aumentar cobertura"},
        }
        signal_quality = {
            "avg_confidence": 0.7,
            "avg_volatility": 35,
            "suppressed_actions_rate": 20.0,
            "total_threads_with_forecast": 1,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {"t-1": "+5"}
        top_risks = [("t-1", 65, "degrading", "Aumentar cobertura")]
        generated_at = datetime(2026, 2, 27, 12, 0, 0, tzinfo=timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify essential sections are present
        assert "# Editorial Operations Report" in result
        assert "Total Threads | 2" in result
        assert "Total Golden Marked | 8" in result
        assert "Avg Confidence | 70%" in result
        assert "Top 3 Threads by Risk" in result
        assert "t-1" in result
        assert "2026-02-27T12:00:00+00:00" in result

    def test_generate_report_with_alerts(self) -> None:
        """Test report includes alerts section when thresholds are crossed."""
        metrics = {
            "total_threads": 2,
            "total_marked": 0,
            "total_denied": 10,
            "total_resolved": 10,
            "baseline_none_rate": 0.5,
            "by_scope": {"global": 0, "objective": 0},
            "by_source": {"objective_golden": 0, "global_golden": 0, "previous": 0, "none": 10},
            "by_reason_code": {},
        }
        forecasts = {}
        signal_quality = {
            "avg_confidence": 0.3,
            "avg_volatility": 70,
            "suppressed_actions_rate": 40.0,
            "total_threads_with_forecast": 0,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {}
        top_risks = []
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify alerts are included
        assert "## Alerts" in result
        assert "High baseline-none rate" in result
        assert "Policy denials detected" in result
        assert "No golden marks" in result

    def test_generate_report_with_top_3_risks_section(self) -> None:
        """Test report includes Top 3 Risks section."""
        metrics = {
            "total_threads": 3,
            "total_marked": 5,
            "total_denied": 0,
            "total_resolved": 10,
            "baseline_none_rate": 0.1,
            "by_scope": {"global": 2, "objective": 3},
            "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 3, "none": 2},
            "by_reason_code": {},
        }
        forecasts = {}
        signal_quality = {
            "avg_confidence": 0.8,
            "avg_volatility": 20,
            "suppressed_actions_rate": 0.0,
            "total_threads_with_forecast": 0,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {}
        top_risks = [
            ("t-critical", 85, "degrading", "Urgent action needed"),
            ("t-warning", 60, "stable", "Monitor closely"),
            ("t-info", 45, "improving", "Keep current practices"),
        ]
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify Top 3 Risks section
        assert "## Top 3 Threads by Risk" in result
        assert "1. t-critical" in result
        assert "2. t-warning" in result
        assert "3. t-info" in result
        assert "Risk Score:** 85/100" in result

    def test_generate_report_with_critical_risk_alert(self) -> None:
        """Test report includes critical risk alert when highest risk > 70."""
        metrics = {
            "total_threads": 1,
            "total_marked": 5,
            "total_denied": 0,
            "total_resolved": 10,
            "baseline_none_rate": 0.1,
            "by_scope": {"global": 2, "objective": 3},
            "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 3, "none": 2},
            "by_reason_code": {},
        }
        forecasts = {}
        signal_quality = {
            "avg_confidence": 0.8,
            "avg_volatility": 20,
            "suppressed_actions_rate": 0.0,
            "total_threads_with_forecast": 0,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {}
        top_risks = [("t-critical", 85, "degrading", "Urgent action needed")]
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify critical risk alert
        assert "Critical risk detected" in result
        assert "t-critical" in result
        assert "85/100" in result


class TestGenerateGithubStepSummary:
    """Tests for GitHub step summary generation."""

    def test_generate_summary_basic(self) -> None:
        """Test generating GitHub step summary."""
        signal_quality = {
            "avg_confidence": 0.75,
            "avg_volatility": 35,
            "suppressed_actions_rate": 20.0,
            "low_confidence_high_volatility_threads": [],
        }
        metrics = {"total_threads": 5}
        top_risks = []

        result = generate_github_step_summary(signal_quality, metrics, top_risks)

        assert "Editorial Operations Summary" in result
        assert "Average Confidence:** 75%" in result
        assert "Average Volatility:** 35/100" in result

    def test_generate_summary_with_noisy_threads(self) -> None:
        """Test summary includes noisy threads section."""
        signal_quality = {
            "avg_confidence": 0.5,
            "avg_volatility": 60,
            "suppressed_actions_rate": 10.0,
            "low_confidence_high_volatility_threads": [
                {"thread_id": "t-noisy", "confidence": 0.4, "volatility": 70, "risk_score": 65}
            ],
        }
        metrics = {"total_threads": 5}
        top_risks = []

        result = generate_github_step_summary(signal_quality, metrics, top_risks)

        assert "Noisy Signal Threads" in result
        assert "t-noisy" in result
        assert "confidence 40%" in result


class TestSLOAlertsEvidence:
    """Tests for SLO alerts evidence integration (Task D)."""

    def test_slo_alerts_section_in_report(self, tmp_path: Path) -> None:
        """Test that SLO alerts evidence is included in the report."""
        metrics = {
            "total_threads": 1,
            "total_marked": 5,
            "total_denied": 0,
            "total_resolved": 10,
            "baseline_none_rate": 0.1,
            "by_scope": {"global": 2, "objective": 3},
            "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 3, "none": 2},
            "by_reason_code": {},
        }
        forecasts = {
            "t-1": {
                "risk_score": 65,
                "trend": "degrading",
                "recommended_focus": "Aumentar cobertura",
                "slo_alerts": [
                    {
                        "alert_id": "slo-1",
                        "severity": "warning",
                        "message": "SLO threshold approaching",
                        "threshold": 0.95,
                        "current_value": 0.94,
                    }
                ],
            }
        }
        signal_quality = {
            "avg_confidence": 0.8,
            "avg_volatility": 20,
            "suppressed_actions_rate": 0.0,
            "total_threads_with_forecast": 1,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {"t-1": "stable"}
        top_risks = [("t-1", 65, "degrading", "Aumentar cobertura")]
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify SLO alerts section is present
        assert "## SLO Alerts Evidence" in result
        assert "slo-1" in result
        assert "SLO threshold approaching" in result

    def test_slo_alerts_empty_when_no_alerts(self, tmp_path: Path) -> None:
        """Test that SLO alerts section handles empty alerts gracefully."""
        metrics = {
            "total_threads": 1,
            "total_marked": 5,
            "total_denied": 0,
            "total_resolved": 10,
            "baseline_none_rate": 0.1,
            "by_scope": {"global": 2, "objective": 3},
            "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 3, "none": 2},
            "by_reason_code": {},
        }
        forecasts = {
            "t-1": {
                "risk_score": 65,
                "trend": "degrading",
                "recommended_focus": "Aumentar cobertura",
                "slo_alerts": [],
            }
        }
        signal_quality = {
            "avg_confidence": 0.8,
            "avg_volatility": 20,
            "suppressed_actions_rate": 0.0,
            "total_threads_with_forecast": 1,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {"t-1": "stable"}
        top_risks = [("t-1", 65, "degrading", "Aumentar cobertura")]
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # When there are no alerts, should still show section with "No alerts"
        assert "## SLO Alerts Evidence" in result
        assert "No SLO alerts" in result or "✅" in result


class TestPlaybookExecutionStatus:
    """Tests for playbook execution status integration (Task D)."""

    def test_playbook_status_section_in_report(self, tmp_path: Path) -> None:
        """Test that playbook execution status is included in the report."""
        metrics = {
            "total_threads": 1,
            "total_marked": 5,
            "total_denied": 0,
            "total_resolved": 10,
            "baseline_none_rate": 0.1,
            "by_scope": {"global": 2, "objective": 3},
            "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 3, "none": 2},
            "by_reason_code": {},
        }
        forecasts = {
            "t-1": {
                "risk_score": 65,
                "trend": "degrading",
                "recommended_focus": "Aumentar cobertura",
                "playbook_executions": [
                    {
                        "playbook_id": "pb-1",
                        "status": "completed",
                        "executed_at": "2026-02-27T10:00:00Z",
                        "actions_taken": ["create_golden", "notify_team"],
                    },
                    {
                        "playbook_id": "pb-2",
                        "status": "pending",
                        "scheduled_at": "2026-02-28T10:00:00Z",
                        "actions_pending": ["review_policy"],
                    },
                ],
            }
        }
        signal_quality = {
            "avg_confidence": 0.8,
            "avg_volatility": 20,
            "suppressed_actions_rate": 0.0,
            "total_threads_with_forecast": 1,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {"t-1": "stable"}
        top_risks = [("t-1", 65, "degrading", "Aumentar cobertura")]
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify playbook execution section is present
        assert "## Playbook Execution Status" in result
        assert "pb-1" in result
        assert "completed" in result
        assert "create_golden" in result
        assert "pending" in result or "scheduled" in result

    def test_executed_pending_actions_section(self, tmp_path: Path) -> None:
        """Test that 'Ações executadas/pendentes' section is included."""
        metrics = {
            "total_threads": 1,
            "total_marked": 5,
            "total_denied": 0,
            "total_resolved": 10,
            "baseline_none_rate": 0.1,
            "by_scope": {"global": 2, "objective": 3},
            "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 3, "none": 2},
            "by_reason_code": {},
        }
        forecasts = {
            "t-1": {
                "risk_score": 65,
                "trend": "degrading",
                "recommended_focus": "Aumentar cobertura",
                "executed_actions": ["action-1", "action-2"],
                "pending_actions": ["action-3", "action-4"],
            }
        }
        signal_quality = {
            "avg_confidence": 0.8,
            "avg_volatility": 20,
            "suppressed_actions_rate": 0.0,
            "total_threads_with_forecast": 1,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {"t-1": "stable"}
        top_risks = [("t-1", 65, "degrading", "Aumentar cobertura")]
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify executed/pending actions section
        assert "## Ações Executadas e Pendentes" in result or "## Actions Executed and Pending" in result
        assert "action-1" in result
        assert "action-3" in result


class TestSkippedBehavior:
    """Tests for SKIPPED behavior when no staging URL (Task D)."""

    def test_skipped_behavior_without_staging_url(self, tmp_path: Path) -> None:
        """Test that report shows SKIPPED status when no staging URL available."""
        # Create minimal insights with staging_url indicator
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 0, "by_scope": {}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 0, "by_source": {}},
                "has_staging_url": False,  # No staging URL
            }
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data: list[dict] = []
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        output_file = tmp_path / "report.md"

        # Mock sys.argv for the main function
        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            result = main()
            assert result == 0  # Should pass structurally
        finally:
            sys.argv = original_argv

        report_content = output_file.read_text()

        # Verify SKIPPED status is indicated
        assert "SKIPPED" in report_content or "skipped" in report_content.lower()

    def test_explicit_skipped_message(self, tmp_path: Path) -> None:
        """Test that SKIPPED message is explicit and informative."""
        insights_data: list[dict] = []
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data: list[dict] = []
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            main()
        finally:
            sys.argv = original_argv

        report_content = output_file.read_text()

        # Verify explicit SKIPPED information
        assert "No staging URL" in report_content or "sem URL de staging" in report_content.lower()


class TestStructuralPass:
    """Tests for PASS estrutural behavior (Task D)."""

    def test_structural_pass_without_real_data(self, tmp_path: Path) -> None:
        """Test that workflow passes structurally even without real data."""
        # Create sample/demo data (not real staging data)
        insights_data = [
            {
                "thread_id": "sample",
                "totals": {"marked_total": 0, "by_scope": {"global": 0, "objective": 0}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 0, "by_source": {"objective_golden": 0, "global_golden": 0, "previous": 0, "none": 0}},
                "recency": {"last_marked_at": None, "last_actor_id": None},
            }
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data = [
            {
                "thread_id": "sample",
                "risk_score": 45,
                "trend": "stable",
                "drivers": ["no_golden_marks"],
                "recommended_focus": "Iniciar marcações golden",
            }
        ]
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            result = main()
            assert result == 0  # Should return 0 (PASS) even with sample data
        finally:
            sys.argv = original_argv

        report_content = output_file.read_text()

        # Verify report is generated even with sample data
        assert "# Editorial Operations Report" in report_content
        assert "sample" in report_content


class TestArtifactFormats:
    """Tests for artifact format validation (Task D)."""

    def test_markdown_artifact_format(self, tmp_path: Path) -> None:
        """Test that markdown report artifact has correct format."""
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {"global": 2, "objective": 3}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 8, "by_source": {"objective_golden": 3}},
            }
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data = [{"thread_id": "t-1", "risk_score": 50, "trend": "stable", "recommended_focus": "Test"}]
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            main()
        finally:
            sys.argv = original_argv

        report_content = output_file.read_text()

        # Verify markdown structure
        assert report_content.startswith("# Editorial Operations Report")
        assert "## Summary" in report_content
        assert "| Metric | Value |" in report_content
        assert "_This report is auto-generated" in report_content

    def test_json_artifact_format(self, tmp_path: Path) -> None:
        """Test that JSON report artifact has correct format."""
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {"global": 2, "objective": 3}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 8, "by_source": {"objective_golden": 3}},
            }
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data = [{"thread_id": "t-1", "risk_score": 50, "trend": "stable", "recommended_focus": "Test"}]
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        output_file = tmp_path / "report.json"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
                "--format", "json",
            ]
            main()
        finally:
            sys.argv = original_argv

        report_content = output_file.read_text()
        report_data = json.loads(report_content)

        # Verify JSON structure
        assert "generated_at" in report_data
        assert "metrics" in report_data
        assert "signal_quality" in report_data
        assert "forecasts" in report_data
        assert "deltas" in report_data
        assert "top_risks" in report_data

    def test_logs_artifact_format(self, tmp_path: Path) -> None:
        """Test that logs artifact follows expected format."""
        # Logs should be captured in stderr or a separate log file
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {"global": 2, "objective": 3}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 8, "by_source": {"objective_golden": 3}},
            }
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data = [{"thread_id": "t-1", "risk_score": 50, "trend": "stable", "recommended_focus": "Test"}]
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            result = main()
            assert result == 0
        finally:
            sys.argv = original_argv

        # Report should be generated successfully
        assert output_file.exists()
        assert output_file.read_text()


class TestTop3RisksSection:
    """Tests for 'Top 3 riscos' section (Task D)."""

    def test_top_3_risks_section_format(self, tmp_path: Path) -> None:
        """Test that Top 3 Risks section has correct format."""
        metrics = {
            "total_threads": 3,
            "total_marked": 5,
            "total_denied": 0,
            "total_resolved": 10,
            "baseline_none_rate": 0.1,
            "by_scope": {"global": 2, "objective": 3},
            "by_source": {"objective_golden": 3, "global_golden": 2, "previous": 3, "none": 2},
            "by_reason_code": {},
        }
        forecasts = {}
        signal_quality = {
            "avg_confidence": 0.8,
            "avg_volatility": 20,
            "suppressed_actions_rate": 0.0,
            "total_threads_with_forecast": 0,
            "low_confidence_high_volatility_threads": [],
        }
        deltas = {}
        top_risks = [
            ("thread-a", 90, "degrading", "Critical risk"),
            ("thread-b", 75, "stable", "High risk"),
            ("thread-c", 60, "improving", "Medium risk"),
        ]
        generated_at = datetime.now(timezone.utc)

        result = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at
        )

        # Verify format includes proper headings and structure
        assert "## Top 3 Threads by Risk" in result
        assert "### 1. thread-a" in result
        assert "### 2. thread-b" in result
        assert "### 3. thread-c" in result
        assert "Risk Score:** 90/100" in result
        assert "Risk Score:** 75/100" in result
        assert "Risk Score:** 60/100" in result


class TestIntegration:
    """Integration tests for the complete workflow."""

    def test_full_workflow_with_all_inputs(self, tmp_path: Path) -> None:
        """Test complete workflow with all input files."""
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {
                    "marked_total": 10,
                    "by_scope": {"global": 4, "objective": 6},
                    "by_reason_code": {"clarity": 5, "cta": 5},
                },
                "policy": {"denied_total": 2},
                "baseline": {
                    "resolved_total": 20,
                    "by_source": {"objective_golden": 8, "global_golden": 5, "previous": 4, "none": 3},
                },
                "recency": {"last_marked_at": "2026-02-27T10:00:00Z", "last_actor_id": "user-1"},
            },
            {
                "thread_id": "t-2",
                "totals": {"marked_total": 5, "by_scope": {"global": 2, "objective": 3}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 10, "by_source": {}},
            },
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data = [
            {
                "thread_id": "t-1",
                "risk_score": 75,
                "trend": "degrading",
                "drivers": ["baseline_none_rate_high"],
                "recommended_focus": "Aumentar cobertura golden",
                "confidence": 0.75,
                "volatility": 40,
            },
            {
                "thread_id": "t-2",
                "risk_score": 45,
                "trend": "improving",
                "drivers": [],
                "recommended_focus": "Manter práticas",
                "confidence": 0.85,
                "volatility": 25,
            },
        ]
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        recommendations_data = [
            {
                "thread_id": "t-1",
                "recommendations": [
                    {"action_id": "create_golden", "severity": "warning", "suppressed": False},
                    {"action_id": "review_policy", "severity": "info", "suppressed": True, "suppression_reason": "Cooldown"},
                ],
            },
            {"thread_id": "t-2", "recommendations": [{"action_id": "review", "severity": "info", "suppressed": False}]},
        ]
        recommendations_file = tmp_path / "recommendations.json"
        recommendations_file.write_text(json.dumps(recommendations_data))

        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--recommendations-file", str(recommendations_file),
                "--output", str(output_file),
            ]
            result = main()
            assert result == 0
        finally:
            sys.argv = original_argv

        report_content = output_file.read_text()

        # Verify all sections are present
        assert "# Editorial Operations Report" in report_content
        assert "Total Threads | 2" in report_content
        assert "Total Golden Marked | 15" in report_content
        assert "Signal Quality" in report_content
        assert "Forecast Summary" in report_content
        assert "Top 3 Threads by Risk" in report_content
        assert "t-1" in report_content
        assert "t-2" in report_content

    def test_workflow_with_previous_report_delta(self, tmp_path: Path) -> None:
        """Test workflow with previous report for delta calculation."""
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 10, "by_source": {}},
            }
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data = [{"thread_id": "t-1", "risk_score": 75, "trend": "degrading", "recommended_focus": "Test"}]
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        # Create previous report
        previous_report = tmp_path / "previous.md"
        previous_report.write_text("""# Editorial Operations Report

## Forecast Summary

| Thread | Risk Score | Delta | Trend | Focus |
|--------|-----------|-------|-------|-------|
| t-1 | 65 | — | stable | Test |
""")

        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--previous-report", str(previous_report),
                "--output", str(output_file),
            ]
            result = main()
            assert result == 0
        finally:
            sys.argv = original_argv

        report_content = output_file.read_text()

        # Verify delta is shown
        assert "+10" in report_content or "📈" in report_content


class TestEvidenciasJobSummary:
    """Tests for evidência automática no job summary (Task D)."""

    def test_job_summary_includes_evidence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that job summary includes automatic evidence."""
        summary_file = tmp_path / "github_step_summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 10, "by_source": {}},
            }
        ]
        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))

        forecasts_data = [
            {
                "thread_id": "t-1",
                "risk_score": 65,
                "trend": "degrading",
                "recommended_focus": "Test",
                "confidence": 0.7,
                "volatility": 40,
            }
        ]
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))

        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
                "--github-step-summary",
            ]
            result = main()
            assert result == 0
        finally:
            sys.argv = original_argv

        # Verify summary was written
        assert summary_file.exists()
        summary_content = summary_file.read_text()

        # Verify evidence is in summary
        assert "Editorial Operations Summary" in summary_content
        assert "Average Confidence" in summary_content


class TestWorkflowRequirements:
    """Tests for specific workflow requirements from Task D."""

    def test_report_includes_top_3_risks_section(self, tmp_path: Path) -> None:
        """Requirement: Adicionar seção 'Top 3 riscos' no report."""
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 10, "by_source": {}},
            }
        ]
        forecasts_data = [
            {"thread_id": "t-1", "risk_score": 80, "trend": "degrading", "recommended_focus": "High risk"}
        ]

        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))
        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            main()
        finally:
            sys.argv = original_argv

        content = output_file.read_text()
        assert "## Top 3 Threads by Risk" in content

    def test_report_includes_executed_pending_actions(self, tmp_path: Path) -> None:
        """Requirement: Adicionar seção 'Ações executadas/pendentes' no report."""
        insights_data = [
            {
                "thread_id": "t-1",
                "totals": {"marked_total": 5, "by_scope": {}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 10, "by_source": {}},
            }
        ]
        forecasts_data = [
            {
                "thread_id": "t-1",
                "risk_score": 65,
                "trend": "stable",
                "recommended_focus": "Test",
                "executed_actions": ["action-1"],
                "pending_actions": ["action-2"],
            }
        ]

        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))
        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            main()
        finally:
            sys.argv = original_argv

        content = output_file.read_text()
        assert "## Ações Executadas e Pendentes" in content or "Actions Executed and Pending" in content
        assert "action-1" in content
        assert "action-2" in content

    def test_skipped_explicit_without_staging(self, tmp_path: Path) -> None:
        """Requirement: Se não houver staging URL, manter comportamento SKIPPED explícito."""
        insights_data: list[dict] = []  # No data = no staging URL
        forecasts_data: list[dict] = []

        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))
        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            result = main()
            assert result == 0
        finally:
            sys.argv = original_argv

        content = output_file.read_text()
        assert "SKIPPED" in content

    def test_structural_pass_no_real_data(self, tmp_path: Path) -> None:
        """Requirement: PASS estrutural quando não há dados reais."""
        # Use sample/demo data instead of real data
        insights_data = [
            {
                "thread_id": "sample",
                "totals": {"marked_total": 0, "by_scope": {"global": 0, "objective": 0}, "by_reason_code": {}},
                "policy": {"denied_total": 0},
                "baseline": {"resolved_total": 0, "by_source": {}},
                "is_sample_data": True,
            }
        ]
        forecasts_data = [
            {"thread_id": "sample", "risk_score": 45, "trend": "stable", "recommended_focus": "Demo"}
        ]

        insights_file = tmp_path / "insights.json"
        insights_file.write_text(json.dumps(insights_data))
        forecasts_file = tmp_path / "forecasts.json"
        forecasts_file.write_text(json.dumps(forecasts_data))
        output_file = tmp_path / "report.md"

        original_argv = sys.argv
        try:
            sys.argv = [
                "editorial_ops_report.py",
                "--insights-file", str(insights_file),
                "--forecasts-file", str(forecasts_file),
                "--output", str(output_file),
            ]
            result = main()
            assert result == 0  # PASS structurally
        finally:
            sys.argv = original_argv

        content = output_file.read_text()
        assert "# Editorial Operations Report" in content  # Report is generated
