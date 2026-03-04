"""v41 Onboarding Simulation Runner - Local TTFV benchmarking harness.

This module provides a simulation framework for measuring TTFV (Time to First Value)
across different onboarding journey scenarios without requiring production environment.
"""

from __future__ import annotations

import time
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from unittest.mock import MagicMock, patch
import random


class JourneyType(str, Enum):
    """Types of onboarding journeys to simulate."""
    HAPPY_PATH = "happy_path"
    INTERRUPTED_RESUME = "interrupted_resume"
    INTERRUPTED_RESTART = "interrupted_restart"
    ABANDON_EARLY = "abandon_early"


class FeatureUsage(str, Enum):
    """Feature usage tracking."""
    NONE = "none"
    PREFILL = "prefill"
    FAST_LANE = "fast_lane"
    SAVE_RESUME = "save_resume"
    ALL = "all"


@dataclass
class JourneyMetrics:
    """Metrics captured during a simulated journey."""
    journey_type: str
    user_id: str
    
    # TTFV metrics
    time_to_first_value_ms: int = 0
    total_duration_ms: int = 0
    
    # Progress metrics
    steps_completed: int = 0
    total_steps: int = 5
    skipped_steps: List[str] = field(default_factory=list)
    
    # Feature usage flags
    prefill_used: bool = False
    fast_lane_used: bool = False
    fast_lane_accepted: bool = False
    resume_used: bool = False
    resume_accepted: Optional[bool] = None
    
    # Completion status
    completed: bool = False
    abandonment_step: Optional[str] = None
    
    # Telemetry captured
    telemetry_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamp
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['started_at'] = self.started_at.isoformat()
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data


@dataclass
class SimulationConfig:
    """Configuration for simulation runs."""
    # Timing (in ms)
    step_duration_base_ms: int = 5000
    step_duration_variance_ms: int = 2000
    prefill_time_saved_ms: int = 3000
    fast_lane_time_saved_per_step_ms: int = 4000
    resume_overhead_ms: int = 500
    
    # Test mode - when True, skip actual sleep for faster tests
    fast_test_mode: bool = False
    
    # Feature probabilities
    prefill_probability: float = 0.4
    fast_lane_eligible_probability: float = 0.3
    fast_lane_accept_probability: float = 0.7
    interrupt_probability: float = 0.3
    abandon_probability: float = 0.15
    
    # Steps in onboarding
    steps: List[str] = field(default_factory=lambda: [
        "welcome",
        "workspace_setup", 
        "template_selection",
        "customization",
        "completion"
    ])
    
    # Fast lane skippable steps
    fast_lane_skippable: List[str] = field(default_factory=lambda: [
        "customization"
    ])


