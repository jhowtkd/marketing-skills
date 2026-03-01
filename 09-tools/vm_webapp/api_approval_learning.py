"""
API v2 Endpoints for Approval Optimizer Learning Loop - v24
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from uuid import uuid4

from vm_webapp.approval_learning import LearningCore, LearningGuardrails


router = APIRouter(prefix="/api/v2/approval-learning")

# Global learning core instance
_learning_core = LearningCore()
_learning_guardrails = LearningGuardrails()


class RunRequest(BaseModel):
    brand_id: str


class FreezeRequest(BaseModel):
    reason: str = "manual_review"


class RejectRequest(BaseModel):
    reason: str


@router.get("/status")
async def get_learning_status() -> dict[str, Any]:
    """
    Get learning loop status and version.
    """
    return {
        "status": "active",
        "version": "v24",
        "features": [
            "observe",
            "learn",
            "apply",
            "freeze",
            "rollback",
        ],
    }


@router.post("/run")
async def run_learning_cycle(request: RunRequest) -> dict[str, Any]:
    """
    Trigger a learning cycle for a brand.
    """
    brand_id = request.brand_id
    
    # Record some sample outcomes for demonstration
    for i in range(5):
        _learning_core.record_outcome({
            "request_id": f"req-{uuid4().hex[:8]}",
            "batch_id": f"batch-{uuid4().hex[:8]}",
            "brand_id": brand_id,
            "approved": True,
            "risk_level": "medium",
            "predicted_risk": 0.6,
            "actual_time_minutes": 6.0,
            "batch_size": 3,
        })
    
    # Generate suggestions
    suggestions = _learning_core.generate_suggestions(brand_id)
    
    return {
        "cycle_id": uuid4().hex[:16],
        "brand_id": brand_id,
        "status": "completed",
        "suggestions_generated": len(suggestions),
        "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }


@router.get("/proposals")
async def get_proposals(brand_id: Optional[str] = None) -> dict[str, Any]:
    """
    Get learning proposals/suggestions.
    """
    if brand_id:
        proposals = _learning_core.generate_suggestions(brand_id)
    else:
        proposals = []
    
    return {
        "proposals": proposals,
        "count": len(proposals),
    }


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str) -> dict[str, Any]:
    """
    Apply a learning proposal.
    """
    result = _learning_core.apply_suggestion(
        proposal_id, 
        _learning_guardrails,
        force=True  # For API, we force apply
    )
    
    if not result.get("applied") and result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, request: RejectRequest) -> dict[str, Any]:
    """
    Reject a learning proposal.
    """
    suggestion = _learning_core._suggestions.get(proposal_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="proposal_not_found")
    
    suggestion.status = "rejected"
    
    return {
        "rejected": True,
        "proposal_id": proposal_id,
        "reason": request.reason,
    }


@router.post("/brands/{brand_id}/freeze")
async def freeze_brand(brand_id: str, request: FreezeRequest) -> dict[str, Any]:
    """
    Freeze learning for a brand.
    """
    result = _learning_core.freeze_brand(brand_id, reason=request.reason)
    return result


@router.post("/brands/{brand_id}/unfreeze")
async def unfreeze_brand(brand_id: str) -> dict[str, Any]:
    """
    Unfreeze learning for a brand.
    """
    result = _learning_core.unfreeze_brand(brand_id)
    return result


@router.post("/proposals/{proposal_id}/rollback")
async def rollback_proposal(proposal_id: str) -> dict[str, Any]:
    """
    Rollback an applied proposal.
    """
    result = _learning_core.rollback_suggestion(proposal_id)
    
    if not result.get("rolled_back") and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/history/{brand_id}")
async def get_learning_history(brand_id: str) -> dict[str, Any]:
    """
    Get learning history for a brand.
    """
    history = _learning_core.get_applied_history(brand_id)
    
    return {
        "brand_id": brand_id,
        "history": history,
        "count": len(history),
    }
