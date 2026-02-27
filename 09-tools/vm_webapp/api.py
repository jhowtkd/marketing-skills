from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from vm_webapp.commands_v2 import (
    add_comment_command,
    add_thread_mode_command,
    complete_task_command,
    create_brand_command,
    create_campaign_command,
    create_project_command,
    create_task_command,
    create_thread_command,
    grant_approval_command,
    mark_editorial_golden_command,
    remove_thread_mode_command,
    rename_thread_command,
    request_workflow_run_command,
    resume_workflow_run_command,
    start_agent_plan_command,
    update_brand_command,
    update_project_command,
)
from vm_webapp.db import session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.quality_eval import evaluate_run_quality
from vm_webapp.repo import (
    append_event,
    close_thread,
    create_thread as create_thread_row,
    get_editorial_policy,
    get_editorial_slo,
    get_event_by_id,
    get_run,
    get_brand_view,
    get_project_view,
    get_thread,
    get_thread_view,
    list_approvals_view,
    list_brands,
    list_brands_view,
    list_editorial_decisions_view,
    list_projects_view,
    list_products_by_brand,
    list_runs_by_thread,
    list_events_by_thread,
    list_stages,
    list_tasks_view,
    list_threads,
    list_threads_view,
    list_timeline_items_view,
    touch_thread_activity,
    upsert_editorial_policy,
    upsert_editorial_slo,
)
from vm_webapp.editorial_decisions import resolve_baseline
from vm_webapp.editorial_policy import (
    PolicyEvaluator,
    Role,
    Scope,
    create_evaluator_from_session,
)
from vm_webapp.observability import render_prometheus
from vm_webapp.stacking import build_context_pack


router = APIRouter()
api_logger = logging.getLogger("vm_webapp.api")