class OnboardingSimulator:
    """Simulator for onboarding journeys."""
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.telemetry_log: List[Dict[str, Any]] = []
        
    def _emit_telemetry(self, event_name: str, user_id: str, **kwargs) -> None:
        """Record telemetry event."""
        event = {
            "event": event_name,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.telemetry_log.append(event)
        
    def _calculate_step_duration(
        self, 
        step: str, 
        use_prefill: bool,
        use_fast_lane: bool
    ) -> int:
        """Calculate simulated duration for a step."""
        base = self.config.step_duration_base_ms
        variance = random.randint(
            -self.config.step_duration_variance_ms,
            self.config.step_duration_variance_ms
        )
        
        duration = base + variance
        
        # Apply time savings
        if use_prefill and step == "template_selection":
            duration -= self.config.prefill_time_saved_ms
            
        if use_fast_lane and step in self.config.fast_lane_skippable:
            duration = 100  # Minimal time for skipped steps
            
        return max(100, duration)
    
    def _should_use_prefill(self) -> bool:
        """Determine if prefill is available and used."""
        return random.random() < self.config.prefill_probability
    
    def _should_offer_fast_lane(self) -> bool:
        """Determine if fast lane is offered."""
        return random.random() < self.config.fast_lane_eligible_probability
    
    def _should_accept_fast_lane(self) -> bool:
        """Determine if user accepts fast lane."""
        return random.random() < self.config.fast_lane_accept_probability
    
    def _should_interrupt(self) -> bool:
        """Determine if journey gets interrupted."""
        return random.random() < self.config.interrupt_probability
    
    def _should_abandon(self) -> bool:
        """Determine if user abandons."""
        return random.random() < self.config.abandon_probability
    
    def simulate_happy_path(self, user_id: str) -> JourneyMetrics:
        """Simulate a complete happy path journey."""
        metrics = JourneyMetrics(
            journey_type=JourneyType.HAPPY_PATH.value,
            user_id=user_id,
            total_steps=len(self.config.steps)
        )
        
        start_time = time.time()
        
        # Check for prefill
        metrics.prefill_used = self._should_use_prefill()
        if metrics.prefill_used:
            self._emit_telemetry("prefill_applied", user_id, step="template_selection")
        
        # Check for fast lane eligibility
        fast_lane_offered = self._should_offer_fast_lane()
        if fast_lane_offered:
            self._emit_telemetry("fast_lane_presented", user_id)
            metrics.fast_lane_used = self._should_accept_fast_lane()
            metrics.fast_lane_accepted = metrics.fast_lane_used
            
            if metrics.fast_lane_used:
                self._emit_telemetry("fast_lane_accepted", user_id)
                metrics.skipped_steps = self.config.fast_lane_skippable.copy()
            else:
                self._emit_telemetry("fast_lane_rejected", user_id)
        
        # Progress through steps
        for i, step in enumerate(self.config.steps):
            if step in metrics.skipped_steps:
                metrics.steps_completed += 1
                continue
                
            step_duration = self._calculate_step_duration(
                step, 
                metrics.prefill_used,
                metrics.fast_lane_used
            )
            
            # Simulate step completion time (skip in fast test mode)
            if not self.config.fast_test_mode:
                if not self.config.fast_test_mode:
                    time.sleep(step_duration / 1000)  # Convert to seconds
            
            metrics.steps_completed += 1
            self._emit_telemetry("step_completed", user_id, step=step, index=i)
            
            # Emit progress saved event (v40 feature)
            self._emit_telemetry("onboarding_progress_saved", user_id, step=step)
        
        metrics.completed = True
        metrics.completed_at = datetime.utcnow()
        elapsed = time.time() - start_time
        # In fast test mode, calculate based on step durations instead of real time
        if self.config.fast_test_mode and elapsed < 0.1:
            calculated_duration = sum(
                self._calculate_step_duration(step, metrics.prefill_used, metrics.fast_lane_used)
                for step in self.config.steps if step not in metrics.skipped_steps
            )
            metrics.total_duration_ms = calculated_duration
        else:
            metrics.total_duration_ms = int(elapsed * 1000)
        metrics.time_to_first_value_ms = metrics.total_duration_ms
        
        self._emit_telemetry("first_value_reached", user_id)
        metrics.telemetry_events = self.telemetry_log.copy()
        self.telemetry_log.clear()
        
        return metrics
    
    def simulate_interrupted_resume(self, user_id: str) -> JourneyMetrics:
        """Simulate interrupted journey with resume."""
        metrics = JourneyMetrics(
            journey_type=JourneyType.INTERRUPTED_RESUME.value,
            user_id=user_id,
            total_steps=len(self.config.steps)
        )
        
        start_time = time.time()
        
        # First session - gets interrupted
        interrupt_at_step = random.randint(1, len(self.config.steps) - 2)
        
        for i, step in enumerate(self.config.steps[:interrupt_at_step + 1]):
            step_duration = self._calculate_step_duration(step, False, False)
            if not self.config.fast_test_mode:
                time.sleep(step_duration / 1000)
            
            metrics.steps_completed += 1
            self._emit_telemetry("step_completed", user_id, step=step, index=i)
            self._emit_telemetry("onboarding_progress_saved", user_id, step=step)
        
        # Interruption happens
        abandonment_step = self.config.steps[interrupt_at_step]
        self._emit_telemetry("onboarding_progress_saved", user_id, 
                            step=abandonment_step, source="auto_save")
        
        # Simulate time passing (hours/days later) - skip in fast mode
        if not self.config.fast_test_mode:
            time.sleep(0.1)
        
        # Second session - resume
        self._emit_telemetry("onboarding_resume_presented", user_id, 
                            last_step=abandonment_step)
        metrics.resume_used = True
        metrics.resume_accepted = True
        self._emit_telemetry("onboarding_resume_accepted", user_id, 
                            resumed_step=abandonment_step)
        
        # Resume overhead
        if not self.config.fast_test_mode:
            time.sleep(self.config.resume_overhead_ms / 1000)
        
        # Continue from where left off
        for i, step in enumerate(self.config.steps[interrupt_at_step + 1:], 
                                  start=interrupt_at_step + 1):
            step_duration = self._calculate_step_duration(step, False, False)
            if not self.config.fast_test_mode:
                time.sleep(step_duration / 1000)
            
            metrics.steps_completed += 1
            self._emit_telemetry("step_completed", user_id, step=step, index=i)
            self._emit_telemetry("onboarding_progress_saved", user_id, step=step)
        
        metrics.completed = True
        metrics.completed_at = datetime.utcnow()
        elapsed = time.time() - start_time
        # In fast test mode, calculate based on step durations instead of real time
        if self.config.fast_test_mode and elapsed < 0.1:
            calculated_duration = sum(
                self._calculate_step_duration(step, metrics.prefill_used, metrics.fast_lane_used)
                for step in self.config.steps if step not in metrics.skipped_steps
            )
            metrics.total_duration_ms = calculated_duration
        else:
            metrics.total_duration_ms = int(elapsed * 1000)
        metrics.time_to_first_value_ms = metrics.total_duration_ms
        
        self._emit_telemetry("first_value_reached", user_id)
        metrics.telemetry_events = self.telemetry_log.copy()
        self.telemetry_log.clear()
        
        return metrics
    
    def simulate_interrupted_restart(self, user_id: str) -> JourneyMetrics:
        """Simulate interrupted journey with restart (not resume)."""
        metrics = JourneyMetrics(
            journey_type=JourneyType.INTERRUPTED_RESTART.value,
            user_id=user_id,
            total_steps=len(self.config.steps)
        )
        
        start_time = time.time()
        
        # First session - gets interrupted
        interrupt_at_step = random.randint(1, len(self.config.steps) - 2)
        
        for i, step in enumerate(self.config.steps[:interrupt_at_step + 1]):
            step_duration = self._calculate_step_duration(step, False, False)
            if not self.config.fast_test_mode:
                time.sleep(step_duration / 1000)
            
            metrics.steps_completed += 1
            self._emit_telemetry("step_completed", user_id, step=step, index=i)
            self._emit_telemetry("onboarding_progress_saved", user_id, step=step)
        
        abandonment_step = self.config.steps[interrupt_at_step]
        
        # Second session - user chooses restart
        if not self.config.fast_test_mode:
            time.sleep(0.1)
        
        self._emit_telemetry("onboarding_resume_presented", user_id, 
                            last_step=abandonment_step)
        metrics.resume_used = True
        metrics.resume_accepted = False
        self._emit_telemetry("onboarding_resume_rejected", user_id, 
                            reason="user_chose_restart")
        
        # Restart from beginning
        metrics.steps_completed = 0
        metrics.skipped_steps = []
        
        for i, step in enumerate(self.config.steps):
            step_duration = self._calculate_step_duration(step, False, False)
            if not self.config.fast_test_mode:
                time.sleep(step_duration / 1000)
            
            metrics.steps_completed += 1
            self._emit_telemetry("step_completed", user_id, step=step, index=i)
            self._emit_telemetry("onboarding_progress_saved", user_id, step=step)
        
        metrics.completed = True
        metrics.completed_at = datetime.utcnow()
        elapsed = time.time() - start_time
        # In fast test mode, calculate based on step durations instead of real time
        if self.config.fast_test_mode and elapsed < 0.1:
            # Calculate for all steps since restart doesn't skip any
            calculated_duration = sum(
                self._calculate_step_duration(step, False, False)
                for step in self.config.steps
            ) * 2  # Double because restart does steps twice
            metrics.total_duration_ms = calculated_duration
        else:
            metrics.total_duration_ms = int(elapsed * 1000)
        metrics.time_to_first_value_ms = metrics.total_duration_ms
        
        self._emit_telemetry("first_value_reached", user_id)
        metrics.telemetry_events = self.telemetry_log.copy()
        self.telemetry_log.clear()
        
        return metrics
    
    def simulate_abandon_early(self, user_id: str) -> JourneyMetrics:
        """Simulate user abandoning onboarding early."""
        metrics = JourneyMetrics(
            journey_type=JourneyType.ABANDON_EARLY.value,
            user_id=user_id,
            total_steps=len(self.config.steps)
        )
        
        start_time = time.time()
        
        # Abandon after 1-2 steps
        abandon_after = random.randint(1, 2)
        
        for i, step in enumerate(self.config.steps[:abandon_after]):
            step_duration = self._calculate_step_duration(step, False, False)
            if not self.config.fast_test_mode:
                time.sleep(step_duration / 1000)
            
            metrics.steps_completed += 1
            self._emit_telemetry("step_completed", user_id, step=step, index=i)
            self._emit_telemetry("onboarding_progress_saved", user_id, step=step)
        
        abandonment_step = self.config.steps[abandon_after - 1]
        metrics.abandonment_step = abandonment_step
        metrics.completed = False
        
        self._emit_telemetry("onboarding_dropoff", user_id, 
                            step=abandonment_step, 
                            reason="user_abandoned")
        
        elapsed = time.time() - start_time
        if self.config.fast_test_mode and elapsed < 0.1:
            calculated_duration = sum(
                self._calculate_step_duration(step, False, False)
                for step in self.config.steps[:abandon_after]
            )
            metrics.total_duration_ms = calculated_duration
        else:
            metrics.total_duration_ms = int(elapsed * 1000)
        metrics.telemetry_events = self.telemetry_log.copy()
        self.telemetry_log.clear()
        
        return metrics
    
    def run_simulation(
        self, 
        journey_type: JourneyType,
        user_id: Optional[str] = None
    ) -> JourneyMetrics:
        """Run a single simulation of specified type."""
        user_id = user_id or f"sim_user_{random.randint(1000, 9999)}"
        
        if journey_type == JourneyType.HAPPY_PATH:
            return self.simulate_happy_path(user_id)
        elif journey_type == JourneyType.INTERRUPTED_RESUME:
            return self.simulate_interrupted_resume(user_id)
        elif journey_type == JourneyType.INTERRUPTED_RESTART:
            return self.simulate_interrupted_restart(user_id)
        elif journey_type == JourneyType.ABANDON_EARLY:
            return self.simulate_abandon_early(user_id)
        else:
            raise ValueError(f"Unknown journey type: {journey_type}")
    
    def run_batch(
        self,
        journey_type: JourneyType,
        count: int = 10
    ) -> List[JourneyMetrics]:
        """Run multiple simulations of same type."""
        return [
            self.run_simulation(journey_type, f"sim_user_{journey_type.value}_{i}")
            for i in range(count)
        ]
    
    def compare_journeys(
        self,
        runs_per_type: int = 10
    ) -> Dict[str, List[JourneyMetrics]]:
        """Run all journey types and return comparison."""
        results = {}
        
        for journey_type in JourneyType:
            results[journey_type.value] = self.run_batch(journey_type, runs_per_type)
            
        return results


def calculate_statistics(metrics_list: List[JourneyMetrics]) -> Dict[str, Any]:
    """Calculate statistics from a list of journey metrics."""
    if not metrics_list:
        return {}
    
    durations = [m.time_to_first_value_ms for m in metrics_list]
    completion_rates = [1 if m.completed else 0 for m in metrics_list]
    
    prefill_usage = sum(1 for m in metrics_list if m.prefill_used)
    fast_lane_usage = sum(1 for m in metrics_list if m.fast_lane_used)
    resume_usage = sum(1 for m in metrics_list if m.resume_used)
    
    return {
        "sample_size": len(metrics_list),
        "avg_ttfv_ms": sum(durations) / len(durations),
        "min_ttfv_ms": min(durations),
        "max_ttfv_ms": max(durations),
        "completion_rate": sum(completion_rates) / len(completion_rates),
        "prefill_adoption": prefill_usage / len(metrics_list),
        "fast_lane_adoption": fast_lane_usage / len(metrics_list),
        "resume_adoption": resume_usage / len(metrics_list),
    }


if __name__ == "__main__":
    # Quick test run
    sim = OnboardingSimulator()
    
    print("Running quick simulation test...")
    
    for journey_type in JourneyType:
        print(f"\n{journey_type.value}:")
        metrics = sim.run_simulation(journey_type)
        print(f"  TTFV: {metrics.time_to_first_value_ms}ms")
        print(f"  Steps: {metrics.steps_completed}/{metrics.total_steps}")
        print(f"  Completed: {metrics.completed}")
        print(f"  Telemetry events: {len(metrics.telemetry_events)}")
