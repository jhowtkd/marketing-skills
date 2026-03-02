"""Recovery Orchestrator - v28 Auto-Recovery Orchestration.

Orquestrador central para recuperação automática com classificação de incidentes
e planejamento de cadeia de recuperação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class IncidentSeverity(Enum):
    """Severidade do incidente."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentType(Enum):
    """Tipo de incidente."""
    HANDOFF_TIMEOUT = "handoff_timeout"
    APPROVAL_SLA_BREACH = "approval_sla_breach"
    QUALITY_REGRESSION = "quality_regression"
    SYSTEM_FAILURE = "system_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class Incident:
    """Representação de um incidente."""
    incident_id: str
    brand_id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: dict = field(default_factory=dict)
    auto_recovery_eligible: bool = True


@dataclass
class RecoveryStep:
    """Um passo na cadeia de recuperação."""
    step_id: str
    name: str
    action: str
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class RecoveryPlan:
    """Plano de recuperação para um incidente."""
    plan_id: str
    incident_id: str
    brand_id: str
    steps: List[RecoveryStep] = field(default_factory=list)
    estimated_duration_seconds: int = 0
    requires_approval: bool = False
    risk_level: str = "low"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RecoveryOrchestrator:
    """Orquestrador central de recuperação automática."""
    
    # Thresholds para classificação de severidade
    INCIDENT_RATE_HIGH_THRESHOLD = 0.15
    INCIDENT_RATE_CRITICAL_THRESHOLD = 0.30
    HANDOFF_TIMEOUT_HIGH_THRESHOLD = 0.10
    APPROVAL_SLA_BREACH_HIGH_THRESHOLD = 0.12
    
    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._plans: dict[str, RecoveryPlan] = {}
        self._execution_logs: dict[str, list] = {}
    
    def classify_incident(
        self,
        incident_type: IncidentType,
        metrics: dict,
        context: dict
    ) -> IncidentSeverity:
        """Classifica a severidade de um incidente baseado em métricas."""
        if incident_type == IncidentType.HANDOFF_TIMEOUT:
            timeout_rate = metrics.get("handoff_timeout_rate", 0)
            if timeout_rate >= self.HANDOFF_TIMEOUT_HIGH_THRESHOLD * 2:
                return IncidentSeverity.CRITICAL
            elif timeout_rate >= self.HANDOFF_TIMEOUT_HIGH_THRESHOLD:
                return IncidentSeverity.HIGH
            elif timeout_rate >= self.HANDOFF_TIMEOUT_HIGH_THRESHOLD / 2:
                return IncidentSeverity.MEDIUM
            return IncidentSeverity.LOW
            
        elif incident_type == IncidentType.APPROVAL_SLA_BREACH:
            breach_rate = metrics.get("approval_sla_breach_rate", 0)
            if breach_rate >= self.APPROVAL_SLA_BREACH_HIGH_THRESHOLD * 2:
                return IncidentSeverity.CRITICAL
            elif breach_rate >= self.APPROVAL_SLA_BREACH_HIGH_THRESHOLD:
                return IncidentSeverity.HIGH
            elif breach_rate >= self.APPROVAL_SLA_BREACH_HIGH_THRESHOLD / 2:
                return IncidentSeverity.MEDIUM
            return IncidentSeverity.LOW
            
        elif incident_type == IncidentType.QUALITY_REGRESSION:
            quality_score = metrics.get("quality_score", 1.0)
            if quality_score < 0.50:
                return IncidentSeverity.CRITICAL
            elif quality_score < 0.70:
                return IncidentSeverity.HIGH
            elif quality_score < 0.85:
                return IncidentSeverity.MEDIUM
            return IncidentSeverity.LOW
            
        elif incident_type == IncidentType.SYSTEM_FAILURE:
            return IncidentSeverity.CRITICAL
            
        return IncidentSeverity.MEDIUM
    
    def plan_recovery_chain(
        self,
        incident: Incident,
        strategy: str = "auto"
    ) -> RecoveryPlan:
        """Planeja uma cadeia de recuperação para um incidente."""
        plan_id = f"plan-{incident.incident_id}"
        steps: List[RecoveryStep] = []
        
        if incident.incident_type == IncidentType.HANDOFF_TIMEOUT:
            steps = [
                RecoveryStep(
                    step_id="diagnose",
                    name="Diagnose Handoff Issue",
                    action="analyze_handoff_queue",
                    timeout_seconds=60,
                ),
                RecoveryStep(
                    step_id="notify",
                    name="Notify Stakeholders",
                    action="send_notification",
                    depends_on=["diagnose"],
                    timeout_seconds=30,
                ),
                RecoveryStep(
                    step_id="requeue",
                    name="Requeue Failed Items",
                    action="requeue_failed_handoffs",
                    depends_on=["diagnose"],
                    timeout_seconds=120,
                    max_retries=2,
                ),
                RecoveryStep(
                    step_id="verify",
                    name="Verify Recovery",
                    action="check_handoff_health",
                    depends_on=["requeue", "notify"],
                    timeout_seconds=60,
                ),
            ]
            
        elif incident.incident_type == IncidentType.APPROVAL_SLA_BREACH:
            steps = [
                RecoveryStep(
                    step_id="identify",
                    name="Identify Stuck Approvals",
                    action="find_stuck_approvals",
                    timeout_seconds=60,
                ),
                RecoveryStep(
                    step_id="escalate",
                    name="Escalate to Managers",
                    action="escalate_approvals",
                    depends_on=["identify"],
                    timeout_seconds=60,
                ),
                RecoveryStep(
                    step_id="extend",
                    name="Extend SLA Where Allowed",
                    action="extend_approval_sla",
                    depends_on=["identify"],
                    timeout_seconds=90,
                ),
            ]
            
        elif incident.incident_type == IncidentType.QUALITY_REGRESSION:
            steps = [
                RecoveryStep(
                    step_id="detect",
                    name="Detect Regression Source",
                    action="analyze_quality_metrics",
                    timeout_seconds=120,
                ),
                RecoveryStep(
                    step_id="freeze",
                    name="Freeze Affected Workflows",
                    action="freeze_workflows",
                    depends_on=["detect"],
                    timeout_seconds=30,
                ),
                RecoveryStep(
                    step_id="rollback",
                    name="Rollback Changes",
                    action="rollback_to_last_known_good",
                    depends_on=["freeze"],
                    timeout_seconds=300,
                    max_retries=1,
                ),
            ]
        
        else:
            steps = [
                RecoveryStep(
                    step_id="assess",
                    name="Assess System State",
                    action="system_health_check",
                    timeout_seconds=60,
                ),
                RecoveryStep(
                    step_id="restart",
                    name="Restart Services",
                    action="restart_affected_services",
                    depends_on=["assess"],
                    timeout_seconds=180,
                ),
            ]
        
        # Determina se requer aprovação baseado na severidade
        requires_approval = incident.severity in (IncidentSeverity.HIGH, IncidentSeverity.CRITICAL)
        
        # Calcula duração estimada
        estimated_duration = sum(s.timeout_seconds for s in steps)
        
        plan = RecoveryPlan(
            plan_id=plan_id,
            incident_id=incident.incident_id,
            brand_id=incident.brand_id,
            steps=steps,
            estimated_duration_seconds=estimated_duration,
            requires_approval=requires_approval,
            risk_level=incident.severity.value,
        )
        
        self._plans[plan_id] = plan
        return plan
    
    def register_incident(self, incident: Incident) -> str:
        """Registra um novo incidente."""
        self._incidents[incident.incident_id] = incident
        self._execution_logs[incident.incident_id] = []
        return incident.incident_id
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Recupera um incidente pelo ID."""
        return self._incidents.get(incident_id)
    
    def get_plan(self, plan_id: str) -> Optional[RecoveryPlan]:
        """Recupera um plano pelo ID."""
        return self._plans.get(plan_id)
    
    def list_incidents(
        self,
        brand_id: Optional[str] = None,
        severity: Optional[IncidentSeverity] = None
    ) -> List[Incident]:
        """Lista incidentes com filtros opcionais."""
        incidents = list(self._incidents.values())
        if brand_id:
            incidents = [i for i in incidents if i.brand_id == brand_id]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        return incidents
