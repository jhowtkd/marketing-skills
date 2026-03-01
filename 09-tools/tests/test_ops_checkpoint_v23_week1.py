"""
Tests for Operational Checkpoint v23 Week 1
"""

import pytest
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from ops_checkpoint_v23_week1 import (
    KPI,
    KPIStatus,
    OperationalCheckpoint,
)


class TestKPI:
    """Test KPI dataclass and status calculation."""
    
    def test_kpi_initialization(self):
        """KPI should initialize with correct values."""
        kpi = KPI(
            name="test_kpi",
            target=-35.0,
            target_direction="decrease",
            unit="minutes",
            formula="test formula",
        )
        
        assert kpi.name == "test_kpi"
        assert kpi.target == -35.0
        assert kpi.target_direction == "decrease"
        assert kpi.unit == "minutes"
        assert kpi.formula == "test formula"
        assert kpi.status == KPIStatus.NO_DATA
    
    def test_kpi_status_pass_decrease(self):
        """KPI should be PASS when target achieved for decrease."""
        kpi = KPI(
            name="test",
            target=-35.0,
            target_direction="decrease",
            baseline=100.0,
            actual=60.0,  # -40% decrease, better than -35%
        )
        
        status = kpi.calculate_status()
        
        assert status == KPIStatus.PASS
    
    def test_kpi_status_attention_decrease(self):
        """KPI should be ATTENTION when >=70% of target achieved."""
        kpi = KPI(
            name="test",
            target=-35.0,
            target_direction="decrease",
            baseline=100.0,
            actual=75.0,  # -25% decrease, better than 70% of target (-24.5%)
        )
        
        status = kpi.calculate_status()
        
        assert status == KPIStatus.ATTENTION
    
    def test_kpi_status_fail_decrease(self):
        """KPI should be FAIL when <70% of target achieved."""
        kpi = KPI(
            name="test",
            target=-35.0,
            target_direction="decrease",
            baseline=100.0,
            actual=90.0,  # -10% decrease, worse than 70% of target
        )
        
        status = kpi.calculate_status()
        
        assert status == KPIStatus.FAIL
    
    def test_kpi_status_pass_increase(self):
        """KPI should be PASS when target achieved for increase."""
        kpi = KPI(
            name="test",
            target=10.0,
            target_direction="increase",
            baseline=100.0,
            actual=120.0,  # +20% increase, better than +10%
        )
        
        status = kpi.calculate_status()
        
        assert status == KPIStatus.PASS
    
    def test_kpi_status_maintain(self):
        """KPI should handle maintain direction (incident rate)."""
        kpi = KPI(
            name="incident_rate",
            target=0.0,
            target_direction="maintain",
            baseline=5.0,
            actual=4.0,  # Improved, should PASS
        )
        
        status = kpi.calculate_status()
        
        assert status == KPIStatus.PASS
    
    def test_kpi_status_maintain_fail(self):
        """KPI should FAIL if incident rate increases."""
        kpi = KPI(
            name="incident_rate",
            target=0.0,
            target_direction="maintain",
            baseline=5.0,
            actual=6.0,  # Worsened, should FAIL
        )
        
        status = kpi.calculate_status()
        
        assert status == KPIStatus.FAIL
    
    def test_kpi_status_no_data(self):
        """KPI should be NO_DATA when actual is None."""
        kpi = KPI(
            name="test",
            target=-35.0,
            target_direction="decrease",
            baseline=100.0,
            actual=None,
        )
        
        status = kpi.calculate_status()
        
        assert status == KPIStatus.NO_DATA


