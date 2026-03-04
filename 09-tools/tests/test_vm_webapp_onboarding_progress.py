"""Tests for v40 onboarding progress save/resume functionality."""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

from vm_webapp.onboarding_progress import (
    OnboardingProgress,
    ProgressStore,
    save_progress,
    get_progress,
    resume_progress,
    has_progress,
    auto_save_trigger,
    delete_progress,
)


class TestOnboardingProgressModel:
    """Test OnboardingProgress Pydantic model."""

    def test_create_progress(self):
        """Test creating an OnboardingProgress instance."""
        progress = OnboardingProgress(
            user_id="user-123",
            session_id="session-456",
            current_step="step_1",
            step_data={"field1": "value1"},
            completed_steps=["step_0"],
        )
        
        assert progress.user_id == "user-123"
        assert progress.session_id == "session-456"
        assert progress.current_step == "step_1"
        assert progress.step_data == {"field1": "value1"}
        assert progress.completed_steps == ["step_0"]
        assert progress.source == "manual"
        assert progress.version == 1

    def test_progress_defaults(self):
        """Test default values for OnboardingProgress."""
        progress = OnboardingProgress(
            user_id="user-123",
            session_id="session-456",
            current_step="step_1",
        )
        
        assert progress.thread_id is None
        assert progress.step_data == {}
        assert progress.completed_steps == []
        assert progress.skipped_steps == []
        assert progress.prefill_data is None
        assert progress.fast_lane_accepted is False
        assert isinstance(progress.updated_at, datetime)


class TestProgressStore:
    """Test ProgressStore in-memory storage."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_save_and_get(self):
        """Test saving and retrieving progress."""
        progress = OnboardingProgress(
            user_id="user-123",
            session_id="session-456",
            current_step="step_1",
        )
        
        ProgressStore.save(progress)
        retrieved = ProgressStore.get("user-123")
        
        assert retrieved is not None
        assert retrieved.user_id == "user-123"
        assert retrieved.current_step == "step_1"

    def test_get_nonexistent(self):
        """Test getting progress that doesn't exist."""
        result = ProgressStore.get("nonexistent-user")
        assert result is None

    def test_delete_existing(self):
        """Test deleting existing progress."""
        progress = OnboardingProgress(
            user_id="user-123",
            session_id="session-456",
            current_step="step_1",
        )
        
        ProgressStore.save(progress)
        deleted = ProgressStore.delete("user-123")
        
        assert deleted is True
        assert ProgressStore.get("user-123") is None

    def test_delete_nonexistent(self):
        """Test deleting progress that doesn't exist."""
        deleted = ProgressStore.delete("nonexistent-user")
        assert deleted is False

    def test_clear_store(self):
        """Test clearing all progress from store."""
        ProgressStore.save(OnboardingProgress(
            user_id="user-1",
            session_id="session-1",
            current_step="step_1",
        ))
        ProgressStore.save(OnboardingProgress(
            user_id="user-2",
            session_id="session-2",
            current_step="step_2",
        ))
        
        ProgressStore.clear()
        
        assert ProgressStore.get("user-1") is None
        assert ProgressStore.get("user-2") is None


