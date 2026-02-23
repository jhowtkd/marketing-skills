from __future__ import annotations

from fastapi import APIRouter, Request

from vm_webapp.db import session_scope
from vm_webapp.repo import list_brands


router = APIRouter()


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/brands")
def brands(request: Request) -> dict[str, list[dict[str, str]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_brands(session)
    return {
        "brands": [{"brand_id": row.brand_id, "name": row.name} for row in rows],
    }
