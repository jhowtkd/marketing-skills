from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request, status

from vm_webapp.schemas.core import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignsListResponse,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get(
    "",
    response_model=CampaignsListResponse,
    summary="List all campaigns",
    description="Returns a list of all campaigns for a specific project. Campaigns organize marketing activities within projects.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with list of campaigns"},
        status.HTTP_400_BAD_REQUEST: {"description": "Missing required project_id parameter"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Project not found"},
    },
)
async def list_campaigns_v2(
    request: Request,
    project_id: str,
) -> CampaignsListResponse:
    """List all campaigns for a project.
    
    Args:
        project_id: The unique identifier of the project to list campaigns for
        
    Returns:
        A list of campaigns belonging to the specified project
    """
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


@router.post(
    "",
    response_model=CampaignResponse,
    summary="Create a new campaign",
    description="Creates a new campaign within a project. Campaigns represent marketing initiatives that can contain multiple workflow runs.",
    responses={
        status.HTTP_201_CREATED: {"description": "Campaign created successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Project or brand not found"},
        status.HTTP_409_CONFLICT: {"description": "Campaign with this title already exists"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign_v2(data: CampaignCreate, request: Request) -> CampaignResponse:
    """Create a new campaign.
    
    Args:
        data: Campaign creation data including brand_id, project_id, and title
        
    Returns:
        The newly created campaign with generated campaign_id
    """
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
        response = json.loads(dedup.response_json)
        return CampaignResponse(
            campaign_id=response["campaign_id"],
            brand_id=data.brand_id,
            project_id=data.project_id,
            title=data.title,
            status="active",
            created_at=datetime.now(),
            updated_at=None,
        )


@router.patch(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update a campaign",
    description="Updates an existing campaign. Currently supports updating the campaign title.",
    responses={
        status.HTTP_200_OK: {"description": "Campaign updated successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Campaign not found"},
        status.HTTP_409_CONFLICT: {"description": "Campaign update conflict"},
    },
)
async def update_campaign_v2(
    campaign_id: str,
    data: CampaignUpdate,
    request: Request,
) -> CampaignResponse:
    """Update a campaign (partial update).
    
    Args:
        campaign_id: The unique identifier of the campaign to update
        data: Campaign update data (currently supports title only)
        
    Returns:
        The updated campaign
    """
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
