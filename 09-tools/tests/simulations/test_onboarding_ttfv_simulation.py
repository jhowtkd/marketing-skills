"""v41 Onboarding TTFV Simulation Tests.

Tests for the onboarding simulation harness that measures TTFV across
different journey scenarios (v38/v39/v40 features).
"""

import pytest
import json
from datetime import datetime
from typing import List

# Import the simulation framework
from tests.simulations.onboarding_simulation_runner import (
    OnboardingSimulator,
    JourneyMetrics,
    JourneyType,
    SimulationConfig,
    calculate_statistics,
)


@pytest.fixture
def fast_sim():
    """Create simulator with fast test mode enabled."""
    config = SimulationConfig(fast_test_mode=True)
    return OnboardingSimulator(config)


class TestJourneyTypes:
    """Test different journey type simulations."""
    
    def test_happy_path_basic(self, fast_sim):
        """Test basic happy path journey completes successfully."""
        metrics = fast_sim.simulate_happy_path("test_user_001")
        
        assert metrics.journey_type == JourneyType.HAPPY_PATH.value
        assert metrics.user_id == "test_user_001"
        assert metrics.completed is True
        assert metrics.steps_completed == 5  # All steps
        assert metrics.time_to_first_value_ms > 0
        assert len(metrics.telemetry_events) > 0
    
    def test_happy_path_with_prefill(self, fast_sim):
        """Test happy path when prefill is used."""
        fast_sim.config.prefill_probability = 1.0  # Force prefill
        
        metrics = fast_sim.simulate_happy_path("test_user_prefill")
        
        assert metrics.prefill_used is True
        # Check telemetry for prefill event
        prefill_events = [e for e in metrics.telemetry_events 
                         if e.get("event") == "prefill_applied"]
        assert len(prefill_events) >= 1
    
    def test_happy_path_with_fast_lane(self, fast_sim):
        """Test happy path when fast lane is accepted."""
        fast_sim.config.fast_lane_eligible_probability = 1.0  # Force eligible
        fast_sim.config.fast_lane_accept_probability = 1.0     # Force accept
        
        metrics = fast_sim.simulate_happy_path("test_user_fastlane")
        
        assert metrics.fast_lane_used is True
        assert metrics.fast_lane_accepted is True
        assert len(metrics.skipped_steps) > 0
        
        # Check telemetry for fast lane events
        presented = [e for e in metrics.telemetry_events 
                    if e.get("event") == "fast_lane_presented"]
        accepted = [e for e in metrics.telemetry_events 
                   if e.get("event") == "fast_lane_accepted"]
        assert len(presented) >= 1
        assert len(accepted) >= 1
    
    def test_interrupted_resume_journey(self, fast_sim):
        """Test interrupted journey with resume."""
        metrics = fast_sim.simulate_interrupted_resume("test_user_resume")
        
        assert metrics.journey_type == JourneyType.INTERRUPTED_RESUME.value
        assert metrics.completed is True
        assert metrics.resume_used is True
        assert metrics.resume_accepted is True
        
        # Should have resume telemetry
        resume_presented = [e for e in metrics.telemetry_events 
                           if e.get("event") == "onboarding_resume_presented"]
        resume_accepted = [e for e in metrics.telemetry_events 
                          if e.get("event") == "onboarding_resume_accepted"]
        assert len(resume_presented) >= 1
        assert len(resume_accepted) >= 1
        
        # Should have progress saved events (v40 feature)
        progress_saved = [e for e in metrics.telemetry_events 
                         if e.get("event") == "onboarding_progress_saved"]
        assert len(progress_saved) >= 1
    
    def test_interrupted_restart_journey(self, fast_sim):
        """Test interrupted journey with restart (not resume)."""
        metrics = fast_sim.simulate_interrupted_restart("test_user_restart")
        
        assert metrics.journey_type == JourneyType.INTERRUPTED_RESTART.value
        assert metrics.completed is True
        assert metrics.resume_used is True
        assert metrics.resume_accepted is False
        
        # Should have resume rejected telemetry
        resume_rejected = [e for e in metrics.telemetry_events 
                          if e.get("event") == "onboarding_resume_rejected"]
        assert len(resume_rejected) >= 1
    
    def test_abandon_early_journey(self, fast_sim):
        """Test early abandonment journey."""
        metrics = fast_sim.simulate_abandon_early("test_user_abandon")
        
        assert metrics.journey_type == JourneyType.ABANDON_EARLY.value
        assert metrics.completed is False
        assert metrics.abandonment_step is not None
        assert metrics.steps_completed < 5
        
        # Should have dropoff telemetry
        dropoff_events = [e for e in metrics.telemetry_events 
                         if e.get("event") == "onboarding_dropoff"]
        assert len(dropoff_events) >= 1


