from __future__ import annotations

from fastapi import APIRouter, Request

from vm_webapp.schemas.core import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    BrandsListResponse,
)

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("", response_model=BrandsListResponse)
async def list_brands_v2(request: Request) -> BrandsListResponse:
    """List all brands."""
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
                created_at=r.created_at,
                updated_at=None,
            )
            for r in rows
        ]
        return BrandsListResponse(brands=brands)


@router.post("", response_model=BrandResponse)
async def create_brand_v2(data: BrandCreate, request: Request) -> BrandResponse:
    """Create a new brand."""
    from vm_webapp.commands_v2 import create_brand_command
    
    result = create_brand_command(
        engine=request.app.state.engine,
        name=data.name,
    )
    return BrandResponse(
        brand_id=result["brand_id"],
        name=data.name,
        description=data.description,
        status="active",
        created_at=result["created_at"],
        updated_at=None,
    )
