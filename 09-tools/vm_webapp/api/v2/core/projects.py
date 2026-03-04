from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, status

from vm_webapp.schemas.core import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectsListResponse,
)
from ._projection import project_command_event

router = APIRouter(prefix="/projects", tags=["projects"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get(
    "",
    response_model=ProjectsListResponse,
    summary="List all projects",
    description="Returns a paginated list of all projects for a specific brand. Use brand_id query parameter to filter.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with list of projects"},
        status.HTTP_400_BAD_REQUEST: {"description": "Missing required brand_id parameter"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Brand not found"},
    },
)
async def list_projects_v2(
    request: Request,
    brand_id: str,
) -> ProjectsListResponse:
    """List all projects for a brand.
    
    Args:
        brand_id: The unique identifier of the brand to list projects for
        
    Returns:
        A list of projects belonging to the specified brand
    """
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


@router.post(
    "",
    response_model=ProjectResponse,
    summary="Create a new project",
    description="Creates a new project under a brand with specified name, objective, and channels. Projects organize campaigns and workflows.",
    responses={
        status.HTTP_201_CREATED: {"description": "Project created successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data or missing required fields"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Brand not found"},
        status.HTTP_409_CONFLICT: {"description": "Project with this name already exists in brand"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_project_v2(
    data: ProjectCreate,
    request: Request,
    response: Response,
) -> ProjectResponse:
    """Create a new project.
    
    Args:
        data: Project creation data including brand_id, name, objective, and channels
        
    Returns:
        The newly created project with generated project_id
    """
    from vm_webapp.db import session_scope
    from vm_webapp.commands_v2 import create_project_command
    from vm_webapp.repo import get_project_view

    actor_id = getattr(request.state, "actor_id", "system")
    idempotency_key = request.headers.get("Idempotency-Key") or _auto_id("idem")

    with session_scope(request.app.state.engine) as session:
        dedup = create_project_command(
            session,
            project_id=data.project_id,
            brand_id=data.brand_id,
            name=data.name,
            objective=data.objective,
            channels=data.channels,
            due_date=data.due_date,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        project_command_event(session, event_id=dedup.event_id)
        payload = json.loads(dedup.response_json)
        project_id = payload["project_id"]
        projected = get_project_view(session, project_id)
        if projected is None:
            raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
        response.status_code = status.HTTP_200_OK
        return ProjectResponse(
            project_id=projected.project_id,
            brand_id=projected.brand_id,
            name=projected.name,
            description=data.description,
            status="active",
            created_at=projected.updated_at,
            updated_at=projected.updated_at,
            event_id=dedup.event_id,
        )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
    description="Updates project metadata.",
    responses={
        status.HTTP_200_OK: {"description": "Project updated successfully"},
        status.HTTP_404_NOT_FOUND: {"description": "Project not found"},
    },
)
async def update_project_v2(project_id: str, data: ProjectUpdate, request: Request) -> ProjectResponse:
    from vm_webapp.commands_v2 import update_project_command
    from vm_webapp.db import session_scope
    from vm_webapp.repo import get_project_view

    actor_id = getattr(request.state, "actor_id", "system")
    idempotency_key = _auto_id("idem")

    with session_scope(request.app.state.engine) as session:
        existing = get_project_view(session, project_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"project not found: {project_id}")

        channels = json.loads(existing.channels_json) if existing.channels_json else []
        dedup = update_project_command(
            session,
            project_id=project_id,
            brand_id=existing.brand_id,
            name=data.name if data.name is not None else existing.name,
            objective=data.objective if data.objective is not None else existing.objective,
            channels=data.channels if data.channels is not None else channels,
            due_date=data.due_date if data.due_date is not None else existing.due_date,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        project_command_event(session, event_id=dedup.event_id)
        updated = get_project_view(session, project_id)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"project not found: {project_id}")

        return ProjectResponse(
            project_id=updated.project_id,
            brand_id=updated.brand_id,
            name=updated.name,
            description=data.description,
            status="active",
            created_at=updated.updated_at,
            updated_at=updated.updated_at,
            event_id=dedup.event_id,
        )
