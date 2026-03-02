"""Tests for v28 Recovery Orchestrator.

TDD: Testes para classificação de incidente e planejamento da cadeia.
"""

from __future__ import annotations

import pytest

from vm_webapp.recovery_orchestrator import (
    Incident,
    IncidentSeverity,
    IncidentType,
    RecoveryOrchestrator,
    RecoveryPlan,
    RecoveryStep,
)


class TestIncidentClassification:
    """Testes para classificação de incidentes."""

    def test_classify_handoff_timeout_low(self):
        """Handoff timeout baixo deve ser LOW severity."""
        orchestrator = RecoveryOrchestrator()
        severity = orchestrator.classify_incident(
            IncidentType.HANDOFF_TIMEOUT,
            {"handoff_timeout_rate": 0.02},
            {}
        )
        assert severity == IncidentSeverity.LOW

    def test_classify_handoff_timeout_medium(self):
        """Handoff timeout médio deve ser MEDIUM severity."""
        orchestrator = RecoveryOrchestrator()
        severity = orchestrator.classify_incident(
            IncidentType.HANDOFF_TIMEOUT,
            {"handoff_timeout_rate": 0.06},
            {}
        )
        assert severity == IncidentSeverity.MEDIUM

    def test_classify_handoff_timeout_high(self):
        """Handoff timeout alto deve ser HIGH severity."""
        orchestrator = RecoveryOrchestrator()
        severity = orchestrator.classify_incident(
            IncidentType.HANDOFF_TIMEOUT,
            {"handoff_timeout_rate": 0.12},
            {}
        )
        assert severity == IncidentSeverity.HIGH

    def test_classify_handoff_timeout_critical(self):
        """Handoff timeout crítico deve ser CRITICAL severity."""
        orchestrator = RecoveryOrchestrator()
        severity = orchestrator.classify_incident(
            IncidentType.HANDOFF_TIMEOUT,
            {"handoff_timeout_rate": 0.25},
            {}
        )
        assert severity == IncidentSeverity.CRITICAL

    def test_classify_approval_sla_breach(self):
        """Approval SLA breach deve ser classificado corretamente."""
        orchestrator = RecoveryOrchestrator()
        
        low = orchestrator.classify_incident(
            IncidentType.APPROVAL_SLA_BREACH,
            {"approval_sla_breach_rate": 0.03},
            {}
        )
        assert low == IncidentSeverity.LOW
        
        high = orchestrator.classify_incident(
            IncidentType.APPROVAL_SLA_BREACH,
            {"approval_sla_breach_rate": 0.15},
            {}
        )
        assert high == IncidentSeverity.HIGH

    def test_classify_quality_regression(self):
        """Quality regression deve ser classificado por score."""
        orchestrator = RecoveryOrchestrator()
        
        critical = orchestrator.classify_incident(
            IncidentType.QUALITY_REGRESSION,
            {"quality_score": 0.40},
            {}
        )
        assert critical == IncidentSeverity.CRITICAL
        
        medium = orchestrator.classify_incident(
            IncidentType.QUALITY_REGRESSION,
            {"quality_score": 0.75},
            {}
        )
        assert medium == IncidentSeverity.MEDIUM

    def test_classify_system_failure_is_critical(self):
        """System failure deve sempre ser CRITICAL."""
        orchestrator = RecoveryOrchestrator()
        severity = orchestrator.classify_incident(
            IncidentType.SYSTEM_FAILURE,
            {},
            {}
        )
        assert severity == IncidentSeverity.CRITICAL


