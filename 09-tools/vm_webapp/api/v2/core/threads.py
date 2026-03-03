from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Request

from vm_webapp.schemas.core import (
    ThreadCreate,
    ThreadUpdate,
    ThreadResponse,
    ThreadsListResponse,
)

router = APIRouter(prefix="/threads", tags=["threads"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@router.get("", response_model=ThreadsListResponse)
async def list_threads_v2(
    request: Request,
    project_id: str,
) -> ThreadsListResponse:
    """List all threads for a project."""
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


@router.post("", response_model=ThreadResponse)
async def create_thread_v2(data: ThreadCreate, request: Request) -> ThreadResponse:
    """Create a new thread."""
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
        response = dedup.response
        return ThreadResponse(
            thread_id=response["thread_id"],
            brand_id=data.brand_id,
            project_id=data.project_id,
            title=data.title,
            status="open",
            created_at=response.get("created_at"),
            updated_at=None,
        )


@router.patch("/{thread_id}", response_model=ThreadResponse)
async def update_thread_v2(
    thread_id: str,
    data: ThreadUpdate,
    request: Request,
) -> ThreadResponse:
    """Update a thread (rename)."""
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
