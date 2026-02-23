from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import Engine

from vm_webapp.db import session_scope
from vm_webapp.events import append_event
from vm_webapp.memory import MemoryIndex
from vm_webapp.models import Run
from vm_webapp.repo import (
    create_run,
    create_stage,
    get_run,
    list_stages,
    update_run_status,
    update_stage_status,
)
from vm_webapp.stacking import load_stack
from vm_webapp.workspace import Workspace


class RunEngine:
    def __init__(
        self,
        *,
        engine: Engine,
        workspace: Workspace,
        memory: MemoryIndex,
        llm: Any,
    ) -> None:
        self.engine = engine
        self.workspace = workspace
        self.memory = memory
        self.llm = llm

    def start_run(
        self,
        *,
        brand_id: str,
        product_id: str,
        thread_id: str,
        stack_path: str,
        user_request: str,
    ) -> Run:
        run_id = uuid4().hex[:16]
        stack = load_stack(stack_path)
        stages = stack.get("sequence", [])

        with session_scope(self.engine) as session:
            run = create_run(
                session,
                run_id=run_id,
                brand_id=brand_id,
                product_id=product_id,
                thread_id=thread_id,
                stack_path=stack_path,
                user_request=user_request,
                status="running",
            )
            for pos, stage in enumerate(stages):
                create_stage(
                    session,
                    run_id=run_id,
                    stage_id=str(stage.get("id", f"stage-{pos+1}")),
                    position=pos,
                    approval_required=bool(stage.get("approval_required", False)),
                    status="pending",
                )

        append_event(
            self._events_path(run_id),
            {"type": "run_started", "run_id": run_id, "thread_id": thread_id},
        )
        return run

    def run_until_gate(self, run_id: str) -> None:
        with session_scope(self.engine) as session:
            run = get_run(session, run_id)
            if run is None:
                raise ValueError(f"run not found: {run_id}")

            blocked = False
            for stage in list_stages(session, run_id):
                if stage.status == "completed":
                    continue
                if stage.approval_required:
                    update_stage_status(
                        session,
                        stage_pk=stage.stage_pk,
                        status="waiting_approval",
                        attempts=stage.attempts,
                    )
                    update_run_status(session, run_id=run_id, status="waiting_approval")
                    append_event(
                        self._events_path(run_id),
                        {
                            "type": "approval_required",
                            "run_id": run_id,
                            "stage_id": stage.stage_id,
                        },
                    )
                    blocked = True
                    break

                self._execute_stage(run, stage.stage_id)
                update_stage_status(
                    session,
                    stage_pk=stage.stage_pk,
                    status="completed",
                    attempts=stage.attempts + 1,
                )
                append_event(
                    self._events_path(run_id),
                    {"type": "stage_completed", "run_id": run_id, "stage_id": stage.stage_id},
                )

            if not blocked:
                update_run_status(session, run_id=run_id, status="completed")
                append_event(
                    self._events_path(run_id),
                    {"type": "run_completed", "run_id": run_id},
                )

    def get_run(self, run_id: str) -> Run:
        with session_scope(self.engine) as session:
            run = get_run(session, run_id)
            if run is None:
                raise ValueError(f"run not found: {run_id}")
            return run

    def _execute_stage(self, run: Run, stage_id: str) -> None:
        artifact_path = self._artifacts_dir(run.run_id) / f"{stage_id}.md"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        content = f"# {stage_id}\n\nPlaceholder artifact for run `{run.run_id}`.\n"
        if self.llm is not None:
            content = self.llm.chat(
                model="kimi-for-coding",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Run ID: {run.run_id}\n"
                            f"Stage: {stage_id}\n"
                            f"User request: {run.user_request}\n"
                            "Generate concise markdown output."
                        ),
                    }
                ],
                temperature=0.2,
                max_tokens=1024,
            )
        artifact_path.write_text(content, encoding="utf-8")
        self.memory.upsert_doc(
            doc_id=f"run:{run.run_id}:stage:{stage_id}",
            text=content,
            meta={
                "run_id": run.run_id,
                "brand_id": run.brand_id,
                "product_id": run.product_id,
                "thread_id": run.thread_id,
                "stage_id": stage_id,
                "kind": "artifact",
            },
        )

    def _artifacts_dir(self, run_id: str) -> Path:
        return self.workspace.root / "runs" / run_id / "artifacts"

    def _events_path(self, run_id: str) -> Path:
        return self.workspace.root / "runs" / run_id / "events.jsonl"
