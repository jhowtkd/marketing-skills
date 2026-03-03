"""Tests for core API endpoints (brands, projects, threads)."""

from __future__ import annotations

import pytest


# ============================================================================
# Brand Tests
# ============================================================================

class TestBrands:
    """Tests for brand endpoints."""

    def test_list_brands(self, client):
        """Test listing brands."""
        response = client.get("/api/v2/brands")
        assert response.status_code == 200
        data = response.json()
        assert "brands" in data
        assert isinstance(data["brands"], list)

    def test_create_brand(self, client):
        """Test creating a brand."""
        response = client.post("/api/v2/brands", json={"name": "Test Brand"})
        assert response.status_code == 200
        data = response.json()
        assert "brand_id" in data
        assert data["name"] == "Test Brand"

    def test_create_brand_without_name(self, client):
        """Test creating a brand without name fails."""
        response = client.post("/api/v2/brands", json={})
        assert response.status_code == 422

    def test_update_brand(self, client, sample_brand):
        """Test updating a brand."""
        brand_id = sample_brand["brand_id"]
        response = client.patch(f"/api/v2/brands/{brand_id}", json={"name": "Updated Brand"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Brand"

    def test_update_nonexistent_brand(self, client):
        """Test updating a nonexistent brand fails."""
        response = client.patch("/api/v2/brands/nonexistent-id", json={"name": "Test"})
        assert response.status_code == 404


# ============================================================================
# Project Tests
# ============================================================================

class TestProjects:
    """Tests for project endpoints."""

    def test_list_projects_with_brand(self, client, sample_brand):
        """Test listing projects for a brand."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/projects?brand_id={brand_id}")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_list_projects_without_brand(self, client):
        """Test listing projects without brand_id fails."""
        response = client.get("/api/v2/projects")
        assert response.status_code == 422

    def test_create_project(self, client, sample_brand):
        """Test creating a project."""
        brand_id = sample_brand["brand_id"]
        response = client.post("/api/v2/projects", json={
            "name": "Test Project",
            "brand_id": brand_id,
            "objective": "test objective",
            "channels": ["email", "social"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert data["name"] == "Test Project"

    def test_create_project_without_brand(self, client):
        """Test creating a project without brand fails."""
        response = client.post("/api/v2/projects", json={
            "name": "Test Project",
            "objective": "test",
        })
        assert response.status_code == 422

    def test_update_project(self, client, sample_project):
        """Test updating a project."""
        project_id = sample_project["project_id"]
        response = client.patch(f"/api/v2/projects/{project_id}", json={
            "name": "Updated Project",
            "objective": "updated objective",
            "channels": ["email"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project"


# ============================================================================
# Thread Tests
# ============================================================================

class TestThreads:
    """Tests for thread endpoints."""

    def test_list_threads_with_project(self, client, sample_project):
        """Test listing threads for a project."""
        project_id = sample_project["project_id"]
        response = client.get(f"/api/v2/threads?project_id={project_id}")
        assert response.status_code == 200
        data = response.json()
        assert "threads" in data
        assert isinstance(data["threads"], list)

    def test_list_threads_without_project(self, client):
        """Test listing threads without project_id fails."""
        response = client.get("/api/v2/threads")
        assert response.status_code == 422

    def test_create_thread(self, client, sample_project):
        """Test creating a thread."""
        project_id = sample_project["project_id"]
        brand_id = sample_project["brand_id"]
        response = client.post("/api/v2/threads", json={
            "title": "Test Thread",
            "project_id": project_id,
            "brand_id": brand_id,
        })
        assert response.status_code == 200
        data = response.json()
        assert "thread_id" in data
        assert data["title"] == "Test Thread"

    def test_update_thread(self, client, sample_thread):
        """Test updating a thread."""
        thread_id = sample_thread["thread_id"]
        response = client.patch(f"/api/v2/threads/{thread_id}", json={
            "title": "Updated Thread",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Thread"

    def test_add_thread_mode(self, client, sample_thread):
        """Test adding a mode to a thread."""
        thread_id = sample_thread["thread_id"]
        response = client.post(f"/api/v2/threads/{thread_id}/modes", json={
            "mode": "content_calendar",
        })
        assert response.status_code == 200

    def test_remove_thread_mode(self, client, sample_thread):
        """Test removing a mode from a thread."""
        thread_id = sample_thread["thread_id"]
        # First add a mode
        client.post(f"/api/v2/threads/{thread_id}/modes", json={"mode": "test_mode"})
        # Then remove it
        response = client.post(f"/api/v2/threads/{thread_id}/modes/test_mode/remove")
        assert response.status_code == 200


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, client):
        """Test 404 response for nonexistent endpoint."""
        response = client.get("/api/v2/nonexistent")
        assert response.status_code == 404

    def test_422_validation_error(self, client):
        """Test 422 response for validation error."""
        response = client.post("/api/v2/brands", json={})  # Missing required 'name'
        assert response.status_code == 422
