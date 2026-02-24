from __future__ import annotations

import json

from sqlalchemy.orm import Session

from vm_webapp.models import BrandView, EventLog, ProjectView


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
