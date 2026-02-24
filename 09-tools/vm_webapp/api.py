from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from vm_webapp.commands_v2 import (
    add_comment_command,
    add_thread_mode_command,
    complete_task_command,
    create_brand_command,
    create_project_command,
    create_thread_command,
    grant_approval_command,
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
from vm_webapp.repo import (
    append_event,
    close_thread,
    create_thread as create_thread_row,
    get_event_by_id,
    get_run,
    get_brand_view,
    get_project_view,
    get_thread,
    get_thread_view,
    list_approvals_view,
    list_brands,
    list_brands_view,
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
)
from vm_webapp.stacking import build_context_pack


router = APIRouter()


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


class TaskCommentRequest(BaseModel):
    message: str


class ForceConflictRequest(BaseModel):
    thread_id: str


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
            payload_rows.append(
                {
                    "run_id": row.run_id,
                    "status": row.status,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "completed_stages": completed,
                    "total_stages": len(stages),
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
    }


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
        result = grant_approval_command(
            session,
            approval_id=approval_id,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
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
