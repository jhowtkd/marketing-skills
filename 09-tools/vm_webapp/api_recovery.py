"""API v2 Recovery Orchestration Endpoints - v28.

Endpoints:
- GET  /api/v2/brands/{brand_id}/recovery/status
- POST /api/v2/brands/{brand_id}/recovery/run
- GET  /api/v2/brands/{brand_id}/recovery/events
- POST /api/v2/brands/{brand_id}/recovery/approve/{request_id}
- POST /api/v2/brands/{brand_id}/recovery/reject/{request_id}
- POST /api/v2/brands/{brand_id}/recovery/freeze/{incident_id}
- POST /api/v2/brands/{brand_id}/recovery/rollback/{run_id}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Path, Body, Query
from pydantic import BaseModel, Field

from vm_webapp.recovery_orchestrator import (
    RecoveryOrchestrator,
    Incident,
    IncidentSeverity,
    IncidentType,
    RecoveryPlan,
)


class IncidentSeverityEnum(str, Enum):
    """Severidade do incidente para API."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentTypeEnum(str, Enum):
    """Tipo de incidente para API."""
    HANDOFF_TIMEOUT = "handoff_timeout"
    APPROVAL_SLA_BREACH = "approval_sla_breach"
    QUALITY_REGRESSION = "quality_regression"
    SYSTEM_FAILURE = "system_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class RunRequest(BaseModel):
    """Request body for run endpoint."""
    incident_type: IncidentTypeEnum = Field(..., description="Type of incident")
    severity: IncidentSeverityEnum = Field(..., description="Severity level")
    description: Optional[str] = Field(default=None, description="Description of the incident")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ApproveRequest(BaseModel):
    """Request body for approve endpoint."""
    approved_by: str = Field(..., description="ID of user approving")
    reason: Optional[str] = Field(default=None, description="Reason for approval")


class RejectRequest(BaseModel):
    """Request body for reject endpoint."""
    rejected_by: str = Field(..., description="ID of user rejecting")
    reason: Optional[str] = Field(default=None, description="Reason for rejection")


class FreezeRequest(BaseModel):
    """Request body for freeze endpoint."""
    reason: Optional[str] = Field(default=None, description="Reason for freezing")


class RollbackRequest(BaseModel):
    """Request body for rollback endpoint."""
    reason: Optional[str] = Field(default=None, description="Reason for rollback")


class RecoveryStepResponse(BaseModel):
    """Response model for recovery step."""
    step_id: str
    name: str
    action: str
    depends_on: list[str] = Field(default_factory=list)
    timeout_seconds: int
    max_retries: int


class RecoveryPlanResponse(BaseModel):
    """Response model for recovery plan."""
    plan_id: str
    incident_id: str
    brand_id: str
    steps: list[RecoveryStepResponse] = Field(default_factory=list)
    estimated_duration_seconds: int
    requires_approval: bool
    risk_level: str
    created_at: str


class RunResponse(BaseModel):
    """Response model for run endpoint."""
    run_id: str
    brand_id: str
    incident_id: str
    status: str
    plan: RecoveryPlanResponse
    auto_executed: bool = False
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    started_at: str
    estimated_completion_at: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    brand_id: str
    state: str
    version: str = "v28"
    metrics: dict[str, int] = Field(default_factory=dict)
    active_incidents: list[dict[str, Any]] = Field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    recent_events: list[dict[str, Any]] = Field(default_factory=list)


class EventsResponse(BaseModel):
    """Response model for events endpoint."""
    events: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    limit: int = 100
    offset: int = 0


class ApproveResponse(BaseModel):
    """Response model for approve endpoint."""
    approval_request_id: str
    brand_id: str
    status: str
    approved_by: str
    approved_at: str
    recovery_status: str


class RejectResponse(BaseModel):
    """Response model for reject endpoint."""
    approval_request_id: str
    brand_id: str
    status: str
    rejected_by: str
    rejection_reason: Optional[str] = None
    rejected_at: str


class FreezeResponse(BaseModel):
    """Response model for freeze endpoint."""
    incident_id: str
    brand_id: str
    status: str
    frozen_at: str
    reason: Optional[str] = None


class RollbackResponse(BaseModel):
    """Response model for rollback endpoint."""
    run_id: str
    brand_id: str
    status: str
    rolled_back_at: str
    reason: Optional[str] = None
    affected_steps: list[str] = Field(default_factory=list)


# Router
router = APIRouter(prefix="/api/v2/brands", tags=["recovery"])

# Global orchestrator instance
_recovery_orchestrator = RecoveryOrchestrator()

