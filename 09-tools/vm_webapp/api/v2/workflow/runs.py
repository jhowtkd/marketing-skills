from __future__ import annotations

from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, status

from vm_webapp.schemas.workflow import (
    WorkflowRunStatus,
    StartWorkflowRunRequest,
)

router = APIRouter(prefix="/workflow/runs", tags=["workflow-runs"])


def _auto_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def _require_idempotency(request: Request) -> str:
    """Extract idempotency key from request headers or generate one."""
    return request.headers.get("Idempotency-Key") or _auto_id("idem")


@router.get(
    "/{run_id}",
    response_model=WorkflowRunStatus,
    summary="Get workflow run status",
    description="Returns the current status of a workflow run including progress percentage, current stage, and completion status.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with run status"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Workflow run not found"},
    },
)
async def get_workflow_run_v2(
    run_id: str,
    request: Request,
) -> WorkflowRunStatus:
    """Get workflow run status.
    
    Args:
        run_id: The unique identifier of the workflow run
        
    Returns:
        Current status of the workflow run including progress and stage information
    """
    from vm_webapp.repo import get_run, list_stages
    from vm_webapp.db import session_scope
    from datetime import datetime
    
    with session_scope(request.app.state.engine) as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        
        stages = list_stages(session, run_id)
        completed = sum(1 for s in stages if s.status == "completed")
        total = len(stages)
        progress_pct = int((completed / total * 100)) if total > 0 else 0
        
        # Determine current stage
        current_stage = None
        for stage in stages:
            if stage.status in ("pending", "running"):
                current_stage = stage.stage_id
                break
        
        return WorkflowRunStatus(
            run_id=run.run_id,
            thread_id=run.thread_id,
            status=run.status,  # type: ignore
            current_stage=current_stage,
            progress_pct=progress_pct,
            started_at=datetime.fromisoformat(run.created_at) if run.created_at else None,
            completed_at=datetime.fromisoformat(run.updated_at) if run.status in ("completed", "failed") else None,
        )


@router.post(
    "",
    response_model=WorkflowRunStatus,
    summary="Start a new workflow run",
    description="Initiates a new workflow run for a thread. The workflow will be queued and executed according to the specified profile mode.",
    responses={
        status.HTTP_201_CREATED: {"description": "Workflow run started successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request data or missing required fields"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Thread not found"},
        status.HTTP_409_CONFLICT: {"description": "Workflow run already exists or conflict"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def start_workflow_run_v2(
    data: StartWorkflowRunRequest,
    request: Request,
) -> WorkflowRunStatus:
    """Start a new workflow run.
    
    Args:
        data: Workflow run request including thread_id, profile_mode, and input payload
        
    Returns:
        The newly created workflow run with pending status
    """
    from vm_webapp.commands_v2 import request_workflow_run_command
    from vm_webapp.repo import get_thread_view, list_stages
    from vm_webapp.db import session_scope
    from datetime import datetime
    
    idem = _require_idempotency(request)
    proposed_run_id = f"run-{uuid4().hex[:12]}"
    actor_id = getattr(request.state, 'actor_id', 'system')
    
    with session_scope(request.app.state.engine) as session:
        thread = get_thread_view(session, data.thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"Thread not found: {data.thread_id}")
        
        dedup = request_workflow_run_command(
            session,
            thread_id=data.thread_id,
            brand_id=thread.brand_id,
            project_id=thread.project_id,
            request_text=data.input_payload.get("request_text", ""),
            mode=data.profile_mode,
            run_id=proposed_run_id,
            skill_overrides=data.input_payload.get("skill_overrides"),
            actor_id=actor_id,
            idempotency_key=idem,
        )
        
        # Queue the run
        request.app.state.workflow_runtime.ensure_queued_run(
            session=session,
            run_id=proposed_run_id,
            thread_id=data.thread_id,
            brand_id=thread.brand_id,
            project_id=thread.project_id,
            request_text=data.input_payload.get("request_text", ""),
            mode=data.profile_mode,
            skill_overrides=data.input_payload.get("skill_overrides") or {},
        )
        
        return WorkflowRunStatus(
            run_id=proposed_run_id,
            thread_id=data.thread_id,
            status="pending",
            current_stage=None,
            progress_pct=0,
            started_at=datetime.now(),
            completed_at=None,
        )


@router.post(
    "/{run_id}/resume",
    summary="Resume a paused workflow run",
    description="Resumes a workflow run that was previously paused. Requires appropriate permissions.",
    responses={
        status.HTTP_200_OK: {"description": "Workflow run resumed successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid run_id or cannot resume"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Workflow run not found"},
        status.HTTP_409_CONFLICT: {"description": "Workflow run not in pausable state"},
    },
)
async def resume_workflow_run_v2(
    run_id: str,
    request: Request,
) -> dict[str, str]:
    """Resume a paused workflow run.
    
    Args:
        run_id: The unique identifier of the workflow run to resume
        
    Returns:
        Status confirmation with run_id and current status
    """
    from vm_webapp.commands_v2 import resume_workflow_run_command
    from vm_webapp.db import session_scope
    
    idem = _require_idempotency(request)
    actor_id = getattr(request.state, 'actor_id', 'system')
    
    with session_scope(request.app.state.engine) as session:
        result = resume_workflow_run_command(
            session,
            run_id=run_id,
            actor_id=actor_id,
            idempotency_key=idem,
        )
        
        import json
        payload = json.loads(result.response_json)
        return {
            "run_id": str(payload.get("run_id", run_id)),
            "status": str(payload.get("status", "running")),
        }


@router.get(
    "/{run_id}/artifacts",
    summary="List workflow run artifacts",
    description="Returns a list of artifacts generated by a workflow run, organized by stage.",
    responses={
        status.HTTP_200_OK: {"description": "Successful response with artifacts list"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Workflow run not found"},
    },
)
async def list_workflow_run_artifacts_v2(
    run_id: str,
    request: Request,
) -> dict[str, list[dict[str, str]]]:
    """List artifacts for a workflow run.
    
    Args:
        run_id: The unique identifier of the workflow run
        
    Returns:
        List of artifacts with stage, name, and path information
    """
    from vm_webapp.repo import get_run
    from vm_webapp.db import session_scope
    
    with session_scope(request.app.state.engine) as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    # Read artifacts from filesystem
    run_root = Path(request.app.state.workspace.root) / "runs" / run_id / "stages"
    artifacts = []
    
    if run_root.exists():
        for stage_dir in run_root.iterdir():
            if stage_dir.is_dir():
                for artifact_file in stage_dir.iterdir():
                    if artifact_file.is_file():
                        artifacts.append({
                            "stage": stage_dir.name,
                            "name": artifact_file.name,
                            "path": str(artifact_file.relative_to(run_root)),
                        })
    
    return {"artifacts": artifacts}
