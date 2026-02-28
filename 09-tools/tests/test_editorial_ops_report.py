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

    def test_report_version_includes_v18(self):
        """Report version should indicate v18."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        assert "v18" in report["report_version"]

    def test_governance_goals_tracking(self):
        """Governance section should track goals progress."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        governance = report["multibrand_governance"]
        assert "goals" in governance
        assert "false_positives_reduction" in governance["goals"]
        assert "approval_without_regen_improvement" in governance["goals"]
        assert "quality_gap_reduction" in governance["goals"]


class TestCrossBrandGapMetric:
    """Test cross-brand p90-p10 gap metric calculations."""

    def test_calculate_gap_from_brand_metrics(self):
        """Should calculate gap from brand threshold metrics."""
        # Arrange
        from vm_webapp.nightly_report_v18 import calculate_cross_brand_gap
        
        brand_metrics = {
            "brand1": {"threshold": 0.8},
            "brand2": {"threshold": 0.6},
            "brand3": {"threshold": 0.7},
        }
        
        # Act
        gap = calculate_cross_brand_gap(brand_metrics)
        
        # Assert - p90=0.8, p10=0.6, gap=0.2
        assert pytest.approx(gap, 0.01) == 0.2

    def test_gap_zero_when_all_same(self):
        """Gap should be zero when all brands have same threshold."""
        # Arrange
        from vm_webapp.nightly_report_v18 import calculate_cross_brand_gap
        
        brand_metrics = {
            "brand1": {"threshold": 0.7},
            "brand2": {"threshold": 0.7},
            "brand3": {"threshold": 0.7},
        }
        
        # Act
        gap = calculate_cross_brand_gap(brand_metrics)
        
        # Assert
        assert gap == 0.0

    def test_gap_with_single_brand(self):
        """Gap should be zero with single brand."""
        # Arrange
        from vm_webapp.nightly_report_v18 import calculate_cross_brand_gap
        
        brand_metrics = {
            "brand1": {"threshold": 0.7},
        }
        
        # Act
        gap = calculate_cross_brand_gap(brand_metrics)
        
        # Assert
        assert gap == 0.0

    def test_gap_empty_brands(self):
        """Gap should be zero with no brands."""
        # Arrange
        from vm_webapp.nightly_report_v18 import calculate_cross_brand_gap
        
        # Act
        gap = calculate_cross_brand_gap({})
        
        # Assert
        assert gap == 0.0


class TestPolicyDiffsTracking:
    """Test policy diffs tracking in report."""

    def test_count_proposals_by_status(self):
        """Should count proposals grouped by status."""
        # Arrange
        from vm_webapp.nightly_report_v18 import count_proposals_by_status
        
        proposals = [
            AdaptationProposal(
                proposal_id="p1", brand_id="b1", objective_key=None,
                current_value=0.5, proposed_value=0.55, adjustment_percent=10.0,
                status=ProposalStatus.PENDING
            ),
            AdaptationProposal(
                proposal_id="p2", brand_id="b1", objective_key=None,
                current_value=0.5, proposed_value=0.55, adjustment_percent=10.0,
                status=ProposalStatus.APPROVED
            ),
            AdaptationProposal(
                proposal_id="p3", brand_id="b1", objective_key=None,
                current_value=0.5, proposed_value=0.55, adjustment_percent=10.0,
                status=ProposalStatus.APPLIED
            ),
            AdaptationProposal(
                proposal_id="p4", brand_id="b1", objective_key=None,
                current_value=0.5, proposed_value=0.55, adjustment_percent=10.0,
                status=ProposalStatus.REJECTED
            ),
        ]
        
        # Act
        counts = count_proposals_by_status(proposals)
        
        # Assert
        assert counts["pending"] == 1
        assert counts["approved"] == 1
        assert counts["applied"] == 1
        assert counts["rejected"] == 1


class TestGuardBlocksTracking:
    """Test guard blocks tracking in report."""

    def test_count_guard_blocks(self):
        """Should count blocks by type."""
        # Arrange
        from vm_webapp.nightly_report_v18 import count_guard_blocks
        
        blocks = [
            {"type": "incident", "brand_id": "b1"},
            {"type": "incident", "brand_id": "b2"},
            {"type": "canary", "brand_id": "b1"},
            {"type": "rollback", "brand_id": "b3"},
        ]
        
        # Act
        counts = count_guard_blocks(blocks)
        
        # Assert
        assert counts["incident"] == 2
        assert counts["canary"] == 1
        assert counts["rollback"] == 1


class TestReportIntegration:
    """Integration tests for nightly report v18."""

    def test_full_report_generation(self):
        """Should generate complete report with all sections."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report, print_report
        
        report = generate_nightly_report()
        
        # Assert - check all expected sections exist
        assert "report_version" in report
        assert "generated_at" in report
        assert "report_date" in report
        assert "summary" in report
        assert "multibrand_governance" in report
        
        # Verify summary has expected fields
        summary = report["summary"]
        assert "total_decisions" in summary
        assert "automation_rate" in summary
        
        # Verify governance has expected fields
        governance = report["multibrand_governance"]
        assert "policy_diffs" in governance
        assert "guard_blocks" in governance
        assert "cross_brand_gap_p90_p10" in governance
        assert "brand_breakdown" in governance
        assert "goals" in governance

    def test_report_date_defaults_to_yesterday(self):
        """Report date should default to yesterday."""
        # Arrange & Act
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        report = generate_nightly_report()
        
        # Assert
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        assert report["report_date"] == yesterday

    def test_report_date_can_be_specified(self):
        """Report date can be specified."""
        # Arrange
        from vm_webapp.nightly_report_v18 import generate_nightly_report
        
        specific_date = datetime(2026, 2, 15, tzinfo=timezone.utc)
        
        # Act
        report = generate_nightly_report(date=specific_date)
        
        # Assert
        assert report["report_date"] == "2026-02-15"