# In-memory storage for demo (in production, use database)
_recovery_runs: dict[str, dict[str, Any]] = {}  # run_id -> run info
_recovery_events: list[dict[str, Any]] = []
_approval_requests: dict[str, dict[str, Any]] = {}  # request_id -> approval request
_frozen_incidents: dict[str, dict[str, Any]] = {}  # incident_id -> freeze info
_recovery_metrics: dict[str, int] = {
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "auto_runs": 0,
    "manual_runs": 0,
    "approval_requests": 0,
    "approved_requests": 0,
    "rejected_requests": 0,
    "frozen_incidents": 0,
    "rolled_back_runs": 0,
}


def _severity_enum_to_class(severity: IncidentSeverityEnum) -> IncidentSeverity:
    """Convert API severity enum to internal class."""
    mapping = {
        IncidentSeverityEnum.LOW: IncidentSeverity.LOW,
        IncidentSeverityEnum.MEDIUM: IncidentSeverity.MEDIUM,
        IncidentSeverityEnum.HIGH: IncidentSeverity.HIGH,
        IncidentSeverityEnum.CRITICAL: IncidentSeverity.CRITICAL,
    }
    return mapping.get(severity, IncidentSeverity.MEDIUM)


def _type_enum_to_class(incident_type: IncidentTypeEnum) -> IncidentType:
    """Convert API incident type enum to internal class."""
    mapping = {
        IncidentTypeEnum.HANDOFF_TIMEOUT: IncidentType.HANDOFF_TIMEOUT,
        IncidentTypeEnum.APPROVAL_SLA_BREACH: IncidentType.APPROVAL_SLA_BREACH,
        IncidentTypeEnum.QUALITY_REGRESSION: IncidentType.QUALITY_REGRESSION,
        IncidentTypeEnum.SYSTEM_FAILURE: IncidentType.SYSTEM_FAILURE,
        IncidentTypeEnum.RESOURCE_EXHAUSTION: IncidentType.RESOURCE_EXHAUSTION,
    }
    return mapping.get(incident_type, IncidentType.SYSTEM_FAILURE)


