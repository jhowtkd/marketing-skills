from __future__ import annotations

from sqlalchemy.orm import Session

from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import get_event_by_id


def project_command_event(session: Session, *, event_id: str) -> None:
    row = get_event_by_id(session, event_id)
    if row is None:
        raise ValueError(f"event not found: {event_id}")
    apply_event_to_read_models(session, row)
