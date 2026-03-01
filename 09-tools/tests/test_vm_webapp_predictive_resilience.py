"""Tests for v27 Predictive Resilience Engine.

TDD: Testes para score composto e classificação de risco.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from vm_webapp.predictive_resilience import (
    PredictiveResilienceEngine,
    ResilienceScore,
    RiskClassification,
    PredictiveSignal,
    MitigationProposal,
    MitigationType,
    MitigationSeverity,
)


class TestResilienceScore:
    """Testes para cálculo de score composto de resiliência."""

    def test_score_creation_with_all_components(self):
        """Score deve ser criado com componentes individuais."""
        score = ResilienceScore(
            incident_component=0.75,
            handoff_component=0.80,
            approval_component=0.85,
            composite_score=0.80,
        )
        
        assert score.incident_component == 0.75
        assert score.handoff_component == 0.80
        assert score.approval_component == 0.85
        assert score.composite_score == 0.80
        assert score.risk_class == RiskClassification.MEDIUM

    def test_composite_score_calculation(self):
        """Score composto deve ser média ponderada dos componentes."""
        score = ResilienceScore(
            incident_component=0.90,
            handoff_component=0.85,
            approval_component=0.95,
        )
        
        # (0.90 + 0.85 + 0.95) / 3 = 0.90
        assert score.composite_score == pytest.approx(0.90, abs=0.01)

    def test_risk_classification_low(self):
        """Score >= 0.85 deve ser LOW risk."""
        score = ResilienceScore(
            incident_component=0.90,
            handoff_component=0.90,
            approval_component=0.85,
        )
        assert score.risk_class == RiskClassification.LOW

    def test_risk_classification_medium(self):
        """Score entre 0.60 e 0.85 deve ser MEDIUM risk."""
        score = ResilienceScore(
            incident_component=0.70,
            handoff_component=0.75,
            approval_component=0.65,
        )
        assert score.risk_class == RiskClassification.MEDIUM

    def test_risk_classification_high(self):
        """Score entre 0.30 e 0.60 deve ser HIGH risk."""
        score = ResilienceScore(
            incident_component=0.50,
            handoff_component=0.45,
            approval_component=0.55,
        )
        assert score.risk_class == RiskClassification.HIGH

    def test_risk_classification_critical(self):
        """Score < 0.30 deve ser CRITICAL risk."""
        score = ResilienceScore(
            incident_component=0.20,
            handoff_component=0.25,
            approval_component=0.15,
        )
        assert score.risk_class == RiskClassification.CRITICAL

    def test_score_to_dict(self):
        """Score deve converter para dict corretamente."""
        score = ResilienceScore(
            incident_component=0.80,
            handoff_component=0.85,
            approval_component=0.75,
            timestamp="2026-03-01T12:00:00Z",
        )
        
        data = score.to_dict()
        assert data["incident_component"] == 0.80
        assert data["handoff_component"] == 0.85
        assert data["approval_component"] == 0.75
        assert data["composite_score"] == pytest.approx(0.80, abs=0.01)
        assert data["risk_class"] == "medium"
        assert data["timestamp"] == "2026-03-01T12:00:00Z"


class TestPredictiveSignal:
    """Testes para sinais preditivos."""

    def test_signal_creation(self):
        """Sinal deve ser criado com todos os campos."""
        signal = PredictiveSignal(
            signal_id="sig-001",
            metric_name="incident_rate",
            current_value=0.15,
            predicted_value=0.25,
            confidence=0.85,
            forecast_horizon_hours=4,
        )
        
        assert signal.signal_id == "sig-001"
        assert signal.metric_name == "incident_rate"
        assert signal.current_value == 0.15
        assert signal.predicted_value == 0.25
        assert signal.confidence == 0.85
        assert signal.forecast_horizon_hours == 4

    def test_signal_delta_calculation(self):
        """Delta deve ser calculado corretamente."""
        signal = PredictiveSignal(
            signal_id="sig-001",
            metric_name="handoff_timeout_rate",
            current_value=0.10,
            predicted_value=0.15,
            confidence=0.80,
        )
        
        # (0.15 - 0.10) / 0.10 = 0.50 (50% increase)
        assert signal.delta == pytest.approx(0.05, abs=0.001)
        assert signal.delta_pct == pytest.approx(0.50, abs=0.01)

    def test_signal_severity_degradation(self):
        """Severidade deve ser baseada na degradação predita."""
        # Small degradation (< 10%)
        signal_low = PredictiveSignal(
            signal_id="sig-001",
            metric_name="incident_rate",
            current_value=0.10,
            predicted_value=0.105,
            confidence=0.90,
        )
        assert signal_low.severity.value == "low"
        
        # Medium degradation (10-30%)
        signal_med = PredictiveSignal(
            signal_id="sig-002",
            metric_name="incident_rate",
            current_value=0.10,
            predicted_value=0.125,
            confidence=0.90,
        )
        assert signal_med.severity.value == "medium"
        
        # High degradation (30-50%)
        signal_high = PredictiveSignal(
            signal_id="sig-003",
            metric_name="incident_rate",
            current_value=0.10,
            predicted_value=0.14,
            confidence=0.90,
        )
        assert signal_high.severity.value == "high"
        
        # Critical degradation (> 50%)
        signal_crit = PredictiveSignal(
            signal_id="sig-004",
            metric_name="incident_rate",
            current_value=0.10,
            predicted_value=0.20,
            confidence=0.90,
        )
        assert signal_crit.severity.value == "critical"


class TestMitigationProposal:
    """Testes para propostas de mitigação."""

    def test_proposal_creation(self):
        """Proposta deve ser criada com todos os campos."""
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.AUTO_ADJUST,
            severity=MitigationSeverity.LOW,
            description="Auto-adjust threshold",
            estimated_impact={"incident_rate": -0.05},
        )
        
        assert proposal.proposal_id == "prop-001"
        assert proposal.signal_id == "sig-001"
        assert proposal.mitigation_type == MitigationType.AUTO_ADJUST
        assert proposal.severity == MitigationSeverity.LOW
        assert proposal.state == "pending"

    def test_low_risk_auto_apply_eligible(self):
        """Propostas LOW devem ser elegíveis para auto-apply."""
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.AUTO_ADJUST,
            severity=MitigationSeverity.LOW,
        )
        assert proposal.can_auto_apply is True

    def test_medium_risk_not_auto_apply(self):
        """Propostas MEDIUM não devem ser elegíveis para auto-apply."""
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.ADJUST_WITH_APPROVAL,
            severity=MitigationSeverity.MEDIUM,
        )
        assert proposal.can_auto_apply is False

    def test_high_risk_requires_escalation(self):
        """Propostas HIGH devem requerer escalação."""
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.FREEZE,
            severity=MitigationSeverity.HIGH,
        )
        assert proposal.requires_escalation is True
        assert proposal.can_auto_apply is False


class TestPredictiveResilienceEngine:
    """Testes para o engine preditivo de resiliência."""

    def test_engine_initialization(self):
        """Engine deve ser inicializado com estado limpo."""
        engine = PredictiveResilienceEngine()
        
        assert engine.VERSION == "v27"
        assert engine.get_status()["cycles_total"] == 0
        assert engine.get_status()["active_cycles"] == 0

    def test_calculate_composite_score(self):
        """Engine deve calcular score composto corretamente."""
        engine = PredictiveResilienceEngine()
        
        metrics = {
            "incident_rate": 0.12,
            "handoff_timeout_rate": 0.08,
            "approval_sla_breach_rate": 0.05,
        }
        
        score = engine.calculate_score(metrics)
        
        assert isinstance(score, ResilienceScore)
        assert 0.0 <= score.composite_score <= 1.0
        assert score.risk_class is not None

    def test_detect_signals_empty_metrics(self):
        """Engine deve retornar lista vazia quando métricas são normais."""
        engine = PredictiveResilienceEngine()
        
        # Métricas dentro dos limites aceitáveis
        metrics = {
            "incident_rate": 0.05,
            "handoff_timeout_rate": 0.03,
            "approval_sla_breach_rate": 0.02,
        }
        
        signals = engine.detect_signals(metrics)
        assert signals == []

    def test_detect_signals_with_degradation(self):
        """Engine deve detectar sinais quando métricas degradam."""
        engine = PredictiveResilienceEngine()
        
        # Simular histórico com tendência de degradação
        engine._metric_history = [
            {"incident_rate": 0.05, "timestamp": "2026-03-01T08:00:00Z"},
            {"incident_rate": 0.07, "timestamp": "2026-03-01T09:00:00Z"},
            {"incident_rate": 0.09, "timestamp": "2026-03-01T10:00:00Z"},
        ]
        
        metrics = {
            "incident_rate": 0.12,
            "handoff_timeout_rate": 0.05,
            "approval_sla_breach_rate": 0.03,
        }
        
        signals = engine.detect_signals(metrics)
        
        # Deve detectar sinal de incident_rate degradando
        assert len(signals) > 0
        assert any(s.metric_name == "incident_rate" for s in signals)

    def test_generate_proposals_for_signals(self):
        """Engine deve gerar propostas para sinais detectados."""
        engine = PredictiveResilienceEngine()
        
        signals = [
            PredictiveSignal(
                signal_id="sig-001",
                metric_name="incident_rate",
                current_value=0.15,
                predicted_value=0.25,
                confidence=0.85,
                severity=MitigationSeverity.MEDIUM,
            )
        ]
        
        proposals = engine.generate_proposals(signals)
        
        assert len(proposals) > 0
        assert proposals[0].signal_id == "sig-001"

    def test_start_cycle(self):
        """Engine deve iniciar ciclo de resiliência."""
        engine = PredictiveResilienceEngine()
        
        cycle = engine.start_cycle("brand-001")
        
        assert cycle.cycle_id is not None
        assert cycle.brand_id == "brand-001"
        assert cycle.state.value == "observing"

    def test_cycle_state_transitions(self):
        """Engine deve gerenciar transições de estado do ciclo."""
        engine = PredictiveResilienceEngine()
        
        cycle = engine.start_cycle("brand-001")
        cycle_id = cycle.cycle_id
        
        # Transition to detecting
        assert engine.update_cycle_state(cycle_id, "detecting") is True
        
        # Get cycle and check state
        updated = engine.get_cycle(cycle_id)
        assert updated.state.value == "detecting"

    def test_apply_mitigation_low_risk(self):
        """Mitigação LOW deve ser aplicável sem aprovação."""
        engine = PredictiveResilienceEngine()
        
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.AUTO_ADJUST,
            severity=MitigationSeverity.LOW,
            description="Auto-adjust timeout",
        )
        
        result = engine.apply_mitigation("prop-001", proposal)
        
        assert result is True
        assert proposal.state == "applied"

    def test_apply_mitigation_medium_risk_requires_approval(self):
        """Mitigação MEDIUM deve requerer aprovação."""
        engine = PredictiveResilienceEngine()
        
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.ADJUST_WITH_APPROVAL,
            severity=MitigationSeverity.MEDIUM,
        )
        
        # Without approval, should fail
        result = engine.apply_mitigation("prop-001", proposal, approved=False)
        assert result is False
        
        # With approval, should succeed
        result = engine.apply_mitigation("prop-001", proposal, approved=True)
        assert result is True
        assert proposal.state == "applied"

    def test_reject_mitigation(self):
        """Engine deve permitir rejeitar proposta."""
        engine = PredictiveResilienceEngine()
        
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.AUTO_ADJUST,
            severity=MitigationSeverity.LOW,
        )
        
        result = engine.reject_mitigation("prop-001", proposal, reason="Not needed")
        
        assert result is True
        assert proposal.state == "rejected"

    def test_freeze_brand(self):
        """Engine deve permitir congelar brand."""
        engine = PredictiveResilienceEngine()
        
        result = engine.freeze_brand("brand-001", reason="Critical risk detected")
        
        assert result is True
        assert "brand-001" in engine._frozen_brands

    def test_rollback_mitigation(self):
        """Engine deve permitir rollback de mitigação."""
        engine = PredictiveResilienceEngine()
        
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.AUTO_ADJUST,
            severity=MitigationSeverity.LOW,
        )
        
        # Apply first
        engine.apply_mitigation("prop-001", proposal)
        assert proposal.state == "applied"
        
        # Then rollback
        result = engine.rollback_mitigation("prop-001", proposal)
        
        assert result is True
        assert proposal.state == "rolled_back"

    def test_get_proposals_status(self):
        """Engine deve retornar status das propostas."""
        engine = PredictiveResilienceEngine()
        
        # Create and apply a proposal
        proposal = MitigationProposal(
            proposal_id="prop-001",
            signal_id="sig-001",
            mitigation_type=MitigationType.AUTO_ADJUST,
            severity=MitigationSeverity.LOW,
        )
        engine.apply_mitigation("prop-001", proposal)
        
        status = engine.get_proposal_status("prop-001")
        
        assert status is not None
        assert status["proposal_id"] == "prop-001"
        assert status["state"] == "applied"

    def test_get_proposal_status_not_found(self):
        """Engine deve retornar None para proposta inexistente."""
        engine = PredictiveResilienceEngine()
        
        status = engine.get_proposal_status("non-existent")
        assert status is None

    def test_false_positive_tracking(self):
        """Engine deve rastrear falsos positivos."""
        engine = PredictiveResilienceEngine()
        
        # Marcar alerta como falso positivo
        engine.record_false_positive("sig-001", reason="Prediction didn't materialize")
        
        status = engine.get_status()
        assert status["false_positives_total"] == 1