def _record_event(brand_id: str, event_type: str, details: dict[str, Any]) -> None:
    """Record recovery event."""
    _recovery_events.append({
        "brand_id": brand_id,
        "event_type": event_type,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _plan_to_response(plan: RecoveryPlan) -> RecoveryPlanResponse:
    """Convert RecoveryPlan to RecoveryPlanResponse."""
    return RecoveryPlanResponse(
        plan_id=plan.plan_id,
        incident_id=plan.incident_id,
        brand_id=plan.brand_id,
        steps=[
            RecoveryStepResponse(
                step_id=s.step_id,
                name=s.name,
                action=s.action,
                depends_on=s.depends_on,
                timeout_seconds=s.timeout_seconds,
                max_retries=s.max_retries,
            )
            for s in plan.steps
        ],
        estimated_duration_seconds=plan.estimated_duration_seconds,
        requires_approval=plan.requires_approval,
        risk_level=plan.risk_level,
        created_at=plan.created_at,
    )


@router.get("/{brand_id}/recovery/status", response_model=StatusResponse)
async def get_recovery_status(
    brand_id: str = Path(..., description="Brand ID")
) -> StatusResponse:
    """Get recovery orchestration status for a brand."""
    # Get active incidents for this brand
    active_incidents = _recovery_orchestrator.list_incidents(brand_id=brand_id)
    
    # Get pending approvals for this brand
    pending_approvals = [
        {
            "request_id": req_id,
            "run_id": req["run_id"],
            "incident_type": req["incident_type"],
            "severity": req["severity"],
            "requested_at": req["requested_at"],
        }
        for req_id, req in _approval_requests.items()
        if req["brand_id"] == brand_id and req["status"] == "pending"
    ]
    
    # Get recent events for this brand
    brand_events = [
        e for e in _recovery_events
        if e["brand_id"] == brand_id
    ][-10:]  # Last 10 events
    
    # Determine state
    state = "idle"
    if pending_approvals:
        state = "awaiting_approval"
    elif active_incidents:
        state = "active"
    elif brand_id in _frozen_incidents:
        state = "frozen"
    
    return StatusResponse(
        brand_id=brand_id,
        state=state,
        version="v28",
        metrics={
            "total_runs": _recovery_metrics["total_runs"],
            "successful_runs": _recovery_metrics["successful_runs"],
            "failed_runs": _recovery_metrics["failed_runs"],
            "auto_runs": _recovery_metrics["auto_runs"],
            "manual_runs": _recovery_metrics["manual_runs"],
            "pending_approvals": len(pending_approvals),
        },
        active_incidents=[
            {
                "incident_id": i.incident_id,
                "type": i.incident_type.value,
                "severity": i.severity.value,
                "description": i.description,
                "timestamp": i.timestamp,
            }
            for i in active_incidents
        ],
        pending_approvals=pending_approvals,
        recent_events=brand_events,
    )


@router.post("/{brand_id}/recovery/run", response_model=RunResponse)
async def run_recovery(
    brand_id: str = Path(..., description="Brand ID"),
    request: RunRequest = Body(...),
) -> RunResponse:
    """Start a new recovery orchestration run."""
    # Create incident
    incident_id = f"inc-{brand_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    incident = Incident(
        incident_id=incident_id,
        brand_id=brand_id,
        incident_type=_type_enum_to_class(request.incident_type),
        severity=_severity_enum_to_class(request.severity),
        description=request.description or f"{request.incident_type.value} incident",
        context=request.context,
    )
    
    # Register incident
    _recovery_orchestrator.register_incident(incident)
    
    # Create recovery plan
    plan = _recovery_orchestrator.plan_recovery_chain(incident)
    
    # Generate run ID
    run_id = f"run-{incident_id}"
    
    # Determine if auto-execution is allowed
    auto_executed = False
    approval_request_id = None
    
    if not plan.requires_approval:
        # Auto-execute for low severity
        auto_executed = True
        _recovery_metrics["auto_runs"] += 1
        status = "started"
        _record_event(brand_id, "recovery_auto_started", {
            "run_id": run_id,
            "incident_id": incident_id,
            "incident_type": request.incident_type.value,
        })
    else:
        # Create approval request for high severity
        approval_request_id = f"approval-{run_id}"
        _approval_requests[approval_request_id] = {
            "request_id": approval_request_id,
            "run_id": run_id,
            "brand_id": brand_id,
            "incident_id": incident_id,
            "incident_type": request.incident_type.value,
            "severity": request.severity.value,
            "plan": plan,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        _recovery_metrics["approval_requests"] += 1
        status = "pending_approval"
        _record_event(brand_id, "recovery_approval_requested", {
            "run_id": run_id,
            "approval_request_id": approval_request_id,
            "incident_id": incident_id,
        })
    
    # Store run info
    _recovery_runs[run_id] = {
        "run_id": run_id,
        "brand_id": brand_id,
        "incident_id": incident_id,
        "status": status,
        "plan": plan,
        "auto_executed": auto_executed,
        "approval_request_id": approval_request_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Update metrics
    _recovery_metrics["total_runs"] += 1
    
    # Calculate estimated completion
    estimated_completion = None
    if plan.estimated_duration_seconds > 0:
        estimated_completion = datetime.now(timezone.utc).isoformat()
    
    return RunResponse(
        run_id=run_id,
        brand_id=brand_id,
        incident_id=incident_id,
        status=status,
        plan=_plan_to_response(plan),
        auto_executed=auto_executed,
        requires_approval=plan.requires_approval,
        approval_request_id=approval_request_id,
        started_at=_recovery_runs[run_id]["started_at"],
        estimated_completion_at=estimated_completion,
    )


@router.get("/{brand_id}/recovery/events", response_model=EventsResponse)
async def get_recovery_events(
    brand_id: str = Path(..., description="Brand ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> EventsResponse:
    """Get recovery events for a brand."""
    # Filter events for this brand
    brand_events = [
        e for e in _recovery_events
        if e["brand_id"] == brand_id
    ]
    
    total = len(brand_events)
    
    # Apply pagination
    paginated_events = brand_events[offset:offset + limit]
    
    return EventsResponse(
        events=paginated_events,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{brand_id}/recovery/approve/{request_id}", response_model=ApproveResponse)
async def approve_recovery(
    brand_id: str = Path(..., description="Brand ID"),
    request_id: str = Path(..., description="Approval request ID"),
    request: ApproveRequest = Body(...),
) -> ApproveResponse:
    """Approve a pending recovery request."""
    if request_id not in _approval_requests:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    approval_req = _approval_requests[request_id]
    
    if approval_req["brand_id"] != brand_id:
        raise HTTPException(status_code=404, detail="Approval request not found for this brand")
    
    if approval_req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Approval request is not pending")
    
    # Update approval request
    approval_req["status"] = "approved"
    approval_req["approved_by"] = request.approved_by
    approval_req["approval_reason"] = request.reason
    approval_req["approved_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update run status
    run_id = approval_req["run_id"]
    if run_id in _recovery_runs:
        _recovery_runs[run_id]["status"] = "started"
    
    # Update metrics
    _recovery_metrics["approved_requests"] += 1
    _recovery_metrics["manual_runs"] += 1
    
    # Record event
    _record_event(brand_id, "recovery_approved", {
        "run_id": run_id,
        "approval_request_id": request_id,
        "approved_by": request.approved_by,
    })
    
    return ApproveResponse(
        approval_request_id=request_id,
        brand_id=brand_id,
        status="approved",
        approved_by=request.approved_by,
        approved_at=approval_req["approved_at"],
        recovery_status="started",
    )


@router.post("/{brand_id}/recovery/reject/{request_id}", response_model=RejectResponse)
async def reject_recovery(
    brand_id: str = Path(..., description="Brand ID"),
    request_id: str = Path(..., description="Approval request ID"),
    request: RejectRequest = Body(...),
) -> RejectResponse:
    """Reject a pending recovery request."""
    if request_id not in _approval_requests:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    approval_req = _approval_requests[request_id]
    
    if approval_req["brand_id"] != brand_id:
        raise HTTPException(status_code=404, detail="Approval request not found for this brand")
    
    if approval_req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Approval request is not pending")
    
    # Update approval request
    approval_req["status"] = "rejected"
    approval_req["rejected_by"] = request.rejected_by
    approval_req["rejection_reason"] = request.reason
    approval_req["rejected_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update run status
    run_id = approval_req["run_id"]
    if run_id in _recovery_runs:
        _recovery_runs[run_id]["status"] = "rejected"
    
    # Update metrics
    _recovery_metrics["rejected_requests"] += 1
    
    # Record event
    _record_event(brand_id, "recovery_rejected", {
        "run_id": run_id,
        "approval_request_id": request_id,
        "rejected_by": request.rejected_by,
        "reason": request.reason,
    })
    
    return RejectResponse(
        approval_request_id=request_id,
        brand_id=brand_id,
        status="rejected",
        rejected_by=request.rejected_by,
        rejection_reason=request.reason,
        rejected_at=approval_req["rejected_at"],
    )


@router.post("/{brand_id}/recovery/freeze/{incident_id}", response_model=FreezeResponse)
async def freeze_recovery(
    brand_id: str = Path(..., description="Brand ID"),
    incident_id: str = Path(..., description="Incident ID"),
    request: FreezeRequest = Body(...),
) -> FreezeResponse:
    """Freeze a recovery in progress."""
    # Check if incident exists
    incident = _recovery_orchestrator.get_incident(incident_id)
    
    if not incident or incident.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    frozen_at = datetime.now(timezone.utc).isoformat()
    
    # Store freeze info
    _frozen_incidents[incident_id] = {
        "incident_id": incident_id,
        "brand_id": brand_id,
        "frozen_at": frozen_at,
        "reason": request.reason,
    }
    
    # Update metrics
    _recovery_metrics["frozen_incidents"] += 1
    
    # Record event
    _record_event(brand_id, "recovery_frozen", {
        "incident_id": incident_id,
        "reason": request.reason,
    })
    
    return FreezeResponse(
        incident_id=incident_id,
        brand_id=brand_id,
        status="frozen",
        frozen_at=frozen_at,
        reason=request.reason,
    )


@router.post("/{brand_id}/recovery/rollback/{run_id}", response_model=RollbackResponse)
async def rollback_recovery(
    brand_id: str = Path(..., description="Brand ID"),
    run_id: str = Path(..., description="Run ID"),
    request: RollbackRequest = Body(...),
) -> RollbackResponse:
    """Rollback a completed recovery."""
    if run_id not in _recovery_runs:
        raise HTTPException(status_code=404, detail="Recovery run not found")
    
    run = _recovery_runs[run_id]
    
    if run["brand_id"] != brand_id:
        raise HTTPException(status_code=404, detail="Recovery run not found for this brand")
    
    rolled_back_at = datetime.now(timezone.utc).isoformat()
    
    # Get affected steps from plan
    plan = run.get("plan", None)
    affected_steps = [s.step_id for s in plan.steps] if plan else []
    
    # Update run status
    run["status"] = "rolled_back"
    run["rolled_back_at"] = rolled_back_at
    run["rollback_reason"] = request.reason
    
    # Update metrics
    _recovery_metrics["rolled_back_runs"] += 1
    
    # Record event
    _record_event(brand_id, "recovery_rolled_back", {
        "run_id": run_id,
        "reason": request.reason,
        "affected_steps": affected_steps,
    })
    
    return RollbackResponse(
        run_id=run_id,
        brand_id=brand_id,
        status="rolled_back",
        rolled_back_at=rolled_back_at,
        reason=request.reason,
        affected_steps=affected_steps,
    )
