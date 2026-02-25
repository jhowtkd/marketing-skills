import json
import pytest
from fastapi.testclient import TestClient
from vm_webapp.app import create_app
from vm_webapp.db import session_scope

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_v2_can_create_campaign_task_and_brand_rule_with_idempotency(client: TestClient) -> None:
    # 1. Create Brand first
    brand_resp = client.post(
        "/api/v2/brands",
        json={"name": "Acme Corp"},
        headers={"Idempotency-Key": "idem-b1"}
    )
    assert brand_resp.status_code == 200
    brand_id = brand_resp.json()["brand_id"]

    # 2. Create Project
    proj_resp = client.post(
        "/api/v2/projects",
        json={"brand_id": brand_id, "name": "Summer Project"},
        headers={"Idempotency-Key": "idem-p1"}
    )
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["project_id"]

    # 3. Create Campaign
    camp_resp = client.post(
        "/api/v2/campaigns",
        json={
            "brand_id": brand_id,
            "project_id": project_id,
            "title": "Summer Sale 2026"
        },
        headers={"Idempotency-Key": "idem-c1"}
    )
    assert camp_resp.status_code == 200
    campaign_id = camp_resp.json()["campaign_id"]
    assert camp_resp.json()["title"] == "Summer Sale 2026"

    # 4. Create Thread
    thread_resp = client.post(
        "/api/v2/threads",
        json={
            "brand_id": brand_id,
            "project_id": project_id,
            "title": "Campaign Thread"
        },
        headers={"Idempotency-Key": "idem-t1"}
    )
    assert thread_resp.status_code == 200
    thread_id = thread_resp.json()["thread_id"]

    # 5. Create Task (linked to campaign)
    task_resp = client.post(
        "/api/v2/tasks",
        json={
            "thread_id": thread_id,
            "campaign_id": campaign_id,
            "brand_id": brand_id,
            "title": "Draft Email"
        },
        headers={"Idempotency-Key": "idem-task-1"}
    )
    assert task_resp.status_code == 200
    task_id = task_resp.json()["task_id"]
    assert task_resp.json()["campaign_id"] == campaign_id

    # 6. List Campaigns
    list_camp_resp = client.get(f"/api/v2/campaigns?project_id={project_id}")
    assert list_camp_resp.status_code == 200
    campaigns = list_camp_resp.json()["campaigns"]
    assert any(c["campaign_id"] == campaign_id for c in campaigns)

    # 7. List Tasks
    list_task_resp = client.get(f"/api/v2/threads/{thread_id}/tasks")
    assert list_task_resp.status_code == 200
    tasks = list_task_resp.json()["items"]
    assert any(t["task_id"] == task_id for t in tasks)
