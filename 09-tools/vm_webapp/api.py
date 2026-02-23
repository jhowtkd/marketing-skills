from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel

from vm_webapp.db import session_scope
from vm_webapp.repo import list_brands, list_products_by_brand
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
