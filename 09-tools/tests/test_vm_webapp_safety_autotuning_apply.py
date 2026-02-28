"""
VM Studio v17 - Safety Gates Auto-Tuning Apply/Rollback Tests

Testes para:
- Autoapply apenas low-risk
- Rollback em degradação 48h
- Bloqueio com canary/rollback ativo
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from vm_webapp.safety_autotuning_apply import (
    ApplyResult,
    RollbackResult,
    SafetyTuningApplier,
    ApplyDecision,
    RollbackTrigger,
)
from vm_webapp.safety_autotuning import (
    GateConfig,
    GatePerformance,
    AdjustmentProposal,
    RiskLevel,
)

UTC = timezone.utc


class TestApplyDecision:
    """Test apply decision enum."""
    
    def test_apply_decision_values(self):
        """Apply decision values are correct."""
        assert ApplyDecision.APPLOYED_AUTO.value == "applied_auto"
        assert ApplyDecision.BLOCKED_HIGH_RISK.value == "blocked_high_risk"
        assert ApplyDecision.BLOCKED_CANARY_ACTIVE.value == "blocked_canary_active"
        assert ApplyDecision.BLOCKED_ROLLBACK_PENDING.value == "blocked_rollback_pending"
        assert ApplyDecision.REJECTED_BY_USER.value == "rejected_by_user"


class TestRollbackTrigger:
    """Test rollback trigger enum."""
    
    def test_rollback_trigger_values(self):
        """Rollback trigger values are correct."""
        assert RollbackTrigger.FP_RATE_SPIKE.value == "fp_rate_spike"
        assert RollbackTrigger.INCIDENTS_INCREASED.value == "incidents_increased"
        assert RollbackTrigger.APPROVAL_RATE_DROP.value == "approval_rate_drop"
        assert RollbackTrigger.MANUAL.value == "manual"


class TestApplyResult:
    """Test apply result structure."""
    
    def test_create_apply_result(self):
        """Can create apply result."""
        result = ApplyResult(
            proposal_id="prop-001",
            decision=ApplyDecision.APPLOYED_AUTO,
            applied_at=datetime.now(UTC),
            previous_value=100,
            new_value=90
        )
        assert result.proposal_id == "prop-001"
        assert result.decision == ApplyDecision.APPLOYED_AUTO
        assert result.new_value == 90


class TestRollbackResult:
    """Test rollback result structure."""
    
    def test_create_rollback_result(self):
        """Can create rollback result."""
        result = RollbackResult(
            proposal_id="prop-001",
            trigger=RollbackTrigger.FP_RATE_SPIKE,
            rolled_back_at=datetime.now(UTC),
            restored_value=100
        )
        assert result.proposal_id == "prop-001"
        assert result.trigger == RollbackTrigger.FP_RATE_SPIKE
        assert result.restored_value == 100


class TestSafetyTuningApplier:
    """Test safety tuning applier."""
    
    def test_autoapply_low_risk_proposal(self):
        """Autoapply permite propostas low-risk."""
        applier = SafetyTuningApplier()
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.LOW,
            reason="HIGH_FP_RATE"
        )
        
        result = applier.apply_proposal(proposal, autoapply=True)
        
        assert result.decision == ApplyDecision.APPLOYED_AUTO
        assert result.new_value == 90
        assert result.previous_value == 100
    
    def test_block_autoapply_medium_risk(self):
        """Autoapply bloqueia propostas medium-risk."""
        applier = SafetyTuningApplier()
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.MEDIUM,
            reason="HIGH_FP_RATE"
        )
        
        result = applier.apply_proposal(proposal, autoapply=True)
        
        assert result.decision == ApplyDecision.BLOCKED_HIGH_RISK
        assert result.new_value is None  # Não aplicado
    
    def test_block_autoapply_high_risk(self):
        """Autoapply bloqueia propostas high-risk."""
        applier = SafetyTuningApplier()
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.HIGH,
            reason="BOTH_METRICS_HIGH"
        )
        
        result = applier.apply_proposal(proposal, autoapply=True)
        
        assert result.decision == ApplyDecision.BLOCKED_HIGH_RISK
    
    def test_block_autoapply_critical_risk(self):
        """Autoapply bloqueia propostas critical-risk."""
        applier = SafetyTuningApplier()
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.CRITICAL,
            reason="CRITICAL_ISSUE"
        )
        
        result = applier.apply_proposal(proposal, autoapply=True)
        
        assert result.decision == ApplyDecision.BLOCKED_HIGH_RISK
    
    def test_manual_apply_allows_medium_risk(self):
        """Apply manual permite propostas medium-risk."""
        applier = SafetyTuningApplier()
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.MEDIUM,
            reason="HIGH_FP_RATE"
        )
        
        result = applier.apply_proposal(proposal, autoapply=False)
        
        assert result.decision == ApplyDecision.APPLOYED_AUTO  # Aplicado via manual
        assert result.new_value == 90
    
    def test_block_when_canary_active(self):
        """Bloqueia quando há canary ativo."""
        applier = SafetyTuningApplier()
        
        # Simula canary ativo
        applier.active_canaries.add("sample_size")
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.LOW,
            reason="HIGH_FP_RATE"
        )
        
        result = applier.apply_proposal(proposal, autoapply=True)
        
        assert result.decision == ApplyDecision.BLOCKED_CANARY_ACTIVE
    
    def test_block_when_rollback_pending(self):
        """Bloqueia quando há rollback pendente."""
        applier = SafetyTuningApplier()
        
        # Simula rollback pendente
        applier.pending_rollbacks.add("sample_size")
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.LOW,
            reason="HIGH_FP_RATE"
        )
        
        result = applier.apply_proposal(proposal, autoapply=True)
        
        assert result.decision == ApplyDecision.BLOCKED_ROLLBACK_PENDING


class TestRollbackMechanism:
    """Test rollback mechanism."""
    
    def test_rollback_on_fp_rate_spike(self):
        """Rollback quando FP rate aumenta significativamente."""
        applier = SafetyTuningApplier()
        
        # Configura aplicação anterior
        applier.applied_proposals["prop-001"] = {
            "gate_name": "sample_size",
            "previous_value": 100,
            "new_value": 90,
            "applied_at": datetime.now(UTC) - timedelta(hours=24)
        }
        
        # Performance atual mostra degradação
        current_perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=30,  # Aumentou de 20 para 30
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=30
        )
        
        # Performance anterior (antes do ajuste)
        previous_perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=20,
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=40
        )
        
        result = applier.evaluate_rollback("prop-001", current_perf, previous_perf)
        
        assert result is not None
        assert result.trigger == RollbackTrigger.FP_RATE_SPIKE
        assert result.restored_value == 100  # Valor anterior
    
    def test_no_rollback_when_improved(self):
        """Não faz rollback quando performance melhorou."""
        applier = SafetyTuningApplier()
        
        applier.applied_proposals["prop-001"] = {
            "gate_name": "sample_size",
            "previous_value": 100,
            "new_value": 90,
            "applied_at": datetime.now(UTC) - timedelta(hours=24)
        }
        
        # Performance melhorou
        current_perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=5,  # Diminuiu de 20 para 5
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=55
        )
        
        previous_perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=20,
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=40
        )
        
        result = applier.evaluate_rollback("prop-001", current_perf, previous_perf)
        
        assert result is None  # Sem rollback necessário
    
    def test_rollback_only_within_48h_window(self):
        """Rollback apenas dentro da janela de 48h."""
        applier = SafetyTuningApplier()
        
        # Aplicação antiga (> 48h)
        applier.applied_proposals["prop-001"] = {
            "gate_name": "sample_size",
            "previous_value": 100,
            "new_value": 90,
            "applied_at": datetime.now(UTC) - timedelta(hours=72)
        }
        
        current_perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=30,
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=30
        )
        
        previous_perf = GatePerformance(
            gate_name="sample_size",
            false_positive_blocks=20,
            missed_incidents=0,
            total_decisions=100,
            approval_without_regen_count=40
        )
        
        result = applier.evaluate_rollback("prop-001", current_perf, previous_perf)
        
        # Não deve fazer rollback após 48h
        assert result is None
    
    def test_rollback_on_incidents_increase(self):
        """Rollback quando incidentes aumentam."""
        applier = SafetyTuningApplier()
        
        applier.applied_proposals["prop-001"] = {
            "gate_name": "confidence_threshold",
            "previous_value": 0.8,
            "new_value": 0.75,
            "applied_at": datetime.now(UTC) - timedelta(hours=12)
        }
        
        current_perf = GatePerformance(
            gate_name="confidence_threshold",
            false_positive_blocks=5,
            missed_incidents=8,  # Aumentou de 2 para 8
            total_decisions=100,
            approval_without_regen_count=40
        )
        
        previous_perf = GatePerformance(
            gate_name="confidence_threshold",
            false_positive_blocks=5,
            missed_incidents=2,
            total_decisions=100,
            approval_without_regen_count=45
        )
        
        result = applier.evaluate_rollback("prop-001", current_perf, previous_perf)
        
        assert result is not None
        assert result.trigger == RollbackTrigger.INCIDENTS_INCREASED


class TestCanaryMechanism:
    """Test canary mechanism."""
    
    def test_start_canary_on_apply(self):
        """Inicia canary quando aplica ajuste."""
        applier = SafetyTuningApplier()
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.LOW,
            reason="HIGH_FP_RATE"
        )
        
        applier.apply_proposal(proposal, autoapply=True)
        
        assert "sample_size" in applier.active_canaries
    
    def test_clear_canary_after_validation(self):
        """Limpa canary após validação."""
        applier = SafetyTuningApplier()
        
        applier.active_canaries.add("sample_size")
        
        applier.clear_canary("sample_size")
        
        assert "sample_size" not in applier.active_canaries


class TestFreezeMechanism:
    """Test freeze mechanism."""
    
    def test_freeze_gate(self):
        """Congela gate para prevenir ajustes."""
        applier = SafetyTuningApplier()
        
        applier.freeze_gate("sample_size", reason="manual_review")
        
        assert "sample_size" in applier.frozen_gates
        
        proposal = AdjustmentProposal(
            gate_name="sample_size",
            current_value=100,
            proposed_value=90,
            adjustment_percent=-10.0,
            risk_level=RiskLevel.LOW,
            reason="HIGH_FP_RATE"
        )
        
        result = applier.apply_proposal(proposal, autoapply=True)
        
        assert result.decision == ApplyDecision.BLOCKED_CANARY_ACTIVE  # Frozen trata como canary
    
    def test_unfreeze_gate(self):
        """Descongela gate."""
        applier = SafetyTuningApplier()
        
        applier.frozen_gates.add("sample_size")
        applier.unfreeze_gate("sample_size")
        
        assert "sample_size" not in applier.frozen_gates
