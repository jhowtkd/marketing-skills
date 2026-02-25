import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vm_webapp.models import Base, CampaignView, TaskView, EventLog
from vm_webapp.projectors_v2 import apply_event_to_read_models

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_projector_creates_campaign_and_task_views(session: Session) -> None:
    now = datetime.now(timezone.utc).isoformat()
    
    # 1. Project CampaignCreated
    campaign_event = EventLog(
        event_id="evt-c1",
        event_type="CampaignCreated",
        aggregate_type="Campaign",
        aggregate_id="camp-1",
        stream_id="camp-1",
        stream_version=1,
        actor_type="user",
        actor_id="u1",
        payload_json=json.dumps({
            "campaign_id": "camp-1",
            "brand_id": "brand-1",
            "project_id": "proj-1",
            "title": "Summer Sale"
        }),
        occurred_at=now
    )
    apply_event_to_read_models(session, campaign_event)
    session.flush()
    
    campaign = session.get(CampaignView, "camp-1")
    assert campaign is not None
    assert campaign.title == "Summer Sale"
    assert campaign.brand_id == "brand-1"
    
    # 2. Project TaskCreated
    task_event = EventLog(
        event_id="evt-t1",
        event_type="TaskCreated",
        aggregate_type="Task",
        aggregate_id="task-1",
        stream_id="task-1",
        stream_version=1,
        actor_type="user",
        actor_id="u1",
        thread_id="thread-1",
        payload_json=json.dumps({
            "task_id": "task-1",
            "campaign_id": "camp-1",
            "brand_id": "brand-1",
            "title": "Email Blast",
            "status": "pending"
        }),
        occurred_at=now
    )
    apply_event_to_read_models(session, task_event)
    session.flush()
    
    task = session.get(TaskView, "task-1")
    assert task is not None
    assert task.title == "Email Blast"
    assert task.campaign_id == "camp-1"
    assert task.brand_id == "brand-1"