class TestRecoveryChainPlanning:
    """Testes para planejamento da cadeia de recuperação."""

    def test_plan_handoff_timeout_chain(self):
        """Plano para handoff timeout deve ter steps corretos."""
        orchestrator = RecoveryOrchestrator()
        incident = Incident(
            incident_id="inc-001",
            brand_id="brand-001",
            incident_type=IncidentType.HANDOFF_TIMEOUT,
            severity=IncidentSeverity.HIGH,
            description="Handoff timeout exceeded",
        )
        
        plan = orchestrator.plan_recovery_chain(incident)
        
        assert plan.incident_id == "inc-001"
        assert plan.brand_id == "brand-001"
        assert len(plan.steps) == 4
        assert plan.steps[0].step_id == "diagnose"
        assert plan.steps[0].action == "analyze_handoff_queue"

    def test_plan_approval_sla_breach_chain(self):
        """Plano para approval SLA breach deve ter steps específicos."""
        orchestrator = RecoveryOrchestrator()
        incident = Incident(
            incident_id="inc-002",
            brand_id="brand-001",
            incident_type=IncidentType.APPROVAL_SLA_BREACH,
            severity=IncidentSeverity.MEDIUM,
            description="Approval SLA breached",
        )
        
        plan = orchestrator.plan_recovery_chain(incident)
        
        assert len(plan.steps) == 3
        assert plan.steps[0].step_id == "identify"
        assert plan.steps[1].step_id == "escalate"
        assert plan.steps[1].depends_on == ["identify"]

    def test_plan_quality_regression_chain(self):
        """Plano para quality regression deve incluir rollback."""
        orchestrator = RecoveryOrchestrator()
        incident = Incident(
            incident_id="inc-003",
            brand_id="brand-001",
            incident_type=IncidentType.QUALITY_REGRESSION,
            severity=IncidentSeverity.HIGH,
            description="Quality score dropped",
        )
        
        plan = orchestrator.plan_recovery_chain(incident)
        
        step_ids = [s.step_id for s in plan.steps]
        assert "detect" in step_ids
        assert "freeze" in step_ids
        assert "rollback" in step_ids

    def test_high_severity_requires_approval(self):
        """Incidentes HIGH/CRITICAL devem requerer aprovação."""
        orchestrator = RecoveryOrchestrator()
        
        high_incident = Incident(
            incident_id="inc-004",
            brand_id="brand-001",
            incident_type=IncidentType.HANDOFF_TIMEOUT,
            severity=IncidentSeverity.HIGH,
            description="High severity",
        )
        high_plan = orchestrator.plan_recovery_chain(high_incident)
        assert high_plan.requires_approval is True
        
        low_incident = Incident(
            incident_id="inc-005",
            brand_id="brand-001",
            incident_type=IncidentType.HANDOFF_TIMEOUT,
            severity=IncidentSeverity.LOW,
            description="Low severity",
        )
        low_plan = orchestrator.plan_recovery_chain(low_incident)
        assert low_plan.requires_approval is False

    def test_plan_estimated_duration(self):
        """Plano deve calcular duração estimada."""
        orchestrator = RecoveryOrchestrator()
        incident = Incident(
            incident_id="inc-006",
            brand_id="brand-001",
            incident_type=IncidentType.HANDOFF_TIMEOUT,
            severity=IncidentSeverity.MEDIUM,
            description="Test incident",
        )
        
        plan = orchestrator.plan_recovery_chain(incident)
        
        assert plan.estimated_duration_seconds > 0
        expected = sum(s.timeout_seconds for s in plan.steps)
        assert plan.estimated_duration_seconds == expected


class TestOrchestratorState:
    """Testes para estado do orquestrador."""

    def test_register_and_get_incident(self):
        """Deve registrar e recuperar incidente."""
        orchestrator = RecoveryOrchestrator()
        incident = Incident(
            incident_id="inc-007",
            brand_id="brand-001",
            incident_type=IncidentType.HANDOFF_TIMEOUT,
            severity=IncidentSeverity.MEDIUM,
            description="Test",
        )
        
        orchestrator.register_incident(incident)
        retrieved = orchestrator.get_incident("inc-007")
        
        assert retrieved is not None
        assert retrieved.incident_id == "inc-007"
        assert retrieved.brand_id == "brand-001"

    def test_list_incidents_with_filters(self):
        """Deve listar incidentes com filtros."""
        orchestrator = RecoveryOrchestrator()
        
        # Add incidents
        for i in range(3):
            orchestrator.register_incident(Incident(
                incident_id=f"inc-brand1-{i}",
                brand_id="brand-001",
                incident_type=IncidentType.HANDOFF_TIMEOUT,
                severity=IncidentSeverity.HIGH if i == 0 else IncidentSeverity.LOW,
                description=f"Test {i}",
            ))
        
        orchestrator.register_incident(Incident(
            incident_id="inc-brand2-001",
            brand_id="brand-002",
            incident_type=IncidentType.HANDOFF_TIMEOUT,
            severity=IncidentSeverity.HIGH,
            description="Test",
        ))
        
        # Filter by brand
        brand1_incidents = orchestrator.list_incidents(brand_id="brand-001")
        assert len(brand1_incidents) == 3
        
        # Filter by severity
        high_incidents = orchestrator.list_incidents(severity=IncidentSeverity.HIGH)
        assert len(high_incidents) == 2

    def test_get_nonexistent_incident_returns_none(self):
        """Recuperar incidente inexistente deve retornar None."""
        orchestrator = RecoveryOrchestrator()
        result = orchestrator.get_incident("nonexistent")
        assert result is None
