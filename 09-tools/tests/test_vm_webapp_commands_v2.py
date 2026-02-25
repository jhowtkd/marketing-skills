import json
from pathlib import Path

from vm_webapp.commands_v2 import (
    create_brand_command,
    grant_and_resume_approval_command,
)
from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.repo import append_event
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.events import EventEnvelope
from uuid import uuid4


def test_create_brand_command_is_idempotent(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        first = create_brand_command(
            session,
            brand_id="b1",
            name="Acme",
            actor_id="workspace-owner",
            idempotency_key="idem-brand-b1",
        )

    with session_scope(engine) as session:
        second = create_brand_command(
            session,
            brand_id="b1",
            name="Acme",
            actor_id="workspace-owner",
            idempotency_key="idem-brand-b1",
        )

    assert first.event_id == second.event_id


def test_grant_and_resume_workflow_gate_returns_run_metadata(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        # Create brand, project, thread
        create_brand_command(
            session,
            brand_id="b1",
            name="Acme",
            actor_id="workspace-owner",
            idempotency_key="brand-1",
        )
        
        # Seed a workflow run approval event
        thread_id = "t-run-1"
        brand_id = "b1"
        project_id = "p1"
        run_id = "run-1"
        approval_id = "apr-run-1"
        stage_key = "research"
        
        # Create approval requested event
        approval_event = EventEnvelope(
            event_id=f"evt-{uuid4().hex[:12]}",
            event_type="ApprovalRequested",
            aggregate_type="thread",
            aggregate_id=thread_id,
            stream_id=f"thread:{thread_id}",
            expected_version=0,
            actor_type="system",
            actor_id="system",
            payload={
                "approval_id": approval_id,
                "thread_id": thread_id,
                "brand_id": brand_id,
                "project_id": project_id,
                "run_id": run_id,
                "stage_key": stage_key,
                "reason": f"workflow_gate:{run_id}:{stage_key}",
            },
            thread_id=thread_id,
            brand_id=brand_id,
            project_id=project_id,
        )
        saved = append_event(session, approval_event)
        apply_event_to_read_models(session, saved)
        
        result = grant_and_resume_approval_command(
            session,
            approval_id=approval_id,
            actor_id="workspace-owner",
            idempotency_key="idem-grant-resume-1",
        )

    payload = json.loads(result.response_json)
    assert payload["approval_id"] == approval_id
    assert payload["run_id"] == run_id
    assert payload["resume_applied"] is True
    assert payload["approval_status"] in {"granted", "already_granted"}
    assert isinstance(payload["event_ids"], list)
