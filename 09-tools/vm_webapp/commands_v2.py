from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from vm_webapp.events import EventEnvelope
from vm_webapp.models import CommandDedup
from vm_webapp.repo import (
    append_event,
    get_command_dedup,
    get_stream_version,
    save_command_dedup,
)


def create_brand_command(
    session: Session,
    *,
    brand_id: str,
    name: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"brand:{brand_id}"
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="BrandCreated",
        aggregate_type="brand",
        aggregate_id=brand_id,
        stream_id=stream_id,
        expected_version=0,
        actor_type="human",
        actor_id=actor_id,
        payload={"brand_id": brand_id, "name": name},
        brand_id=brand_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="create_brand",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "brand_id": brand_id, "name": name},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def create_project_command(
    session: Session,
    *,
    project_id: str,
    brand_id: str,
    name: str,
    objective: str,
    channels: list[str],
    due_date: str | None,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"project:{project_id}"
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ProjectCreated",
        aggregate_type="project",
        aggregate_id=project_id,
        stream_id=stream_id,
        expected_version=0,
        actor_type="human",
        actor_id=actor_id,
        payload={
            "project_id": project_id,
            "brand_id": brand_id,
            "name": name,
            "objective": objective,
            "channels": channels,
            "due_date": due_date,
        },
        brand_id=brand_id,
        project_id=project_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="create_project",
        event_id=saved.event_id,
        response={
            "event_id": saved.event_id,
            "project_id": project_id,
            "brand_id": brand_id,
        },
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def create_thread_command(
    session: Session,
    *,
    thread_id: str,
    project_id: str,
    brand_id: str,
    title: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ThreadCreated",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=f"thread:{thread_id}",
        expected_version=0,
        actor_type="human",
        actor_id=actor_id,
        payload={
            "thread_id": thread_id,
            "project_id": project_id,
            "brand_id": brand_id,
            "title": title,
        },
        brand_id=brand_id,
        project_id=project_id,
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="create_thread",
        event_id=saved.event_id,
        response={
            "event_id": saved.event_id,
            "thread_id": thread_id,
            "project_id": project_id,
            "brand_id": brand_id,
        },
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup


def add_thread_mode_command(
    session: Session,
    *,
    thread_id: str,
    mode: str,
    actor_id: str,
    idempotency_key: str,
) -> CommandDedup:
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    stream_id = f"thread:{thread_id}"
    expected = get_stream_version(session, stream_id)
    event = EventEnvelope(
        event_id=f"evt-{uuid4().hex[:12]}",
        event_type="ThreadModeAdded",
        aggregate_type="thread",
        aggregate_id=thread_id,
        stream_id=stream_id,
        expected_version=expected,
        actor_type="human",
        actor_id=actor_id,
        payload={"thread_id": thread_id, "mode": mode},
        thread_id=thread_id,
    )
    saved = append_event(session, event)
    save_command_dedup(
        session,
        idempotency_key=idempotency_key,
        command_name="add_thread_mode",
        event_id=saved.event_id,
        response={"event_id": saved.event_id, "thread_id": thread_id, "mode": mode},
    )
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    assert dedup is not None
    return dedup
