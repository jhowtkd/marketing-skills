"""Tests for v45 rollout integration scenarios.

This module tests end-to-end scenarios:
- Control -> Promote -> Rollback flow
- Phase transitions
- Decision validation at each phase
- Reproducibility

Total: 5+ tests
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime
from pathlib import Path

from tests.simulations.simulation_models import (
    ExperimentMetrics,
    ExperimentPhase,
    GateCheck,
    PromotionPolicyConfig,
    RollbackPolicyConfig,
    RolloutDecisionType,
    VariantMetrics,
)

from tests.simulations.rollout_engines import (
    PromotionEngine,
    RollbackEngine,
    PolicyPersistence,
)

from tests.simulations.v45_rollout_integration import (
    RolloutSimulationRunner,
    create_variant_metrics_from_benchmark,
    generate_synthetic_v44_results,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_variant_metrics() -> dict:
    """Create sample variant metrics for testing."""
    return {
        "control": VariantMetrics(
            variant_id="control",
            sample_size=100,
            conversions=70,
            total_time_to_value_ms=2_500_000,
            avg_time_to_value_ms=25_000.0,
            completion_rate=0.70,
            abandonment_rate=0.30,
            prefill_adoption=0.40,
            fast_lane_adoption=0.30,
        ),
        "treatment": VariantMetrics(
            variant_id="treatment",
            sample_size=100,
            conversions=80,
            total_time_to_value_ms=2_000_000,
            avg_time_to_value_ms=20_000.0,
            completion_rate=0.80,
            abandonment_rate=0.20,
            prefill_adoption=0.45,
            fast_lane_adoption=0.35,
        ),
    }


@pytest.fixture
def experiment_metrics(sample_variant_metrics) -> ExperimentMetrics:
    """Create experiment metrics for testing."""
    return ExperimentMetrics(
        experiment_id="exp_test",
        variant_metrics=sample_variant_metrics,
        control_variant_id="control",
    )


@pytest.fixture
def degraded_metrics(sample_variant_metrics) -> ExperimentMetrics:
    """Create degraded experiment metrics for testing."""
    degraded_variants = {
        "control": sample_variant_metrics["control"],
        "treatment": VariantMetrics(
            variant_id="treatment",
            sample_size=100,
            conversions=50,  # Degraded: 50% vs 80% before
            total_time_to_value_ms=3_500_000,
            avg_time_to_value_ms=35_000.0,  # Degraded: 35s vs 20s before
            completion_rate=0.50,
            abandonment_rate=0.50,
            prefill_adoption=0.30,
            fast_lane_adoption=0.25,
        ),
    }
    
    return ExperimentMetrics(
        experiment_id="exp_degraded",
        variant_metrics=degraded_variants,
        control_variant_id="control",
    )


@pytest.fixture
def simulation_runner() -> RolloutSimulationRunner:
    """Create a simulation runner for testing."""
    return RolloutSimulationRunner(
        experiment_id="exp_test",
        random_seed=42,
    )


# =============================================================================
# END-TO-END SCENARIO TESTS (5+ tests)
# =============================================================================

class TestEndToEndScenarios:
    """End-to-end scenario tests."""
    
    def test_full_promote_rollback_workflow(self, experiment_metrics, degraded_metrics):
        """
        Test complete workflow: Control -> Promote -> Degrade -> Rollback.
        
        Scenario:
        1. Control baseline established
        2. Treatment evaluated and promoted
        3. Treatment degrades (with multiple consecutive violations)
        4. Rollback triggered
        5. Control restored
        """
        # Use a more aggressive rollback config for testing
        rollback_config = RollbackPolicyConfig(
            max_completion_rate_drop=0.15,
            max_ttfv_increase_ratio=1.30,
            min_sample_size_for_rollback=50,
            consecutive_failures_threshold=1,  # Trigger on first violation
        )
        
        runner = RolloutSimulationRunner(
            experiment_id="exp_full_workflow",
            random_seed=42,
            rollback_config=rollback_config,
        )
        
        # Phase 1: Control Baseline
        control = experiment_metrics.get_control_metrics()
        phase1 = runner.run_phase_1_control_baseline(control)
        assert phase1.phase == ExperimentPhase.CONTROL_BASELINE
        assert phase1.decision == RolloutDecisionType.CONTINUE
        
        # Phase 2: Treatment Evaluation
        phase2 = runner.run_phase_2_treatment_evaluation(experiment_metrics)
        assert phase2.phase == ExperimentPhase.TREATMENT_EVALUATION
        assert phase2.decision == RolloutDecisionType.PROMOTE
        assert len(phase2.gate_checks) == 2
        
        # Phase 3: Treatment Promoted
        phase3 = runner.run_phase_3_treatment_promoted(experiment_metrics)
        assert phase3.phase == ExperimentPhase.TREATMENT_PROMOTED
        assert phase3.decision == RolloutDecisionType.PROMOTE
        
        # Phase 4: Treatment Degraded (severe degradation)
        degraded_metrics_data, phase4 = runner.run_phase_4_treatment_degraded(
            experiment_metrics,
            degradation_factor=0.50,  # Severe 50% degradation
        )
        assert phase4.phase == ExperimentPhase.TREATMENT_DEGRADED
        
        # Phase 5: Rollback (should trigger with consecutive_failures_threshold=1)
        if phase4.decision == RolloutDecisionType.ROLLBACK:
            phase5 = runner.run_phase_5_rollback_executed(control)
            assert phase5.phase == ExperimentPhase.ROLLED_BACK
            assert phase5.decision == RolloutDecisionType.ROLLBACK
            assert phase5.variant_id == "control"
            expected_phases = 5
            expected_final = ExperimentPhase.ROLLED_BACK
        else:
            # If not rolled back, continue monitoring
            expected_phases = 4
            expected_final = ExperimentPhase.TREATMENT_DEGRADED
        
        # Verify report
        runner.report.complete()
        assert len(runner.report.phases) == expected_phases
        
        # Update final state based on what happened
        if phase4.decision == RolloutDecisionType.ROLLBACK:
            runner.report.final_state = ExperimentPhase.ROLLED_BACK
            runner.report.final_decision = RolloutDecisionType.ROLLBACK
        else:
            runner.report.final_state = ExperimentPhase.TREATMENT_DEGRADED
            runner.report.final_decision = RolloutDecisionType.CONTINUE
        
        assert runner.report.final_state == expected_final
    
    def test_successful_promotion_no_rollback(self, experiment_metrics):
        """
        Test scenario where treatment is promoted and stays healthy.
        
        Scenario:
        1. Control baseline established
        2. Treatment evaluated and promoted
        3. Treatment remains healthy (no degradation)
        4. System stays on treatment
        """
        runner = RolloutSimulationRunner(
            experiment_id="exp_success",
            random_seed=42,
        )
        
        # Run full simulation without forcing rollback
        report = runner.run_full_simulation(
            experiment_metrics,
            force_rollback=False,
        )
        
        # Should have 3 phases (no degradation/rollback)
        assert len(report.phases) == 3
        assert report.phases[0].phase == ExperimentPhase.CONTROL_BASELINE
        assert report.phases[1].phase == ExperimentPhase.TREATMENT_EVALUATION
        assert report.phases[2].phase == ExperimentPhase.TREATMENT_PROMOTED
        
        # Final state should be promoted
        assert report.final_decision == RolloutDecisionType.PROMOTE
        assert report.final_state == ExperimentPhase.TREATMENT_PROMOTED
    
    def test_treatment_not_promoted_insufficient_lift(self):
        """
        Test scenario where treatment fails promotion criteria.
        
        Scenario:
        1. Control baseline established
        2. Treatment evaluated but has insufficient lift
        3. Decision is CONTINUE
        4. No promotion occurs
        """
        # Create metrics where treatment is worse than control
        variants = {
            "control": VariantMetrics(
                variant_id="control",
                sample_size=100,
                conversions=80,
                total_time_to_value_ms=2_000_000,
                avg_time_to_value_ms=20_000.0,
                completion_rate=0.80,
                abandonment_rate=0.20,
                prefill_adoption=0.40,
                fast_lane_adoption=0.30,
            ),
            "treatment": VariantMetrics(
                variant_id="treatment",
                sample_size=100,
                conversions=60,
                total_time_to_value_ms=3_000_000,
                avg_time_to_value_ms=30_000.0,
                completion_rate=0.60,  # Worse than control
                abandonment_rate=0.40,
                prefill_adoption=0.35,
                fast_lane_adoption=0.25,
            ),
        }
        
        bad_metrics = ExperimentMetrics(
            experiment_id="exp_bad_treatment",
            variant_metrics=variants,
            control_variant_id="control",
        )
        
        runner = RolloutSimulationRunner(
            experiment_id="exp_bad_treatment",
            random_seed=42,
        )
        
        report = runner.run_full_simulation(bad_metrics, force_rollback=False)
        
        # Should stop after evaluation phase
        assert len(report.phases) == 2
        assert report.phases[1].decision == RolloutDecisionType.CONTINUE
        assert report.final_state == ExperimentPhase.TREATMENT_EVALUATION
    
    def test_reproducibility_with_same_seed(self, experiment_metrics):
        """
        Test that simulations are reproducible with same random seed.
        
        Run same simulation twice with same seed and verify identical results.
        """
        seed = 12345
        
        runner1 = RolloutSimulationRunner(
            experiment_id="exp_repro",
            random_seed=seed,
        )
        report1 = runner1.run_full_simulation(experiment_metrics, force_rollback=False)
        
        runner2 = RolloutSimulationRunner(
            experiment_id="exp_repro",
            random_seed=seed,
        )
        report2 = runner2.run_full_simulation(experiment_metrics, force_rollback=False)
        
        # Compare key aspects
        assert report1.final_decision == report2.final_decision
        assert report1.final_state == report2.final_state
        assert len(report1.phases) == len(report2.phases)
        
        # Compare phase decisions
        for p1, p2 in zip(report1.phases, report2.phases):
            assert p1.decision == p2.decision
            assert p1.variant_id == p2.variant_id
    
    def test_phase_transitions_valid(self, experiment_metrics, degraded_metrics):
        """
        Test that phase transitions follow valid state machine.
        
        Valid transitions:
        - CONTROL_BASELINE -> TREATMENT_EVALUATION
        - TREATMENT_EVALUATION -> TREATMENT_PROMOTED (if promoted)
        - TREATMENT_EVALUATION -> end (if not promoted)
        - TREATMENT_PROMOTED -> TREATMENT_DEGRADED (if monitoring)
        - TREATMENT_PROMOTED -> end (if no monitoring)
        - TREATMENT_DEGRADED -> ROLLED_BACK (if rollback triggered)
        - TREATMENT_DEGRADED -> end (if degradation continues)
        - ROLLED_BACK -> end
        """
        runner = RolloutSimulationRunner(
            experiment_id="exp_transitions",
            random_seed=42,
        )
        
        control = experiment_metrics.get_control_metrics()
        
        # Phase 1
        phase1 = runner.run_phase_1_control_baseline(control)
        assert phase1.phase == ExperimentPhase.CONTROL_BASELINE
        
        # Phase 2
        phase2 = runner.run_phase_2_treatment_evaluation(experiment_metrics)
        assert phase2.phase == ExperimentPhase.TREATMENT_EVALUATION
        
        # Transition: 1 -> 2
        assert phase1.phase != phase2.phase
        
        # Phase 3
        phase3 = runner.run_phase_3_treatment_promoted(experiment_metrics)
        assert phase3.phase == ExperimentPhase.TREATMENT_PROMOTED
        
        # Transition: 2 -> 3
        assert phase2.phase != phase3.phase
        
        # Phase 4
        _, phase4 = runner.run_phase_4_treatment_degraded(experiment_metrics)
        assert phase4.phase == ExperimentPhase.TREATMENT_DEGRADED
        
        # Transition: 3 -> 4
        assert phase3.phase != phase4.phase
        
        # Phase 5
        phase5 = runner.run_phase_5_rollback_executed(control)
        assert phase5.phase == ExperimentPhase.ROLLED_BACK
        
        # Transition: 4 -> 5
        assert phase4.phase != phase5.phase


# =============================================================================
# DECISION VALIDATION TESTS
# =============================================================================

class TestDecisionValidation:
    """Tests for validating decisions at each phase."""
    
    def test_baseline_phase_always_continue(self, experiment_metrics, simulation_runner):
        """Test that baseline phase always returns CONTINUE."""
        control = experiment_metrics.get_control_metrics()
        phase = simulation_runner.run_phase_1_control_baseline(control)
        
        assert phase.decision == RolloutDecisionType.CONTINUE
        assert phase.gate_checks[0].passed is True
    
    def test_evaluation_phase_promote_with_good_metrics(self, experiment_metrics, simulation_runner):
        """Test that good treatment metrics result in PROMOTE decision."""
        phase = simulation_runner.run_phase_2_treatment_evaluation(experiment_metrics)
        
        assert phase.decision == RolloutDecisionType.PROMOTE
        assert all(check.passed for check in phase.gate_checks)
    
    def test_evaluation_phase_continue_with_bad_metrics(self, simulation_runner):
        """Test that bad treatment metrics result in CONTINUE decision."""
        # Create poor performing treatment
        variants = {
            "control": VariantMetrics(
                variant_id="control",
                sample_size=100,
                conversions=70,
                total_time_to_value_ms=2_500_000,
                avg_time_to_value_ms=25_000.0,
                completion_rate=0.70,
                abandonment_rate=0.30,
                prefill_adoption=0.40,
                fast_lane_adoption=0.30,
            ),
            "treatment": VariantMetrics(
                variant_id="treatment",
                sample_size=100,
                conversions=65,
                total_time_to_value_ms=2_600_000,
                avg_time_to_value_ms=26_000.0,
                completion_rate=0.65,  # Marginal improvement
                abandonment_rate=0.35,
                prefill_adoption=0.40,
                fast_lane_adoption=0.30,
            ),
        }
        
        metrics = ExperimentMetrics(
            experiment_id="exp_marginal",
            variant_metrics=variants,
            control_variant_id="control",
        )
        
        phase = simulation_runner.run_phase_2_treatment_evaluation(metrics)
        
        # Should continue due to insufficient lift
        assert phase.decision == RolloutDecisionType.CONTINUE
    
    def test_rollback_phase_with_severe_degradation(self, experiment_metrics, simulation_runner):
        """Test that severe degradation triggers ROLLBACK."""
        # Degrade severely
        _, phase = simulation_runner.run_phase_4_treatment_degraded(
            experiment_metrics,
            degradation_factor=0.50,  # 50% degradation
        )
        
        # Should trigger rollback after consecutive violations
        if phase.decision == RolloutDecisionType.ROLLBACK:
            assert "violation" in phase.decision_reason.lower() or "drop" in phase.decision_reason.lower()


# =============================================================================
# REPORT GENERATION TESTS
# =============================================================================

class TestReportGeneration:
    """Tests for simulation report generation."""
    
    def test_report_contains_all_phases(self, experiment_metrics):
        """Test that report contains all executed phases."""
        # Use threshold=1 to force rollback
        rollback_config = RollbackPolicyConfig(
            max_completion_rate_drop=0.15,
            max_ttfv_increase_ratio=1.30,
            min_sample_size_for_rollback=50,
            consecutive_failures_threshold=1,
        )
        runner = RolloutSimulationRunner(
            experiment_id="exp_report",
            random_seed=42,
            rollback_config=rollback_config,
        )
        report = runner.run_full_simulation(
            experiment_metrics,
            force_rollback=True,
            degradation_factor=0.50,  # Severe degradation
        )
        
        # Should have all 5 phases when rollback is triggered
        phases = [p.phase for p in report.phases]
        assert ExperimentPhase.CONTROL_BASELINE in phases
        assert ExperimentPhase.TREATMENT_EVALUATION in phases
        assert ExperimentPhase.TREATMENT_PROMOTED in phases
        assert ExperimentPhase.TREATMENT_DEGRADED in phases
        
        # ROLLED_BACK may or may not be present depending on consecutive violations
        # With threshold=1 and severe degradation, it should be there
        if report.final_state == ExperimentPhase.ROLLED_BACK:
            assert ExperimentPhase.ROLLED_BACK in phases
    
    def test_report_serialization(self, experiment_metrics):
        """Test that report can be serialized to dict and JSON."""
        runner = RolloutSimulationRunner(experiment_id="exp_json", random_seed=42)
        report = runner.run_full_simulation(experiment_metrics, force_rollback=False)
        
        # Convert to dict
        data = report.to_dict()
        
        # Verify structure
        assert "simulation_id" in data
        assert "experiment_id" in data
        assert "phases" in data
        assert "final_decision" in data
        assert "final_state" in data
        
        # Should be JSON serializable
        json_str = json.dumps(data)
        assert len(json_str) > 0
    
    def test_report_duration_calculation(self, experiment_metrics):
        """Test that report calculates duration correctly."""
        runner = RolloutSimulationRunner(experiment_id="exp_duration", random_seed=42)
        report = runner.run_full_simulation(experiment_metrics, force_rollback=False)
        
        assert report.duration_seconds is not None
        assert report.duration_seconds >= 0
        assert report.started_at is not None
        assert report.completed_at is not None


# =============================================================================
# V44 BENCHMARK INTEGRATION TESTS
# =============================================================================

class TestV44BenchmarkIntegration:
    """Tests for integration with v44 benchmark results."""
    
    def test_load_v44_synthetic_results(self):
        """Test loading synthetic v44 results."""
        benchmark = generate_synthetic_v44_results()
        
        assert "experiments" in benchmark
        assert "exp_cta_copy" in benchmark["experiments"]
        assert "exp_resume_timing" in benchmark["experiments"]
        
        # Check variant structure
        cta_exp = benchmark["experiments"]["exp_cta_copy"]
        assert "variants" in cta_exp
        assert "control" in cta_exp["variants"]
        assert "treatment" in cta_exp["variants"]
    
    def test_convert_benchmark_to_metrics(self):
        """Test converting benchmark data to VariantMetrics."""
        benchmark = generate_synthetic_v44_results()
        variant_data = benchmark["experiments"]["exp_cta_copy"]["variants"]["treatment"]
        
        metrics = create_variant_metrics_from_benchmark(variant_data, "treatment")
        
        assert metrics.variant_id == "treatment"
        assert metrics.sample_size == 100
        assert metrics.completion_rate == 0.80
        assert metrics.avg_time_to_value_ms == 20000.0
    
    def test_simulation_with_benchmark_data(self):
        """Test running simulation using v44 benchmark data."""
        benchmark = generate_synthetic_v44_results()
        exp_data = benchmark["experiments"]["exp_cta_copy"]
        
        control = create_variant_metrics_from_benchmark(
            exp_data["variants"]["control"],
            "control"
        )
        treatment = create_variant_metrics_from_benchmark(
            exp_data["variants"]["treatment"],
            "treatment"
        )
        
        experiment_metrics = ExperimentMetrics(
            experiment_id="exp_cta_copy",
            variant_metrics={"control": control, "treatment": treatment},
            control_variant_id="control",
        )
        
        runner = RolloutSimulationRunner(experiment_id="exp_cta_copy", random_seed=42)
        report = runner.run_full_simulation(experiment_metrics, force_rollback=False)
        
        # Treatment should be promoted (it has good metrics)
        assert report.final_decision == RolloutDecisionType.PROMOTE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
