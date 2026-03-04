"""Tests for workflow API endpoints."""

from __future__ import annotations

import pytest


class TestWorkflowProfiles:
    """Tests for workflow profile endpoints."""

    def test_list_workflow_profiles(self, client):
        """Test listing workflow profiles."""
        response = client.get("/api/v2/workflow-profiles")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert isinstance(data["profiles"], list)


class TestWorkflowRuns:
    """Tests for workflow run endpoints."""

    def test_list_workflow_runs(self, client, sample_thread):
        """Test listing workflow runs for a thread."""
        thread_id = sample_thread["thread_id"]
        response = client.get(f"/api/v2/threads/{thread_id}/workflow-runs")
        assert response.status_code == 200
        data = response.json()
        # Response can have 'runs' or 'items' key
        assert "runs" in data or "items" in data

    def test_start_workflow_run(self, client, sample_thread):
        """Test starting a workflow run."""
        thread_id = sample_thread["thread_id"]
        response = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            json={
                "mode": "test_mode",
                "request_text": "Test request",
            },
            headers={"Idempotency-Key": "wf-start-1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data

    def test_start_workflow_run_without_mode(self, client, sample_thread):
        """Test starting a workflow run without mode uses default mode."""
        thread_id = sample_thread["thread_id"]
        response = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            json={"request_text": "Test request"},
            headers={"Idempotency-Key": "wf-start-missing-mode"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "requested_mode" in data

    def test_get_workflow_run(self, client, sample_thread):
        """Test getting a workflow run."""
        thread_id = sample_thread["thread_id"]
        # First create a run
        create_response = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            json={"mode": "test_mode", "request_text": "Test"},
            headers={"Idempotency-Key": "wf-get-run-create"},
        )
        run_id = create_response.json()["run_id"]
        
        # Then get it
        response = client.get(f"/api/v2/workflow-runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id

    def test_resume_workflow_run(self, client, sample_thread):
        """Test resuming a workflow run."""
        thread_id = sample_thread["thread_id"]
        # First create a run
        create_response = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            json={"mode": "test_mode", "request_text": "Test"},
            headers={"Idempotency-Key": "wf-resume-create"},
        )
        run_id = create_response.json()["run_id"]
        
        # Then resume it
        response = client.post(
            f"/api/v2/workflow-runs/{run_id}/resume",
            headers={"Idempotency-Key": "wf-resume"},
        )
        assert response.status_code == 200


class TestArtifacts:
    """Tests for artifact endpoints."""

    def test_list_artifacts(self, client, sample_thread):
        """Test listing artifacts for a run."""
        thread_id = sample_thread["thread_id"]
        # First create a run
        create_response = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            json={"mode": "test_mode", "request_text": "Test"},
            headers={"Idempotency-Key": "wf-artifacts-create"},
        )
        run_id = create_response.json()["run_id"]
        
        # Then list artifacts
        response = client.get(f"/api/v2/workflow-runs/{run_id}/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data


class TestTimeline:
    """Tests for timeline endpoints."""

    def test_get_timeline(self, client, sample_thread):
        """Test getting timeline for a thread."""
        thread_id = sample_thread["thread_id"]
        response = client.get(f"/api/v2/threads/{thread_id}/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data or "items" in data
        timeline_items = data.get("events", data.get("items"))
        assert isinstance(timeline_items, list)


class TestQuality:
    """Tests for quality evaluation endpoints."""

    def test_quality_evaluation(self, client, sample_thread):
        """Test requesting quality evaluation for a run."""
        thread_id = sample_thread["thread_id"]
        # First create a run
        create_response = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            json={"mode": "test_mode", "request_text": "Test"},
            headers={"Idempotency-Key": "wf-quality-create"},
        )
        run_id = create_response.json()["run_id"]
        
        # Then request evaluation
        response = client.post(
            f"/api/v2/workflow-runs/{run_id}/quality-evaluation",
            json={"depth": "deep", "rubric_version": "v1"},
            headers={"Idempotency-Key": "wf-quality-eval"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data or "fallback_applied" in data

    def test_get_baseline(self, client, sample_thread):
        """Test getting resolved baseline for a run."""
        thread_id = sample_thread["thread_id"]
        # First create a run
        create_response = client.post(
            f"/api/v2/threads/{thread_id}/workflow-runs",
            json={"mode": "test_mode", "request_text": "Test"},
            headers={"Idempotency-Key": "wf-baseline-create"},
        )
        run_id = create_response.json()["run_id"]
        
        # Then get baseline
        response = client.get(f"/api/v2/workflow-runs/{run_id}/baseline")
        assert response.status_code == 200
        data = response.json()
        assert "baseline_run_id" in data
        assert "source" in data
