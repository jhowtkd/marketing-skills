"""Pytest fixtures for API v2 tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


@pytest.fixture
def test_settings():
    """Create test settings with in-memory database."""
    return Settings(
        vm_db_url="sqlite:///:memory:",
        vm_workspace_root="/tmp/test_workspace",
        kimi_api_key=None,  # Disable LLM for tests
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    return create_app(settings=test_settings, enable_in_process_worker=False)


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_brand(client):
    """Create a sample brand for tests."""
    response = client.post("/api/v2/brands", json={"name": "Test Brand"})
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def sample_project(client, sample_brand):
    """Create a sample project for tests."""
    brand_id = sample_brand.get("brand_id")
    response = client.post("/api/v2/projects", json={
        "name": "Test Project",
        "brand_id": brand_id,
        "objective": "test objective",
        "channels": ["email"],
    })
    assert response.status_code == 200
    data = response.json()
    data["brand_id"] = brand_id
    return data


@pytest.fixture
def sample_thread(client, sample_project):
    """Create a sample thread for tests."""
    project_id = sample_project.get("project_id")
    brand_id = sample_project.get("brand_id")
    response = client.post("/api/v2/threads", json={
        "title": "Test Thread",
        "project_id": project_id,
        "brand_id": brand_id,
    })
    assert response.status_code == 200
    data = response.json()
    data["project_id"] = project_id
    data["brand_id"] = brand_id
    return data
