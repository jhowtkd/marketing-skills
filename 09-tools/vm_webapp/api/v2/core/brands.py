from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, status

from vm_webapp.schemas.core import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    BrandsListResponse,
)
from ._projection import project_command_event

router = APIRouter(prefix="/brands", tags=["brands"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get(
    "",
    response_model=BrandsListResponse,
    summary="List all brands",
    description="Returns a paginated list of all brands in the system. Results can be filtered by status.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with list of brands"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized - valid authentication required"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)
async def list_brands_v2(request: Request) -> BrandsListResponse:
    """List all brands.
    
    Returns all brands accessible to the authenticated user.
    """
    from vm_webapp.repo import list_brands_view
    from vm_webapp.db import session_scope
    
    with session_scope(request.app.state.engine) as session:
        rows = list_brands_view(session)
        brands = [
            BrandResponse(
                brand_id=r.brand_id,
                name=r.name,
                description=None,
                status="active",
                created_at=r.updated_at,
                updated_at=None,
            )
            for r in rows
        ]
        return BrandsListResponse(brands=brands)


@router.post(
    "",
    response_model=BrandResponse,
    summary="Create a new brand",
    description="Creates a new brand with the specified name and optional description. Returns the created brand with generated ID.",
    responses={
        status.HTTP_201_CREATED: {"description": "Brand created successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_409_CONFLICT: {"description": "Brand with this name already exists"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_brand_v2(data: BrandCreate, request: Request, response: Response) -> BrandResponse:
    """Create a new brand.
    
    Args:
        data: Brand creation data including name and optional description
        
    Returns:
        The newly created brand with generated brand_id
    """
    from vm_webapp.db import session_scope
    from vm_webapp.commands_v2 import create_brand_command

    actor_id = getattr(request.state, "actor_id", "system")
    idempotency_key = request.headers.get("Idempotency-Key") or _auto_id("idem")

    with session_scope(request.app.state.engine) as session:
        dedup = create_brand_command(
            session,
            brand_id=data.brand_id,
            name=data.name,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        project_command_event(session, event_id=dedup.event_id)
        payload = json.loads(dedup.response_json)
        brand_id = payload["brand_id"]
        from vm_webapp.repo import get_brand_view

        projected = get_brand_view(session, brand_id)
        if projected is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")
        response.status_code = status.HTTP_200_OK
        return BrandResponse(
            brand_id=projected.brand_id,
            name=projected.name,
            description=data.description,
            status="active",
            created_at=projected.updated_at,
            updated_at=None,
            event_id=dedup.event_id,
        )


@router.patch(
    "/{brand_id}",
    response_model=BrandResponse,
    summary="Update a brand",
    description="Updates brand name and/or description.",
    responses={
        status.HTTP_200_OK: {"description": "Brand updated successfully"},
        status.HTTP_404_NOT_FOUND: {"description": "Brand not found"},
    },
)
async def update_brand_v2(brand_id: str, data: BrandUpdate, request: Request) -> BrandResponse:
    from vm_webapp.commands_v2 import update_brand_command
    from vm_webapp.db import session_scope
    from vm_webapp.repo import get_brand_view

    actor_id = getattr(request.state, "actor_id", "system")
    idempotency_key = _auto_id("idem")

    with session_scope(request.app.state.engine) as session:
        existing = get_brand_view(session, brand_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")

        resolved_name = data.name if data.name is not None else existing.name
        dedup = update_brand_command(
            session,
            brand_id=brand_id,
            name=resolved_name,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        project_command_event(session, event_id=dedup.event_id)
        updated = get_brand_view(session, brand_id)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")

        response = json.loads(dedup.response_json)
        return BrandResponse(
            brand_id=response["brand_id"],
            name=updated.name,
            description=data.description,
            status="active",
            created_at=updated.updated_at,
            updated_at=None,
            event_id=dedup.event_id,
        )
