from __future__ import annotations

import time

from sqlalchemy.engine import Engine

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.orchestrator_v2 import process_new_events
from vm_webapp.settings import Settings


class InProcessEventWorker:
    def __init__(self, *, engine: Engine) -> None:
        self.engine = engine

    def pump(self, *, max_events: int = 50) -> int:
        with session_scope(self.engine) as session:
            return process_new_events(session, max_events=max_events)


def run_worker_loop(
    *,
    settings: Settings,
    poll_interval_ms: int = 500,
    max_events: int = 50,
) -> None:
    engine = build_engine(settings.vm_db_path, db_url=settings.vm_db_url)
    init_db(engine)
    worker = InProcessEventWorker(engine=engine)
    poll_interval_seconds = max(0, poll_interval_ms) / 1000
    while True:
        processed = worker.pump(max_events=max_events)
        if processed == 0:
            time.sleep(poll_interval_seconds)
