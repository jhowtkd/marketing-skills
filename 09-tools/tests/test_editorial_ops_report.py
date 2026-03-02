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


# =============================================================================
# v27: Predictive Resilience Section Tests
# =============================================================================

class TestNightlyReportV27Section:
    """Test v27 Predictive Resilience section in nightly report."""
    
    def test_report_includes_v27_section(self):
        """Nightly report should include v27 Predictive Resilience section."""
        report = generate_nightly_report()
        
        assert "predictive_resilience_v27" in report
    
    def test_v27_section_structure(self):
        """v27 section should have correct structure."""
        report = generate_nightly_report()
        v27 = report["predictive_resilience_v27"]
        
        assert "version" in v27
        assert v27["version"] == "v27"
        assert "summary" in v27
        assert "resilience_score" in v27
        assert "risk_distribution" in v27
        assert "mitigations" in v27
        assert "rollbacks" in v27
        assert "performance" in v27
        assert "false_positive_tracking" in v27
        assert "goals_progress" in v27
    
    def test_v27_summary_fields(self):
        """v27 summary should have correct fields."""
        report = generate_nightly_report()
        summary = report["predictive_resilience_v27"]["summary"]
        
        assert "cycles_total" in summary
        assert "cycles_active" in summary
        assert "brands_frozen" in summary
        assert "alerts_generated" in summary
        assert "false_positives" in summary
        assert isinstance(summary["cycles_total"], int)
        assert isinstance(summary["alerts_generated"], int)
    
    def test_v27_resilience_score_fields(self):
        """v27 resilience score should have component breakdown."""
        report = generate_nightly_report()
        score = report["predictive_resilience_v27"]["resilience_score"]
        
        assert "composite_avg" in score
        assert "composite_min" in score
        assert "composite_max" in score
        assert "by_component" in score
        
        components = score["by_component"]
        assert "incident" in components
        assert "handoff" in components
        assert "approval" in components
    
    def test_v27_risk_distribution_fields(self):
        """v27 risk distribution should have all levels."""
        report = generate_nightly_report()
        risk = report["predictive_resilience_v27"]["risk_distribution"]
        
        assert "low" in risk
        assert "medium" in risk
        assert "high" in risk
        assert "critical" in risk
    
    def test_v27_mitigations_fields(self):
        """v27 mitigations should have detailed breakdown."""
        report = generate_nightly_report()
        mitigations = report["predictive_resilience_v27"]["mitigations"]
        
        assert "applied_total" in mitigations
        assert "blocked_total" in mitigations
        assert "rejected_total" in mitigations
        assert "auto_applied_low_risk" in mitigations
        assert "pending_approval" in mitigations
        assert "by_severity" in mitigations
        
        by_severity = mitigations["by_severity"]
        assert "low" in by_severity
        assert "medium" in by_severity
        assert "high" in by_severity
        assert "critical" in by_severity
    
    def test_v27_performance_fields(self):
        """v27 performance should have time-based metrics."""
        report = generate_nightly_report()
        performance = report["predictive_resilience_v27"]["performance"]
        
        assert "time_to_detect_avg_seconds" in performance
        assert "time_to_mitigate_avg_seconds" in performance
        assert "target_time_to_detect_seconds" in performance
        assert "target_time_to_mitigate_seconds" in performance
        assert "time_to_detect_improvement" in performance
        assert "time_to_mitigate_improvement" in performance
    
    def test_v27_false_positive_tracking_fields(self):
        """v27 false positive tracking should have detailed metrics."""
        report = generate_nightly_report()
        fp = report["predictive_resilience_v27"]["false_positive_tracking"]
        
        assert "total_alerts" in fp
        assert "false_positives" in fp
        assert "false_positive_rate" in fp
        assert "target_rate" in fp
        assert "status" in fp
        assert "by_metric" in fp
        
        by_metric = fp["by_metric"]
        assert "incident_rate" in by_metric
        assert "handoff_timeout" in by_metric
        assert "approval_sla" in by_metric
    
    def test_v27_goals_progress_fields(self):
        """v27 goals progress should track all 6-week KPIs."""
        report = generate_nightly_report()
        goals = report["predictive_resilience_v27"]["goals_progress"]
        
        assert "incident_rate_reduction" in goals
        assert "handoff_timeout_reduction" in goals
        assert "approval_sla_breach_reduction" in goals
        assert "false_positive_rate" in goals
        
        # Check goal structure
        for goal_name, goal in goals.items():
            assert "target" in goal
            assert "current" in goal
            assert "status" in goal
    
    def test_v27_incident_rate_reduction_goal(self):
        """v27 should track incident_rate reduction goal (-20%)."""
        report = generate_nightly_report()
        goal = report["predictive_resilience_v27"]["goals_progress"]["incident_rate_reduction"]
        
        assert "target" in goal
        assert "current" in goal
        assert goal["target"] == "-20%"
        assert goal["status"] in ["achieved", "on_track", "at_risk"]
    
    def test_v27_handoff_timeout_reduction_goal(self):
        """v27 should track handoff timeout reduction goal (-25%)."""
        report = generate_nightly_report()
        goal = report["predictive_resilience_v27"]["goals_progress"]["handoff_timeout_reduction"]
        
        assert "target" in goal
        assert "current" in goal
        assert goal["target"] == "-25%"
    
    def test_v27_approval_sla_breach_reduction_goal(self):
        """v27 should track approval SLA breach reduction goal (-30%)."""
        report = generate_nightly_report()
        goal = report["predictive_resilience_v27"]["goals_progress"]["approval_sla_breach_reduction"]
        
        assert "target" in goal
        assert "current" in goal
        assert goal["target"] == "-30%"
    
    def test_v27_false_positive_rate_goal(self):
        """v27 should track false positive rate goal (<= 15%)."""
        report = generate_nightly_report()
        goal = report["predictive_resilience_v27"]["goals_progress"]["false_positive_rate"]
        
        assert "target" in goal
        assert "current" in goal
        assert goal["target"] == "<= 15%"
    
    def test_v27_false_positive_rate_below_target(self):
        """v27 false positive rate should be at or below 15% target."""
        report = generate_nightly_report()
        fp = report["predictive_resilience_v27"]["false_positive_tracking"]
        
        assert fp["false_positive_rate"] <= fp["target_rate"]
        assert fp["status"] in ["on_target", "achieved"]


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
    
    def test_v27_cycles_matches_performance(self):
        """v27 cycles should be consistent with performance metrics."""
        report = generate_nightly_report()
        v27 = report["predictive_resilience_v27"]
        
        # 4-hour cycles in 24h = 6 cycles
        assert v27["summary"]["cycles_total"] == 6
    
    def test_v27_alerts_matches_false_positive_tracking(self):
        """v27 alerts count should match false positive tracking."""
        report = generate_nightly_report()
        v27 = report["predictive_resilience_v27"]
        
        summary_alerts = v27["summary"]["alerts_generated"]
        fp_alerts = v27["false_positive_tracking"]["total_alerts"]
        
        assert summary_alerts == fp_alerts
    
    def test_v27_false_positive_rate_calculation(self):
        """v27 false positive rate should be correctly calculated."""
        report = generate_nightly_report()
        fp = report["predictive_resilience_v27"]["false_positive_tracking"]
        
        calculated_rate = fp["false_positives"] / fp["total_alerts"]
        assert fp["false_positive_rate"] == pytest.approx(calculated_rate, abs=0.001)
    
    def test_v27_mitigations_less_than_alerts(self):
        """Applied mitigations should be <= generated alerts."""
        report = generate_nightly_report()
        v27 = report["predictive_resilience_v27"]
        
        assert v27["mitigations"]["applied_total"] <= v27["summary"]["alerts_generated"]
    
    def test_v27_risk_distribution_has_valid_counts(self):
        """v27 risk distribution should have valid non-negative counts."""
        report = generate_nightly_report()
        v27 = report["predictive_resilience_v27"]
        
        risk_total = sum(v27["risk_distribution"].values())
        # Risk distribution represents unique risk assessments, not total alerts
        assert risk_total >= 0
        assert v27["risk_distribution"]["low"] >= 0
        assert v27["risk_distribution"]["medium"] >= 0
        assert v27["risk_distribution"]["high"] >= 0
        assert v27["risk_distribution"]["critical"] >= 0
    
    def test_v27_time_to_detect_improvement_over_v26(self):
        """v27 time to detect should show improvement over v26."""
        report = generate_nightly_report()
        
        v26_time = report["online_control_loop_v26"]["performance"]["time_to_detect_avg_seconds"]
        v27_time = report["predictive_resilience_v27"]["performance"]["time_to_detect_avg_seconds"]
        
        # v27 should be faster (lower time) than v26
        assert v27_time <= v26_time
    
    def test_v27_time_to_mitigate_improvement_over_v26(self):
        """v27 time to mitigate should show improvement over v26."""
        report = generate_nightly_report()
        
        v26_time = report["online_control_loop_v26"]["performance"]["time_to_mitigate_avg_seconds"]
        v27_time = report["predictive_resilience_v27"]["performance"]["time_to_mitigate_avg_seconds"]
        
        # v27 should be faster (lower time) than v26
        assert v27_time <= v26_time
