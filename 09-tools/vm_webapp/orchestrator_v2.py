from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy.orm import Session

from vm_webapp.agent_runtime_v2 import run_planning_step
from vm_webapp.events import EventEnvelope
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import (
    append_event,
    get_event_by_id,
    get_stream_version,
    get_thread_view,
    list_unprocessed_events,
    mark_event_processed,
)


def process_new_events(session: Session) -> None:
    for event in list_unprocessed_events(session):
        if event.event_type == "AgentPlanStarted":
            payload = json.loads(event.payload_json)
            thread_id = payload["thread_id"]
            expected = get_stream_version(session, f"thread:{thread_id}")
            approval_event = append_event(
                session,
                EventEnvelope(
                    event_id=f"evt-{uuid4().hex[:12]}",
                    event_type="ApprovalRequested",
                    aggregate_type="thread",
                    aggregate_id=thread_id,
                    stream_id=f"thread:{thread_id}",
                    expected_version=expected,
                    actor_type="system",
                    actor_id="orchestrator-v2",
                    payload={
                        "thread_id": thread_id,
                        "approval_id": f"apr-{uuid4().hex[:10]}",
                        "reason": "Human gate before agent execution",
                        "required_role": "editor",
                    },
                    thread_id=thread_id,
                    causation_id=event.event_id,
                    correlation_id=event.correlation_id or event.event_id,
                ),
            )
            apply_event_to_read_models(session, approval_event)

        if event.event_type == "ApprovalGranted":
            payload = json.loads(event.payload_json)
            thread_id = event.thread_id or payload.get("thread_id")
            if thread_id:
                thread = get_thread_view(session, thread_id)
                mode = "plan_90d"
                if thread is not None and thread.modes_json:
                    modes = json.loads(thread.modes_json)
                    if modes:
                        mode = str(modes[0])
                emitted = run_planning_step(
                    session,
                    thread_id=thread_id,
                    project_id=thread.project_id if thread is not None else "",
                    brand_id=thread.brand_id if thread is not None else "",
                    mode=mode,
                    request_text="Run approved planning step",
                    actor_id="agent:vm-planner",
                )
                for envelope in emitted:
                    row = get_event_by_id(session, envelope.event_id)
                    if row is not None:
                        apply_event_to_read_models(session, row)

        mark_event_processed(session, event.event_id)
