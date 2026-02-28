"""
VM Studio v17 - Safety Gates Auto-Tuning Engine Tests

Auto-tuning semanal semi-automático dos safety gates com:
- Limites rígidos (±10% max adjustment)
- Guardas de volume mínimo
- Análise de performance
"""

import pytest
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from vm_webapp.safety_autotuning import (
    GateConfig,
    GatePerformance,
    AdjustmentProposal,
    SafetyAutoTuner,
    RiskLevel,
    TuningCycleResult,
)

UTC = timezone.utc


class TestGateConfig:
    """Test gate configuration dataclass."""
    
    def test_create_gate_config(self):
        """Can create gate configuration."""
        config = GateConfig(
            gate_name="sample_size",
            current_value=100,
            min_value=50,
            max_value=500
        )
        assert config.gate_name == "sample_size"
        assert config.current_value == 100
        assert config.min_value == 50
        assert config.max_value == 500


class TestGatePerformance:
    """Test gate performance metrics."""
    
    def test_create_performance_metrics(self):
        """Can create performance metrics."""
        perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=10,
            missed_incidents=2,
            total_decisions=100,
            approval_without_regen_count=45
        )
        assert perf.gate_name == "sample_size"
        assert perf.false_positive_blocks == 10
        assert perf.missed_incidents == 2
        assert perf.total_decisions == 100
        assert perf.approval_without_regen_count == 45
    
    def test_calculate_fp_rate(self):
        """Calculate false positive rate."""
        perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=10,
            missed_incidents=2,
            total_decisions=100,
            approval_without_regen_count=45
        )
        assert perf.false_positive_rate == 0.10  # 10/100
    
    def test_calculate_approval_rate(self):
        """Calculate approval without regen rate."""
        perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=10,
            missed_incidents=2,
            total_decisions=100,
            approval_without_regen_count=45
        )
        assert perf.approval_without_regen_rate == 0.45  # 45/100


class TestAdjustmentProposal:
    """Test adjustment proposal structure."""
    
    def test_create_proposal(self):
        """Can create adjustment proposal."""
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.LOW,
            reason="HIGH_FP_RATE"
        )
        assert proposal.gate_name == "sample_size"
        assert proposal.current_value == 100
        assert proposal.proposed_value == 90
        assert proposal.adjustment_percent == -10.0
        assert proposal.risk_level == RiskLevel.LOW
        assert proposal.reason == "HIGH_FP_RATE"


