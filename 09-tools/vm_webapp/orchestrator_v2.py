from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy.orm import Session

from vm_webapp.events import EventEnvelope
from vm_webapp.repo import (
    append_event,
    get_stream_version,
    list_unprocessed_events,
    mark_event_processed,
)


def process_new_events(session: Session) -> None:
    for event in list_unprocessed_events(session):
        if event.event_type == "AgentPlanStarted":
            payload = json.loads(event.payload_json)
            thread_id = payload["thread_id"]
            expected = get_stream_version(session, f"thread:{thread_id}")
            append_event(
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

        mark_event_processed(session, event.event_id)