class TestSaveProgress:
    """Test save_progress function."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_save_progress_creates_new_record(self):
        """save_progress creates new record."""
        progress = save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={"field1": "value1"},
            completed_steps=["step_0"],
        )
        
        assert progress.user_id == "user-123"
        assert progress.current_step == "step_1"
        assert progress.step_data == {"field1": "value1"}
        assert progress.completed_steps == ["step_0"]
        assert progress.version == 1

    def test_save_progress_updates_existing_record(self):
        """save_progress updates existing record."""
        # First save
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={"field1": "value1"},
            completed_steps=["step_0"],
        )
        
        # Update
        progress = save_progress(
            user_id="user-123",
            current_step="step_2",
            step_data={"field2": "value2"},
            completed_steps=["step_0", "step_1"],
        )
        
        assert progress.current_step == "step_2"
        assert progress.completed_steps == ["step_0", "step_1"]
        assert progress.version == 2

    def test_save_progress_preserves_existing_fields(self):
        """save_progress preserves fields from existing record."""
        # First save with all fields
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={"field1": "value1"},
            completed_steps=["step_0"],
            thread_id="thread-abc",
            session_id="session-xyz",
            skipped_steps=["optional_step"],
            prefill_data={"template": "blog"},
            fast_lane_accepted=True,
        )
        
        # Update only some fields
        progress = save_progress(
            user_id="user-123",
            current_step="step_2",
            step_data={"field2": "value2"},
            completed_steps=["step_0", "step_1"],
        )
        
        # Preserved fields should remain
        assert progress.thread_id == "thread-abc"
        assert progress.session_id == "session-xyz"
        assert progress.skipped_steps == ["optional_step"]
        assert progress.prefill_data == {"template": "blog"}
        assert progress.fast_lane_accepted is True

    def test_save_progress_allows_overriding_fields(self):
        """save_progress allows overriding existing fields via kwargs."""
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={"field1": "value1"},
            completed_steps=["step_0"],
            fast_lane_accepted=False,
        )
        
        progress = save_progress(
            user_id="user-123",
            current_step="step_2",
            step_data={"field2": "value2"},
            completed_steps=["step_0", "step_1"],
            fast_lane_accepted=True,
        )
        
        assert progress.fast_lane_accepted is True


class TestGetProgress:
    """Test get_progress function."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_get_progress_returns_none_when_not_found(self):
        """get_progress returns None when not found."""
        result = get_progress("nonexistent-user")
        assert result is None

    def test_get_progress_returns_correct_data(self):
        """get_progress returns correct data."""
        save_progress(
            user_id="user-123",
            current_step="step_2",
            step_data={"key": "value"},
            completed_steps=["step_0", "step_1"],
        )
        
        progress = get_progress("user-123")
        
        assert progress is not None
        assert progress.user_id == "user-123"
        assert progress.current_step == "step_2"
        assert progress.step_data == {"key": "value"}
        assert progress.completed_steps == ["step_0", "step_1"]


class TestResumeProgress:
    """Test resume_progress function."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_resume_progress_returns_none_when_no_progress(self):
        """resume_progress returns None when no progress exists."""
        result = resume_progress("nonexistent-user")
        assert result is None

    def test_resume_progress_marks_as_resumed(self):
        """resume_progress marks as resumed."""
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={"key": "value"},
            completed_steps=["step_0"],
            source="manual",
        )
        
        progress = resume_progress("user-123")
        
        assert progress is not None
        assert progress.source == "resume"
        assert progress.version == 2

    def test_resume_progress_preserves_data(self):
        """resume_progress preserves all existing data."""
        save_progress(
            user_id="user-123",
            current_step="step_2",
            step_data={"field": "data"},
            completed_steps=["step_0", "step_1"],
            thread_id="thread-123",
            session_id="session-456",
        )
        
        progress = resume_progress("user-123")
        
        assert progress.current_step == "step_2"
        assert progress.step_data == {"field": "data"}
        assert progress.completed_steps == ["step_0", "step_1"]
        assert progress.thread_id == "thread-123"
        assert progress.session_id == "session-456"

    def test_resume_progress_updates_timestamp(self):
        """resume_progress updates the timestamp."""
        before_save = datetime.now(timezone.utc)
        
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={},
            completed_steps=[],
        )
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        progress = resume_progress("user-123")
        
        assert progress.updated_at >= before_save


class TestHasProgress:
    """Test has_progress function."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_has_progress_returns_false_when_no_progress(self):
        """has_progress returns False when no progress."""
        assert has_progress("nonexistent-user") is False

    def test_has_progress_returns_true_when_progress_exists(self):
        """has_progress returns True when progress exists."""
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={},
            completed_steps=[],
        )
        
        assert has_progress("user-123") is True


