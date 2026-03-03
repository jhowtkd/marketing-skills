from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Request

from vm_webapp.schemas.core import (
    ProjectCreate,
    ProjectResponse,
    ProjectsListResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get("", response_model=ProjectsListResponse)
async def list_projects_v2(
    request: Request,
    brand_id: str,
) -> ProjectsListResponse:
    """List all projects for a brand."""
    from vm_webapp.repo import list_projects_view
    from vm_webapp.db import session_scope
    
    with session_scope(request.app.state.engine) as session:
        rows = list_projects_view(session, brand_id=brand_id)
        projects = [
            ProjectResponse(
                project_id=r.project_id,
                brand_id=r.brand_id,
                name=r.name,
                description=getattr(r, 'description', None),
                status="active",
                created_at=r.updated_at,  # projects view uses updated_at
                updated_at=r.updated_at,
            )
            for r in rows
        ]
        return ProjectsListResponse(projects=projects)


@router.post("", response_model=ProjectResponse)
async def create_project_v2(data: ProjectCreate, request: Request) -> ProjectResponse:
    """Create a new project."""
    from vm_webapp.commands_v2 import create_project_command
    from vm_webapp.db import session_scope
    
    actor_id = getattr(request.state, 'actor_id', 'system')
    idempotency_key = _auto_id("idem")
    
    with session_scope(request.app.state.engine) as session:
        dedup = create_project_command(
            session,
            project_id=None,
            brand_id=data.brand_id,
            name=data.name,
            objective=data.objective,
            channels=data.channels,
            due_date=data.due_date,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        response = dedup.response
        return ProjectResponse(
            project_id=response["project_id"],
            brand_id=data.brand_id,
            name=data.name,
            description=data.description,
            status="active",
            created_at=response.get("created_at"),
            updated_at=None,
        )
