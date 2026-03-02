"""Onboarding Cross-Session Continuity API v2 Endpoints.

v35: API endpoints for continuity operations with conflict detection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from vm_webapp.onboarding_continuity import (
    ContinuityGraph,
    CheckpointStatus,
    HandoffStatus,
    SourcePriority,
)
from vm_webapp.onboarding_resume_orchestrator import (
    ResumeOrchestrator,
    ConflictResolution,
)


# Request/Response Models

class CheckpointInput(BaseModel):
    """Input for creating a checkpoint."""
    user_id: str
    step_id: str
    step_data: Dict[str, Any] = Field(default_factory=dict)
    form_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunContinuityRequest(BaseModel):
    """Request to run continuity checkpoint creation."""
    user_id: str
    source_session: str
    target_session: Optional[str] = None
    step_id: str
    step_data: Dict[str, Any] = Field(default_factory=dict)
    form_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_priority: str = "session"


class RunContinuityResponse(BaseModel):
    """Response from continuity run."""
    brand_id: str
    user_id: str
    checkpoint_id: str
    bundle_id: Optional[str] = None
    version: int
    created_at: str


class ResumeRequest(BaseModel):
    """Request to resume from a handoff."""
    bundle_id: str
    target_session: str
    resumed_by: str
    force: bool = False


class ResumeResponse(BaseModel):
    """Response from resume operation."""
    success: bool
    bundle_id: str
    context: Optional[Dict[str, Any]] = None
    auto_applied: Optional[bool] = None
    needs_approval: Optional[bool] = None
    risk_level: Optional[str] = None
    conflicts: Optional[List[Dict[str, Any]]] = None
    reason: Optional[str] = None


class FreezeRequest(BaseModel):
    """Request to freeze continuity operations."""
    frozen_by: str
    reason: str


class FreezeResponse(BaseModel):
    """Response from freeze operation."""
    brand_id: str
    status: str
    frozen_at: str


class RollbackRequest(BaseModel):
    """Request to rollback continuity operations."""
    rolled_back_by: str
    reason: str


class RollbackResponse(BaseModel):
    """Response from rollback operation."""
    brand_id: str
    rolled_back_count: int
    rolled_back_at: str


class StatusResponse(BaseModel):
    """Continuity status response."""
    brand_id: str
    state: str
    version: str = "v35"
    frozen: bool
    metrics: Dict[str, Any]
    recent_handoffs: List[Dict[str, Any]]


class HandoffsListResponse(BaseModel):
    """List of handoff bundles."""
    brand_id: str
    handoffs: List[Dict[str, Any]]
    total: int
    filter_status: Optional[str] = None


class HandoffDetailResponse(BaseModel):
    """Single handoff detail."""
    bundle_id: str
    user_id: str
    brand_id: str
    source_session: str
    target_session: Optional[str]
    checkpoint_ids: List[str]
    context_payload: Dict[str, Any]
    source_priority: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


# Global state (in production, use proper database)
_continuity_graph = ContinuityGraph()
_resume_orchestrator = ResumeOrchestrator(_continuity_graph)
_continuity_metrics: Dict[str, int] = {
    "checkpoints_created": 0,
    "bundles_created": 0,
    "resumes_completed": 0,
    "resumes_failed": 0,
    "resumes_auto_applied": 0,
    "resumes_needing_approval": 0,
    "resumes_rolled_back": 0,
    "context_loss_events": 0,
    "conflicts_detected": 0,
}
_pending_approvals: Dict[str, Dict[str, Any]] = {}
_frozen_brands: Dict[str, Dict[str, Any]] = {}


# Router
router = APIRouter(prefix="/api/v2/brands", tags=["onboarding-continuity"])


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _get_source_priority(priority_str: str) -> SourcePriority:
    """Convert string to SourcePriority."""
    mapping = {
        "session": SourcePriority.SESSION,
        "recovery": SourcePriority.RECOVERY,
        "default": SourcePriority.DEFAULT,
    }
    return mapping.get(priority_str.lower(), SourcePriority.SESSION)


@router.get("/{brand_id}/onboarding-continuity/status", response_model=StatusResponse)
async def get_continuity_status(brand_id: str) -> Dict[str, Any]:
    """Get onboarding continuity status for a brand.
    
    Returns metrics and recent handoffs.
    """
    # Get handoffs for this brand
    brand_bundles = [
        bundle for bundle in _continuity_graph._bundles.values()
        if bundle.brand_id == brand_id
    ]
    
    recent = sorted(
        brand_bundles,
        key=lambda b: b.created_at,
        reverse=True
    )[:10]  # Last 10

    return {
        "brand_id": brand_id,
        "state": "frozen" if brand_id in _frozen_brands else "active",
        "version": "v35",
        "frozen": brand_id in _frozen_brands,
        "metrics": {**_continuity_metrics, **_continuity_graph.get_handoff_metrics()},
        "recent_handoffs": [h.to_dict() for h in recent],
    }


@router.post("/{brand_id}/onboarding-continuity/run", response_model=RunContinuityResponse)
async def run_continuity(brand_id: str, request: RunContinuityRequest) -> Dict[str, Any]:
    """Create checkpoint and optionally handoff bundle.
    
    Records user progress and prepares for cross-session handoff.
    """
    if brand_id in _frozen_brands:
        raise HTTPException(status_code=403, detail="Continuity operations frozen for this brand")

    # Create checkpoint
    checkpoint = _continuity_graph.create_checkpoint(
        user_id=request.user_id,
        brand_id=brand_id,
        step_id=request.step_id,
        step_data=request.step_data,
        form_data=request.form_data,
        metadata=request.metadata,
    )
    
    _continuity_metrics["checkpoints_created"] += 1

    bundle_id = None
    
    # Create handoff bundle if target session specified
    if request.target_session:
        source_priority = _get_source_priority(request.source_priority)
        
        bundle = _continuity_graph.create_handoff_bundle(
            user_id=request.user_id,
            brand_id=brand_id,
            source_session=request.source_session,
            target_session=request.target_session,
            checkpoint_ids=[checkpoint.checkpoint_id],
            source_priority=source_priority,
        )
        
        bundle_id = bundle.bundle_id
        _continuity_metrics["bundles_created"] += 1

    return {
        "brand_id": brand_id,
        "user_id": request.user_id,
        "checkpoint_id": checkpoint.checkpoint_id,
        "bundle_id": bundle_id,
        "version": checkpoint.version,
        "created_at": _now_iso(),
    }


@router.get("/{brand_id}/onboarding-continuity/handoffs", response_model=HandoffsListResponse)
async def list_handoffs(
    brand_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """List handoff bundles for a brand.
    
    Supports filtering by status.
    """
    handoffs = [
        bundle for bundle in _continuity_graph._bundles.values()
        if bundle.brand_id == brand_id
    ]
    
    # Apply filter
    if status:
        handoffs = [h for h in handoffs if h.status.value == status]

    return {
        "brand_id": brand_id,
        "handoffs": [h.to_dict() for h in handoffs],
        "total": len(handoffs),
        "filter_status": status,
    }


@router.get(
    "/{brand_id}/onboarding-continuity/handoffs/{bundle_id}",
    response_model=HandoffDetailResponse,
)
async def get_handoff_detail(brand_id: str, bundle_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific handoff bundle."""
    bundle = _continuity_graph.get_bundle(bundle_id)
    
    if not bundle or bundle.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Handoff not found")

    return {
        "bundle_id": bundle.bundle_id,
        "user_id": bundle.user_id,
        "brand_id": bundle.brand_id,
        "source_session": bundle.source_session,
        "target_session": bundle.target_session,
        "checkpoint_ids": bundle.checkpoint_ids,
        "context_payload": bundle.context_payload,
        "source_priority": bundle.source_priority.value,
        "status": bundle.status.value,
        "created_at": bundle.created_at,
        "started_at": bundle.started_at,
        "completed_at": bundle.completed_at,
    }


