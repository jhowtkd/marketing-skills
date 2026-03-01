"""Tests for v18 multibrand governance section in nightly report.

Tests new governance section with:
- Policy diffs tracking
- Guard blocks tracking
- Cross-brand gap metrics
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from vm_webapp.policy_adaptation import (
    PolicyProposalEngine,
    AdaptationProposal,
    ProposalStatus,
    CrossBrandMetrics,
)


class TestNightlyReportGovernanceSection:
    """Test v18 governance section in nightly report."""

    def test_report_includes_governance_section(self):
        """Report should include multibrand governance section."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        assert "multibrand_governance" in report

    def test_governance_section_has_policy_diffs(self):
        """Governance section should track policy diffs."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        governance = report["multibrand_governance"]
        assert "policy_diffs" in governance
        assert "proposed" in governance["policy_diffs"]
        assert "applied" in governance["policy_diffs"]
        assert "rejected" in governance["policy_diffs"]

    def test_governance_section_has_guard_blocks(self):
        """Governance section should track guard blocks."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        governance = report["multibrand_governance"]
        assert "guard_blocks" in governance
        assert "incident" in governance["guard_blocks"]
        assert "canary" in governance["guard_blocks"]
        assert "rollback" in governance["guard_blocks"]

    def test_governance_section_has_cross_brand_gap(self):
        """Governance section should include cross-brand gap metric."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        governance = report["multibrand_governance"]
        assert "cross_brand_gap_p90_p10" in governance
        assert isinstance(governance["cross_brand_gap_p90_p10"], float)

    def test_governance_section_has_brand_breakdown(self):
        """Governance section should have per-brand breakdown."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        governance = report["multibrand_governance"]
        assert "brand_breakdown" in governance
        assert isinstance(governance["brand_breakdown"], list)

    def test_brand_breakdown_has_required_fields(self):
        """Brand breakdown entries should have required fields."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        brands = report["multibrand_governance"]["brand_breakdown"]
        for brand in brands:
            assert "brand_id" in brand
            assert "proposals_count" in brand
            assert "current_gap" in brand
            assert "status" in brand  # active, frozen, etc.


# v22 DAG Section Tests

class TestNightlyReportDagSection:
    """Test v22 DAG section in nightly report."""

    def test_report_includes_dag_section(self):
        """Report should include DAG operations section."""
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        assert "dag_operations" in report

    def test_dag_section_has_run_metrics(self):
        """DAG section should track run metrics."""
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        dag_ops = report["dag_operations"]
        assert "runs_total" in dag_ops
        assert "runs_completed" in dag_ops
        assert "runs_failed" in dag_ops
        assert "runs_aborted" in dag_ops

    def test_dag_section_has_node_metrics(self):
        """DAG section should track node metrics."""
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        dag_ops = report["dag_operations"]
        assert "nodes_executed" in dag_ops
        assert "nodes_failed" in dag_ops
        assert "nodes_timeout" in dag_ops

    def test_dag_section_has_retry_metrics(self):
        """DAG section should track retry metrics."""
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        dag_ops = report["dag_operations"]
        assert "retries_total" in dag_ops
        assert "handoff_failures" in dag_ops

    def test_dag_section_has_approval_metrics(self):
        """DAG section should track approval metrics."""
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        dag_ops = report["dag_operations"]
        assert "approvals_pending" in dag_ops
        assert "approvals_granted" in dag_ops
        assert "approvals_rejected" in dag_ops
        assert "avg_approval_wait_sec" in dag_ops

    def test_dag_section_has_bottleneck_analysis(self):
        """DAG section should include bottleneck analysis."""
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        dag_ops = report["dag_operations"]
        assert "bottlenecks" in dag_ops
        assert isinstance(dag_ops["bottlenecks"], list)

    def test_bottleneck_has_required_fields(self):
        """Bottleneck entries should have required fields."""
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        bottlenecks = report["dag_operations"]["bottlenecks"]
        for bottleneck in bottlenecks:
            assert "node_type" in bottleneck
            assert "avg_wait_sec" in bottleneck
            assert "failure_rate" in bottleneck
