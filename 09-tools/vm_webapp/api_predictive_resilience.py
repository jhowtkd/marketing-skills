"""API v2 Predictive Resilience Endpoints - v27.

Endpoints:
- GET  /api/v2/brands/{brand_id}/predictive-resilience/status
- POST /api/v2/brands/{brand_id}/predictive-resilience/run
- GET  /api/v2/brands/{brand_id}/predictive-resilience/events
- GET  /api/v2/brands/{brand_id}/predictive-resilience/proposals/{id}
- POST /api/v2/brands/{brand_id}/predictive-resilience/proposals/{id}/apply
- POST /api/v2/brands/{brand_id}/predictive-resilience/proposals/{id}/reject
- POST /api/v2/brands/{brand_id}/predictive-resilience/freeze
- POST /api/v2/brands/{brand_id}/predictive-resilience/unfreeze
- POST /api/v2/brands/{brand_id}/predictive-resilience/rollback
- GET  /api/v2/brands/{brand_id}/predictive-resilience/metrics
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from vm_webapp.predictive_resilience import (
    PredictiveResilienceEngine,
    ResilienceScore,
    RiskClassification,
    MitigationProposal,
    MitigationSeverity,
    MitigationType,
    PredictiveSignal,
)


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


class ResilienceScoreResponse(BaseModel):
    """Response model for resilience score."""
    incident_component: float
    handoff_component: float
    approval_component: float
    composite_score: float
    risk_class: str
    timestamp: str


class ProposalResponse(BaseModel):
    """Response model for proposal operations."""
    proposal_id: str
    signal_id: str
    state: str
    mitigation_type: str
    severity: str
    description: str
    can_auto_apply: bool
    requires_escalation: bool
    estimated_impact: dict[str, float]
    created_at: str
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class SignalResponse(BaseModel):
    """Response model for predictive signals."""
    signal_id: str
    metric_name: str
    current_value: float
    predicted_value: float
    delta: float
    delta_pct: float
    confidence: float
    forecast_horizon_hours: int
    severity: str
    timestamp: str


class CycleResponse(BaseModel):
    """Response model for cycle operations."""
    cycle_id: str
    brand_id: str
    state: str
    started_at: str
    completed_at: Optional[str] = None
    score: Optional[ResilienceScoreResponse] = None
    signals_detected: int = 0
    signals: list[SignalResponse] = Field(default_factory=list)
    proposals_generated: int = 0
    proposals: list[ProposalResponse] = Field(default_factory=list)


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    brand_id: str
    state: str
    version: str = "v27"
    cycle_id: Optional[str] = None
    last_run_at: Optional[str] = None
    resilience_score: Optional[ResilienceScoreResponse] = None
    active_proposals: list[ProposalResponse] = Field(default_factory=list)
    active_signals: list[SignalResponse] = Field(default_factory=list)
    cycles_total: int = 0
    proposals_total: int = 0
    proposals_applied: int = 0
    proposals_rejected: int = 0
    proposals_rolled_back: int = 0
    false_positives_total: int = 0
    frozen_brands: int = 0


class RunResponse(BaseModel):
    """Response model for run endpoint."""
    cycle_id: str
    brand_id: str
    enabled: bool = True
    score: ResilienceScoreResponse
    signals_detected: int
    proposals_generated: int
    proposals_applied: int
    proposals_pending: int
    freeze_triggered: bool
    proposals: list[ProposalResponse] = Field(default_factory=list)
    signals: list[SignalResponse] = Field(default_factory=list)
    applied_ids: list[str] = Field(default_factory=list)
    pending_ids: list[str] = Field(default_factory=list)


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


class FreezeResponse(BaseModel):
    """Response model for freeze endpoint."""
    brand_id: str
    state: str
    frozen_at: str
    reason: Optional[str] = None


class UnfreezeResponse(BaseModel):
    """Response model for unfreeze endpoint."""
    brand_id: str
    state: str
    unfrozen_at: str


# Router
router = APIRouter(prefix="/api/v2/brands", tags=["predictive-resilience"])

# Global engine instance (in production, use dependency injection)
predictive_engine = PredictiveResilienceEngine()

# In-memory storage for demo (in production, use database)
_brand_cycles: dict[str, str] = {}  # brand_id -> active_cycle_id
_frozen_brands: dict[str, dict[str, Any]] = {}  # brand_id -> freeze info
_events: list[dict[str, Any]] = []
_proposals_store: dict[str, MitigationProposal] = {}  # proposal_id -> proposal


def _record_event(brand_id: str, event_type: str, details: dict[str, Any]) -> None:
    """Record predictive resilience event."""
    _events.append({
        "brand_id": brand_id,
        "event_type": event_type,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _score_to_response(score: ResilienceScore) -> ResilienceScoreResponse:
    """Convert ResilienceScore to ResilienceScoreResponse."""
    return ResilienceScoreResponse(
        incident_component=score.incident_component,
        handoff_component=score.handoff_component,
        approval_component=score.approval_component,
        composite_score=score.composite_score,
        risk_class=score.risk_class.value,
        timestamp=score.timestamp or datetime.now(timezone.utc).isoformat(),
    )


def _signal_to_response(signal: PredictiveSignal) -> SignalResponse:
    """Convert PredictiveSignal to SignalResponse."""
    return SignalResponse(
        signal_id=signal.signal_id,
        metric_name=signal.metric_name,
        current_value=signal.current_value,
        predicted_value=signal.predicted_value,
        delta=signal.delta,
        delta_pct=signal.delta_pct,
        confidence=signal.confidence,
        forecast_horizon_hours=signal.forecast_horizon_hours,
        severity=signal.severity.value,
        timestamp=signal.timestamp or datetime.now(timezone.utc).isoformat(),
    )


def _proposal_to_response(proposal: MitigationProposal) -> ProposalResponse:
    """Convert MitigationProposal to ProposalResponse."""
    return ProposalResponse(
        proposal_id=proposal.proposal_id,
        signal_id=proposal.signal_id,
        state=proposal.state,
        mitigation_type=proposal.mitigation_type.value,
        severity=proposal.severity.value,
        description=proposal.description,
        can_auto_apply=proposal.can_auto_apply,
        requires_escalation=proposal.requires_escalation,
        estimated_impact=proposal.estimated_impact,
        created_at=proposal.created_at or datetime.now(timezone.utc).isoformat(),
        applied_at=proposal.applied_at,
        rolled_back_at=proposal.rolled_back_at,
        rejection_reason=proposal.rejection_reason,
    )


@router.get("/{brand_id}/predictive-resilience/status", response_model=StatusResponse)
async def get_predictive_resilience_status(
    brand_id: str = Path(..., description="Brand ID"),
) -> StatusResponse:
    """Get current predictive resilience status for a brand."""
    # Check if brand is frozen
    is_frozen = predictive_engine.is_brand_frozen(brand_id)
    
    # Get engine status
    engine_status = predictive_engine.get_status()
    
    # Get active cycle
    cycle_id = _brand_cycles.get(brand_id)
    cycle = None
    if cycle_id:
        cycle = predictive_engine.get_cycle(cycle_id)
    
    # Build active proposals list
    active_proposals = []
    active_signals = []
    last_run_at = None
    score_response = None
    
    if cycle:
        last_run_at = cycle.started_at
        
        # Get pending proposals
        for prop in cycle.proposals:
            if prop.state == "pending":
                active_proposals.append(_proposal_to_response(prop))
        
        # Get active signals
        for sig in cycle.signals:
            active_signals.append(_signal_to_response(sig))
        
        # Get score
        if cycle.score:
            score_response = _score_to_response(cycle.score)
    
    return StatusResponse(
        brand_id=brand_id,
        state="frozen" if is_frozen else (cycle.state if cycle else "idle"),
        version=predictive_engine.VERSION,
        cycle_id=cycle_id,
        last_run_at=last_run_at,
        resilience_score=score_response,
        active_proposals=active_proposals,
        active_signals=active_signals,
        cycles_total=engine_status.get("cycles_total", 0),
        proposals_total=engine_status.get("total_proposals", 0),
        proposals_applied=engine_status.get("proposals_applied", 0),
        proposals_rejected=engine_status.get("proposals_rejected", 0),
        proposals_rolled_back=engine_status.get("proposals_rolled_back", 0),
        false_positives_total=engine_status.get("false_positives_total", 0),
        frozen_brands=engine_status.get("frozen_brands", 0),
    )


@router.post("/{brand_id}/predictive-resilience/run", response_model=RunResponse)
async def run_predictive_resilience(
    brand_id: str = Path(..., description="Brand ID"),
    auto_apply_low_risk: bool = Query(default=True, description="Auto-apply low-risk mitigations"),
) -> RunResponse:
    """Run a new predictive resilience cycle for a brand."""
    # Check if frozen
    if predictive_engine.is_brand_frozen(brand_id):
        raise HTTPException(status_code=403, detail="Brand is frozen")
    
    # Check if already running
    existing_cycle_id = _brand_cycles.get(brand_id)
    if existing_cycle_id:
        existing_cycle = predictive_engine.get_cycle(existing_cycle_id)
        if existing_cycle and existing_cycle.state not in ["completed"]:
            raise HTTPException(
                status_code=409,
                detail=f"Cycle {existing_cycle_id} is already running"
            )
    
    # Mock metrics for demo (in production, fetch from monitoring)
    mock_metrics = {
        "incident_rate": 0.12,
        "handoff_timeout_rate": 0.08,
        "approval_sla_breach_rate": 0.05,
    }
    
    # Start new cycle
    cycle = predictive_engine.start_cycle(brand_id=brand_id)
    _brand_cycles[brand_id] = cycle.cycle_id
    
    # Calculate score
    score = predictive_engine.calculate_score(mock_metrics)
    cycle.score = score
    
    # Detect signals
    signals = predictive_engine.detect_signals(mock_metrics)
    cycle.signals = signals
    
    # Generate proposals
    proposals = predictive_engine.generate_proposals(signals)
    cycle.proposals = proposals
    
    # Store proposals
    for prop in proposals:
        _proposals_store[prop.proposal_id] = prop
    
    # Auto-apply low-risk if enabled
    applied_ids = []
    pending_ids = []
    
    for proposal in proposals:
        if auto_apply_low_risk and proposal.can_auto_apply:
            success = predictive_engine.apply_mitigation(
                proposal.proposal_id, proposal
            )
            if success:
                applied_ids.append(proposal.proposal_id)
        else:
            pending_ids.append(proposal.proposal_id)
    
    # Check for critical risk and freeze if needed
    freeze_triggered = False
    if score.risk_class == RiskClassification.CRITICAL:
        freeze_triggered = predictive_engine.evaluate_and_freeze_if_critical(brand_id, score)
    
    # Complete cycle
    predictive_engine.update_cycle_state(cycle.cycle_id, "completed")
    
    # Record event
    _record_event(brand_id, "predictive_cycle_completed", {
        "cycle_id": cycle.cycle_id,
        "score": score.composite_score,
        "risk_class": score.risk_class.value,
        "signals_detected": len(signals),
        "proposals_generated": len(proposals),
        "proposals_applied": len(applied_ids),
        "freeze_triggered": freeze_triggered,
    })
    
    return RunResponse(
        cycle_id=cycle.cycle_id,
        brand_id=brand_id,
        enabled=True,
        score=_score_to_response(score),
        signals_detected=len(signals),
        proposals_generated=len(proposals),
        proposals_applied=len(applied_ids),
        proposals_pending=len(pending_ids),
        freeze_triggered=freeze_triggered,
        proposals=[_proposal_to_response(p) for p in proposals],
        signals=[_signal_to_response(s) for s in signals],
        applied_ids=applied_ids,
        pending_ids=pending_ids,
    )


@router.get("/{brand_id}/predictive-resilience/events", response_model=EventsResponse)
async def get_predictive_resilience_events(
    brand_id: str = Path(..., description="Brand ID"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    since: Optional[str] = Query(default=None, description="ISO timestamp filter"),
) -> EventsResponse:
    """Get predictive resilience events for a brand."""
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


@router.get("/{brand_id}/predictive-resilience/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    brand_id: str = Path(..., description="Brand ID"),
    proposal_id: str = Path(..., description="Proposal ID"),
) -> ProposalResponse:
    """Get proposal details."""
    # Find proposal in store
    proposal = _proposals_store.get(proposal_id)
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return _proposal_to_response(proposal)


@router.post("/{brand_id}/predictive-resilience/proposals/{proposal_id}/apply", response_model=ProposalResponse)
async def apply_proposal(
    brand_id: str = Path(..., description="Brand ID"),
    proposal_id: str = Path(..., description="Proposal ID"),
    request: ApplyRequest = Body(default_factory=ApplyRequest),
) -> ProposalResponse:
    """Apply a predictive resilience proposal."""
    # Check if frozen
    if predictive_engine.is_brand_frozen(brand_id):
        raise HTTPException(status_code=403, detail="Brand is frozen")
    
    # Find proposal
    proposal = _proposals_store.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Try to apply
    result = predictive_engine.apply_mitigation(
        proposal_id=proposal_id,
        proposal=proposal,
        approved=request.approved,
    )
    
    if not result:
        if not proposal.can_auto_apply and not request.approved:
            raise HTTPException(
                status_code=403,
                detail="Proposal requires explicit approval"
            )
        raise HTTPException(status_code=409, detail="Could not apply proposal")
    
    # Record event
    _record_event(brand_id, "proposal_applied", {
        "proposal_id": proposal_id,
        "severity": proposal.severity.value,
        "auto_applied": proposal.can_auto_apply,
    })
    
    return _proposal_to_response(proposal)


@router.post("/{brand_id}/predictive-resilience/proposals/{proposal_id}/reject", response_model=ProposalResponse)
async def reject_proposal(
    brand_id: str = Path(..., description="Brand ID"),
    proposal_id: str = Path(..., description="Proposal ID"),
    request: RejectRequest = Body(default_factory=RejectRequest),
) -> ProposalResponse:
    """Reject a predictive resilience proposal."""
    # Find proposal
    proposal = _proposals_store.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Check if already applied
    if proposal.state == "applied":
        raise HTTPException(status_code=409, detail="Cannot reject already applied proposal")
    
    # Reject
    predictive_engine.reject_mitigation(
        proposal_id=proposal_id,
        proposal=proposal,
        reason=request.reason or "",
    )
    
    # Record event
    _record_event(brand_id, "proposal_rejected", {
        "proposal_id": proposal_id,
        "reason": request.reason,
    })
    
    return _proposal_to_response(proposal)


@router.post("/{brand_id}/predictive-resilience/freeze", response_model=FreezeResponse)
async def freeze_brand(
    brand_id: str = Path(..., description="Brand ID"),
    request: FreezeRequest = Body(default_factory=FreezeRequest),
) -> FreezeResponse:
    """Freeze predictive resilience operations for a brand."""
    # Check if already frozen
    if predictive_engine.is_brand_frozen(brand_id):
        raise HTTPException(status_code=409, detail="Brand is already frozen")
    
    # Freeze
    predictive_engine.freeze_brand(brand_id, reason=request.reason or "Manual freeze")
    
    frozen_at = datetime.now(timezone.utc).isoformat()
    _frozen_brands[brand_id] = {
        "frozen_at": frozen_at,
        "reason": request.reason,
    }
    
    # Record event
    _record_event(brand_id, "brand_frozen", {
        "reason": request.reason,
    })
    
    return FreezeResponse(
        brand_id=brand_id,
        state="frozen",
        frozen_at=frozen_at,
        reason=request.reason,
    )


@router.post("/{brand_id}/predictive-resilience/unfreeze", response_model=UnfreezeResponse)
async def unfreeze_brand(
    brand_id: str = Path(..., description="Brand ID"),
) -> UnfreezeResponse:
    """Unfreeze predictive resilience operations for a brand."""
    # Check if frozen
    if not predictive_engine.is_brand_frozen(brand_id):
        raise HTTPException(status_code=400, detail="Brand is not frozen")
    
    # Unfreeze
    predictive_engine.unfreeze_brand(brand_id)
    
    if brand_id in _frozen_brands:
        del _frozen_brands[brand_id]
    
    unfrozen_at = datetime.now(timezone.utc).isoformat()
    
    # Record event
    _record_event(brand_id, "brand_unfrozen", {})
    
    return UnfreezeResponse(
        brand_id=brand_id,
        state="active",
        unfrozen_at=unfrozen_at,
    )


@router.post("/{brand_id}/predictive-resilience/rollback", response_model=RollbackResponse)
async def rollback_proposals(
    brand_id: str = Path(..., description="Brand ID"),
    request: RollbackRequest = Body(default_factory=RollbackRequest),
) -> RollbackResponse:
    """Rollback applied proposals for a brand."""
    rolled_back: list[str] = []
    
    # Get active cycle
    cycle_id = _brand_cycles.get(brand_id)
    if cycle_id:
        cycle = predictive_engine.get_cycle(cycle_id)
        if cycle:
            # Rollback specific proposal or all applied
            if request.proposal_id:
                # Rollback specific
                proposal = _proposals_store.get(request.proposal_id)
                if proposal and proposal.state == "applied":
                    if predictive_engine.rollback_mitigation(request.proposal_id, proposal):
                        rolled_back.append(request.proposal_id)
            else:
                # Rollback all applied
                for prop in list(cycle.proposals):
                    if prop.state == "applied":
                        if predictive_engine.rollback_mitigation(prop.proposal_id, prop):
                            rolled_back.append(prop.proposal_id)
    
    # Record event
    if rolled_back:
        _record_event(brand_id, "proposals_rolled_back", {
            "rolled_back": rolled_back,
        })
    
    return RollbackResponse(rolled_back=rolled_back)


@router.get("/{brand_id}/predictive-resilience/metrics")
async def get_predictive_resilience_metrics(
    brand_id: str = Path(..., description="Brand ID"),
) -> str:
    """Get predictive resilience metrics in Prometheus format."""
    # Get engine status
    status = predictive_engine.get_status()
    
    # Generate Prometheus format metrics
    lines = [
        "# HELP predictive_alerts_total Total number of predictive alerts",
        "# TYPE predictive_alerts_total counter",
        f'predictive_alerts_total{{brand="{brand_id}"}} {status.get("cycles_total", 0)}',
        "",
        "# HELP predictive_mitigations_applied_total Total mitigations applied",
        "# TYPE predictive_mitigations_applied_total counter",
        f'predictive_mitigations_applied_total{{brand="{brand_id}"}} {status.get("proposals_applied", 0)}',
        "",
        "# HELP predictive_mitigations_blocked_total Total mitigations blocked",
        "# TYPE predictive_mitigations_blocked_total counter",
        f'predictive_mitigations_blocked_total{{brand="{brand_id}"}} 0',
        "",
        "# HELP predictive_mitigations_rejected_total Total mitigations rejected",
        "# TYPE predictive_mitigations_rejected_total counter",
        f'predictive_mitigations_rejected_total{{brand="{brand_id}"}} {status.get("proposals_rejected", 0)}',
        "",
        "# HELP predictive_false_positives_total Total false positive alerts",
        "# TYPE predictive_false_positives_total counter",
        f'predictive_false_positives_total{{brand="{brand_id}"}} {status.get("false_positives_total", 0)}',
        "",
        "# HELP predictive_rollbacks_total Total rollbacks",
        "# TYPE predictive_rollbacks_total counter",
        f'predictive_rollbacks_total{{brand="{brand_id}"}} {status.get("proposals_rolled_back", 0)}',
        "",
        "# HELP predictive_time_to_detect_seconds Time to detect degradation",
        "# TYPE predictive_time_to_detect_seconds gauge",
        f'predictive_time_to_detect_seconds{{brand="{brand_id}"}} 0',
        "",
        "# HELP predictive_time_to_mitigate_seconds Time to mitigate degradation",
        "# TYPE predictive_time_to_mitigate_seconds gauge",
        f'predictive_time_to_mitigate_seconds{{brand="{brand_id}"}} 0',
        "",
        "# HELP predictive_frozen_brands_total Total frozen brands",
        "# TYPE predictive_frozen_brands_total gauge",
        f'predictive_frozen_brands_total{{brand="{brand_id}"}} {status.get("frozen_brands", 0)}',
    ]
    
    return "\n".join(lines)
