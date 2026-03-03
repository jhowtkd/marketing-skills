from __future__ import annotations

from fastapi import APIRouter, Request, status

from vm_webapp.schemas.core import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    BrandsListResponse,
)

router = APIRouter(prefix="/brands", tags=["brands"])


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
async def create_brand_v2(data: BrandCreate, request: Request) -> BrandResponse:
    """Create a new brand.
    
    Args:
        data: Brand creation data including name and optional description
        
    Returns:
        The newly created brand with generated brand_id
    """
    from vm_webapp.commands_v2 import create_brand_command
    from vm_webapp.db import session_scope
    from uuid import uuid4
    
    actor_id = getattr(request.state, 'actor_id', 'system')
    idempotency_key = f"idem-{uuid4().hex[:10]}"
    
    from datetime import datetime
    import json
    
    with session_scope(request.app.state.engine) as session:
        dedup = create_brand_command(
            session,
            brand_id=None,
            name=data.name,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        response = json.loads(dedup.response_json)
        return BrandResponse(
            brand_id=response["brand_id"],
            name=data.name,
            description=data.description,
            status="active",
            created_at=datetime.now(),
            updated_at=None,
        )
