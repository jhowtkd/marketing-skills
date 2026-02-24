from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from vm_webapp.models import BrandView, EventLog, ProjectView, ThreadView, TimelineItemView


def apply_event_to_read_models(session: Session, event: EventLog) -> None:
    payload = json.loads(event.payload_json)

    if event.event_type == "BrandCreated":
        row = session.get(BrandView, payload["brand_id"])
        if row is None:
            row = BrandView(
                brand_id=payload["brand_id"],
                name=payload["name"],
                updated_at=event.occurred_at,
            )
            session.add(row)
        else:
            row.name = payload["name"]
            row.updated_at = event.occurred_at
        return

    if event.event_type == "ProjectCreated":
        row = session.get(ProjectView, payload["project_id"])
        if row is None:
            row = ProjectView(
                project_id=payload["project_id"],
                brand_id=payload["brand_id"],
                name=payload["name"],
                objective=payload.get("objective", ""),
                channels_json=json.dumps(payload.get("channels", []), ensure_ascii=False),
                due_date=payload.get("due_date"),
                updated_at=event.occurred_at,
            )
            session.add(row)
        else:
            row.name = payload["name"]
            row.objective = payload.get("objective", row.objective)
            row.channels_json = json.dumps(payload.get("channels", []), ensure_ascii=False)
            row.due_date = payload.get("due_date")
            row.updated_at = event.occurred_at
        return

    if event.event_type == "ThreadCreated":
        row = session.get(ThreadView, payload["thread_id"])
        if row is None:
            session.add(
                ThreadView(
                    thread_id=payload["thread_id"],
                    brand_id=payload["brand_id"],
                    project_id=payload["project_id"],
                    title=payload["title"],
                    status="open",
                    modes_json="[]",
                    last_activity_at=event.occurred_at,
                )
            )
        return

    if event.event_type == "ThreadModeAdded":
        row = session.get(ThreadView, payload["thread_id"])
        if row is None:
            return
        modes = json.loads(row.modes_json)
        if payload["mode"] not in modes:
            modes.append(payload["mode"])
            row.modes_json = json.dumps(modes, ensure_ascii=False)
        row.last_activity_at = event.occurred_at

    if event.thread_id:
        timeline_item = session.scalar(
            select(TimelineItemView).where(TimelineItemView.event_id == event.event_id)
        )
        if timeline_item is None:
            session.add(
                TimelineItemView(
                    event_id=event.event_id,
                    thread_id=event.thread_id,
                    event_type=event.event_type,
                    actor_type=event.actor_type,
                    actor_id=event.actor_id,
                    payload_json=event.payload_json,
                    occurred_at=event.occurred_at,
                )
            )
