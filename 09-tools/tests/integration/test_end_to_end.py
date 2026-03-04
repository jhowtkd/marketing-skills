"""End-to-end integration tests."""

from __future__ import annotations

from datetime import datetime, timezone

class TestEndToEndWorkflow:
    """End-to-end test: Create brand → project → thread → workflow."""

    def test_complete_workflow_lifecycle(self, client):
        """Test complete workflow lifecycle:
        
        1. Create brand
        2. Create project
        3. Create thread
        4. Start workflow
        5. Verify status
        """
        # Step 1: Create brand
        brand_response = client.post("/api/v2/brands", json={
            "name": "E2E Test Brand",
            "description": "Brand for E2E testing",
        })
        assert brand_response.status_code == 200
        brand_data = brand_response.json()
        brand_id = brand_data["brand_id"]
        print(f"✓ Created brand: {brand_id}")

        # Step 2: Create project
        project_response = client.post("/api/v2/projects", json={
            "name": "E2E Test Project",
            "brand_id": brand_id,
            "objective": "E2E testing",
            "channels": ["email", "social"],
        })
        assert project_response.status_code == 200
        project_data = project_response.json()
        project_id = project_data["project_id"]
        print(f"✓ Created project: {project_id}")

        # Step 3: Create thread
        thread_response = client.post("/api/v2/threads", json={
            "title": "E2E Test Thread",
            "project_id": project_id,
            "brand_id": brand_id,
        })
        assert thread_response.status_code == 200
        thread_data = thread_response.json()
        thread_id = thread_data["thread_id"]
        print(f"✓ Created thread: {thread_id}")

        # Step 4: List threads to verify
        list_response = client.get(f"/api/v2/threads?project_id={project_id}")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert any(t["thread_id"] == thread_id for t in list_data.get("threads", []))
        print(f"✓ Verified thread in list")

        # Step 5: Add mode to thread
        mode_response = client.post(f"/api/v2/threads/{thread_id}/modes", json={
            "mode": "e2e_test_mode",
        })
        assert mode_response.status_code == 200
        print(f"✓ Added mode to thread")

        # Step 6: Start workflow run
        run_response = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", json={
            "mode": "e2e_test_mode",
            "request_text": "E2E test request",
        }, headers={"Idempotency-Key": "e2e-run"})
        assert run_response.status_code == 200
        run_data = run_response.json()
        run_id = run_data["run_id"]
        print(f"✓ Started workflow run: {run_id}")

        # Step 7: Get workflow run
        get_run_response = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert get_run_response.status_code == 200
        get_run_data = get_run_response.json()
        assert get_run_data["run_id"] == run_id
        print(f"✓ Verified workflow run")

        # Step 8: Get timeline
        timeline_response = client.get(f"/api/v2/threads/{thread_id}/timeline")
        assert timeline_response.status_code == 200
        timeline_data = timeline_response.json()
        assert "events" in timeline_data or "items" in timeline_data
        print(f"✓ Retrieved timeline")

    def test_project_hierarchy(self, client):
        """Test project hierarchy with multiple threads."""
        # Create brand
        brand_response = client.post("/api/v2/brands", json={"name": "Hierarchy Test Brand"})
        brand_id = brand_response.json()["brand_id"]

        # Create project
        project_response = client.post("/api/v2/projects", json={
            "name": "Hierarchy Test Project",
            "brand_id": brand_id,
            "objective": "Testing hierarchy",
        })
        project_id = project_response.json()["project_id"]

        # Create multiple threads
        thread_ids = []
        for i in range(3):
            thread_response = client.post("/api/v2/threads", json={
                "title": f"Thread {i+1}",
                "project_id": project_id,
                "brand_id": brand_id,
            })
            thread_ids.append(thread_response.json()["thread_id"])

        # Verify all threads are listed
        list_response = client.get(f"/api/v2/threads?project_id={project_id}")
        list_data = list_response.json()
        listed_thread_ids = {t["thread_id"] for t in list_data.get("threads", [])}
        
        for tid in thread_ids:
            assert tid in listed_thread_ids, f"Thread {tid} not found in list"

    def test_workflow_run_resume(self, client):
        """Test workflow run creation and resume."""
        # Create brand, project, thread
        brand_id = client.post("/api/v2/brands", json={"name": "Resume Test"}).json()["brand_id"]
        project_id = client.post("/api/v2/projects", json={
            "name": "Resume Test Project",
            "brand_id": brand_id,
        }).json()["project_id"]
        thread_id = client.post("/api/v2/threads", json={
            "title": "Resume Test Thread",
            "project_id": project_id,
            "brand_id": brand_id,
        }).json()["thread_id"]

        # Start run
        run_response = client.post(f"/api/v2/threads/{thread_id}/workflow-runs", json={
            "mode": "test",
            "request_text": "Test",
        }, headers={"Idempotency-Key": "resume-run"})
        run_id = run_response.json()["run_id"]

        # Resume run
        resume_response = client.post(
            f"/api/v2/workflow-runs/{run_id}/resume",
            headers={"Idempotency-Key": "resume-run-command"},
        )
        assert resume_response.status_code == 200


class TestOnboardingE2E:
    """End-to-end tests for onboarding features."""

    def test_onboarding_event_tracking_e2e(self, client, sample_brand):
        """Test complete event tracking flow."""
        brand_id = sample_brand["brand_id"]

        # Track multiple events
        events = [
            {
                "event": "onboarding_started",
                "user_id": "e2e-user",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "brand_id": brand_id,
                "step": "step_1",
                "metadata": {"step": 1},
            },
            {
                "event": "time_to_first_value",
                "user_id": "e2e-user",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "brand_id": brand_id,
                "step": "step_2",
                "duration_ms": 1200,
                "metadata": {"step": 2},
            },
            {
                "event": "onboarding_completed",
                "user_id": "e2e-user",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "brand_id": brand_id,
                "step": "step_3",
                "metadata": {"step": 3},
            },
        ]

        for event in events:
            response = client.post("/api/v2/onboarding/events", json=event)
            assert response.status_code == 200

        # Get metrics
        metrics_response = client.get(f"/api/v2/onboarding/metrics?brand_id={brand_id}")
        assert metrics_response.status_code == 200
        print(f"✓ Tracked {len(events)} events and retrieved metrics")

    def test_experiment_workflow(self, client, sample_brand):
        """Test experiment creation and execution flow."""
        brand_id = sample_brand["brand_id"]

        # Get experiment status
        status_response = client.get(f"/api/v2/brands/{brand_id}/onboarding-experiments/status")
        assert status_response.status_code == 200

        # List experiments
        list_response = client.get(f"/api/v2/brands/{brand_id}/onboarding-experiments")
        assert list_response.status_code == 200
        print(f"✓ Retrieved experiments for brand")
