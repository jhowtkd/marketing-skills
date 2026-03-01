"""Tests for ops_checkpoint_v21_week1.py script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ops_checkpoint_v21_week1 import (
    KPIDefinition,
    KPIResult,
    Status,
    evaluate_kpi,
    identify_regressions,
    analyze_causes,
    recommend_actions,
    generate_checkpoint,
    KPI_DEFINITIONS,
)


class TestKPIDefinitions:
    """Test KPI definitions are correctly structured."""

    def test_all_kpis_defined(self):
        """All required KPIs should be defined."""
        required_kpis = [
            "approval_timeout_rate",
            "mean_decision_latency_medium_high",
            "incident_rate",
            "approval_without_regen_24h",
            "agent_plans_created_total",
            "agent_steps_autoexecuted_total",
            "agent_steps_waiting_approval_total",
            "agent_approval_timeout_total",
            "agent_response_time_seconds",
            "escalation_distribution",
        ]
        for kpi_id in required_kpis:
            assert kpi_id in KPI_DEFINITIONS, f"Missing KPI: {kpi_id}"

    def test_kpi_has_required_fields(self):
        """Each KPI should have required fields."""
        for kpi_id, kpi_def in KPI_DEFINITIONS.items():
            assert kpi_def.name, f"{kpi_id} missing name"
            assert kpi_def.description, f"{kpi_id} missing description"
            assert kpi_def.formula, f"{kpi_id} missing formula"
            assert kpi_def.unit, f"{kpi_id} missing unit"
            assert kpi_def.target_direction in [
                "decrease", "increase", "maintain", "informational"
            ], f"{kpi_id} invalid target_direction"


class TestEvaluateKPI:
    """Test KPI evaluation logic."""

    def test_pass_when_target_achieved_decrease(self):
        """PASS when reduction target is met or exceeded."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=-30.0,
            target_direction="decrease",
            unit="%",
            formula="test",
        )
        result = evaluate_kpi(kpi, 5.0, 10.0)  # -50% reduction
        assert result.status == Status.PASS
        assert result.progress_pct == 100.0

    def test_attention_when_progress_70_99_percent(self):
        """ATTENTION when progress is between 70-99%."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=-30.0,
            target_direction="decrease",
            unit="%",
            formula="test",
        )
        # For exactly 70% progress with target -30%: need -21% change
        # -21% change: current = 79 when previous = 100
        result = evaluate_kpi(kpi, 79.0, 100.0)  # -21% reduction, 70% of target
        assert result.status == Status.ATTENTION
        assert result.progress_pct == 70.0

    def test_fail_when_progress_below_70_percent(self):
        """FAIL when progress is below 70%."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=-30.0,
            target_direction="decrease",
            unit="%",
            formula="test",
        )
        result = evaluate_kpi(kpi, 8.5, 10.0)  # -15% reduction, 50% of target
        assert result.status == Status.FAIL

    def test_pass_when_target_achieved_increase(self):
        """PASS when increase target is met."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=2.0,
            target_direction="increase",
            unit="p.p.",
            formula="test",
        )
        result = evaluate_kpi(kpi, 2.5, 0.5)  # +2pp increase
        assert result.status == Status.PASS

    def test_fail_when_increase_not_met(self):
        """FAIL when increase target is not met."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=2.0,
            target_direction="increase",
            unit="p.p.",
            formula="test",
        )
        # To get +0.5 change when target is +2.0 (25% progress):
        # With a large baseline, a small absolute change is a small % change
        # If baseline is 100, then 100 -> 101 is only 1% increase
        # For +0.5pp with 25% progress: we need change_pct = 0.5
        # change_pct = ((current - prev) / prev) * 100 = 0.5
        # (current - prev) / prev = 0.005
        # current = prev * 1.005
        # If prev = 100, current = 100.5
        result = evaluate_kpi(kpi, 100.5, 100.0)  # +0.5% increase, 25% of target
        assert result.status == Status.FAIL
        assert result.progress_pct == 25.0

    def test_incident_rate_always_fail_if_increased(self):
        """Incident rate should FAIL if it increased, regardless of amount."""
        kpi = KPI_DEFINITIONS["incident_rate"]
        result = evaluate_kpi(kpi, 0.6, 0.5)  # +20% increase
        assert result.status == Status.FAIL
        assert "Incident rate aumentou" in result.notes

    def test_maintain_target_pass_if_no_change(self):
        """PASS if value maintained (no increase)."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=0.0,
            target_direction="maintain",
            unit="%",
            formula="test",
        )
        result = evaluate_kpi(kpi, 5.0, 5.0)  # No change
        assert result.status == Status.PASS

    def test_maintain_target_fail_if_increased(self):
        """FAIL if value increased when target is maintain."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=0.0,
            target_direction="maintain",
            unit="%",
            formula="test",
        )
        result = evaluate_kpi(kpi, 5.5, 5.0)  # Increased
        assert result.status == Status.FAIL

    def test_insufficient_data_when_no_current_value(self):
        """INSUFFICIENT_DATA when current value is None."""
        kpi = KPI_DEFINITIONS["approval_timeout_rate"]
        result = evaluate_kpi(kpi, None, 10.0)
        assert result.status == Status.INSUFFICIENT_DATA

    def test_informational_kpi_always_pass(self):
        """Informational KPIs should always PASS."""
        kpi = KPIDefinition(
            name="Test",
            description="Test KPI",
            target_value=0.0,
            target_direction="informational",
            unit="count",
            formula="test",
        )
        result = evaluate_kpi(kpi, 100.0, None)
        assert result.status == Status.PASS


