from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from vm_webapp.events import EventEnvelope
from vm_webapp.models import CommandDedup
from vm_webapp.repo import (
    append_event,
    get_command_dedup,
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