def _require_open_thread(session, *, thread_id: str, brand_id: str, product_id: str):
    row = get_thread(session, thread_id=thread_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
    if row.brand_id != brand_id or row.product_id != product_id:
        raise HTTPException(status_code=409, detail="thread context mismatch")
    if row.status != "open":
        raise HTTPException(status_code=409, detail=f"thread is {row.status}")
    return row


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


def _database_dependency_status(request: Request) -> dict[str, str]:
    try:
        with session_scope(request.app.state.engine) as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return {"status": "error"}


def _worker_dependency_status(request: Request) -> dict[str, str]:
    worker = getattr(request.app.state, "event_worker", None)
    mode = getattr(
        request.app.state,
        "worker_mode",
        "in_process" if worker is not None else "external",
    )
    if mode == "in_process":
        status = "ok" if worker is not None else "missing"
    else:
        status = "ok"
    return {"status": status, "mode": str(mode)}


@router.get("/v2/health/live")
def health_live(request: Request) -> dict[str, str]:
    request_id = getattr(request.state, "request_id", "")
    correlation_id = getattr(request.state, "correlation_id", "")
    if request_id:
        api_logger.debug(
            "health_live request_id=%s correlation_id=%s",
            request_id,
            correlation_id,
        )
    return {"status": "live"}


@router.get("/v2/health/ready")
def health_ready(request: Request) -> dict[str, object]:
    dependencies = {
        "database": _database_dependency_status(request),
        "worker": _worker_dependency_status(request),
    }
    status = (
        "ready"
        if all(dep.get("status") == "ok" for dep in dependencies.values())
        else "not_ready"
    )
    return {"status": status, "dependencies": dependencies}


@router.get("/brands")
def brands(request: Request) -> dict[str, list[dict[str, str]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_brands(session)
    return {
        "brands": [{"brand_id": row.brand_id, "name": row.name} for row in rows],
    }


@router.get("/products")
def products(brand_id: str, request: Request) -> dict[str, list[dict[str, str]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_products_by_brand(session, brand_id)
    return {
        "products": [
            {"product_id": row.product_id, "brand_id": row.brand_id, "name": row.name}
            for row in rows
        ],
    }


def require_idempotency(request: Request) -> str:
    key = request.headers.get("Idempotency-Key")
    if not key:
        raise HTTPException(status_code=400, detail="missing Idempotency-Key header")
    return key


# RBAC: allowed roles for editorial golden marking
_EDITORIAL_GOLDEN_ALLOWED_ROLES = {"editor", "admin"}


def _require_editorial_role(request: Request) -> str:
    """Extract and validate user role for editorial actions.
    
    Header chain: X-User-Role -> workspace-owner (default) -> editor
    Only editor and admin roles are allowed for golden marking.
    Raises 403 if role is viewer or not allowed.
    """
    raw_role = request.headers.get("X-User-Role", "workspace-owner")
    # Map workspace-owner to editor
    if raw_role == "workspace-owner":
        role = "editor"
    else:
        role = raw_role
    
    if role not in _EDITORIAL_GOLDEN_ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"role '{role}' is not authorized to mark editorial golden"
        )
    return role


def _parse_bearer_token(auth_header: str | None) -> dict[str, str] | None:
    """Parse Bearer token and extract actor_id and role.
    
    Expected format: "Bearer <actor_id>:<role>"
    Returns None if invalid format or missing.
    """
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    token = parts[1]
    token_parts = token.split(":", 1)
    if len(token_parts) != 2:
        return None
    
    actor_id, role = token_parts
    
    # Normalize role
    if role == "workspace-owner":
        normalized_role = "editor"
    else:
        normalized_role = role
    
    return {
        "actor_id": actor_id,
        "actor_role": normalized_role,
    }


def get_actor_context(request: Request) -> dict[str, str]:
    """Extract actor identity and role from request.
    
    Priority (highest to lowest):
    1. Authorization: Bearer <actor_id>:<role>
    2. X-User-Id and X-User-Role headers (legacy fallback)
    3. workspace-owner / editor (default fallback)
    
    Returns dict with:
    - actor_id: extracted or default
    - actor_role: normalized (admin|editor|viewer)
    """
    # Try Bearer token first
    auth_header = request.headers.get("Authorization")
    bearer_ctx = _parse_bearer_token(auth_header)
    if bearer_ctx:
        return bearer_ctx
    
    # Fallback to legacy headers
    actor_id = request.headers.get("X-User-Id", "workspace-owner")
    raw_role = request.headers.get("X-User-Role", "workspace-owner")
    
    # Normalize role
    if raw_role == "workspace-owner":
        actor_role = "editor"
    else:
        actor_role = raw_role
    
    return {
        "actor_id": actor_id,
        "actor_role": actor_role,
    }


def require_valid_auth(request: Request) -> dict[str, str]:
    """Require valid authentication for editorial actions.
    
    Similar to get_actor_context but raises 401 for invalid Bearer tokens.
    Legacy headers (X-User-*) are accepted as valid fallback.
    
    Returns dict with actor_id and actor_role.
    """
    auth_header = request.headers.get("Authorization")
    
    # If Authorization header is present, it must be valid
    if auth_header:
        bearer_ctx = _parse_bearer_token(auth_header)
        if bearer_ctx is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or malformed Authorization token"
            )
        return bearer_ctx
    
    # No Authorization header - use legacy fallback
    return get_actor_context(request)


def _require_admin_role(request: Request) -> str:
    """Extract and validate user role is admin.
    
    Header chain: Authorization Bearer -> X-User-Role -> workspace-owner (default)
    Only admin role is allowed.
    Raises 403 if role is not admin.
    """
    auth_header = request.headers.get("Authorization")
    bearer_ctx = _parse_bearer_token(auth_header)
    
    if bearer_ctx:
        role = bearer_ctx["actor_role"]
        actor_id = bearer_ctx["actor_id"]
    else:
        raw_role = request.headers.get("X-User-Role", "workspace-owner")
        role = "editor" if raw_role == "workspace-owner" else raw_role
        actor_id = request.headers.get("X-User-Id", "workspace-owner")
    
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"role '{role}' is not authorized to manage editorial policy"
        )
    return actor_id


def _get_policy_for_brand(session, brand_id: str) -> dict[str, bool]:
    """Get editorial policy for a brand, returning defaults if not set."""
    policy = get_editorial_policy(session, brand_id)
    if policy is None:
        return {
            "editor_can_mark_objective": True,
            "editor_can_mark_global": False,
        }
    return {
        "editor_can_mark_objective": policy.editor_can_mark_objective,
        "editor_can_mark_global": policy.editor_can_mark_global,
    }


def _enforce_scope_policy_with_brand(
    session, 
    brand_id: str, 
    actor_role: str, 
    scope: str
) -> None:
    """Enforce scope-based policy for editorial golden marking using brand policy.
    
    Raises 403 if actor_role is not allowed for the given scope based on brand policy.
    Uses the PolicyEvaluator for deterministic decisions.
    """
    evaluator = create_evaluator_from_session(session, brand_id)
    result = evaluator.evaluate(
        role=actor_role,
        scope=scope,
        brand_id=brand_id,
    )
    
    if not result.allowed:
        raise HTTPException(
            status_code=403,
            detail=f"role '{actor_role}' is not authorized to mark golden with scope '{scope}'"
        )


def project_command_event(session, *, event_id: str) -> None:
    row = get_event_by_id(session, event_id)
    if row is None:
        raise ValueError(f"event not found: {event_id}")
    apply_event_to_read_models(session, row)


def pump_event_worker(request: Request, *, max_events: int = 30) -> int:
    worker = getattr(request.app.state, "event_worker", None)
    if worker is None:
        return 0
    return int(worker.pump(max_events=max_events))


class BrandCreateRequest(BaseModel):
    brand_id: str | None = None
    name: str


class ProjectCreateRequest(BaseModel):
    project_id: str | None = None
    brand_id: str
    name: str
    objective: str = ""
    channels: list[str] = Field(default_factory=list)
    due_date: str | None = None


class CampaignCreateRequest(BaseModel):
    campaign_id: str | None = None
    brand_id: str
    project_id: str
    title: str


class TaskCreateRequest(BaseModel):
    task_id: str | None = None
    thread_id: str
    campaign_id: str | None = None
    brand_id: str | None = None
    title: str


class ThreadCreateV2Request(BaseModel):
    thread_id: str | None = None
    project_id: str
    brand_id: str
    title: str


class BrandUpdateRequest(BaseModel):
    name: str


class ProjectUpdateRequest(BaseModel):
    name: str
    objective: str = ""
    channels: list[str] = Field(default_factory=list)
    due_date: str | None = None


class ThreadUpdateRequest(BaseModel):
    title: str


class ThreadModeAddRequest(BaseModel):
    mode: str


class WorkflowRunRequest(BaseModel):
    request_text: str
    mode: str = "plan_90d"
    skill_overrides: dict[str, list[str]] = Field(default_factory=dict)


class QualityEvaluationRequest(BaseModel):
    depth: str = "heuristic"
    rubric_version: str = "v1"


class TaskCommentRequest(BaseModel):
    message: str


class ForceConflictRequest(BaseModel):
    thread_id: str


class EditorialGoldenMarkRequest(BaseModel):
    run_id: str
    scope: str
    objective_key: str | None = None
    justification: str
    reason_code: str | None = None

    @field_validator("reason_code")
    @classmethod
    def validate_reason_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"clarity", "structure", "cta", "persuasion", "accuracy", "tone", "other"}
        if v not in allowed:
            raise ValueError(f"reason_code must be one of: {', '.join(sorted(allowed))}")
        return v


class EditorialPolicyUpdateRequest(BaseModel):
    editor_can_mark_objective: bool = True
    editor_can_mark_global: bool = False


class EditorialSLOUpdateRequest(BaseModel):
    max_baseline_none_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    max_policy_denied_rate: float = Field(default=0.2, ge=0.0, le=1.0)
    min_confidence: float = Field(default=0.4, ge=0.0, le=1.0)
    auto_remediation_enabled: bool = False


@router.post("/v2/brands")
def create_brand_v2(payload: BrandCreateRequest, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = create_brand_command(
            session,
            brand_id=payload.brand_id,
            name=payload.name,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        response_payload = json.loads(result.response_json)
    return {"event_id": result.event_id, "brand_id": str(response_payload["brand_id"])}


@router.get("/v2/brands")
def list_brands_v2(request: Request) -> dict[str, list[dict[str, str]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_brands_view(session)
    return {
        "brands": [{"brand_id": row.brand_id, "name": row.name} for row in rows],
    }


@router.patch("/v2/brands/{brand_id}")
def update_brand_v2(
    brand_id: str, payload: BrandUpdateRequest, request: Request
) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        if get_brand_view(session, brand_id) is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")
        result = update_brand_command(
            session,
            brand_id=brand_id,
            name=payload.name,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        updated = get_brand_view(session, brand_id)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")
    return {"event_id": result.event_id, "brand_id": updated.brand_id, "name": updated.name}


@router.post("/v2/projects")
def create_project_v2(payload: ProjectCreateRequest, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = create_project_command(
            session,
            project_id=payload.project_id,
            brand_id=payload.brand_id,
            name=payload.name,
            objective=payload.objective,
            channels=payload.channels,
            due_date=payload.due_date,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        response_payload = json.loads(result.response_json)
    return {"event_id": result.event_id, "project_id": str(response_payload["project_id"])}


@router.patch("/v2/projects/{project_id}")
def update_project_v2(
    project_id: str, payload: ProjectUpdateRequest, request: Request
) -> dict[str, object]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        existing = get_project_view(session, project_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
        result = update_project_command(
            session,
            project_id=project_id,
            brand_id=existing.brand_id,
            name=payload.name,
            objective=payload.objective,
            channels=payload.channels,
            due_date=payload.due_date,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        updated = get_project_view(session, project_id)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    return {
        "event_id": result.event_id,
        "project_id": updated.project_id,
        "brand_id": updated.brand_id,
        "name": updated.name,
        "objective": updated.objective,
        "channels": json.loads(updated.channels_json),
        "due_date": updated.due_date,
    }


@router.get("/v2/projects")
def list_projects_v2(
    brand_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_projects_view(session, brand_id=brand_id)
    return {
        "projects": [
            {
                "project_id": row.project_id,
                "brand_id": row.brand_id,
                "name": row.name,
                "objective": row.objective,
                "channels": json.loads(row.channels_json),
                "due_date": row.due_date,
            }
            for row in rows
        ]
    }


@router.post("/v2/campaigns")
def create_campaign_v2(payload: CampaignCreateRequest, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = create_campaign_command(
            session,
            campaign_id=payload.campaign_id,
            brand_id=payload.brand_id,
            project_id=payload.project_id,
            title=payload.title,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        response_payload = json.loads(result.response_json)
    return {
        "event_id": result.event_id,
        "campaign_id": str(response_payload["campaign_id"]),
        "title": str(response_payload["title"]),
    }


@router.get("/v2/campaigns")
def list_campaigns_v2(
    project_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
    with session_scope(request.app.state.engine) as session:
        from vm_webapp.repo import list_campaigns_view

        rows = list_campaigns_view(session, project_id=project_id)
    return {
        "campaigns": [
            {
                "campaign_id": row.campaign_id,
                "brand_id": row.brand_id,
                "project_id": row.project_id,
                "title": row.title,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


@router.post("/v2/tasks")
def create_task_v2(payload: TaskCreateRequest, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = create_task_command(
            session,
            task_id=payload.task_id,
            thread_id=payload.thread_id,
            campaign_id=payload.campaign_id,
            brand_id=payload.brand_id,
            title=payload.title,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        response_payload = json.loads(result.response_json)
    return {
        "event_id": result.event_id,
        "task_id": str(response_payload["task_id"]),
        "campaign_id": response_payload.get("campaign_id"),
    }


@router.post("/v2/threads")
def create_thread_v2(payload: ThreadCreateV2Request, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = create_thread_command(
            session,
            thread_id=payload.thread_id,
            project_id=payload.project_id,
            brand_id=payload.brand_id,
            title=payload.title,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        response_payload = json.loads(result.response_json)
    return {"event_id": result.event_id, "thread_id": str(response_payload["thread_id"])}


@router.get("/v2/threads")
def list_threads_v2(
    project_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_threads_view(session, project_id=project_id)
    return {
        "threads": [
            {
                "thread_id": row.thread_id,
                "project_id": row.project_id,
                "brand_id": row.brand_id,
                "title": row.title,
                "status": row.status,
                "modes": json.loads(row.modes_json),
                "last_activity_at": row.last_activity_at,
            }
            for row in rows
        ]
    }


@router.patch("/v2/threads/{thread_id}")
def update_thread_v2(
    thread_id: str, payload: ThreadUpdateRequest, request: Request
) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        if get_thread_view(session, thread_id) is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        result = rename_thread_command(
            session,
            thread_id=thread_id,
            title=payload.title,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        updated = get_thread_view(session, thread_id)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
    return {"event_id": result.event_id, "thread_id": updated.thread_id, "title": updated.title}


@router.post("/v2/threads/{thread_id}/modes")
def add_thread_mode_v2(
    thread_id: str, payload: ThreadModeAddRequest, request: Request
) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = add_thread_mode_command(
            session,
            thread_id=thread_id,
            mode=payload.mode,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
    return {"event_id": result.event_id, "thread_id": thread_id}


@router.post("/v2/threads/{thread_id}/modes/{mode}/remove")
def remove_thread_mode_v2(
    thread_id: str, mode: str, request: Request
) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        if get_thread_view(session, thread_id) is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        result = remove_thread_mode_command(
            session,
            thread_id=thread_id,
            mode=mode,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
    return {"event_id": result.event_id, "thread_id": thread_id, "mode": mode}


@router.get("/v2/workflow-profiles")
def list_workflow_profiles_v2(request: Request) -> dict[str, list[dict[str, object]]]:
    payload = request.app.state.workflow_runtime.list_profiles()
    return {"profiles": payload}


@router.get("/v2/metrics")
def metrics_v2(request: Request) -> dict[str, object]:
    return request.app.state.workflow_runtime.metrics.snapshot()


@router.get("/v2/metrics/prometheus")
def metrics_prometheus(request: Request) -> PlainTextResponse:
    metrics = request.app.state.workflow_runtime.metrics
    metrics.record_count("http_request_total:metrics_prometheus")
    payload = render_prometheus(metrics.snapshot())
    return PlainTextResponse(payload, media_type="text/plain; version=0.0.4")


@router.post("/v2/threads/{thread_id}/workflow-runs")
def start_workflow_run_v2(
    thread_id: str, payload: WorkflowRunRequest, request: Request
) -> dict[str, str]:
    idem = require_idempotency(request)
    proposed_run_id = f"run-{uuid4().hex[:12]}"
    with session_scope(request.app.state.engine) as session:
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        result = request_workflow_run_command(
            session,
            thread_id=thread_id,
            brand_id=thread.brand_id,
            project_id=thread.project_id,
            request_text=payload.request_text,
            mode=payload.mode,
            run_id=proposed_run_id,
            skill_overrides=payload.skill_overrides,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        command_payload = json.loads(result.response_json)
        run_id = str(command_payload["run_id"])
        queued = request.app.state.workflow_runtime.ensure_queued_run(
            session=session,
            run_id=run_id,
            thread_id=thread.thread_id,
            brand_id=thread.brand_id,
            project_id=thread.project_id,
            request_text=payload.request_text,
            mode=payload.mode,
            skill_overrides=payload.skill_overrides,
        )
    return {
        "run_id": run_id,
        "status": str(queued.get("status", "queued")),
        "requested_mode": str(queued.get("requested_mode", payload.mode)),
        "effective_mode": str(queued.get("effective_mode", payload.mode)),
    }


@router.get("/v2/threads/{thread_id}/workflow-runs")
def list_workflow_runs_v2(
    thread_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
    pump_event_worker(request, max_events=20)
    with session_scope(request.app.state.engine) as session:
        rows = list_runs_by_thread(session, thread_id)
        payload_rows: list[dict[str, object]] = []
        for row in rows:
            stages = list_stages(session, row.run_id)
            completed = sum(1 for stage in stages if stage.status == "completed")
            # Read plan.json for mode information
            run_root = Path(request.app.state.workspace.root) / "runs" / row.run_id
            plan_path = run_root / "plan.json"
            requested_mode = row.stack_path
            effective_mode = row.stack_path
            if plan_path.exists():
                try:
                    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
                    requested_mode = str(plan_payload.get("requested_mode", row.stack_path))
                    effective_mode = str(plan_payload.get("effective_mode", row.stack_path))
                except Exception:
                    pass
            # Read objective_key from plan.json
            objective_key = ""
            if plan_path.exists():
                try:
                    objective_key = str(plan_payload.get("objective_key", ""))
                except Exception:
                    pass
            
            payload_rows.append(
                {
                    "run_id": row.run_id,
                    "status": row.status,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "completed_stages": completed,
                    "total_stages": len(stages),
                    "request_text": row.user_request,
                    "requested_mode": requested_mode,
                    "effective_mode": effective_mode,
                    "objective_key": objective_key,
                }
            )
    return {
        "runs": payload_rows
    }


@router.get("/v2/workflow-runs/{run_id}/artifacts")
def list_workflow_run_artifacts_v2(run_id: str, request: Request) -> dict[str, object]:
    pump_event_worker(request, max_events=20)
    root = Path(request.app.state.workspace.root) / "runs" / run_id / "stages"
    stages: list[dict[str, object]] = []
    if root.exists():
        for stage_dir in sorted(root.iterdir()):
            manifest = stage_dir / "manifest.json"
            if manifest.exists():
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                payload["stage_dir"] = stage_dir.name
                stages.append(payload)
    return {"run_id": run_id, "stages": stages}


@router.get("/v2/workflow-runs/{run_id}")
def get_workflow_run_v2(run_id: str, request: Request) -> dict[str, object]:
    pump_event_worker(request, max_events=30)
    with session_scope(request.app.state.engine) as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        stage_rows = list_stages(session, run_id)
        approvals = list_approvals_view(session, thread_id=run.thread_id)
        events = list_events_by_thread(session, run.thread_id)

    run_root = Path(request.app.state.workspace.root) / "runs" / run_id
    plan_payload: dict[str, object] = {"mode": "plan_90d", "stages": []}
    plan_path = run_root / "plan.json"
    if plan_path.exists():
        plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_stage_map = {
        str(stage["key"]): stage for stage in plan_payload.get("stages", []) if isinstance(stage, dict)
    }

    manifests_by_stage: dict[str, dict[str, object]] = {}
    stages_root = run_root / "stages"
    if stages_root.exists():
        for stage_dir in sorted(stages_root.iterdir()):
            manifest_path = stage_dir / "manifest.json"
            if manifest_path.exists():
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                payload["stage_dir"] = stage_dir.name
                manifests_by_stage[str(payload.get("stage_key", ""))] = payload

    pending = []
    prefix = f"workflow_gate:{run_id}:"
    for approval in approvals:
        if approval.reason.startswith(prefix) and approval.status == "pending":
            pending.append(
                {
                    "approval_id": approval.approval_id,
                    "status": approval.status,
                    "reason": approval.reason,
                    "required_role": approval.required_role,
                }
            )

    stage_errors: dict[str, dict[str, object]] = {}
    for event in events:
        if event.event_type != "WorkflowRunStageFailed":
            continue
        payload = json.loads(event.payload_json)
        if str(payload.get("run_id", "")) != run.run_id:
            continue
        stage_key = str(payload.get("stage_key", ""))
        if not stage_key:
            continue
        stage_errors[stage_key] = {
            "error_code": payload.get("error_code"),
            "error_message": payload.get("error_message"),
            "retryable": bool(payload.get("retryable", False)),
        }

    stages_payload: list[dict[str, object]] = []
    for row in stage_rows:
        plan_stage = plan_stage_map.get(row.stage_id, {})
        manifest = manifests_by_stage.get(row.stage_id)
        error_meta = stage_errors.get(
            row.stage_id,
            {"error_code": None, "error_message": None, "retryable": False},
        )
        stages_payload.append(
            {
                "stage_id": row.stage_id,
                "position": row.position,
                "status": row.status,
                "attempts": row.attempts,
                "approval_required": row.approval_required,
                "skills": list(plan_stage.get("skills", []))
                if isinstance(plan_stage.get("skills", []), list)
                else [],
                "manifest": manifest,
                "error_code": error_meta["error_code"],
                "error_message": error_meta["error_message"],
                "retryable": error_meta["retryable"],
            }
        )

    requested_mode = str(plan_payload.get("requested_mode", plan_payload.get("mode", "plan_90d")))
    effective_mode = str(plan_payload.get("effective_mode", plan_payload.get("mode", "plan_90d")))
    fallback_applied = bool(
        plan_payload.get("fallback_applied", requested_mode != effective_mode)
    )

    return {
        "run_id": run.run_id,
        "thread_id": run.thread_id,
        "brand_id": run.brand_id,
        "project_id": run.product_id,
        "status": run.status,
        "request_text": run.user_request,
        "mode": effective_mode,
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
        "profile_version": str(plan_payload.get("profile_version", "v1")),
        "fallback_applied": fallback_applied,
        "stages": stages_payload,
        "pending_approvals": pending,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "objective_key": str(plan_payload.get("objective_key", "")),
    }


@router.get("/v2/workflow-runs/{run_id}/baseline")
def get_workflow_run_baseline_v2(run_id: str, request: Request) -> dict[str, object]:
    pump_event_worker(request, max_events=20)
    with session_scope(request.app.state.engine) as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        
        # Get all runs in thread ordered by creation
        runs = list_runs_by_thread(session, run.thread_id)
        
        # Get editorial decisions
        decisions_rows = list_editorial_decisions_view(session, thread_id=run.thread_id)
        decisions: dict[str, Any] = {"global": None, "objective": {}}
        for row in decisions_rows:
            if row.scope == "global":
                decisions["global"] = {"run_id": row.run_id}
            elif row.scope == "objective" and row.objective_key:
                decisions["objective"][row.objective_key] = {"run_id": row.run_id}
        
        # Get objective_key from plan.json
        run_root = Path(request.app.state.workspace.root) / "runs" / run_id
        plan_path = run_root / "plan.json"
        objective_key = ""
        if plan_path.exists():
            try:
                plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
                objective_key = str(plan_payload.get("objective_key", ""))
            except Exception:
                pass
        
        # Resolve baseline
        runs_data = [{"run_id": r.run_id, "objective_key": objective_key if r.run_id == run_id else ""} for r in runs]
        # Fill objective_key for other runs
        for r in runs_data:
            if r["run_id"] != run_id:
                r_plan_path = Path(request.app.state.workspace.root) / "runs" / r["run_id"] / "plan.json"
                if r_plan_path.exists():
                    try:
                        r_plan = json.loads(r_plan_path.read_text(encoding="utf-8"))
                        r["objective_key"] = str(r_plan.get("objective_key", ""))
                    except Exception:
                        pass
        
        baseline = resolve_baseline(
            active_run_id=run_id,
            active_objective_key=objective_key if objective_key else None,
            runs=runs_data,
            decisions=decisions,
        )
        
    # Record metrics for baseline resolution
    request.app.state.workflow_runtime.metrics.record_count("editorial_baseline_resolved_total")
    request.app.state.workflow_runtime.metrics.record_count(f"editorial_baseline_source:{baseline['source']}")
    
    return {
        "run_id": run_id,
        "baseline_run_id": baseline["baseline_run_id"],
        "source": baseline["source"],
        "objective_key": objective_key,
    }


@router.post("/v2/workflow-runs/{run_id}/quality-evaluation")
def evaluate_workflow_run_quality_v2(
    run_id: str, payload: QualityEvaluationRequest, request: Request
) -> dict[str, object]:
    require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        request_text = str(run.user_request or "")

    depth = payload.depth.strip().lower() if payload.depth.strip() else "heuristic"
    rubric_version = payload.rubric_version.strip() if payload.rubric_version.strip() else "v1"
    return evaluate_run_quality(
        run_id=run_id,
        request_text=request_text,
        workspace_root=Path(request.app.state.workspace.root),
        depth=depth,
        rubric_version=rubric_version,
    )


@router.post("/v2/workflow-runs/{run_id}/resume")
def resume_workflow_run_v2(run_id: str, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = resume_workflow_run_command(
            session,
            run_id=run_id,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        if result.event_id.startswith("evt-"):
            project_command_event(session, event_id=result.event_id)
    payload = json.loads(result.response_json)
    return {
        "run_id": str(payload.get("run_id", run_id)),
        "status": str(payload.get("status", "running")),
    }


@router.get("/v2/workflow-runs/{run_id}/artifact-content")
def get_workflow_artifact_content_v2(
    run_id: str, stage_dir: str, artifact_path: str, request: Request
) -> dict[str, str]:
    root = Path(request.app.state.workspace.root) / "runs" / run_id / "stages" / stage_dir
    if not root.exists():
        raise HTTPException(status_code=404, detail="stage not found")
    target = (root / artifact_path).resolve()
    root_resolved = root.resolve()
    if root_resolved not in target.parents and target != root_resolved:
        raise HTTPException(status_code=400, detail="invalid artifact path")
    if not target.exists():
        raise HTTPException(status_code=404, detail="artifact not found")
    return {
        "run_id": run_id,
        "stage_dir": stage_dir,
        "artifact_path": artifact_path,
        "content": target.read_text(encoding="utf-8"),
    }


@router.get("/v2/threads/{thread_id}/timeline")
def list_thread_timeline_v2(
    thread_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
    pump_event_worker(request, max_events=20)
    with session_scope(request.app.state.engine) as session:
        rows = list_timeline_items_view(session, thread_id=thread_id)
    return {
        "items": [
            {
                "event_id": row.event_id,
                "thread_id": row.thread_id,
                "event_type": row.event_type,
                "actor_type": row.actor_type,
                "actor_id": row.actor_id,
                "payload": json.loads(row.payload_json),
                "occurred_at": row.occurred_at,
            }
            for row in rows
        ]
    }


@router.get("/v2/threads/{thread_id}/tasks")
def list_thread_tasks_v2(
    thread_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
    pump_event_worker(request, max_events=20)
    with session_scope(request.app.state.engine) as session:
        rows = list_tasks_view(session, thread_id=thread_id)
    return {
        "items": [
            {
                "task_id": row.task_id,
                "thread_id": row.thread_id,
                "title": row.title,
                "status": row.status,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


@router.get("/v2/threads/{thread_id}/approvals")
def list_thread_approvals_v2(
    thread_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
    pump_event_worker(request, max_events=20)
    with session_scope(request.app.state.engine) as session:
        rows = list_approvals_view(session, thread_id=thread_id)
    return {
        "items": [
            {
                "approval_id": row.approval_id,
                "thread_id": row.thread_id,
                "status": row.status,
                "reason": row.reason,
                "required_role": row.required_role,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


@router.post("/v2/tasks/{task_id}/comment")
def comment_task_v2(
    task_id: str, payload: TaskCommentRequest, request: Request
) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = add_comment_command(
            session,
            task_id=task_id,
            message=payload.message,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
    return {"event_id": result.event_id, "task_id": task_id}


@router.post("/v2/tasks/{task_id}/complete")
def complete_task_v2(task_id: str, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = complete_task_command(
            session,
            task_id=task_id,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
    return {"event_id": result.event_id, "task_id": task_id}


@router.post("/v2/approvals/{approval_id}/grant")
def grant_approval_v2(approval_id: str, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        try:
            result = grant_approval_command(
                session,
                approval_id=approval_id,
                actor_id="workspace-owner",
                idempotency_key=idem,
            )
        except ValueError as exc:
            message = str(exc)
            if message.startswith("approval not found:"):
                raise HTTPException(status_code=404, detail=message) from exc
            raise
        project_command_event(session, event_id=result.event_id)
    return {"event_id": result.event_id, "approval_id": approval_id}


@router.post("/v2/threads/{thread_id}/agent-plan/start")
def start_agent_plan_v2(thread_id: str, request: Request) -> dict[str, str]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = start_agent_plan_command(
            session,
            thread_id=thread_id,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
    return {"event_id": result.event_id, "thread_id": thread_id}


@router.post("/v2/test/force-conflict")
def force_conflict_v2(payload: ForceConflictRequest, request: Request) -> dict[str, str]:
    stream_id = f"thread:{payload.thread_id}"
    with session_scope(request.app.state.engine) as session:
        append_event(
            session,
            EventEnvelope(
                event_id=f"evt-conflict-a-{payload.thread_id}",
                event_type="ConflictProbe",
                aggregate_type="thread",
                aggregate_id=payload.thread_id,
                stream_id=stream_id,
                expected_version=0,
                actor_type="system",
                actor_id="test-helper",
                payload={"thread_id": payload.thread_id},
                thread_id=payload.thread_id,
            ),
        )
        append_event(
            session,
            EventEnvelope(
                event_id=f"evt-conflict-b-{payload.thread_id}",
                event_type="ConflictProbe",
                aggregate_type="thread",
                aggregate_id=payload.thread_id,
                stream_id=stream_id,
                expected_version=0,
                actor_type="system",
                actor_id="test-helper",
                payload={"thread_id": payload.thread_id},
                thread_id=payload.thread_id,
            ),
        )
    return {"status": "ok"}


class ChatRequest(BaseModel):
    brand_id: str
    product_id: str
    thread_id: str
    message: str


class ThreadCreateRequest(BaseModel):
    brand_id: str
    product_id: str
    title: str | None = None


class FoundationRunRequest(BaseModel):
    brand_id: str
    product_id: str
    thread_id: str
    user_request: str


@router.get("/threads")
def threads(brand_id: str, product_id: str, request: Request) -> dict[str, list[dict[str, str]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_threads(session, brand_id=brand_id, product_id=product_id)
    return {
        "threads": [
            {
                "thread_id": row.thread_id,
                "brand_id": row.brand_id,
                "product_id": row.product_id,
                "title": row.title,
                "status": row.status,
                "last_activity_at": row.last_activity_at,
            }
            for row in rows
        ]
    }


@router.post("/threads")
def create_thread_api(payload: ThreadCreateRequest, request: Request) -> dict[str, str]:
    thread_id = f"thread-{uuid4().hex[:12]}"
    title = payload.title or "New Thread"
    with session_scope(request.app.state.engine) as session:
        row = create_thread_row(
            session,
            thread_id=thread_id,
            brand_id=payload.brand_id,
            product_id=payload.product_id,
            title=title,
        )
    return {"thread_id": row.thread_id, "status": row.status, "title": row.title}


@router.post("/threads/{thread_id}/close")
def close_thread_api(thread_id: str, request: Request) -> dict[str, str]:
    with session_scope(request.app.state.engine) as session:
        row = get_thread(session, thread_id=thread_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        close_thread(session, thread_id=thread_id)
    return {"thread_id": thread_id, "status": "closed"}


@router.get("/threads/{thread_id}/messages")
def thread_messages(thread_id: str, request: Request) -> dict[str, list[dict[str, str]]]:
    chat_path = Path(request.app.state.workspace.root) / "threads" / thread_id / "chat.jsonl"
    if not chat_path.exists():
        return {"messages": []}
    messages: list[dict[str, str]] = []
    for line in chat_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            messages.append(json.loads(line))
    return {"messages": messages}


@router.post("/runs/foundation")
def start_foundation_run(payload: FoundationRunRequest, request: Request) -> dict[str, str]:
    with session_scope(request.app.state.engine) as session:
        _require_open_thread(
            session,
            thread_id=payload.thread_id,
            brand_id=payload.brand_id,
            product_id=payload.product_id,
        )

    stack_path = (
        Path(__file__).resolve().parents[2] / "06-stacks" / "foundation-stack" / "stack.yaml"
    )
    run_engine = request.app.state.run_engine
    run = run_engine.start_run(
        brand_id=payload.brand_id,
        product_id=payload.product_id,
        thread_id=payload.thread_id,
        stack_path=str(stack_path),
        user_request=payload.user_request,
    )
    run_engine.run_until_gate(run.run_id)
    run = run_engine.get_run(run.run_id)
    with session_scope(request.app.state.engine) as session:
        touch_thread_activity(session, payload.thread_id)
    return {"run_id": run.run_id, "status": run.status}


@router.get("/runs")
def runs(thread_id: str, request: Request) -> dict[str, list[dict[str, object]]]:
    with session_scope(request.app.state.engine) as session:
        rows = list_runs_by_thread(session, thread_id)
        runs_payload = []
        for row in rows:
            stages = list_stages(session, row.run_id)
            runs_payload.append(
                {
                    "run_id": row.run_id,
                    "thread_id": row.thread_id,
                    "brand_id": row.brand_id,
                    "product_id": row.product_id,
                    "status": row.status,
                    "stack_path": row.stack_path,
                    "created_at": row.created_at,
                    "stages": [
                        {
                            "stage_id": stage.stage_id,
                            "status": stage.status,
                            "approval_required": stage.approval_required,
                            "attempts": stage.attempts,
                            "position": stage.position,
                        }
                        for stage in stages
                    ],
                }
            )
    return {
        "runs": runs_payload
    }


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: str, request: Request) -> dict[str, str]:
    run_engine = request.app.state.run_engine
    try:
        run_engine.approve_and_continue(run_id)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=409, detail=message) from exc

    run = run_engine.get_run(run_id)
    return {"run_id": run.run_id, "status": run.status}


@router.get("/runs/{run_id}/events")
def run_events(
    run_id: str,
    request: Request,
    from_start: bool = False,
    max_events: int = 100,
) -> StreamingResponse:
    workspace = request.app.state.workspace
    events_path = Path(workspace.root) / "runs" / run_id / "events.jsonl"

    def event_iter():
        emitted = 0
        offset = 0
        if not from_start and events_path.exists():
            offset = events_path.stat().st_size

        while emitted < max_events:
            if events_path.exists():
                with events_path.open("r", encoding="utf-8") as fh:
                    fh.seek(offset)
                    for line in fh:
                        event = line.strip()
                        if not event:
                            continue
                        yield f"data: {event}\n\n"
                        emitted += 1
                        if emitted >= max_events:
                            return
                    offset = fh.tell()
            time.sleep(0.1)

    return StreamingResponse(event_iter(), media_type="text/event-stream")


@router.post("/chat")
def chat(payload: ChatRequest, request: Request) -> dict[str, str]:
    with session_scope(request.app.state.engine) as session:
        _require_open_thread(
            session,
            thread_id=payload.thread_id,
            brand_id=payload.brand_id,
            product_id=payload.product_id,
        )

    workspace = request.app.state.workspace
    memory = request.app.state.memory
    llm = request.app.state.llm
    settings = request.app.state.settings

    retrieved_hits = memory.search(
        payload.message,
        filters={"brand_id": payload.brand_id},
        top_k=3,
    )
    retrieved = [
        {
            "title": str(hit.meta.get("title", hit.doc_id)),
            "text": hit.text,
        }
        for hit in retrieved_hits
    ]

    soul_path = workspace.brand_soul_path(payload.brand_id)
    essence_path = workspace.product_essence_path(payload.brand_id, payload.product_id)
    soul_md = soul_path.read_text(encoding="utf-8") if soul_path.exists() else ""
    essence_md = essence_path.read_text(encoding="utf-8") if essence_path.exists() else ""

    context = build_context_pack(
        brand_soul_md=soul_md,
        product_essence_md=essence_md,
        retrieved=retrieved,
        stage_contract="Write output in Markdown.",
        user_request=payload.message,
    )

    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": payload.message},
    ]
    assistant_message = "(llm not configured)"
    if llm is not None:
        assistant_message = llm.chat(
            model=settings.kimi_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )

    now = datetime.now(timezone.utc).isoformat()
    chat_path = Path(workspace.root) / "threads" / payload.thread_id / "chat.jsonl"
    chat_path.parent.mkdir(parents=True, exist_ok=True)
    with chat_path.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "ts": now,
                    "role": "user",
                    "content": payload.message,
                    "brand_id": payload.brand_id,
                    "product_id": payload.product_id,
                    "thread_id": payload.thread_id,
                },
                ensure_ascii=False,
            )
        )
        fh.write("\n")
        fh.write(
            json.dumps(
                {
                    "ts": now,
                    "role": "assistant",
                    "content": assistant_message,
                    "brand_id": payload.brand_id,
                    "product_id": payload.product_id,
                    "thread_id": payload.thread_id,
                },
                ensure_ascii=False,
            )
        )
        fh.write("\n")

    with session_scope(request.app.state.engine) as session:
        touch_thread_activity(session, payload.thread_id)

    memory.upsert_doc(
        doc_id=f"chat:{payload.thread_id}:{uuid4().hex[:8]}",
        text=assistant_message,
        meta={
            "brand_id": payload.brand_id,
            "product_id": payload.product_id,
            "thread_id": payload.thread_id,
            "kind": "chat",
        },
    )

    return {"assistant_message": assistant_message}


@router.post("/v2/threads/{thread_id}/editorial-decisions/golden")
def mark_editorial_golden_v2(
    thread_id: str, payload: EditorialGoldenMarkRequest, request: Request
) -> dict[str, object]:
    idem = require_idempotency(request)
    
    # RBAC: validate user role
    _require_editorial_role(request)
    
    # Get actor context (identity + role) - require valid auth
    actor_ctx = require_valid_auth(request)
    
    # Validation: justification must not be empty
    if not payload.justification or not payload.justification.strip():
        raise HTTPException(status_code=422, detail="justification is required")
    
    # Validation: scope must be valid
    if payload.scope not in {"global", "objective"}:
        raise HTTPException(status_code=422, detail="scope must be 'global' or 'objective'")
    
    # Validation: objective scope requires objective_key
    if payload.scope == "objective" and not payload.objective_key:
        raise HTTPException(status_code=422, detail="objective_key is required when scope is 'objective'")
    
    with session_scope(request.app.state.engine) as session:
        # Validation: thread must exist
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        # Validation: run must belong to thread
        run = get_run(session, payload.run_id)
        if run is None or run.thread_id != thread_id:
            raise HTTPException(status_code=404, detail=f"run not found in thread: {payload.run_id}")
        
        # Policy: enforce scope-based authorization using brand policy
        try:
            _enforce_scope_policy_with_brand(
                session, 
                brand_id=thread.brand_id,
                actor_role=actor_ctx["actor_role"], 
                scope=payload.scope
            )
        except HTTPException as e:
            if e.status_code == 403:
                # Record policy denial metric
                request.app.state.workflow_runtime.metrics.record_count("editorial_golden_policy_denied_total")
                request.app.state.workflow_runtime.metrics.record_count(f"editorial_golden_policy_denied_role:{actor_ctx['actor_role']}")
                request.app.state.workflow_runtime.metrics.record_count(f"editorial_golden_policy_denied_scope:{payload.scope}")
            raise
        
        result = mark_editorial_golden_command(
            session,
            thread_id=thread_id,
            run_id=payload.run_id,
            scope=payload.scope,
            objective_key=payload.objective_key,
            justification=payload.justification,
            reason_code=payload.reason_code,
            actor_id=actor_ctx["actor_id"],
            actor_role=actor_ctx["actor_role"],
            idempotency_key=idem,
        )
        project_command_event(session, event_id=result.event_id)
        response_payload = json.loads(result.response_json)
    
    # Record metrics for golden marking
    request.app.state.workflow_runtime.metrics.record_count("editorial_golden_marked_total")
    request.app.state.workflow_runtime.metrics.record_count(f"editorial_golden_marked_scope:{payload.scope}")
    
    return {
        "event_id": result.event_id,
        "thread_id": thread_id,
        "run_id": payload.run_id,
        "scope": payload.scope,
        "objective_key": payload.objective_key,
    }


@router.get("/v2/threads/{thread_id}/editorial-decisions")
def list_editorial_decisions_v2(thread_id: str, request: Request) -> dict[str, object]:
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        rows = list_editorial_decisions_view(session, thread_id=thread_id)
        
        global_decision = None
        objective_decisions = []
        
        for row in rows:
            decision = {
                "run_id": row.run_id,
                "justification": row.justification,
                "updated_at": row.updated_at,
            }
            if row.scope == "global":
                global_decision = decision
            elif row.scope == "objective" and row.objective_key:
                decision["objective_key"] = row.objective_key
                objective_decisions.append(decision)
    
    # Record metric for decisions list
    request.app.state.workflow_runtime.metrics.record_count("editorial_decisions_list_total")
    
    return {
        "global": global_decision,
        "objective": objective_decisions,
    }


@router.get("/v2/threads/{thread_id}/editorial-decisions/audit")
def get_editorial_audit_v2(
    thread_id: str, 
    request: Request,
    scope: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    """Get audit trail of editorial golden decisions for a thread.
    
    Returns chronological list of EditorialGoldenMarked events with full context.
    Supports filtering by scope and pagination.
    """
    pump_event_worker(request, max_events=20)
    
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        # Query timeline items for EditorialGoldenMarked events
        from sqlalchemy import select
        from vm_webapp.models import TimelineItemView
        
        query = (
            select(TimelineItemView)
            .where(TimelineItemView.thread_id == thread_id)
            .where(TimelineItemView.event_type == "EditorialGoldenMarked")
            .order_by(TimelineItemView.timeline_pk.asc())
        )
        
        rows = list(session.scalars(query))
        
        events = []
        for row in rows:
            payload = json.loads(row.payload_json)
            
            # Apply scope filter if provided
            if scope and payload.get("scope") != scope:
                continue
            
            events.append({
                "event_id": row.event_id,
                "event_type": row.event_type,
                "occurred_at": row.occurred_at,
                "actor_id": row.actor_id,
                "actor_role": payload.get("actor_role", "editor"),
                "scope": payload.get("scope"),
                "objective_key": payload.get("objective_key"),
                "run_id": payload.get("run_id"),
                "justification": payload.get("justification"),
                "reason_code": payload.get("reason_code"),
            })
        
        # Apply pagination
        total = len(events)
        paginated_events = events[offset:offset + limit]
        
        return {
            "thread_id": thread_id,
            "events": paginated_events,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/v2/brands/{brand_id}/editorial-policy")
def get_editorial_policy_v2(brand_id: str, request: Request) -> dict[str, object]:
    """Get editorial policy for a brand.
    
    Returns default policy if no custom policy is set.
    """
    with session_scope(request.app.state.engine) as session:
        # Verify brand exists
        brand = get_brand_view(session, brand_id)
        if brand is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")
        
        policy = _get_policy_for_brand(session, brand_id)
        
    return {
        "brand_id": brand_id,
        "editor_can_mark_objective": policy["editor_can_mark_objective"],
        "editor_can_mark_global": policy["editor_can_mark_global"],
        "updated_at": brand.updated_at,
    }


@router.put("/v2/brands/{brand_id}/editorial-policy")
def update_editorial_policy_v2(
    brand_id: str, 
    payload: EditorialPolicyUpdateRequest, 
    request: Request
) -> dict[str, object]:
    """Update editorial policy for a brand.
    
    Only admin role can update policy.
    Requires Idempotency-Key header.
    """
    idem = require_idempotency(request)
    actor_id = _require_admin_role(request)
    
    with session_scope(request.app.state.engine) as session:
        # Verify brand exists
        brand = get_brand_view(session, brand_id)
        if brand is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")
        
        # Check idempotency
        from vm_webapp.repo import get_command_dedup, save_command_dedup
        dedup = get_command_dedup(session, idempotency_key=idem)
        if dedup is not None:
            # Return existing policy
            policy = _get_policy_for_brand(session, brand_id)
            return {
                "brand_id": brand_id,
                "editor_can_mark_objective": policy["editor_can_mark_objective"],
                "editor_can_mark_global": policy["editor_can_mark_global"],
                "updated_at": brand.updated_at,
            }
        
        # Update policy
        policy = upsert_editorial_policy(
            session,
            brand_id=brand_id,
            editor_can_mark_objective=payload.editor_can_mark_objective,
            editor_can_mark_global=payload.editor_can_mark_global,
        )
        
        # Save dedup record
        save_command_dedup(
            session,
            idempotency_key=idem,
            command_name="update_editorial_policy",
            event_id=f"policy-update-{brand_id}",
            response={
                "brand_id": brand_id,
                "editor_can_mark_objective": policy.editor_can_mark_objective,
                "editor_can_mark_global": policy.editor_can_mark_global,
            },
        )
        
        return {
            "brand_id": brand_id,
            "editor_can_mark_objective": policy.editor_can_mark_objective,
            "editor_can_mark_global": policy.editor_can_mark_global,
            "updated_at": policy.updated_at,
        }


@router.get("/v2/brands/{brand_id}/editorial-slo")
def get_editorial_slo_v2(brand_id: str, request: Request) -> dict[str, object]:
    """Get editorial SLO configuration for a brand.
    
    Returns default SLO if no custom configuration is set.
    """
    with session_scope(request.app.state.engine) as session:
        # Verify brand exists
        brand = get_brand_view(session, brand_id)
        if brand is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")
        
        slo = get_editorial_slo(session, brand_id)
        
    return {
        "brand_id": brand_id,
        "max_baseline_none_rate": slo.max_baseline_none_rate if slo else 0.5,
        "max_policy_denied_rate": slo.max_policy_denied_rate if slo else 0.2,
        "min_confidence": slo.min_confidence if slo else 0.4,
        "auto_remediation_enabled": slo.auto_remediation_enabled if slo else False,
        "updated_at": slo.updated_at if slo else brand.updated_at,
    }


@router.put("/v2/brands/{brand_id}/editorial-slo")
def update_editorial_slo_v2(
    brand_id: str, 
    payload: EditorialSLOUpdateRequest, 
    request: Request
) -> dict[str, object]:
    """Update editorial SLO configuration for a brand.
    
    Only admin role can update SLO.
    Requires Idempotency-Key header.
    """
    idem = require_idempotency(request)
    actor_id = _require_admin_role(request)
    
    with session_scope(request.app.state.engine) as session:
        # Verify brand exists
        brand = get_brand_view(session, brand_id)
        if brand is None:
            raise HTTPException(status_code=404, detail=f"brand not found: {brand_id}")
        
        # Check idempotency
        from vm_webapp.repo import get_command_dedup, save_command_dedup
        dedup = get_command_dedup(session, idempotency_key=idem)
        if dedup is not None:
            # Return existing SLO
            slo = get_editorial_slo(session, brand_id)
            return {
                "brand_id": brand_id,
                "max_baseline_none_rate": slo.max_baseline_none_rate if slo else 0.5,
                "max_policy_denied_rate": slo.max_policy_denied_rate if slo else 0.2,
                "min_confidence": slo.min_confidence if slo else 0.4,
                "auto_remediation_enabled": slo.auto_remediation_enabled if slo else False,
                "updated_at": slo.updated_at if slo else brand.updated_at,
            }
        
        # Update SLO
        slo = upsert_editorial_slo(
            session,
            brand_id=brand_id,
            max_baseline_none_rate=payload.max_baseline_none_rate,
            max_policy_denied_rate=payload.max_policy_denied_rate,
            min_confidence=payload.min_confidence,
            auto_remediation_enabled=payload.auto_remediation_enabled,
        )
        
        # Save dedup record
        save_command_dedup(
            session,
            idempotency_key=idem,
            command_name="update_editorial_slo",
            event_id=f"slo-update-{brand_id}",
            response={
                "brand_id": brand_id,
                "max_baseline_none_rate": slo.max_baseline_none_rate,
                "max_policy_denied_rate": slo.max_policy_denied_rate,
                "min_confidence": slo.min_confidence,
                "auto_remediation_enabled": slo.auto_remediation_enabled,
            },
        )
        
        return {
            "brand_id": brand_id,
            "max_baseline_none_rate": slo.max_baseline_none_rate,
            "max_policy_denied_rate": slo.max_policy_denied_rate,
            "min_confidence": slo.min_confidence,
            "auto_remediation_enabled": slo.auto_remediation_enabled,
            "updated_at": slo.updated_at,
        }


@router.get("/v2/threads/{thread_id}/editorial-decisions/insights")
def get_editorial_insights_v2(thread_id: str, request: Request) -> dict[str, object]:
    """Get editorial governance insights for a thread.
    
    Returns aggregated KPIs including totals by scope, reason_code,
    policy denials, baseline resolution stats, and recency metrics.
    """
    pump_event_worker(request, max_events=20)
    
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        from sqlalchemy import select, func
        from vm_webapp.models import TimelineItemView, EventLog
        
        # Query all EditorialGoldenMarked events for this thread
        query = (
            select(TimelineItemView)
            .where(TimelineItemView.thread_id == thread_id)
            .where(TimelineItemView.event_type == "EditorialGoldenMarked")
            .order_by(TimelineItemView.timeline_pk.asc())
        )
        
        rows = list(session.scalars(query))
        
        # Calculate totals
        marked_total = len(rows)
        by_scope: dict[str, int] = {"global": 0, "objective": 0}
        by_reason_code: dict[str, int] = {}
        last_marked_at: str | None = None
        last_actor_id: str | None = None
        
        for row in rows:
            payload = json.loads(row.payload_json)
            scope = payload.get("scope")
            if scope in by_scope:
                by_scope[scope] += 1
            
            reason_code = payload.get("reason_code") or "other"
            by_reason_code[reason_code] = by_reason_code.get(reason_code, 0) + 1
            
            if last_marked_at is None or row.occurred_at > last_marked_at:
                last_marked_at = row.occurred_at
                last_actor_id = row.actor_id
        
        # Query policy denials from metrics (stored as events with denial info)
        denial_query = (
            select(EventLog)
            .where(EventLog.thread_id == thread_id)
            .where(EventLog.event_type == "EditorialGoldenPolicyDenied")
        )
        denied_total = len(list(session.scalars(denial_query)))
        
        # Calculate baseline resolution stats from event log
        baseline_query = (
            select(EventLog)
            .where(EventLog.thread_id == thread_id)
            .where(EventLog.event_type == "EditorialBaselineResolved")
        )
        baseline_rows = list(session.scalars(baseline_query))
        resolved_total = len(baseline_rows)
        by_source: dict[str, int] = {
            "objective_golden": 0,
            "global_golden": 0,
            "previous": 0,
            "none": 0,
        }
        for row in baseline_rows:
            payload = json.loads(row.payload_json)
            source = payload.get("source", "none")
            if source in by_source:
                by_source[source] += 1
        
        return {
            "thread_id": thread_id,
            "totals": {
                "marked_total": marked_total,
                "by_scope": by_scope,
                "by_reason_code": by_reason_code,
            },
            "policy": {
                "denied_total": denied_total,
            },
            "baseline": {
                "resolved_total": resolved_total,
                "by_source": by_source,
            },
            "recency": {
                "last_marked_at": last_marked_at,
                "last_actor_id": last_actor_id,
            },
        }


@router.get("/v2/threads/{thread_id}/editorial-decisions/recommendations")
def get_editorial_recommendations_v2(thread_id: str, request: Request) -> dict[str, object]:
    """Get automated operational recommendations for editorial governance.
    
    Analyzes KPIs from insights and generates actionable recommendations
    with severity levels (info, warning, critical).
    """
    from datetime import datetime, timezone
    from vm_webapp.editorial_recommendations import generate_recommendations, recommendations_to_dict
    
    pump_event_worker(request, max_events=20)
    
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        # Reuse insights logic - call the insights endpoint logic directly
        from sqlalchemy import select
        from vm_webapp.models import TimelineItemView, EventLog
        
        # Query all EditorialGoldenMarked events for this thread
        query = (
            select(TimelineItemView)
            .where(TimelineItemView.thread_id == thread_id)
            .where(TimelineItemView.event_type == "EditorialGoldenMarked")
            .order_by(TimelineItemView.timeline_pk.asc())
        )
        
        rows = list(session.scalars(query))
        
        # Calculate totals
        marked_total = len(rows)
        by_scope: dict[str, int] = {"global": 0, "objective": 0}
        by_reason_code: dict[str, int] = {}
        last_marked_at: str | None = None
        last_actor_id: str | None = None
        
        for row in rows:
            payload = json.loads(row.payload_json)
            scope = payload.get("scope")
            if scope in by_scope:
                by_scope[scope] += 1
            
            reason_code = payload.get("reason_code") or "other"
            by_reason_code[reason_code] = by_reason_code.get(reason_code, 0) + 1
            
            if last_marked_at is None or row.occurred_at > last_marked_at:
                last_marked_at = row.occurred_at
                last_actor_id = row.actor_id
        
        # Query policy denials
        denial_query = (
            select(EventLog)
            .where(EventLog.thread_id == thread_id)
            .where(EventLog.event_type == "EditorialGoldenPolicyDenied")
        )
        denied_total = len(list(session.scalars(denial_query)))
        
        # Calculate baseline resolution stats
        baseline_query = (
            select(EventLog)
            .where(EventLog.thread_id == thread_id)
            .where(EventLog.event_type == "EditorialBaselineResolved")
        )
        baseline_rows = list(session.scalars(baseline_query))
        resolved_total = len(baseline_rows)
        by_source: dict[str, int] = {
            "objective_golden": 0,
            "global_golden": 0,
            "previous": 0,
            "none": 0,
        }
        for row in baseline_rows:
            payload = json.loads(row.payload_json)
            source = payload.get("source", "none")
            if source in by_source:
                by_source[source] += 1
        
        # Build insights data structure
        insights_data = {
            "thread_id": thread_id,
            "totals": {
                "marked_total": marked_total,
                "by_scope": by_scope,
                "by_reason_code": by_reason_code,
            },
            "policy": {
                "denied_total": denied_total,
            },
            "baseline": {
                "resolved_total": resolved_total,
                "by_source": by_source,
            },
            "recency": {
                "last_marked_at": last_marked_at,
                "last_actor_id": last_actor_id,
            },
        }
        
        # Build recent events list for cooldown tracking
        recent_events = [{"action_id": "baseline_resolved", "occurred_at": row.occurred_at} for row in baseline_rows[-10:]]
        
        # Generate recommendations with anti-noise guardrails
        recommendations = generate_recommendations(insights_data, recent_events=recent_events)
        
        return {
            "thread_id": thread_id,
            "recommendations": recommendations_to_dict(recommendations),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/v2/threads/{thread_id}/editorial-decisions/forecast")
def get_editorial_forecast_v2(thread_id: str, request: Request) -> dict[str, object]:
    """Get predictive editorial risk forecast for a thread.
    
    Returns deterministic and explainable risk assessment including:
    - risk_score: 0-100 (higher = more risk)
    - trend: improving|stable|degrading
    - drivers: list of contributing factors
    - recommended_focus: actionable guidance
    """
    from datetime import datetime, timezone
    from vm_webapp.editorial_forecast import calculate_forecast, forecast_to_dict
    
    pump_event_worker(request, max_events=20)
    
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        # Reuse insights logic
        from sqlalchemy import select
        from vm_webapp.models import TimelineItemView, EventLog
        
        # Query all EditorialGoldenMarked events for this thread
        query = (
            select(TimelineItemView)
            .where(TimelineItemView.thread_id == thread_id)
            .where(TimelineItemView.event_type == "EditorialGoldenMarked")
            .order_by(TimelineItemView.timeline_pk.asc())
        )
        
        rows = list(session.scalars(query))
        
        # Calculate totals
        marked_total = len(rows)
        by_scope: dict[str, int] = {"global": 0, "objective": 0}
        by_reason_code: dict[str, int] = {}
        last_marked_at: str | None = None
        last_actor_id: str | None = None
        
        for row in rows:
            payload = json.loads(row.payload_json)
            scope = payload.get("scope")
            if scope in by_scope:
                by_scope[scope] += 1
            
            reason_code = payload.get("reason_code") or "other"
            by_reason_code[reason_code] = by_reason_code.get(reason_code, 0) + 1
            
            if last_marked_at is None or row.occurred_at > last_marked_at:
                last_marked_at = row.occurred_at
                last_actor_id = row.actor_id
        
        # Query policy denials
        denial_query = (
            select(EventLog)
            .where(EventLog.thread_id == thread_id)
            .where(EventLog.event_type == "EditorialGoldenPolicyDenied")
        )
        denied_total = len(list(session.scalars(denial_query)))
        
        # Calculate baseline resolution stats
        baseline_query = (
            select(EventLog)
            .where(EventLog.thread_id == thread_id)
            .where(EventLog.event_type == "EditorialBaselineResolved")
        )
        baseline_rows = list(session.scalars(baseline_query))
        resolved_total = len(baseline_rows)
        by_source: dict[str, int] = {
            "objective_golden": 0,
            "global_golden": 0,
            "previous": 0,
            "none": 0,
        }
        for row in baseline_rows:
            payload = json.loads(row.payload_json)
            source = payload.get("source", "none")
            if source in by_source:
                by_source[source] += 1
        
        # Build insights data structure
        insights_data = {
            "thread_id": thread_id,
            "totals": {
                "marked_total": marked_total,
                "by_scope": by_scope,
                "by_reason_code": by_reason_code,
            },
            "policy": {
                "denied_total": denied_total,
            },
            "baseline": {
                "resolved_total": resolved_total,
                "by_source": by_source,
            },
            "recency": {
                "last_marked_at": last_marked_at,
                "last_actor_id": last_actor_id,
            },
        }
        
        # Calculate forecast
        forecast = calculate_forecast(insights_data)
        
        # Record metric for forecast requests
        request.app.state.workflow_runtime.metrics.record_count("editorial_forecast_requested_total")
        
        return {
            "thread_id": thread_id,
            "risk_score": forecast.risk_score,
            "trend": forecast.trend,
            "drivers": forecast.drivers,
            "recommended_focus": forecast.recommended_focus,
            "confidence": forecast.confidence,
            "volatility": forecast.volatility,
            "calibration_notes": forecast.calibration_notes,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


class EditorialPlaybookExecuteRequest(BaseModel):
    action_id: str
    run_id: str | None = None
    note: str | None = None
    
    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, v: str) -> str:
        valid_actions = {"open_review_task", "prepare_guided_regeneration", "suggest_policy_review"}
        if v not in valid_actions:
            raise ValueError(f"action_id must be one of: {valid_actions}")
        return v


@router.post("/v2/threads/{thread_id}/editorial-decisions/playbook/execute")
def execute_editorial_playbook_v2(
    thread_id: str,
    request: Request,
    body: EditorialPlaybookExecuteRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> dict[str, object]:
    """Execute an editorial recovery playbook action with one click.
    
    Actions:
    - open_review_task: Creates a review task for editorial review
    - prepare_guided_regeneration: Prepares context for guided regeneration
    - suggest_policy_review: Suggests reviewing brand editorial policy
    
    Emits EditorialPlaybookExecuted event and returns created entities.
    """
    from vm_webapp.commands_v2 import execute_editorial_playbook_command
    
    # Get actor context (identity + role)
    actor_ctx = require_valid_auth(request)
    actor_id = actor_ctx["actor_id"]
    actor_role = actor_ctx.get("actor_role", "editor")
    
    pump_event_worker(request, max_events=20)
    
    with session_scope(request.app.state.engine) as session:
        # Verify thread exists
        thread = get_thread_view(session, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        
        try:
            dedup = execute_editorial_playbook_command(
                session,
                thread_id=thread_id,
                action_id=body.action_id,
                run_id=body.run_id,
                note=body.note,
                actor_id=actor_id,
                actor_role=actor_role,
                idempotency_key=idempotency_key,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        
        import json as _json
        response = _json.loads(dedup.response_json) if dedup.response_json else {}
        
        return {
            "status": "success",
            "executed_action": body.action_id,
            "created_entities": response.get("created_entities", []),
            "event_id": response.get("event_id"),
        }
