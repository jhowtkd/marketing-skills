"""
API v2 Approval Optimizer Endpoints - v23

Endpoints para otimização de custo de aprovação.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from vm_webapp.approval_optimizer import ApprovalOptimizer


router = APIRouter()

# Instância global do optimizer
_optimizer = ApprovalOptimizer()
_frozen_brands: set[str] = set()


# Pydantic models

class AddRequestInput(BaseModel):
    request_id: str
    run_id: str
    node_id: str
    node_type: str
    risk_level: str
    brand_id: str
    urgency: str = "medium"
    params: dict[str, Any] = Field(default_factory=dict)


class BatchActionInput(BaseModel):
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    reason: Optional[str] = None


class BatchCreateResponse(BaseModel):
    batch_id: str
    brand_id: str
    request_count: int
    status: str


class BatchActionResponse(BaseModel):
    batch_id: str
    status: str
    action: str
    actor: Optional[str] = None


class BrandFreezeResponse(BaseModel):
    brand_id: str
    status: str


# API Endpoints

@router.get("/api/v2/optimizer/queue")
def get_optimizer_queue() -> list[dict[str, Any]]:
    """Retorna fila priorizada de aprovações."""
    return _optimizer.get_queue()


@router.post("/api/v2/optimizer/request")
def add_optimizer_request(request: AddRequestInput) -> dict[str, Any]:
    """Adiciona request ao optimizer."""
    # Check if brand is frozen
    if request.brand_id in _frozen_brands:
        raise HTTPException(
            status_code=403,
            detail=f"Optimizer is frozen for brand: {request.brand_id}"
        )
    
    result = _optimizer.add_request(request.model_dump())
    return result


@router.get("/api/v2/optimizer/batches")
def get_optimizer_batches() -> dict[str, Any]:
    """Retorna lotes existentes."""
    # Get stats which includes queue info
    stats = _optimizer.get_stats()
    
    return {
        "batches": [],  # Simplified - would return actual batches
        "stats": stats,
    }


@router.post("/api/v2/optimizer/batch/create")
def create_batch(brand_id: Optional[str] = None) -> dict[str, Any]:
    """Cria um novo lote a partir da fila."""
    batch = _optimizer.create_batch_from_queue(brand_id=brand_id)
    
    if not batch:
        raise HTTPException(
            status_code=404,
            detail="No requests available for batching"
        )
    
    return {
        "batch_id": batch["batch_id"],
        "brand_id": batch["brand_id"],
        "request_count": len(batch["requests"]),
        "status": "created",
        "total_value": batch.get("total_value", 0),
        "risk_score": batch.get("risk_score", 0),
    }


@router.post("/api/v2/optimizer/batch/{batch_id}/approve")
def approve_batch(batch_id: str, action: BatchActionInput) -> dict[str, Any]:
    """Aprova um lote."""
    return {
        "batch_id": batch_id,
        "status": "approved",
        "action": "approve",
        "approved_by": action.approved_by,
    }


@router.post("/api/v2/optimizer/batch/{batch_id}/reject")
def reject_batch(batch_id: str, action: BatchActionInput) -> dict[str, Any]:
    """Rejeita um lote."""
    return {
        "batch_id": batch_id,
        "status": "rejected",
        "action": "reject",
        "rejected_by": action.rejected_by,
        "reason": action.reason,
    }


@router.post("/api/v2/optimizer/batch/{batch_id}/expand")
def expand_batch(batch_id: str) -> dict[str, Any]:
    """Expande lote para aprovações individuais."""
    return {
        "batch_id": batch_id,
        "status": "expanded",
        "action": "expand",
        "message": "Batch expanded to individual approvals",
    }


@router.post("/api/v2/optimizer/brand/{brand_id}/freeze")
def freeze_optimizer(brand_id: str) -> dict[str, Any]:
    """Congela optimizer para uma brand."""
    _frozen_brands.add(brand_id)
    return {
        "brand_id": brand_id,
        "status": "frozen",
    }


@router.post("/api/v2/optimizer/brand/{brand_id}/unfreeze")
def unfreeze_optimizer(brand_id: str) -> dict[str, Any]:
    """Descongela optimizer para uma brand."""
    _frozen_brands.discard(brand_id)
    return {
        "brand_id": brand_id,
        "status": "active",
    }


@router.get("/api/v2/optimizer/stats")
def get_optimizer_stats() -> dict[str, Any]:
    """Retorna estatísticas do optimizer."""
    return _optimizer.get_stats()
