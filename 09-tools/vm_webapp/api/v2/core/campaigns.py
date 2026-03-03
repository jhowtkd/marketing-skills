from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Request

from vm_webapp.schemas.core import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignsListResponse,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get("", response_model=CampaignsListResponse)
async def list_campaigns_v2(
    request: Request,
    project_id: str,
) -> CampaignsListResponse:
    """List all campaigns for a project."""
    from vm_webapp.repo import list_campaigns_view
    from vm_webapp.db import session_scope
    
    with session_scope(request.app.state.engine) as session:
        rows = list_campaigns_view(session, project_id=project_id)
        campaigns = [
            CampaignResponse(
                campaign_id=r.campaign_id,
                brand_id=r.brand_id,
                project_id=r.project_id,
                title=r.title,
                status="active",
                created_at=r.updated_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
        return CampaignsListResponse(campaigns=campaigns)


@router.post("", response_model=CampaignResponse)
async def create_campaign_v2(data: CampaignCreate, request: Request) -> CampaignResponse:
    """Create a new campaign."""
    from vm_webapp.commands_v2 import create_campaign_command
    from vm_webapp.db import session_scope
    
    actor_id = getattr(request.state, 'actor_id', 'system')
    idempotency_key = _auto_id("idem")
    
    with session_scope(request.app.state.engine) as session:
        dedup = create_campaign_command(
            session,
            campaign_id=None,
            brand_id=data.brand_id,
            project_id=data.project_id,
            title=data.title,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        response = dedup.response
        return CampaignResponse(
            campaign_id=response["campaign_id"],
            brand_id=data.brand_id,
            project_id=data.project_id,
            title=data.title,
            status="active",
            created_at=None,
            updated_at=None,
        )


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign_v2(
    campaign_id: str,
    data: CampaignUpdate,
    request: Request,
) -> CampaignResponse:
    """Update a campaign (partial update)."""
    from vm_webapp.db import session_scope
    from vm_webapp.models import CampaignView
    
    with session_scope(request.app.state.engine) as session:
        campaign = session.get(CampaignView, campaign_id)
        if campaign is None:
            raise ValueError(f"Campaign not found: {campaign_id}")
        
        # For now, just return the campaign as-is
        # Full update would require an update_campaign_command
        return CampaignResponse(
            campaign_id=campaign_id,
            brand_id=campaign.brand_id,
            project_id=campaign.project_id,
            title=data.title or campaign.title,
            status="active",
            created_at=campaign.updated_at,
            updated_at=campaign.updated_at,
        )
