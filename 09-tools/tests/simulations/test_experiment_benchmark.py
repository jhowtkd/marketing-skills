"""v44 Experiment Benchmark Tests.

Tests for the ExperimentBenchmarkRunner and related functionality.
"""

import json
import pytest
from pathlib import Path

from tests.simulations.v44_experiment_benchmark import (
    ExperimentBenchmarkRunner,
    BenchmarkConfig,
    generate_experiment_report,
    EXP_CTA_COPY,
    EXP_RESUME_TIMING,
)
from tests.simulations.onboarding_simulation_runner import (
    OnboardingSimulator,
    SimulationConfig,
    VariantConfig,
    JourneyType,
)


class TestExperimentBenchmarkRunner:
    """Test suite for ExperimentBenchmarkRunner."""
    
    def test_runner_initialization(self):
        """Test runner initializes with correct defaults."""
        config = BenchmarkConfig(
            simulations_per_variant=10,
            fast_test_mode=True,
            random_seed=42,
        )
        runner = ExperimentBenchmarkRunner(config)
        
        assert runner.config.simulations_per_variant == 10
        assert runner.config.fast_test_mode is True
        assert runner.config.random_seed == 42
        assert runner.results == {}
    
    def test_runner_reproducibility(self):
        """Test that same seed produces same results."""
        config = BenchmarkConfig(
            simulations_per_variant=5,
            fast_test_mode=True,
            random_seed=123,
        )
        
        # First run
        runner1 = ExperimentBenchmarkRunner(config)
        results1 = runner1.run_experiment(EXP_CTA_COPY)
        
        # Second run with same seed
        runner2 = ExperimentBenchmarkRunner(config)
        results2 = runner2.run_experiment(EXP_CTA_COPY)
        
        # Results should be identical
        for variant_id in results1:
            stats1 = results1[variant_id].stats
            stats2 = results2[variant_id].stats
            assert stats1["avg_ttfv_ms"] == stats2["avg_ttfv_ms"]
            assert stats1["completion_rate"] == stats2["completion_rate"]
    
    def test_run_single_experiment(self):
        """Test running a single experiment."""
        config = BenchmarkConfig(
            simulations_per_variant=5,
            fast_test_mode=True,
            random_seed=42,
        )
        runner = ExperimentBenchmarkRunner(config)
        
        results = runner.run_experiment(EXP_CTA_COPY)
        
        # Should have both variants
        assert "control" in results
        assert "treatment" in results
        
        # Each should have correct sample size
        assert len(results["control"].metrics_list) == 5
        assert len(results["treatment"].metrics_list) == 5
        
        # Each result should have experiment_id and variant_id
        for variant_id, result in results.items():
            assert result.experiment_id == "exp_cta_copy"
            assert result.variant_id == variant_id
    
    def test_run_all_experiments(self):
        """Test running all predefined experiments."""
        config = BenchmarkConfig(
            simulations_per_variant=3,
            fast_test_mode=True,
            random_seed=42,
        )
        runner = ExperimentBenchmarkRunner(config)
        
        results = runner.run_all_experiments()
        
        # Should have both experiments
        assert "exp_cta_copy" in results
        assert "exp_resume_timing" in results
        
        # Each should have its variants
        assert "control" in results["exp_cta_copy"]
        assert "treatment" in results["exp_cta_copy"]
        assert "control" in results["exp_resume_timing"]
        assert "delay_2s" in results["exp_resume_timing"]
    
    def test_get_variant_comparison(self):
        """Test getting variant comparison data."""
        config = BenchmarkConfig(
            simulations_per_variant=5,
            fast_test_mode=True,
            random_seed=42,
        )
        runner = ExperimentBenchmarkRunner(config)
        runner.run_experiment(EXP_CTA_COPY)
        
        comparison = runner.get_variant_comparison("exp_cta_copy")
        
        # Should have comparison for both variants
        assert len(comparison) == 2
        
        # Should be sorted by score descending
        assert comparison[0]["score"] >= comparison[1]["score"]
        
        # Each item should have required fields
        for item in comparison:
            assert "variant_id" in item
            assert "experiment_id" in item
            assert "sample_size" in item
            assert "ttfv_avg_ms" in item
            assert "completion_rate" in item
            assert "abandonment_rate" in item
            assert "score" in item
    
    def test_variant_comparison_empty(self):
        """Test getting comparison for non-existent experiment."""
        runner = ExperimentBenchmarkRunner()
        comparison = runner.get_variant_comparison("non_existent")
        assert comparison == []


