from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from vm_webapp.db import session_scope
from vm_webapp.repo import (
    list_brands,
    list_products_by_brand,
    list_runs_by_thread,
    list_stages,
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
