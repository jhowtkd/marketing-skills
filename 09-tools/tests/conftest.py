"""Pytest fixtures for vm_webapp tests."""

from __future__ import annotations

import pytest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vm_webapp.models import Base
from vm_webapp.app import create_app
from vm_webapp.settings import Settings


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database with all tables."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.sqlite3"


@pytest.fixture
def test_settings(tmp_path: Path):
    """Create app settings for API-level tests."""
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    return Settings(
        vm_db_path=workspace_root / "test.sqlite3",
        vm_workspace_root=str(workspace_root),
        kimi_api_key="test-api-key",
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app with full routing for HTTP tests."""
    return create_app(settings=test_settings, enable_in_process_worker=False)


@pytest.fixture
def client(app) -> TestClient:
    """Create HTTP client for integration-style tests."""
    return TestClient(app)


@pytest.fixture
def sample_brand(client):
    """Create a sample brand for HTTP tests."""
    response = client.post("/api/v2/brands", json={"name": "Test Brand"})
    assert response.status_code == 200
    return response.json()