class TestIdentifyRegressions:
    """Test regression identification."""

    def test_identifies_fail_status_as_regression(self):
        """FAIL status should be identified as regression."""
        kpi_def = KPI_DEFINITIONS["approval_timeout_rate"]
        results = [
            KPIResult(
                definition=kpi_def,
                current_value=8.0,
                previous_value=10.0,
                change_pct=-20.0,
                status=Status.FAIL,
                progress_pct=50.0,
            )
        ]
        regressions = identify_regressions(results)
        assert len(regressions) == 1
        assert regressions[0]["severity"] == "HIGH"

    def test_identifies_attention_status_as_regression(self):
        """ATTENTION status should be identified as medium regression."""
        kpi_def = KPI_DEFINITIONS["approval_timeout_rate"]
        results = [
            KPIResult(
                definition=kpi_def,
                current_value=7.5,
                previous_value=10.0,
                change_pct=-25.0,
                status=Status.ATTENTION,
                progress_pct=83.0,
            )
        ]
        regressions = identify_regressions(results)
        assert len(regressions) == 1
        assert regressions[0]["severity"] == "MEDIUM"

    def test_incident_rate_is_critical(self):
        """Incident rate regression should be marked CRITICAL."""
        kpi_def = KPI_DEFINITIONS["incident_rate"]
        results = [
            KPIResult(
                definition=kpi_def,
                current_value=0.8,
                previous_value=0.5,
                change_pct=60.0,
                status=Status.FAIL,
                progress_pct=0.0,
            )
        ]
        regressions = identify_regressions(results)
        assert regressions[0]["severity"] == "CRITICAL"

    def test_no_regressions_when_all_pass(self):
        """No regressions when all KPIs PASS."""
        kpi_def = KPI_DEFINITIONS["approval_timeout_rate"]
        results = [
            KPIResult(
                definition=kpi_def,
                current_value=5.0,
                previous_value=10.0,
                change_pct=-50.0,
                status=Status.PASS,
                progress_pct=100.0,
            )
        ]
        regressions = identify_regressions(results)
        assert len(regressions) == 0


class TestAnalyzeCauses:
    """Test cause analysis."""

    def test_analyzes_timeout_rate_cause(self):
        """Should identify cause for timeout rate regression."""
        regressions = [{"kpi": "Approval Timeout Rate", "severity": "HIGH"}]
        causes = analyze_causes(regressions)
        assert any("timeout rate elevado" in c.lower() for c in causes)

    def test_analyzes_latency_cause(self):
        """Should identify cause for latency regression."""
        regressions = [{"kpi": "Mean Decision Latency (Medium/High)", "severity": "MEDIUM"}]
        causes = analyze_causes(regressions)
        assert any("latência" in c.lower() for c in causes)

    def test_analyzes_incident_cause(self):
        """Should identify cause for incident rate regression."""
        regressions = [{"kpi": "Incident Rate", "severity": "CRITICAL"}]
        causes = analyze_causes(regressions)
        assert any("incidentes" in c.lower() for c in causes)

    def test_empty_causes_when_no_regressions(self):
        """No causes when no regressions."""
        causes = analyze_causes([])
        assert len(causes) == 0


