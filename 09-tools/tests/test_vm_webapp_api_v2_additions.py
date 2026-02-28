"""Additional API v2 tests for first-run recommendation endpoints (v12)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.events import EventEnvelope
from vm_webapp.projectors_v2 import apply_event_to_read_models
from vm_webapp.repo import append_event
from vm_webapp.settings import Settings


def create_test_app(tmp_path: Path):
    """Helper to create test app with fresh database."""
    db_path = tmp_path / "test.db"
    engine = build_engine(db_path)
    init_db(engine)
    
    settings = Settings(
        vm_workspace_root=tmp_path / "runtime" / "vm",
        vm_db_path=db_path,
    )
    app = create_app(settings=settings)
    # Ensure app uses the same engine
    app.state.engine = engine
    return app, engine


def test_first_run_recommendation_endpoint_returns_top3_and_confidence(tmp_path: Path) -> None:
    """GET /api/v2/threads/{thread_id}/first-run-recommendation should return top 3 with confidence."""
    app, engine = create_test_app(tmp_path)
    client = TestClient(app)
    
    # Create brand, project, thread first
    with session_scope(engine) as session:
        # Create brand
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-brand",
                event_type="BrandCreated",
                aggregate_type="brand",
                aggregate_id="b1",
                stream_id="brand:b1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"brand_id": "b1", "name": "Test Brand"},
                brand_id="b1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        # Create project (different stream)
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-project",
                event_type="ProjectCreated",
                aggregate_type="project",
                aggregate_id="p1",
                stream_id="project:p1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"project_id": "p1", "brand_id": "b1", "name": "Test Project"},
                brand_id="b1",
                project_id="p1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        # Create thread (different stream)
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-thread",
                event_type="ThreadCreated",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"thread_id": "t1", "brand_id": "b1", "project_id": "p1", "title": "Test Thread"},
                brand_id="b1",
                project_id="p1",
                thread_id="t1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        # Add some completed runs with outcomes (each with its own stream)
        for i, (profile, mode, quality) in enumerate([
            ("engagement", "fast", 0.85),
            ("awareness", "balanced", 0.75),
            ("conversion", "quality", 0.90),
        ]):
            row = append_event(
                session,
                EventEnvelope(
                    event_id=f"evt-run-{i}",
                    event_type="RunCompleted",
                    aggregate_type="run",
                    aggregate_id=f"run-{i}",
                    stream_id=f"run:{i}",  # Each run has its own stream
                    expected_version=0,
                    actor_type="system",
                    actor_id="runner",
                    thread_id="t1",
                    brand_id="b1",
                    project_id="p1",
                    payload={
                        "run_id": f"run-{i}",
                        "thread_id": "t1",
                        "brand_id": "b1",
                        "project_id": "p1",
                        "profile": profile,
                        "mode": mode,
                        "approved": True,
                        "quality_score": quality,
                        "duration_ms": 4000,
                        "completed_at": "2026-02-28T10:00:00Z",
                    },
                ),
            )
            apply_event_to_read_models(session, row)
    
    response = client.get("/api/v2/threads/t1/first-run-recommendation")
    assert response.status_code == 200
    
    data = response.json()
    assert "recommendations" in data
    assert "scope" in data
    assert len(data["recommendations"]) <= 3
    
    # Check first recommendation has required fields
    if data["recommendations"]:
        rec = data["recommendations"][0]
        assert "profile" in rec
        assert "mode" in rec
        assert "score" in rec
        assert "confidence" in rec
        assert "reason_codes" in rec


def test_first_run_recommendation_endpoint_returns_fallback_scope(tmp_path: Path) -> None:
    """Endpoint should return fallback scope when no data available."""
    app, engine = create_test_app(tmp_path)
    client = TestClient(app)
    
    # Create brand, project, thread but no runs
    with session_scope(engine) as session:
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-brand",
                event_type="BrandCreated",
                aggregate_type="brand",
                aggregate_id="b1",
                stream_id="brand:b1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"brand_id": "b1", "name": "Test Brand"},
                brand_id="b1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-project",
                event_type="ProjectCreated",
                aggregate_type="project",
                aggregate_id="p1",
                stream_id="project:p1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"project_id": "p1", "brand_id": "b1", "name": "Test Project"},
                brand_id="b1",
                project_id="p1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-thread",
                event_type="ThreadCreated",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"thread_id": "t1", "brand_id": "b1", "project_id": "p1", "title": "Test Thread"},
                brand_id="b1",
                project_id="p1",
                thread_id="t1",
            ),
        )
        apply_event_to_read_models(session, row)
    
    response = client.get("/api/v2/threads/t1/first-run-recommendation")
    assert response.status_code == 200
    
    data = response.json()
    assert data["scope"] in ["objective", "brand", "global", "default"]
    # Should return at least a default recommendation
    assert len(data["recommendations"]) >= 1


def test_first_run_outcomes_endpoint_returns_aggregate_snapshot(tmp_path: Path) -> None:
    """GET /api/v2/threads/{thread_id}/first-run-outcomes should return aggregate snapshot."""
    app, engine = create_test_app(tmp_path)
    client = TestClient(app)
    
    with session_scope(engine) as session:
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-brand",
                event_type="BrandCreated",
                aggregate_type="brand",
                aggregate_id="b1",
                stream_id="brand:b1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"brand_id": "b1", "name": "Test Brand"},
                brand_id="b1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-project",
                event_type="ProjectCreated",
                aggregate_type="project",
                aggregate_id="p1",
                stream_id="project:p1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"project_id": "p1", "brand_id": "b1", "name": "Test Project"},
                brand_id="b1",
                project_id="p1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-thread",
                event_type="ThreadCreated",
                aggregate_type="thread",
                aggregate_id="t1",
                stream_id="thread:t1",
                expected_version=0,
                actor_type="human",
                actor_id="user",
                payload={"thread_id": "t1", "brand_id": "b1", "project_id": "p1", "title": "Test Thread"},
                brand_id="b1",
                project_id="p1",
                thread_id="t1",
            ),
        )
        apply_event_to_read_models(session, row)
        
        # Add completed runs
        row = append_event(
            session,
            EventEnvelope(
                event_id="evt-run-1",
                event_type="RunCompleted",
                aggregate_type="run",
                aggregate_id="run-1",
                stream_id="run:1",
                expected_version=0,
                actor_type="system",
                actor_id="runner",
                thread_id="t1",
                brand_id="b1",
                project_id="p1",
                payload={
                    "run_id": "run-1",
                    "thread_id": "t1",
                    "brand_id": "b1",
                    "project_id": "p1",
                    "profile": "engagement",
                    "mode": "fast",
                    "approved": True,
                    "quality_score": 0.85,
                    "duration_ms": 4000,
                    "completed_at": "2026-02-28T10:00:00Z",
                },
            ),
        )
        apply_event_to_read_models(session, row)
    
    response = client.get("/api/v2/threads/t1/first-run-outcomes")
    assert response.status_code == 200
    
    data = response.json()
    assert "aggregates" in data
    assert "thread_id" in data
    
    # Should have aggregate data
    if data["aggregates"]:
        agg = data["aggregates"][0]
        assert "profile" in agg
        assert "mode" in agg
        assert "total_runs" in agg
        assert "success_24h_count" in agg
        assert "success_rate" in agg
