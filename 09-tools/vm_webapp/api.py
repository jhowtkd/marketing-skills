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
)
from vm_webapp.db import session_scope
from vm_webapp.orchestrator_v2 import process_new_events
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import (
    get_event_by_id,
    list_approvals_view,
    list_brands,
    list_projects_view,
    list_products_by_brand,
    list_runs_by_thread,
    list_stages,
    list_tasks_view,
    list_timeline_items_view,
)
from vm_webapp.stacking import build_context_pack


router = APIRouter()


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


class BrandCreateRequest(BaseModel):
    brand_id: str
    name: str


class ProjectCreateRequest(BaseModel):
    project_id: str
    brand_id: str
    name: str
    objective: str = ""
    channels: list[str] = Field(default_factory=list)
    due_date: str | None = None


class ThreadCreateRequest(BaseModel):
    thread_id: str
    project_id: str
    brand_id: str
    title: str


class ThreadModeAddRequest(BaseModel):
    mode: str


class TaskCommentRequest(BaseModel):
    message: str


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
    return {"event_id": result.event_id, "brand_id": payload.brand_id}


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
    return {"event_id": result.event_id, "project_id": payload.project_id}


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
def create_thread_v2(payload: ThreadCreateRequest, request: Request) -> dict[str, str]:
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
    return {"event_id": result.event_id, "thread_id": payload.thread_id}


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


@router.get("/v2/threads/{thread_id}/timeline")
def list_thread_timeline_v2(
    thread_id: str, request: Request
) -> dict[str, list[dict[str, object]]]:
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
        process_new_events(session)
    return {"event_id": result.event_id, "approval_id": approval_id}


class ChatRequest(BaseModel):
    brand_id: str
    product_id: str
    thread_id: str
    message: str


class FoundationRunRequest(BaseModel):
    brand_id: str
    product_id: str
    thread_id: str
    user_request: str


@router.post("/runs/foundation")
def start_foundation_run(payload: FoundationRunRequest, request: Request) -> dict[str, str]:
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