class TestAutoSaveTrigger:
    """Test auto_save_trigger function."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_auto_save_trigger_works_correctly(self):
        """auto_save_trigger works correctly."""
        auto_save_trigger(
            user_id="user-123",
            step="step_1",
            data={"field1": "value1"},
        )
        
        progress = get_progress("user-123")
        
        assert progress is not None
        assert progress.current_step == "step_1"
        assert progress.step_data == {"field1": "value1"}
        assert progress.completed_steps == ["step_1"]
        assert progress.source == "auto_save"

    def test_auto_save_trigger_appends_completed_steps(self):
        """auto_save_trigger appends to completed steps."""
        auto_save_trigger(
            user_id="user-123",
            step="step_1",
            data={"field1": "value1"},
        )
        
        auto_save_trigger(
            user_id="user-123",
            step="step_2",
            data={"field2": "value2"},
        )
        
        progress = get_progress("user-123")
        
        assert progress.completed_steps == ["step_1", "step_2"]

    def test_auto_save_trigger_merges_step_data(self):
        """auto_save_trigger merges step data."""
        auto_save_trigger(
            user_id="user-123",
            step="step_1",
            data={"field1": "value1"},
        )
        
        auto_save_trigger(
            user_id="user-123",
            step="step_2",
            data={"field2": "value2"},
        )
        
        progress = get_progress("user-123")
        
        assert progress.step_data == {"field1": "value1", "field2": "value2"}

    def test_auto_save_trigger_does_not_duplicate_steps(self):
        """auto_save_trigger does not duplicate completed steps."""
        auto_save_trigger(
            user_id="user-123",
            step="step_1",
            data={"field1": "value1"},
        )
        
        auto_save_trigger(
            user_id="user-123",
            step="step_1",
            data={"field1": "updated"},
        )
        
        progress = get_progress("user-123")
        
        assert progress.completed_steps == ["step_1"]

    def test_auto_save_trigger_preserves_existing_data(self):
        """auto_save_trigger preserves data from existing progress."""
        save_progress(
            user_id="user-123",
            current_step="step_0",
            step_data={},
            completed_steps=[],
            thread_id="thread-abc",
            prefill_data={"template": "blog"},
        )
        
        auto_save_trigger(
            user_id="user-123",
            step="step_1",
            data={"field1": "value1"},
        )
        
        progress = get_progress("user-123")
        
        assert progress.thread_id == "thread-abc"
        assert progress.prefill_data == {"template": "blog"}


class TestIdempotency:
    """Test idempotency - multiple saves don't duplicate."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_multiple_saves_dont_duplicate(self):
        """idempotency: multiple saves don't duplicate."""
        # Save multiple times with same data
        for i in range(5):
            save_progress(
                user_id="user-123",
                current_step="step_1",
                step_data={"field": f"value_{i}"},
                completed_steps=["step_0"],
            )
        
        # Should only have one record
        progress = get_progress("user-123")
        assert progress is not None
        assert progress.version == 5  # Version increments with each save
        assert progress.step_data == {"field": "value_4"}  # Last save wins

    def test_idempotency_preserves_single_record(self):
        """Multiple saves to same user_id updates single record."""
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={"count": 1},
            completed_steps=["step_0"],
        )
        
        save_progress(
            user_id="user-123",
            current_step="step_2",
            step_data={"count": 2},
            completed_steps=["step_0", "step_1"],
        )
        
        save_progress(
            user_id="user-123",
            current_step="step_3",
            step_data={"count": 3},
            completed_steps=["step_0", "step_1", "step_2"],
        )
        
        # Verify only one record exists
        all_records = list(ProgressStore._progress.values())
        user_records = [r for r in all_records if r.user_id == "user-123"]
        
        assert len(user_records) == 1
        assert user_records[0].current_step == "step_3"
        assert user_records[0].version == 3


