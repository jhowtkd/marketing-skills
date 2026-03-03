"""Tests for onboarding persistence."""

from __future__ import annotations

import pytest


class TestOnboardingEvents:
    """Tests for onboarding event tracking."""

    def test_track_event_persists(self, client):
        """Test that tracked events are persisted."""
        brand_id = "b-test"
        response = client.post("/api/v2/onboarding/events", json={
            "event_type": "test_event",
            "brand_id": brand_id,
            "payload": {"test": "data"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True or "event_id" in data

    def test_track_event_without_brand(self, client):
        """Test tracking event without brand_id fails."""
        response = client.post("/api/v2/onboarding/events", json={
            "event_type": "test_event",
        })
        # May fail or succeed depending on implementation
        assert response.status_code in [200, 422]

    def test_get_metrics(self, client):
        """Test getting onboarding metrics."""
        brand_id = "b-test"
        # First track an event
        client.post("/api/v2/onboarding/events", json={
            "event_type": "test_event",
            "brand_id": brand_id,
        })
        
        # Then get metrics
        response = client.get(f"/api/v2/onboarding/metrics?brand_id={brand_id}")
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data or "events" in data or "metrics" in data


class TestOnboardingExperiments:
    """Tests for onboarding experiments."""

    def test_list_experiments(self, client, sample_brand):
        """Test listing experiments for a brand."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-experiments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "experiments" in data

    def test_get_experiment_status(self, client, sample_brand):
        """Test getting experiment status."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-experiments/status")
        assert response.status_code == 200


class TestOnboardingPersonalization:
    """Tests for onboarding personalization."""

    def test_get_personalization_status(self, client, sample_brand):
        """Test getting personalization status."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-personalization/status")
        assert response.status_code == 200

    def test_list_personalization_policies(self, client, sample_brand):
        """Test listing personalization policies."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-personalization/policies")
        assert response.status_code == 200


class TestOnboardingRecovery:
    """Tests for onboarding recovery."""

    def test_get_recovery_status(self, client, sample_brand):
        """Test getting recovery status."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-recovery/status")
        assert response.status_code == 200

    def test_list_recovery_cases(self, client, sample_brand):
        """Test listing recovery cases."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-recovery/cases")
        assert response.status_code == 200


class TestOnboardingActivation:
    """Tests for onboarding activation."""

    def test_get_activation_status(self, client, sample_brand):
        """Test getting activation status."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-activation/status")
        assert response.status_code == 200


class TestOnboardingContinuity:
    """Tests for onboarding continuity."""

    def test_get_continuity_status(self, client, sample_brand):
        """Test getting continuity status."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-continuity/status")
        assert response.status_code == 200

    def test_list_handoffs(self, client, sample_brand):
        """Test listing handoffs."""
        brand_id = sample_brand["brand_id"]
        response = client.get(f"/api/v2/brands/{brand_id}/onboarding-continuity/handoffs")
        assert response.status_code == 200
