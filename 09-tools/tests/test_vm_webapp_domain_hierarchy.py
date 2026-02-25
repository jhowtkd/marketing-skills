from pathlib import Path
import json

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import append_event
from vm_webapp.models import CampaignView, TaskView


def test_projector_creates_campaign_and_task_views(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        # 1. Project Campaign
        evt_campaign = append_event(
            session,
            EventEnvelope(
                event_id="evt-camp-1",
                event_type="CampaignCreated",
                aggregate_type="campaign",
                aggregate_id="c1",
                stream_id="campaign:c1",
                expected_version=0,
                actor_type="human",
                actor_id="user-1",
                payload={
                    "campaign_id": "c1",
                    "brand_id": "b1",
                    "project_id": "p1",
                    "title": "Black Friday 2026"
                },
                brand_id="b1",
                project_id="p1",
            ),
        )
        apply_event_to_read_models(session, evt_campaign)

        # 2. Project Task with hierarchy
        evt_task = append_event(
            session,
            EventEnvelope(
                event_id="evt-task-1",
                event_type="TaskCreated",
                aggregate_type="task",
                aggregate_id="t1",
                stream_id="task:t1",
                expected_version=0,
                actor_type="human",
                actor_id="user-1",
                payload={
                    "task_id": "t1",
                    "campaign_id": "c1",
                    "brand_id": "b1",
                    "title": "Design Banner",
                    "status": "todo"
                },
                brand_id="b1",
                thread_id="thread-1"
            ),
        )
        apply_event_to_read_models(session, evt_task)

    with session_scope(engine) as session:
        campaign = session.get(CampaignView, "c1")
        assert campaign is not None
        assert campaign.brand_id == "b1"
        assert campaign.project_id == "p1"

        task = session.get(TaskView, "t1")
        assert task is not None
        assert task.campaign_id == "c1"
        assert task.brand_id == "b1"