class TestOperationalCheckpoint:
    """Test OperationalCheckpoint functionality."""
    
    def test_checkpoint_initialization(self):
        """Checkpoint should initialize with all required KPIs."""
        checkpoint = OperationalCheckpoint(window_days=7)
        
        assert checkpoint.version == "v23.0.0"
        assert checkpoint.window_days == 7
        assert len(checkpoint.kpis) == 10
        
        # Check required KPIs exist
        kpi_names = [k.name for k in checkpoint.kpis]
        required = [
            "approval_human_minutes_per_job",
            "approval_queue_length_p95",
            "incident_rate",
            "throughput_jobs_per_day",
            "approval_batches_created_total",
            "approval_batches_approved_total",
            "approval_batches_expanded_total",
            "approval_human_minutes_saved",
            "approval_queue_wait_seconds_avg",
            "approval_queue_wait_seconds_p95",
        ]
        
        for req in required:
            assert req in kpi_names
    
    def test_checkpoint_collects_metrics(self):
        """Checkpoint should collect metrics from system."""
        checkpoint = OperationalCheckpoint()
        
        metrics = checkpoint.collect_metrics()
        
        # Should return dict (may be empty if metrics not available)
        assert isinstance(metrics, dict)
    
    def test_checkpoint_updates_kpis(self):
        """Checkpoint should update KPIs with collected metrics."""
        checkpoint = OperationalCheckpoint()
        
        mock_metrics = {
            "batches_created_total": 10,
            "batches_approved_total": 8,
            "batches_expanded_total": 2,
            "human_minutes_saved": 120.0,
            "approval_queue_p95": 15,
        }
        
        checkpoint.update_kpis_with_metrics(mock_metrics)
        
        # Check specific KPIs were updated
        batches_kpi = next(k for k in checkpoint.kpis if k.name == "approval_batches_created_total")
        assert batches_kpi.actual == 10.0
        
        saved_kpi = next(k for k in checkpoint.kpis if k.name == "approval_human_minutes_saved")
        assert saved_kpi.actual == 120.0
    
    def test_get_top_bottlenecks(self):
        """Should identify bottlenecks from KPI status."""
        checkpoint = OperationalCheckpoint()
        
        # Set up failing KPIs
        for kpi in checkpoint.kpis:
            if kpi.name == "approval_queue_length_p95":
                kpi.actual = 50.0
                kpi.baseline = 30.0
                kpi.status = kpi.calculate_status()
        
        bottlenecks = checkpoint.get_top_bottlenecks()
        
        assert isinstance(bottlenecks, list)
        # Should identify queue length as bottleneck
        names = [b["name"] for b in bottlenecks]
        assert any("Fila" in n for n in names)
    
    def test_get_recommended_actions(self):
        """Should generate actions for non-PASS KPIs."""
        checkpoint = OperationalCheckpoint()
        
        # Set up a FAIL KPI
        for kpi in checkpoint.kpis:
            if kpi.name == "incident_rate":
                kpi.actual = 10.0
                kpi.baseline = 5.0
                kpi.status = KPIStatus.FAIL
        
        actions = checkpoint.get_recommended_actions()
        
        assert isinstance(actions, list)
        # Should have at least one P0 action
        priorities = [a["priority"] for a in actions]
        assert "P0" in priorities
    
    def test_get_operational_decision_contain(self):
        """Should return CONTAIN when there are FAILs."""
        checkpoint = OperationalCheckpoint()
        
        # Set up failing KPI
        for kpi in checkpoint.kpis:
            if kpi.name == "incident_rate":
                kpi.actual = 10.0
                kpi.baseline = 5.0
                kpi.status = KPIStatus.FAIL
        
        decision = checkpoint.get_operational_decision()
        
        assert "CONTER" in decision
    
    def test_get_operational_decision_maintain(self):
        """Should return MANTER when there are ATTENTIONs or NO_DATA."""
        checkpoint = OperationalCheckpoint()
        
        # Set up ATTENTION KPIs
        for kpi in checkpoint.kpis:
            kpi.status = KPIStatus.ATTENTION
        
        decision = checkpoint.get_operational_decision()
        
        assert "MANTER" in decision
    
    def test_get_operational_decision_expandir(self):
        """Should return EXPANDIR when all PASS."""
        checkpoint = OperationalCheckpoint()
        
        # Set all to PASS
        for kpi in checkpoint.kpis:
            kpi.actual = 100.0
            kpi.baseline = 150.0 if kpi.target_direction == "decrease" else 50.0
            kpi.status = KPIStatus.PASS
        
        decision = checkpoint.get_operational_decision()
        
        assert "EXPANDIR" in decision
    
    def test_generate_markdown_report(self):
        """Should generate valid Markdown report."""
        checkpoint = OperationalCheckpoint()
        
        # Set some mock data
        for kpi in checkpoint.kpis:
            kpi.actual = 100.0
            kpi.baseline = 150.0
            kpi.status = KPIStatus.PASS
        
        report = checkpoint.generate_markdown_report()
        
        assert "# Operational Checkpoint v23" in report
        assert "## 1. Resumo Executivo" in report
        assert "## 2. Tabela de KPIs" in report
        assert "## 3. Top Gargalos" in report
        assert "## 4. Causas Prováveis" in report
        assert "## 5. Ações Recomendadas" in report
        assert "## 6. Decisão Operacional" in report
    
    def test_generate_report_with_no_data(self):
        """Should handle NO_DATA gracefully in report."""
        checkpoint = OperationalCheckpoint()
        
        # Leave all as NO_DATA
        report = checkpoint.generate_markdown_report()
        
        assert "NO_DATA" in report or "❓" in report
        assert "MANTER" in report or "CONTER" in report


class TestMainFunction:
    """Test main entry point."""
    
    def test_script_runs_without_error(self, tmp_path):
        """Script should run without errors."""
        import subprocess
        import sys
        
        output_file = tmp_path / "test_report.md"
        
        result = subprocess.run(
            [
                sys.executable,
                "09-tools/scripts/ops_checkpoint_v23_week1.py",
                "--window-days", "7",
                "--output", str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd="/Users/jhonatan/Repos/marketing-skills",
        )
        
        assert result.returncode == 0
        assert output_file.exists()
    
    def test_json_output(self, tmp_path):
        """Script should support JSON output."""
        import subprocess
        import sys
        import json
        
        output_file = tmp_path / "test_report.json"
        
        result = subprocess.run(
            [
                sys.executable,
                "09-tools/scripts/ops_checkpoint_v23_week1.py",
                "--json",
                "--output", str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd="/Users/jhonatan/Repos/marketing-skills",
        )
        
        assert result.returncode == 0
        assert output_file.exists()
        
        # Verify valid JSON
        data = json.loads(output_file.read_text())
        assert "version" in data
        assert "kpis" in data
