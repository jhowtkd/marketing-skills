"""Pytest fixtures for integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


@pytest.fixture
def test_settings(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    db_path = workspace_root / "test.sqlite3"
    return Settings(
        vm_db_path=db_path,
        vm_workspace_root=str(workspace_root),
        kimi_api_key="test-api-key",
    )


@pytest.fixture
def app(test_settings):
    return create_app(settings=test_settings, enable_in_process_worker=False)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_brand(client):
    response = client.post("/api/v2/brands", json={"name": "Integration Brand"})
    assert response.status_code == 200
    return response.json()