class TestDeleteProgress:
    """Test delete_progress function."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_delete_progress_returns_true_when_deleted(self):
        """delete_progress returns True when progress is deleted."""
        save_progress(
            user_id="user-123",
            current_step="step_1",
            step_data={},
            completed_steps=[],
        )
        
        result = delete_progress("user-123")
        
        assert result is True
        assert has_progress("user-123") is False

    def test_delete_progress_returns_false_when_not_found(self):
        """delete_progress returns False when progress not found."""
        result = delete_progress("nonexistent-user")
        
        assert result is False


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestProgressAPI:
    """Test API endpoints for progress."""

    def setup_method(self):
        """Clear store before each test."""
        ProgressStore.clear()

    def test_get_progress_endpoint_not_found(self):
        """GET /progress/{user_id} returns 404 when not found."""
        from fastapi.testclient import TestClient
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v2/onboarding/progress/nonexistent-user")
        
        assert response.status_code == 404

    def test_save_and_get_progress_endpoint(self):
        """POST and GET /progress/{user_id} work correctly."""
        from fastapi.testclient import TestClient
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # Save progress
        save_data = {
            "current_step": "step_1",
            "step_data": {"field1": "value1"},
            "completed_steps": ["step_0"],
        }
        response = client.post("/api/v2/onboarding/progress/user-123", json=save_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["current_step"] == "step_1"
        
        # Get progress
        response = client.get("/api/v2/onboarding/progress/user-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["current_step"] == "step_1"
        assert data["step_data"] == {"field1": "value1"}
        assert data["completed_steps"] == ["step_0"]

    def test_resume_progress_endpoint(self):
        """POST /progress/{user_id}/resume works correctly."""
        from fastapi.testclient import TestClient
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # First save progress
        save_data = {
            "current_step": "step_1",
            "step_data": {"field1": "value1"},
            "completed_steps": ["step_0"],
        }
        client.post("/api/v2/onboarding/progress/user-123", json=save_data)
        
        # Resume progress
        response = client.post("/api/v2/onboarding/progress/user-123/resume")
        
        assert response.status_code == 200
        data = response.json()
        assert data["resumed"] is True
        assert data["progress"]["source"] == "resume"

    def test_resume_progress_endpoint_not_found(self):
        """POST /progress/{user_id}/resume returns resumed=False when not found."""
        from fastapi.testclient import TestClient
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v2/onboarding/progress/nonexistent-user/resume")
        
        assert response.status_code == 200
        data = response.json()
        assert data["resumed"] is False
        assert data["progress"] is None

    def test_delete_progress_endpoint(self):
        """DELETE /progress/{user_id} works correctly."""
        from fastapi.testclient import TestClient
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # First save progress
        save_data = {
            "current_step": "step_1",
            "step_data": {},
            "completed_steps": [],
        }
        client.post("/api/v2/onboarding/progress/user-123", json=save_data)
        
        # Delete progress
        response = client.delete("/api/v2/onboarding/progress/user-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert data["user_id"] == "user-123"

    def test_check_progress_exists_endpoint(self):
        """GET /progress/{user_id}/exists works correctly."""
        from fastapi.testclient import TestClient
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # Check when not exists
        response = client.get("/api/v2/onboarding/progress/user-123/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_progress"] is False
        assert data["user_id"] == "user-123"
        
        # Save progress
        save_data = {
            "current_step": "step_1",
            "step_data": {},
            "completed_steps": [],
        }
        client.post("/api/v2/onboarding/progress/user-123", json=save_data)
        
        # Check when exists
        response = client.get("/api/v2/onboarding/progress/user-123/exists")
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_progress"] is True

    def test_auto_save_endpoint(self):
        """POST /progress/{user_id}/auto-save works correctly."""
        from fastapi.testclient import TestClient
        from vm_webapp.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        auto_save_data = {
            "step": "step_1",
            "data": {"field1": "value1"},
        }
        response = client.post("/api/v2/onboarding/progress/user-123/auto-save", json=auto_save_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["auto_saved"] is True
        assert data["step"] == "step_1"