class TestSafetyAutoTuner:
    """Test safety auto-tuner engine."""
    
    def test_analyze_cycle_returns_proposals(self):
        """Analyze cycle returns list of proposals."""
        tuner = SafetyAutoTuner()
        
        configs = [
            GateConfig(gate_name="sample_size", current_value=100, min_value=50, max_value=500),
        ]
        
        performances = [
            GatePerformance(
                gate_name="sample_size",
                false_positive_blocks=15,  # High FP rate
                missed_incidents=0,
                total_decisions=100,
                approval_without_regen_count=40
            ),
        ]
        
        proposals = tuner.analyze_cycle(configs, performances)
        
        assert isinstance(proposals, list)
    
    def test_propose_adjustments_with_high_fp_rate(self):
        """Propose lowering threshold when FP rate is high."""
        tuner = SafetyAutoTuner()
        
        config = GateConfig(
            gate_name="sample_size",
            current_value=100,
            min_value=50,
            max_value=500
        )
        
        performance = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=20,  # 20% FP rate (high)
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=40
        )
        
        proposal = tuner.propose_adjustment(config, performance)
        
        assert proposal is not None
        assert proposal.adjustment_percent < 0  # Should decrease threshold
        assert proposal.adjustment_percent >= -10.0  # Max -10%
    
    def test_propose_adjustments_with_missed_incidents(self):
        """Propose raising threshold when incidents are missed."""
        tuner = SafetyAutoTuner()
        
        config = GateConfig(
            gate_name="confidence_threshold",
            current_value=0.8,
            min_value=0.5,
            max_value=0.95
        )
        
        performance = GatePerformance(
            gate_name="confidence_threshold",
            false_positive_blocks=5,
            missed_incidents=5,  # 5% missed (high)
            total_decisions=100,
            approval_without_regen_count=45
        )
        
        proposal = tuner.propose_adjustment(config, performance)
        
        assert proposal is not None
        assert proposal.adjustment_percent > 0  # Should increase threshold
        assert proposal.adjustment_percent <= 10.0  # Max +10%
    
    def test_no_proposal_when_performance_good(self):
        """No proposal when performance is balanced."""
        tuner = SafetyAutoTuner()
        
        config = GateConfig(
            gate_name="sample_size",
            current_value=100,
            min_value=50,
            max_value=500
        )
        
        performance = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=5,  # 5% FP rate (acceptable)
            missed_incidents=1,  # 1% missed (acceptable)
            total_decisions=100,
            approval_without_regen_count=50
        )
        
        proposal = tuner.propose_adjustment(config, performance)
        
        assert proposal is None  # No adjustment needed
    
    def test_clamp_adjustment_to_max_10_percent(self):
        """Adjustment is clamped to ±10%."""
        tuner = SafetyAutoTuner()
        
        config = GateConfig(
            gate_name="sample_size",
            current_value=100,
            min_value=50,
            max_value=500
        )
        
        # Very high FP rate would suggest large adjustment
        performance = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=50,  # 50% would suggest -30% adjustment
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=30
        )
        
        proposal = tuner.propose_adjustment(config, performance)
        
        assert proposal is not None
        assert proposal.adjustment_percent == -10.0  # Clamped to -10%
        assert proposal.proposed_value == 90  # 100 * 0.9
    
    def test_block_adjustment_by_volume_insufficient(self):
        """Block adjustment when volume is insufficient."""
        tuner = SafetyAutoTuner(min_volume_threshold=50)
        
        config = GateConfig(
            gate_name="sample_size",
            current_value=100,
            min_value=50,
            max_value=500
        )
        
        performance = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=5,
            missed_incidents=0,
            total_decisions=30,  # Below threshold of 50
            approval_without_regen_count=20
        )
        
        proposal = tuner.propose_adjustment(config, performance)
        
        # Should return blocked proposal instead of None
        assert proposal is not None
        assert proposal.blocked_by_volume is True
    
    def test_respect_min_max_bounds(self):
        """Proposed value respects min/max bounds."""
        tuner = SafetyAutoTuner()
        
        config = GateConfig(
            gate_name="sample_size",
            current_value=55,
            min_value=50,
            max_value=500
        )
        
        # High FP rate suggests decreasing
        performance = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=20,
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=40
        )
        
        proposal = tuner.propose_adjustment(config, performance)
        
        assert proposal is not None
        assert proposal.proposed_value >= config.min_value  # Should not go below 50
    
    def test_respect_max_bounds(self):
        """Proposed value respects max bound."""
        tuner = SafetyAutoTuner()
        
        config = GateConfig(
            gate_name="confidence_threshold",
            current_value=0.94,
            min_value=0.5,
            max_value=0.95
        )
        
        # High missed incidents suggests increasing
        performance = GatePerformance(
            gate_name="confidence_threshold",
            false_positive_blocks=0,
            missed_incidents=10,
            total_decisions=100,
            approval_without_regen_count=40
        )
        
        proposal = tuner.propose_adjustment(config, performance)
        
        assert proposal is not None
        assert proposal.proposed_value <= config.max_value  # Should not exceed 0.95


class TestTuningCycleResult:
    """Test tuning cycle result."""
    
    def test_create_cycle_result(self):
        """Can create tuning cycle result."""
        result = TuningCycleResult(
            cycle_id="cycle-2026-02-28",
            timestamp=datetime.now(UTC),
            proposals=[],
            applied_count=0,
            blocked_count=0
        )
        assert result.cycle_id == "cycle-2026-02-28"
        assert result.applied_count == 0
        assert result.blocked_count == 0


class TestAutoTunerIntegration:
    """Integration tests for auto-tuner."""
    
    def test_full_cycle_with_multiple_gates(self):
        """Process multiple gates in one cycle."""
        tuner = SafetyAutoTuner()
        
        configs = [
            GateConfig(gate_name="sample_size", current_value=100, min_value=50, max_value=500),
            GateConfig(gate_name="confidence_threshold", current_value=0.8, min_value=0.5, max_value=0.95),
        ]
        
        performances = [
            GatePerformance(
                gate_name="sample_size",
                false_positive_blocks=20,
                missed_incidents=0,
                total_decisions=100,
                approval_without_regen_count=40
            ),
            GatePerformance(
                gate_name="confidence_threshold",
                false_positive_blocks=20,  # High FP rate - needs adjustment
                missed_incidents=0,
                total_decisions=100,
                approval_without_regen_count=50
            ),
        ]
        
        result = tuner.run_cycle("cycle-001", configs, performances)
        
        assert result.cycle_id == "cycle-001"
        assert len(result.proposals) == 2
        assert result.proposals[0].gate_name == "sample_size"
        assert result.proposals[1].gate_name == "confidence_threshold"
