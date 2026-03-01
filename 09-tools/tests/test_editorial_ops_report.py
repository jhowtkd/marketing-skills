"""Tests for v26 Editorial Ops Report - Online Control Loop section.

TDD approach: tests for nightly report including control loop section.
"""

import pytest
from datetime import datetime, timezone

from vm_webapp.nightly_report_v18 import generate_nightly_report


class TestNightlyReportV26Section:
    """Test v26 Online Control Loop section in nightly report."""
    
    def test_report_includes_v26_section(self):
        """Nightly report should include v26 Online Control Loop section."""
        report = generate_nightly_report()
        
        assert "online_control_loop_v26" in report
    
    def test_v26_section_structure(self):
        """v26 section should have correct structure."""
        report = generate_nightly_report()
        v26 = report["online_control_loop_v26"]
        
        assert "version" in v26
        assert v26["version"] == "v26"
        assert "summary" in v26
        assert "regressions" in v26
        assert "mitigations" in v26
        assert "rollbacks" in v26
        assert "performance" in v26
        assert "clamp_status" in v26
        assert "goals_progress" in v26
    
    def test_v26_summary_fields(self):
        """v26 summary should have correct fields."""
        report = generate_nightly_report()
        summary = report["online_control_loop_v26"]["summary"]
        
        assert "cycles_total" in summary
        assert "cycles_active" in summary
        assert "brands_frozen" in summary
        assert isinstance(summary["cycles_total"], int)
        assert isinstance(summary["cycles_active"], int)
        assert isinstance(summary["brands_frozen"], int)
    
    def test_v26_regressions_fields(self):
        """v26 regressions should have correct fields."""
        report = generate_nightly_report()
        regressions = report["online_control_loop_v26"]["regressions"]
        
        assert "detected_total" in regressions
        assert "by_severity" in regressions
        assert "by_metric" in regressions
        
        by_severity = regressions["by_severity"]
        assert "low" in by_severity
        assert "medium" in by_severity
        assert "high" in by_severity
        assert "critical" in by_severity
        
        by_metric = regressions["by_metric"]
        assert "v1_score" in by_metric
        assert "approval_rate" in by_metric
        assert "incident_rate" in by_metric
    
    def test_v26_mitigations_fields(self):
        """v26 mitigations should have correct fields."""
        report = generate_nightly_report()
        mitigations = report["online_control_loop_v26"]["mitigations"]
        
        assert "applied_total" in mitigations
        assert "blocked_total" in mitigations
        assert "by_severity" in mitigations
    
    def test_v26_performance_fields(self):
        """v26 performance should have time-based metrics."""
        report = generate_nightly_report()
        performance = report["online_control_loop_v26"]["performance"]
        
        assert "time_to_detect_avg_seconds" in performance
        assert "time_to_mitigate_avg_seconds" in performance
        assert "target_time_to_detect_seconds" in performance
        assert "target_time_to_mitigate_seconds" in performance
        assert "time_to_detect_improvement" in performance
        assert "time_to_mitigate_improvement" in performance
    
    def test_v26_clamp_status_fields(self):
        """v26 clamp status should have correct fields."""
        report = generate_nightly_report()
        clamp = report["online_control_loop_v26"]["clamp_status"]
        
        assert "per_cycle_limit" in clamp
        assert "weekly_limit" in clamp
        assert "current_weekly_usage_avg" in clamp
        assert "brands_near_limit" in clamp
    
    def test_v26_goals_progress_fields(self):
        """v26 goals progress should track all KPIs."""
        report = generate_nightly_report()
        goals = report["online_control_loop_v26"]["goals_progress"]
        
        assert "time_to_detect_regression" in goals
        assert "time_to_mitigate" in goals
        assert "approval_without_regen_24h" in goals
        assert "incident_rate" in goals
        
        # Check goal structure
        for goal_name, goal in goals.items():
            assert "status" in goal
    
    def test_v26_time_to_detect_goal(self):
        """v26 should track time_to_detect_regression goal."""
        report = generate_nightly_report()
        goal = report["online_control_loop_v26"]["goals_progress"]["time_to_detect_regression"]
        
        assert "target" in goal
        assert "current" in goal
        assert goal["target"] == "-50%"
        assert goal["status"] in ["achieved", "on_track", "at_risk"]
    
    def test_v26_time_to_mitigate_goal(self):
        """v26 should track time_to_mitigate goal."""
        report = generate_nightly_report()
        goal = report["online_control_loop_v26"]["goals_progress"]["time_to_mitigate"]
        
        assert "target" in goal
        assert "current" in goal
        assert goal["target"] == "-40%"
    
    def test_v26_approval_rate_goal(self):
        """v26 should track approval_without_regen_24h goal."""
        report = generate_nightly_report()
        goal = report["online_control_loop_v26"]["goals_progress"]["approval_without_regen_24h"]
        
        assert "target_pp" in goal
        assert "current_pp" in goal
        assert goal["target_pp"] == 2.0
    
    def test_v26_incident_rate_goal(self):
        """v26 should track incident_rate goal."""
        report = generate_nightly_report()
        goal = report["online_control_loop_v26"]["goals_progress"]["incident_rate"]
        
        assert "target" in goal
        assert "current" in goal
        assert goal["target"] == "no_increase"
    
    def test_report_version(self):
        """Report should have correct version."""
        report = generate_nightly_report()
        
        assert "report_version" in report
        assert report["report_version"] == "v18.0.0"
    
    def test_report_has_timestamps(self):
        """Report should have generation timestamp."""
        report = generate_nightly_report()
        
        assert "generated_at" in report
        assert "report_date" in report
    
    def test_report_sections_exist(self):
        """Report should have all expected sections."""
        report = generate_nightly_report()
        
        assert "summary" in report
        assert "multibrand_governance" in report
        assert "online_control_loop_v26" in report
        assert "quality_optimizer_v25" in report
        assert "approval_learning_impact" in report


class TestNightlyReportIntegration:
    """Test nightly report integration with metrics."""
    
    def test_v26_cycles_matches_performance(self):
        """v26 cycles should be consistent with performance metrics."""
        report = generate_nightly_report()
        v26 = report["online_control_loop_v26"]
        
        # 4-hour cycles in 24h = 6 cycles
        assert v26["summary"]["cycles_total"] == 6
    
    def test_v26_mitigations_less_than_regressions(self):
        """Applied mitigations should be <= detected regressions."""
        report = generate_nightly_report()
        v26 = report["online_control_loop_v26"]
        
        assert v26["mitigations"]["applied_total"] <= v26["regressions"]["detected_total"]
    
    def test_v26_severity_counts_consistent(self):
        """Severity counts should be consistent."""
        report = generate_nightly_report()
        v26 = report["online_control_loop_v26"]
        
        by_severity = v26["regressions"]["by_severity"]
        total_by_severity = sum(by_severity.values())
        
        assert total_by_severity == v26["regressions"]["detected_total"]
