from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from vm_webapp.events import EventEnvelope
from vm_webapp.repo import append_event, get_stream_version


def run_planning_step(
    session: Session,
    *,
    thread_id: str,
    project_id: str,
    brand_id: str,
    mode: str,
    request_text: str,
    actor_id: str,
) -> list[EventEnvelope]:
    stream_id = f"thread:{thread_id}"
    current = get_stream_version(session, stream_id)

    started = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="AgentStepStarted",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=current,
        actor_type="agent",
        actor_id=actor_id,
        payload={
            "thread_id": thread_id,
            "project_id": project_id,
            "brand_id": brand_id,
            "mode": mode,
            "request_text": request_text,
        },
        thread_id=thread_id,
        project_id=project_id,
        brand_id=brand_id,
    )
    row_started = append_event(session, started)

    completed = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="AgentStepCompleted",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=row_started.stream_version,
        actor_type="agent",
        actor_id=actor_id,
        payload={
            "thread_id": thread_id,
            "project_id": project_id,
            "brand_id": brand_id,
            "mode": mode,
            "summary": "Step completed",
        },
        thread_id=thread_id,
        project_id=project_id,
        brand_id=brand_id,
    )
    row_completed = append_event(session, completed)

    artifact = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="AgentArtifactPublished",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=row_completed.stream_version,
        actor_type="agent",
        actor_id=actor_id,
        payload={
            "thread_id": thread_id,
            "project_id": project_id,
            "brand_id": brand_id,
            "mode": mode,
            "artifact_path": f"08-output/{thread_id}/{mode}.md",
        },
        thread_id=thread_id,
        project_id=project_id,
        brand_id=brand_id,
    )
    append_event(session, artifact)
    return [started, completed, artifact]
