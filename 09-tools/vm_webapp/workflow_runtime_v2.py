from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vm_webapp.artifacts import write_stage_outputs
from vm_webapp.db import session_scope
from vm_webapp.events import EventEnvelope, now_iso
from vm_webapp.memory import MemoryIndex
from vm_webapp.repo import (
    append_event,
    create_run,
    create_stage,
    get_stream_version,
    update_run_status,
    update_stage_status,
)
from vm_webapp.workspace import Workspace


class WorkflowRuntimeV2:
    def __init__(
        self, *, engine: Engine, workspace: Workspace, memory: MemoryIndex, llm: Any
    ) -> None:
        self.engine = engine
        self.workspace = workspace
        self.memory = memory
        self.llm = llm

    def execute_thread_run(
        self,
        *,
        thread_id: str,
        brand_id: str,
        project_id: str,
        request_text: str,
        mode: str,
        actor_id: str,
        session: Session | None = None,
    ) -> dict[str, str]:
        if session is not None:
            return self._execute_in_session(
                session=session,
                thread_id=thread_id,
                brand_id=brand_id,
                project_id=project_id,
                request_text=request_text,
                mode=mode,
                actor_id=actor_id,
            )

        with session_scope(self.engine) as db_session:
            return self._execute_in_session(
                session=db_session,
                thread_id=thread_id,
                brand_id=brand_id,
                project_id=project_id,
                request_text=request_text,
                mode=mode,
                actor_id=actor_id,
            )

    def _execute_in_session(
        self,
        *,
        session: Session,
        thread_id: str,
        brand_id: str,
        project_id: str,
        request_text: str,
        mode: str,
        actor_id: str,
    ) -> dict[str, str]:
        run_id = uuid4().hex[:16]
        stage_key = f"plan-{mode}"
        stage_dir = self.workspace.root / "runs" / run_id / "stages" / f"01-{stage_key}"

        create_run(
            session,
            run_id=run_id,
            brand_id=brand_id,
            product_id=project_id,
            thread_id=thread_id,
            stack_path="v2/workflow",
            user_request=request_text,
            status="running",
        )
        stage = create_stage(
            session,
            run_id=run_id,
            stage_id=stage_key,
            position=0,
            approval_required=False,
            status="running",
        )

        started = append_event(
            session,
            EventEnvelope(
                event_id=f"evt-{uuid4().hex[:12]}",
                event_type="WorkflowRunStarted",
                aggregate_type="thread",
                aggregate_id=thread_id,
                stream_id=f"thread:{thread_id}",
                expected_version=get_stream_version(session, f"thread:{thread_id}"),
                actor_type="agent",
                actor_id=actor_id,
                payload={"thread_id": thread_id, "run_id": run_id, "mode": mode},
                thread_id=thread_id,
                brand_id=brand_id,
                project_id=project_id,
            ),
        )

        artifact_text = f"# Workflow Output\n\nRequest: {request_text}\nMode: {mode}\n"
        manifest = write_stage_outputs(
            stage_dir=stage_dir,
            run_id=run_id,
            thread_id=thread_id,
            stage_key=stage_key,
            stage_position=1,
            attempt=1,
            input_payload={"request_text": request_text, "mode": mode},
            output_payload={"summary": "Workflow completed"},
            artifacts={"result.md": artifact_text},
            event_id=started.event_id,
            status="completed",
        )

        update_stage_status(session, stage_pk=stage.stage_pk, status="completed", attempts=1)
        update_run_status(session, run_id=run_id, status="completed")

        run_root = self.workspace.root / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        (run_root / "run.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "brand_id": brand_id,
                    "project_id": project_id,
                    "mode": mode,
                    "status": "completed",
                    "created_at": now_iso(),
                    "manifest_paths": [str(Path("stages") / f"01-{stage_key}" / "manifest.json")],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.memory.upsert_doc(
            doc_id=f"workflow:{run_id}",
            text=artifact_text,
            meta={"thread_id": thread_id, "run_id": run_id, "kind": "workflow_artifact"},
        )
        return {
            "run_id": run_id,
            "status": "completed",
            "manifest_count": str(len(manifest["artifacts"])),
        }
