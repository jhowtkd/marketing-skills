from __future__ import annotations

from sqlalchemy.engine import Engine

from vm_webapp.db import session_scope
from vm_webapp.orchestrator_v2 import process_new_events


class InProcessEventWorker:
    def __init__(self, *, engine: Engine) -> None:
        self.engine = engine

    def pump(self, *, max_events: int = 50) -> int:
        with session_scope(self.engine) as session:
            return process_new_events(session, max_events=max_events)