class TestExperimentReport:
    """Test suite for report generation."""
    
    def test_generate_json_report(self, tmp_path):
        """Test JSON report generation."""
        config = BenchmarkConfig(
            simulations_per_variant=3,
            fast_test_mode=True,
            random_seed=42,
        )
        runner = ExperimentBenchmarkRunner(config)
        results = runner.run_all_experiments()
        
        report_paths = generate_experiment_report(results, str(tmp_path))
        
        # Check files exist
        assert Path(report_paths["json"]).exists()
        assert Path(report_paths["markdown"]).exists()
        
        # Load and validate JSON
        with open(report_paths["json"]) as f:
            data = json.load(f)
        
        assert "generated_at" in data
        assert "version" in data
        assert data["version"] == "v44"
        assert "methodology" in data
        assert "experiments" in data
        assert "ranking" in data
        
        # Check experiments
        assert "exp_cta_copy" in data["experiments"]
        assert "exp_resume_timing" in data["experiments"]
        
        # Check ranking
        assert len(data["ranking"]) > 0
        assert data["ranking"][0]["rank"] == 1
    
    def test_generate_markdown_report(self, tmp_path):
        """Test Markdown report generation."""
        config = BenchmarkConfig(
            simulations_per_variant=3,
            fast_test_mode=True,
            random_seed=42,
        )
        runner = ExperimentBenchmarkRunner(config)
        results = runner.run_all_experiments()
        
        report_paths = generate_experiment_report(results, str(tmp_path))
        
        # Load and validate Markdown
        with open(report_paths["markdown"]) as f:
            content = f.read()
        
        assert "# v44 Experiment Benchmark Report" in content
        assert "## 🏆 Global Ranking" in content
        assert "## 🔬 Experiment Details" in content
        assert "exp_cta_copy" in content
        assert "exp_resume_timing" in content


class TestVariantConfigIntegration:
    """Test suite for VariantConfig integration with simulator."""
    
    def test_variant_config_applied_to_metrics(self):
        """Test that variant config is applied to journey metrics."""
        variant_config = VariantConfig(
            experiment_id="test_exp",
            variant_id="test_variant",
            cta_copy="Test CTA",
            prefill_enabled=True,
        )
        
        sim_config = SimulationConfig(
            fast_test_mode=True,
            variant_config=variant_config,
        )
        simulator = OnboardingSimulator(sim_config)
        
        metrics = simulator.run_simulation(JourneyType.HAPPY_PATH, "test_user")
        
        assert metrics.experiment_id == "test_exp"
        assert metrics.variant_id == "test_variant"
    
    def test_variant_config_no_prefill(self):
        """Test that prefill can be disabled via variant config."""
        variant_config = VariantConfig(
            experiment_id="test_exp",
            variant_id="no_prefill",
            prefill_enabled=False,
        )
        
        sim_config = SimulationConfig(
            fast_test_mode=True,
            variant_config=variant_config,
            prefill_probability=1.0,  # Would normally always use prefill
        )
        simulator = OnboardingSimulator(sim_config)
        
        # Run multiple times to ensure prefill is never used
        for i in range(10):
            metrics = simulator.run_simulation(JourneyType.HAPPY_PATH, f"user_{i}")
            assert metrics.prefill_used is False
    
    def test_fallback_to_control(self):
        """Test fallback behavior when variant config is not provided."""
        sim_config = SimulationConfig(
            fast_test_mode=True,
            variant_config=None,
        )
        simulator = OnboardingSimulator(sim_config)
        
        metrics = simulator.run_simulation(JourneyType.HAPPY_PATH, "test_user")
        
        # Should run without errors, with None experiment/variant IDs
        assert metrics.experiment_id is None
        assert metrics.variant_id is None
        # Should still complete successfully
        assert metrics.completed is True


class TestFastTestMode:
    """Test suite for fast test mode behavior."""
    
    def test_fast_mode_speed(self):
        """Test that fast mode actually runs quickly."""
        import time
        
        config = BenchmarkConfig(
            simulations_per_variant=10,
            fast_test_mode=True,
            random_seed=42,
        )
        runner = ExperimentBenchmarkRunner(config)
        
        start = time.time()
        runner.run_experiment(EXP_CTA_COPY)
        elapsed = time.time() - start
        
        # Should complete in under 1 second with fast mode
        assert elapsed < 1.0, f"Fast mode took too long: {elapsed:.2f}s"


class TestExperimentDefinitions:
    """Test suite for predefined experiment definitions."""
    
    def test_cta_copy_experiment_structure(self):
        """Test CTA copy experiment has correct structure."""
        assert EXP_CTA_COPY["experiment_id"] == "exp_cta_copy"
        assert "control" in EXP_CTA_COPY["variants"]
        assert "treatment" in EXP_CTA_COPY["variants"]
        
        control = EXP_CTA_COPY["variants"]["control"]
        assert control.cta_copy == "Continuar"
        assert control.experiment_id == "exp_cta_copy"
        
        treatment = EXP_CTA_COPY["variants"]["treatment"]
        assert treatment.cta_copy == "Configurar Agora"
        assert treatment.variant_id == "treatment"
    
    def test_resume_timing_experiment_structure(self):
        """Test resume timing experiment has correct structure."""
        assert EXP_RESUME_TIMING["experiment_id"] == "exp_resume_timing"
        assert "control" in EXP_RESUME_TIMING["variants"]
        assert "delay_2s" in EXP_RESUME_TIMING["variants"]
        
        control = EXP_RESUME_TIMING["variants"]["control"]
        assert control.resume_delay_ms == 0
        
        delay = EXP_RESUME_TIMING["variants"]["delay_2s"]
        assert delay.resume_delay_ms == 2000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