class TestRecommendActions:
    """Test action recommendations."""

    def test_p0_action_for_incident_rate(self):
        """Should recommend P0 action for incident rate."""
        regressions = [{"kpi": "Incident Rate", "severity": "CRITICAL"}]
        actions = recommend_actions(regressions, ["cause"])
        p0_actions = [a for a in actions if a["priority"] == "P0"]
        assert len(p0_actions) > 0
        assert any("incident" in a["action"].lower() for a in p0_actions)

    def test_p0_action_for_critical_timeout(self):
        """Should recommend P0 action for critical timeout rate."""
        regressions = [{"kpi": "Approval Timeout Rate", "severity": "CRITICAL"}]
        actions = recommend_actions(regressions, ["cause"])
        p0_actions = [a for a in actions if a["priority"] == "P0"]
        assert len(p0_actions) > 0

    def test_p1_action_for_latency(self):
        """Should recommend P1 action for latency."""
        regressions = [{"kpi": "Mean Decision Latency (Medium/High)", "severity": "MEDIUM"}]
        actions = recommend_actions(regressions, ["cause"])
        p1_actions = [a for a in actions if a["priority"] == "P1"]
        assert any("latência" in a["action"].lower() or "prompt" in a["action"].lower() for a in p1_actions)

    def test_always_has_p2_actions(self):
        """Should always have some P2 improvement actions."""
        actions = recommend_actions([], [])
        p2_actions = [a for a in actions if a["priority"] == "P2"]
        assert len(p2_actions) >= 1

    def test_action_has_required_fields(self):
        """Each action should have priority, action, owner, eta."""
        regressions = [{"kpi": "Incident Rate", "severity": "CRITICAL"}]
        actions = recommend_actions(regressions, ["cause"])
        for action in actions:
            assert "priority" in action
            assert "action" in action
            assert "owner" in action
            assert "eta" in action


class TestGenerateCheckpoint:
    """Test checkpoint generation."""

    def test_checkpoint_has_required_fields(self):
        """Generated checkpoint should have all required fields."""
        checkpoint = generate_checkpoint(window_days=7)
        assert checkpoint.window_days == 7
        assert checkpoint.generated_at is not None
        assert checkpoint.kpi_results is not None
        assert checkpoint.top_regressions is not None
        assert checkpoint.probable_causes is not None
        assert checkpoint.recommended_actions is not None

    def test_insufficient_data_flag(self):
        """Should mark data as insufficient when no data source."""
        checkpoint = generate_checkpoint(window_days=7)
        assert not checkpoint.data_sufficient

    def test_all_kpis_evaluated(self):
        """All KPIs should be evaluated."""
        checkpoint = generate_checkpoint(window_days=7)
        evaluated_names = {r.definition.name for r in checkpoint.kpi_results}
        defined_names = {d.name for d in KPI_DEFINITIONS.values()}
        assert evaluated_names == defined_names


class TestCLI:
    """Test command-line interface."""

    def test_script_runs_without_errors(self):
        """Script should execute without errors."""
        script_path = Path(__file__).parent.parent / "scripts" / "ops_checkpoint_v21_week1.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--window-days", "7", "--format", "json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_json_output_format(self):
        """JSON output should be valid."""
        script_path = Path(__file__).parent.parent / "scripts" / "ops_checkpoint_v21_week1.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--window-days", "7", "--format", "json"],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        assert "window_days" in data
        assert "generated_at" in data
        assert "kpis" in data

    def test_markdown_output_format(self):
        """Markdown output should contain expected sections."""
        script_path = Path(__file__).parent.parent / "scripts" / "ops_checkpoint_v21_week1.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--window-days", "7", "--format", "markdown"],
            capture_output=True,
            text=True,
        )
        output = result.stdout
        assert "# Operational Checkpoint v21" in output
        assert "## KPIs vs Metas" in output
        assert "## Top Regressões" in output
        assert "## Causas Prováveis" in output
        assert "## Ações Recomendadas" in output

    def test_mock_data_flag(self):
        """Mock data flag should work."""
        script_path = Path(__file__).parent.parent / "scripts" / "ops_checkpoint_v21_week1.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--use-mock-data", "--format", "json"],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        assert data["data_sufficient"] is True

    def test_output_file_written(self, tmp_path):
        """Output file should be written when specified."""
        script_path = Path(__file__).parent.parent / "scripts" / "ops_checkpoint_v21_week1.py"
        output_file = tmp_path / "test_report.md"
        result = subprocess.run(
            [sys.executable, str(script_path), "--output", str(output_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Operational Checkpoint v21" in content


class TestStatusEnum:
    """Test Status enum values."""

    def test_status_values(self):
        """Status enum should have expected values."""
        assert Status.PASS.value == "PASS"
        assert Status.ATTENTION.value == "ATTENTION"
        assert Status.FAIL.value == "FAIL"
        assert Status.INSUFFICIENT_DATA.value == "INSUFFICIENT_DATA"
