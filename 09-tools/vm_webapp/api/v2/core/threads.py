from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request, status

from vm_webapp.schemas.core import (
    ThreadCreate,
    ThreadUpdate,
    ThreadResponse,
    ThreadsListResponse,
)

router = APIRouter(prefix="/threads", tags=["threads"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get(
    "",
    response_model=ThreadsListResponse,
    summary="List all threads",
    description="Returns a list of all threads for a specific project. Threads represent conversation contexts for workflow execution.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with list of threads"},
        status.HTTP_400_BAD_REQUEST: {"description": "Missing required project_id parameter"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Project not found"},
    },
)
async def list_threads_v2(
    request: Request,
    project_id: str,
) -> ThreadsListResponse:
    """List all threads for a project.
    
    Args:
        project_id: The unique identifier of the project to list threads for
        
    Returns:
        A list of threads belonging to the specified project
    """
    from vm_webapp.repo import list_threads_view
    from vm_webapp.db import session_scope
    
    with session_scope(request.app.state.engine) as session:
        rows = list_threads_view(session, project_id=project_id)
        threads = [
            ThreadResponse(
                thread_id=r.thread_id,
                brand_id=r.brand_id,
                project_id=r.project_id,
                title=r.title,
                status="open" if r.is_open else "closed",
                created_at=r.created_at,
                updated_at=r.last_activity_at,
            )
            for r in rows
        ]
        return ThreadsListResponse(threads=threads)


@router.post(
    "",
    response_model=ThreadResponse,
    summary="Create a new thread",
    description="Creates a new thread within a project. Threads are conversation contexts that contain workflow runs and timeline items.",
    responses={
        status.HTTP_201_CREATED: {"description": "Thread created successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Project or brand not found"},
        status.HTTP_409_CONFLICT: {"description": "Thread creation conflict"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_thread_v2(data: ThreadCreate, request: Request) -> ThreadResponse:
    """Create a new thread.
    
    Args:
        data: Thread creation data including brand_id, project_id, and title
        
    Returns:
        The newly created thread with generated thread_id
    """
    from vm_webapp.commands_v2 import create_thread_command
    from vm_webapp.db import session_scope
    
    actor_id = getattr(request.state, 'actor_id', 'system')
    idempotency_key = _auto_id("idem")
    
    with session_scope(request.app.state.engine) as session:
        dedup = create_thread_command(
            session,
            thread_id=None,
            project_id=data.project_id,
            brand_id=data.brand_id,
            title=data.title,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        response = json.loads(dedup.response_json)
        return ThreadResponse(
            thread_id=response["thread_id"],
            brand_id=data.brand_id,
            project_id=data.project_id,
            title=data.title,
            status="open",
            created_at=datetime.now(),
            updated_at=None,
        )


@router.patch(
    "/{thread_id}",
    response_model=ThreadResponse,
    summary="Update a thread",
    description="Updates an existing thread. Currently supports renaming the thread title.",
    responses={
        status.HTTP_200_OK: {"description": "Thread updated successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Thread not found"},
        status.HTTP_409_CONFLICT: {"description": "Thread update conflict"},
    },
)
async def update_thread_v2(
    thread_id: str,
    data: ThreadUpdate,
    request: Request,
) -> ThreadResponse:
    """Update a thread (rename).
    
    Args:
        thread_id: The unique identifier of the thread to update
        data: Thread update data (currently supports title only)
        
    Returns:
        The updated thread
    """
    from vm_webapp.commands_v2 import rename_thread_command
    from vm_webapp.db import session_scope
    from vm_webapp.repo import get_thread_view
    
    actor_id = getattr(request.state, 'actor_id', 'system')
    idempotency_key = _auto_id("idem")
    
    with session_scope(request.app.state.engine) as session:
        # Get current thread to return updated data
        thread_view = get_thread_view(session, thread_id)
        if thread_view is None:
            raise ValueError(f"Thread not found: {thread_id}")
        
        if data.title:
            dedup = rename_thread_command(
                session,
                thread_id=thread_id,
                title=data.title,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
            )
            title = data.title
        else:
            title = thread_view.title
        
        return ThreadResponse(
            thread_id=thread_id,
            brand_id=thread_view.brand_id,
            project_id=thread_view.project_id,
            title=title,
            status="open" if thread_view.is_open else "closed",
            created_at=thread_view.created_at,
            updated_at=thread_view.last_activity_at,
        )