class TestTelemetryValidation:
    """Validate expected telemetry is emitted."""
    
    def test_fast_lane_telemetry_events(self, fast_sim):
        """Validate fast lane telemetry events are captured."""
        fast_sim.config.fast_lane_eligible_probability = 1.0
        fast_sim.config.fast_lane_accept_probability = 1.0
        metrics = fast_sim.simulate_happy_path("test_telemetry_fl")
        
        event_names = [e.get("event") for e in metrics.telemetry_events]
        
        assert "fast_lane_presented" in event_names
        assert "fast_lane_accepted" in event_names
        assert "first_value_reached" in event_names
    
    def test_save_resume_telemetry_events(self, fast_sim):
        """Validate save/resume telemetry events (v40)."""
        metrics = fast_sim.simulate_interrupted_resume("test_telemetry_sr")
        
        event_names = [e.get("event") for e in metrics.telemetry_events]
        
        assert "onboarding_progress_saved" in event_names
        assert "onboarding_resume_presented" in event_names
        assert "onboarding_resume_accepted" in event_names
        assert "first_value_reached" in event_names
    
    def test_all_required_telemetry_present(self, fast_sim):
        """Test that all expected telemetry events can be emitted."""
        # Run all journey types
        all_events = set()
        
        for journey_type in JourneyType:
            metrics = fast_sim.run_simulation(journey_type)
            for event in metrics.telemetry_events:
                all_events.add(event.get("event"))
        
        # Check expected events were seen
        expected_events = {
            "step_completed",
            "onboarding_progress_saved",
            "onboarding_resume_presented",
            "onboarding_resume_accepted",
            "onboarding_resume_rejected",
            "fast_lane_presented",
            "fast_lane_accepted",
            "first_value_reached",
            "onboarding_dropoff",
        }
        
        for event in expected_events:
            assert event in all_events, f"Expected event '{event}' not found"


class TestMetricsCalculation:
    """Test metrics calculation and statistics."""
    
    def test_journey_metrics_to_dict(self, fast_sim):
        """Test metrics can be serialized to dict."""
        metrics = fast_sim.simulate_happy_path("test_dict")
        
        data = metrics.to_dict()
        
        assert data["journey_type"] == JourneyType.HAPPY_PATH.value
        assert data["user_id"] == "test_dict"
        assert "time_to_first_value_ms" in data
        assert "telemetry_events" in data
        assert isinstance(data["started_at"], str)  # ISO format
    
    def test_statistics_calculation(self, fast_sim):
        """Test statistics calculation from multiple runs."""
        # Generate 5 happy path runs
        metrics_list: List[JourneyMetrics] = [
            fast_sim.simulate_happy_path(f"stats_user_{i}")
            for i in range(5)
        ]
        
        stats = calculate_statistics(metrics_list)
        
        assert stats["sample_size"] == 5
        assert stats["avg_ttfv_ms"] > 0
        assert stats["min_ttfv_ms"] <= stats["max_ttfv_ms"]
        assert 0 <= stats["completion_rate"] <= 1
        assert 0 <= stats["prefill_adoption"] <= 1
    
    def test_empty_statistics(self):
        """Test statistics with empty list."""
        stats = calculate_statistics([])
        assert stats == {}