@router.post("/{brand_id}/onboarding-continuity/resume", response_model=ResumeResponse)
async def resume_continuity(brand_id: str, request: ResumeRequest) -> Dict[str, Any]:
    """Execute resume from a handoff bundle.
    
    Validates consistency and applies context to target session.
    """
    if brand_id in _frozen_brands:
        raise HTTPException(status_code=403, detail="Continuity operations frozen for this brand")

    bundle = _continuity_graph.get_bundle(request.bundle_id)
    if not bundle or bundle.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Bundle not found")

    # Execute resume via orchestrator
    result = _resume_orchestrator.execute_resume(
        bundle_id=request.bundle_id,
        force=request.force,
    )

    # Update metrics
    if result["success"]:
        _continuity_metrics["resumes_completed"] += 1
        if result.get("auto_applied"):
            _continuity_metrics["resumes_auto_applied"] += 1
    else:
        _continuity_metrics["resumes_failed"] += 1
        if result.get("needs_approval"):
            _continuity_metrics["resumes_needing_approval"] += 1
            # Queue for approval
            _pending_approvals[request.bundle_id] = {
                "brand_id": brand_id,
                "bundle_id": request.bundle_id,
                "resumed_by": request.resumed_by,
                "risk_level": result.get("risk_level"),
                "conflicts": result.get("conflicts"),
                "requested_at": _now_iso(),
            }

    return result


@router.post("/{brand_id}/onboarding-continuity/freeze", response_model=FreezeResponse)
async def freeze_continuity(brand_id: str, request: FreezeRequest) -> Dict[str, Any]:
    """Freeze all continuity operations for a brand."""
    _frozen_brands[brand_id] = {
        "frozen_by": request.frozen_by,
        "reason": request.reason,
        "frozen_at": _now_iso(),
    }

    return {
        "brand_id": brand_id,
        "status": "frozen",
        "frozen_at": _now_iso(),
    }


@router.post("/{brand_id}/onboarding-continuity/rollback", response_model=RollbackResponse)
async def rollback_continuity(brand_id: str, request: RollbackRequest) -> Dict[str, Any]:
    """Rollback continuity operations for a brand.
    
    Rolls back all completed handoffs and clears pending approvals.
    """
    # Get brand handoffs
    brand_bundles = [
        bundle for bundle in _continuity_graph._bundles.values()
        if bundle.brand_id == brand_id
    ]
    
    rolled_back_count = 0
    
    # Rollback completed handoffs
    for bundle in brand_bundles:
        if bundle.status == HandoffStatus.COMPLETED:
            _resume_orchestrator.rollback_resume(bundle.bundle_id)
            rolled_back_count += 1

    # Clear pending approvals for this brand
    bundles_to_remove = [
        bid for bid, p in _pending_approvals.items()
        if p.get("brand_id") == brand_id
    ]
    for bid in bundles_to_remove:
        del _pending_approvals[bid]

    _continuity_metrics["resumes_rolled_back"] += rolled_back_count

    return {
        "brand_id": brand_id,
        "rolled_back_count": rolled_back_count,
        "rolled_back_at": _now_iso(),
    }
