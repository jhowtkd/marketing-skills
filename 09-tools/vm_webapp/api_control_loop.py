"""API v2 Control Loop Endpoints - v26.

Endpoints:
- GET  /api/v2/brands/{brand_id}/control-loop/status
- POST /api/v2/brands/{brand_id}/control-loop/run
- GET  /api/v2/brands/{brand_id}/control-loop/events
- POST /api/v2/brands/{brand_id}/control-loop/proposals/{id}/apply
- POST /api/v2/brands/{brand_id}/control-loop/proposals/{id}/reject
- POST /api/v2/brands/{brand_id}/control-loop/freeze
- POST /api/v2/brands/{brand_id}/control-loop/rollback
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from vm_webapp.online_control_loop import (
    OnlineControlLoop,
    ControlLoopState,
    AdjustmentSeverity,
    MicroAdjustment,
    AdjustmentType,
)
from vm_webapp.control_loop_sentinel import RegressionSentinel


# Request/Response models
class ApplyRequest(BaseModel):
    """Request body for apply endpoint."""
    approved: bool = Field(default=False, description="Explicit approval for medium/high severity")


class RejectRequest(BaseModel):
    """Request body for reject endpoint."""
    reason: Optional[str] = Field(default=None, description="Reason for rejection")


class FreezeRequest(BaseModel):
    """Request body for freeze endpoint."""
    reason: Optional[str] = Field(default=None, description="Reason for freezing")


class RollbackRequest(BaseModel):
    """Request body for rollback endpoint."""
    proposal_id: Optional[str] = Field(default=None, description="Specific proposal to rollback")


class ProposalResponse(BaseModel):
    """Response model for proposal operations."""
    proposal_id: str
    state: str
    adjustment_type: str
    target_gate: str
    current_value: float
    proposed_value: float
    delta: float
    severity: str
    requires_approval: bool
    estimated_impact: dict[str, float]
    applied_at: Optional[str] = None
    rejected_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    reason: Optional[str] = None


class CycleResponse(BaseModel):
    """Response model for cycle operations."""
    cycle_id: str
    brand_id: str
    state: str
    started_at: str
    completed_at: Optional[str] = None
    regressions_detected: int = 0
    proposals_generated: int = 0
    proposals: list[ProposalResponse] = Field(default_factory=list)


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    brand_id: str
    state: str
    cycle_id: Optional[str] = None
    last_run_at: Optional[str] = None
    active_proposals: list[ProposalResponse] = Field(default_factory=list)
    active_regressions: list[dict[str, Any]] = Field(default_factory=list)
    version: str = "v26"


class EventsResponse(BaseModel):
    """Response model for events endpoint."""
    events: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    limit: int = 100
    offset: int = 0


class RollbackResponse(BaseModel):
    """Response model for rollback endpoint."""
    rolled_back: list[str] = Field(default_factory=list)
    rolled_back_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Router
router = APIRouter(prefix="/api/v2/brands", tags=["control-loop"])

# Global instances (in production, use dependency injection)
control_loop = OnlineControlLoop()
sentinel = RegressionSentinel()

# In-memory storage for demo (in production, use database)
_brand_cycles: dict[str, str] = {}  # brand_id -> active_cycle_id
_frozen_brands: dict[str, dict[str, Any]] = {}  # brand_id -> freeze info
_events: list[dict[str, Any]] = []


def _record_event(brand_id: str, event_type: str, details: dict[str, Any]) -> None:
    """Record control loop event."""
    _events.append({
        "brand_id": brand_id,
        "event_type": event_type,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _adjustment_to_response(adj: MicroAdjustment) -> ProposalResponse:
    """Convert MicroAdjustment to ProposalResponse."""
    return ProposalResponse(
        proposal_id=adj.adjustment_id,
        state=adj.state,
        adjustment_type=adj.adjustment_type.value,
        target_gate=adj.target_gate,
        current_value=adj.current_value,
        proposed_value=adj.proposed_value,
        delta=adj.delta,
        severity=adj.severity.value,
        requires_approval=adj.requires_approval,
        estimated_impact=adj.estimated_impact,
        applied_at=adj.applied_at,
        rolled_back_at=adj.rolled_back_at,
    )


@router.get("/{brand_id}/control-loop/status", response_model=StatusResponse)
async def get_control_loop_status(
    brand_id: str = Path(..., description="Brand ID"),
) -> StatusResponse:
    """Get current control loop status for a brand."""
    # Check if brand is frozen
    if brand_id in _frozen_brands:
        return StatusResponse(
            brand_id=brand_id,
            state="frozen",
            active_proposals=[],
            active_regressions=[],
        )
    
    # Get active cycle
    cycle_id = _brand_cycles.get(brand_id)
    if cycle_id is None:
        return StatusResponse(
            brand_id=brand_id,
            state="idle",
            active_proposals=[],
            active_regressions=[],
        )
    
    cycle = control_loop.get_cycle(cycle_id)
    if cycle is None:
        return StatusResponse(
            brand_id=brand_id,
            state="idle",
            active_proposals=[],
            active_regressions=[],
        )
    
    # Get active proposals (pending adjustments)
    active_proposals = [
        _adjustment_to_response(adj)
        for adj in cycle.adjustments
        if adj.state == "pending"
    ]
    
    # Get active regressions
    active_regressions = [
        {
            "metric": sig.metric_name,
            "severity": sig.severity,
            "delta_pct": sig.delta_pct,
            "detected_at": sig.detected_at,
        }
        for sig in cycle.regression_signals
    ]
    
    return StatusResponse(
        brand_id=brand_id,
        state=cycle.state.value,
        cycle_id=cycle.cycle_id,
        last_run_at=cycle.started_at,
        active_proposals=active_proposals,
        active_regressions=active_regressions,
    )


@router.post("/{brand_id}/control-loop/run", response_model=CycleResponse)
async def run_control_loop(
    brand_id: str = Path(..., description="Brand ID"),
) -> CycleResponse:
    """Run a new control loop cycle for a brand."""
    # Check if frozen
    if brand_id in _frozen_brands:
        raise HTTPException(status_code=403, detail="Control loop is frozen for this brand")
    
    # Check if already running
    existing_cycle_id = _brand_cycles.get(brand_id)
    if existing_cycle_id:
        existing_cycle = control_loop.get_cycle(existing_cycle_id)
        if existing_cycle and existing_cycle.state not in [
            ControlLoopState.COMPLETED,
            ControlLoopState.BLOCKED,
        ]:
            raise HTTPException(
                status_code=409,
                detail=f"Cycle {existing_cycle_id} is already running"
            )
    
    # Start new cycle
    cycle = control_loop.start_cycle(brand_id=brand_id)
    _brand_cycles[brand_id] = cycle.cycle_id
    
    # Simulate regression detection
    # In production, this would use real metrics
    mock_metrics = {
        "v1_score": 65.0,
        "approval_rate": 0.70,
        "incident_rate": 0.04,
    }
    
    # Add metric points to sentinel
    run_id = f"run-{brand_id}"
    sentinel.add_metric_point(run_id=run_id, metrics=mock_metrics)
    
    # Detect regressions
    regressions = sentinel.detect_regression(
        run_id=run_id,
        current_metrics=mock_metrics,
    )
    
    control_loop.add_regression_signals_to_cycle(cycle.cycle_id, regressions)
    
    # Generate proposals based on regressions
    current_params = {
        "v1_score_min": 70.0,
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    
    proposals = control_loop.propose(
        brand_id=brand_id,
        signals=regressions,
        current_params=current_params,
    )
    
    for proposal in proposals:
        control_loop.add_adjustment_to_cycle(cycle.cycle_id, proposal)
    
    # Record event
    _record_event(brand_id, "cycle_started", {
        "cycle_id": cycle.cycle_id,
        "regressions_detected": len(regressions),
        "proposals_generated": len(proposals),
    })
    
    # Update cycle state
    control_loop.update_cycle_state(cycle.cycle_id, ControlLoopState.PROPOSING)
    
    return CycleResponse(
        cycle_id=cycle.cycle_id,
        brand_id=brand_id,
        state=cycle.state.value,
        started_at=cycle.started_at,
        regressions_detected=len(regressions),
        proposals_generated=len(proposals),
        proposals=[_adjustment_to_response(p) for p in proposals],
    )


@router.get("/{brand_id}/control-loop/events", response_model=EventsResponse)
async def get_control_loop_events(
    brand_id: str = Path(..., description="Brand ID"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    since: Optional[str] = Query(default=None, description="ISO timestamp filter"),
) -> EventsResponse:
    """Get control loop events for a brand."""
    # Filter events by brand
    brand_events = [e for e in _events if e.get("brand_id") == brand_id]
    
    # Apply time filter if provided
    if since:
        brand_events = [
            e for e in brand_events
            if e.get("timestamp", "") >= since
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


@router.post("/{brand_id}/control-loop/proposals/{proposal_id}/apply", response_model=ProposalResponse)
async def apply_proposal(
    brand_id: str = Path(..., description="Brand ID"),
    proposal_id: str = Path(..., description="Proposal ID"),
    request: ApplyRequest = Body(default_factory=ApplyRequest),
) -> ProposalResponse:
    """Apply a control loop proposal."""
    # Check if frozen
    if brand_id in _frozen_brands:
        raise HTTPException(status_code=403, detail="Control loop is frozen")
    
    # Find proposal in active cycle
    cycle_id = _brand_cycles.get(brand_id)
    if not cycle_id:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    cycle = control_loop.get_cycle(cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    # Find the adjustment
    adjustment = None
    for adj in cycle.adjustments:
        if adj.adjustment_id == proposal_id:
            adjustment = adj
            break
    
    if not adjustment:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Try to apply
    result = control_loop.apply(
        adjustment_id=proposal_id,
        adjustment=adjustment,
        approved=request.approved,
    )
    
    if not result:
        if adjustment.requires_approval and not request.approved:
            raise HTTPException(
                status_code=403,
                detail="Proposal requires explicit approval"
            )
        raise HTTPException(status_code=409, detail="Could not apply proposal")
    
    # Record event
    _record_event(brand_id, "proposal_applied", {
        "proposal_id": proposal_id,
        "adjustment_type": adjustment.adjustment_type.value,
        "delta": adjustment.delta,
    })
    
    return _adjustment_to_response(adjustment)


@router.post("/{brand_id}/control-loop/proposals/{proposal_id}/reject", response_model=ProposalResponse)
async def reject_proposal(
    brand_id: str = Path(..., description="Brand ID"),
    proposal_id: str = Path(..., description="Proposal ID"),
    request: RejectRequest = Body(default_factory=RejectRequest),
) -> ProposalResponse:
    """Reject a control loop proposal."""
    # Find proposal in active cycle
    cycle_id = _brand_cycles.get(brand_id)
    if not cycle_id:
        raise HTTPException(status_code=404, detail="No active cycle found")
    
    cycle = control_loop.get_cycle(cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    # Find the adjustment
    adjustment = None
    for adj in cycle.adjustments:
        if adj.adjustment_id == proposal_id:
            adjustment = adj
            break
    
    if not adjustment:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Check if already applied
    if adjustment.state == "applied":
        raise HTTPException(status_code=409, detail="Cannot reject already applied proposal")
    
    # Mark as rejected
    adjustment.state = "rejected"
    rejected_at = datetime.now(timezone.utc).isoformat()
    
    # Record event
    _record_event(brand_id, "proposal_rejected", {
        "proposal_id": proposal_id,
        "reason": request.reason,
    })
    
    response = _adjustment_to_response(adjustment)
    response.rejected_at = rejected_at
    response.reason = request.reason
    
    return response


@router.get("/{brand_id}/control-loop/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    brand_id: str = Path(..., description="Brand ID"),
    proposal_id: str = Path(..., description="Proposal ID"),
) -> ProposalResponse:
    """Get proposal details."""
    # Find proposal in any cycle
    adjustment = None
    for cycle in control_loop._cycles.values():
        for adj in cycle.adjustments:
            if adj.adjustment_id == proposal_id:
                adjustment = adj
                break
        if adjustment:
            break
    
    if not adjustment:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return _adjustment_to_response(adjustment)


@router.post("/{brand_id}/control-loop/freeze")
async def freeze_control_loop(
    brand_id: str = Path(..., description="Brand ID"),
    request: FreezeRequest = Body(default_factory=FreezeRequest),
) -> dict[str, Any]:
    """Freeze the control loop for a brand."""
    frozen_at = datetime.now(timezone.utc).isoformat()
    
    _frozen_brands[brand_id] = {
        "frozen_at": frozen_at,
        "reason": request.reason,
    }
    
    # Update active cycle if exists
    cycle_id = _brand_cycles.get(brand_id)
    if cycle_id:
        control_loop.update_cycle_state(cycle_id, ControlLoopState.BLOCKED)
    
    # Record event
    _record_event(brand_id, "control_loop_frozen", {
        "reason": request.reason,
    })
    
    return {
        "brand_id": brand_id,
        "state": "frozen",
        "frozen_at": frozen_at,
        "reason": request.reason,
    }


@router.post("/{brand_id}/control-loop/rollback", response_model=RollbackResponse)
async def rollback_control_loop(
    brand_id: str = Path(..., description="Brand ID"),
    request: RollbackRequest = Body(default_factory=RollbackRequest),
) -> RollbackResponse:
    """Rollback applied proposals for a brand."""
    rolled_back: list[str] = []
    
    # Find active cycle
    cycle_id = _brand_cycles.get(brand_id)
    if cycle_id:
        cycle = control_loop.get_cycle(cycle_id)
        if cycle:
            # Rollback specific proposal or all applied
            if request.proposal_id:
                # Rollback specific
                for adj in cycle.adjustments:
                    if adj.adjustment_id == request.proposal_id and adj.state == "applied":
                        if control_loop.rollback(request.proposal_id):
                            rolled_back.append(request.proposal_id)
                        break
            else:
                # Rollback all applied
                for adj in list(cycle.adjustments):
                    if adj.state == "applied":
                        if control_loop.rollback(adj.adjustment_id):
                            rolled_back.append(adj.adjustment_id)
    
    # Record event
    if rolled_back:
        _record_event(brand_id, "control_loop_rollback", {
            "rolled_back": rolled_back,
        })
    
    return RollbackResponse(rolled_back=rolled_back)


@router.get("/{brand_id}/control-loop/metrics")
async def get_control_loop_metrics(
    brand_id: str = Path(..., description="Brand ID"),
) -> str:
    """Get control loop metrics in Prometheus format."""
    from vm_webapp.observability import render_prometheus
    
    # Get status for metrics
    status = control_loop.get_status()
    
    # Generate Prometheus format metrics
    metrics_lines = [
        "# HELP control_loop_cycles_total Total number of control loop cycles",
        "# TYPE control_loop_cycles_total counter",
        f'control_loop_cycles_total{{brand="{brand_id}"}} {status.get("total_cycles", 0)}',
        "",
        "# HELP control_loop_regressions_detected_total Total regressions detected",
        "# TYPE control_loop_regressions_detected_total counter",
        f'control_loop_regressions_detected_total{{brand="{brand_id}"}} 0',
        "",
        "# HELP control_loop_mitigations_applied_total Total mitigations applied",
        "# TYPE control_loop_mitigations_applied_total counter",
        f'control_loop_mitigations_applied_total{{brand="{brand_id}"}} {status.get("total_adjustments_applied", 0)}',
        "",
        "# HELP control_loop_blocked_total Total blocked operations",
        "# TYPE control_loop_blocked_total counter",
        f'control_loop_blocked_total{{brand="{brand_id}"}} 0',
        "",
        "# HELP control_loop_rollbacks_total Total rollbacks",
        "# TYPE control_loop_rollbacks_total counter",
        f'control_loop_rollbacks_total{{brand="{brand_id}"}} {status.get("total_adjustments_rolled_back", 0)}',
        "",
        "# HELP control_loop_time_to_detect_seconds Time to detect regression",
        "# TYPE control_loop_time_to_detect_seconds gauge",
        f'control_loop_time_to_detect_seconds{{brand="{brand_id}"}} 0',
        "",
        "# HELP control_loop_time_to_mitigate_seconds Time to mitigate regression",
        "# TYPE control_loop_time_to_mitigate_seconds gauge",
        f'control_loop_time_to_mitigate_seconds{{brand="{brand_id}"}} 0',
    ]
    
    return "\n".join(metrics_lines)