class TestBatchSimulations:
    """Test batch simulation runs."""
    
    def test_batch_happy_path(self, fast_sim):
        """Test running multiple happy path simulations."""
        results = fast_sim.run_batch(JourneyType.HAPPY_PATH, count=5)
        
        assert len(results) == 5
        for metrics in results:
            assert metrics.journey_type == JourneyType.HAPPY_PATH.value
            assert metrics.completed is True
    
    def test_compare_journeys(self, fast_sim):
        """Test comparison of all journey types."""
        comparison = fast_sim.compare_journeys(runs_per_type=3)
        
        # Should have all journey types
        for journey_type in JourneyType:
            assert journey_type.value in comparison
            assert len(comparison[journey_type.value]) == 3


class TestFeatureInteraction:
    """Test interaction of multiple features (v38+v39+v40)."""
    
    def test_prefill_plus_fast_lane(self, fast_sim):
        """Test happy path with both prefill and fast lane."""
        fast_sim.config.prefill_probability = 1.0
        fast_sim.config.fast_lane_eligible_probability = 1.0
        fast_sim.config.fast_lane_accept_probability = 1.0
        
        metrics = fast_sim.simulate_happy_path("test_combo")
        
        assert metrics.prefill_used is True
        assert metrics.fast_lane_used is True
        assert metrics.completed is True
        
        # Both features should emit telemetry
        events = [e.get("event") for e in metrics.telemetry_events]
        assert "prefill_applied" in events
        assert "fast_lane_accepted" in events
    
    def test_all_features_together(self, fast_sim):
        """Test journey using all v38/v39/v40 features."""
        # This is an interrupted resume with prefill and fast lane
        # Note: resume doesn't combine with fast lane in this simulation,
        # but we can verify the telemetry for each feature separately
        
        # Run each feature separately and verify
        happy_metrics = fast_sim.simulate_happy_path("test_all_features")
        resume_metrics = fast_sim.simulate_interrupted_resume("test_all_features_resume")
        
        # Verify each feature's telemetry is present
        happy_events = [e.get("event") for e in happy_metrics.telemetry_events]
        resume_events = [e.get("event") for e in resume_metrics.telemetry_events]
        
        # Happy path may have fast lane
        assert "first_value_reached" in happy_events
        
        # Resume has save/resume telemetry
        assert "onboarding_progress_saved" in resume_events
        assert "onboarding_resume_presented" in resume_events


class TestConfiguration:
    """Test simulation configuration options."""
    
    def test_custom_timing_config(self, fast_sim):
        """Test simulation with custom timing."""
        fast_sim.config.step_duration_base_ms = 1000  # Faster steps
        fast_sim.config.step_duration_variance_ms = 0   # No variance
        
        metrics = fast_sim.simulate_happy_path("test_timing")
        
        # Should complete faster with lower base duration
        assert metrics.completed is True
    
    def test_zero_probability_config(self, fast_sim):
        """Test with all optional features disabled."""
        fast_sim.config.prefill_probability = 0.0
        fast_sim.config.fast_lane_eligible_probability = 0.0
        fast_sim.config.abandon_probability = 0.0
        
        metrics = fast_sim.simulate_happy_path("test_no_features")
        
        assert metrics.prefill_used is False
        assert metrics.fast_lane_used is False
        assert metrics.completed is True


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_fast_lane_rejection(self, fast_sim):
        """Test when fast lane is offered but rejected."""
        fast_sim.config.fast_lane_eligible_probability = 1.0
        fast_sim.config.fast_lane_accept_probability = 0.0  # Force reject
        
        metrics = fast_sim.simulate_happy_path("test_fl_reject")
        
        # fast_lane_used = was offered AND accepted
        # fast_lane_accepted = acceptance decision
        assert metrics.fast_lane_used is False  # Not used because rejected
        assert metrics.fast_lane_accepted is False  # Was rejected
        assert len(metrics.skipped_steps) == 0  # No steps skipped
        
        # Should have presentation and rejection telemetry
        events = [e.get("event") for e in metrics.telemetry_events]
        assert "fast_lane_presented" in events
        assert "fast_lane_rejected" in events
    
    def test_single_step_completion(self, fast_sim):
        """Test metrics with single step scenario."""
        fast_sim.config.steps = ["welcome", "completion"]
        
        metrics = fast_sim.simulate_happy_path("test_minimal")
        
        assert metrics.total_steps == 2
        assert metrics.steps_completed == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
