"""v44 Experiment Benchmark - Comparative A/B Testing Harness.

This module provides a benchmark framework for comparing experiment variants
across multiple simulations with reproducible results.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from tests.simulations.onboarding_simulation_runner import (
    OnboardingSimulator,
    JourneyType,
    SimulationConfig,
    VariantConfig,
    JourneyMetrics,
    calculate_statistics,
)


# =============================================================================
# EXPERIMENT CONFIGURATIONS
# =============================================================================

# Experimento 1: CTA Copy Variation
EXP_CTA_COPY = {
    "experiment_id": "exp_cta_copy",
    "name": "CTA Copy Test",
    "description": "Testa mudança de copy do CTA principal de 'Continuar' para 'Configurar Agora'",
    "hypothesis": "Copy mais específica ('Configurar Agora') aumenta completion rate",
    "variants": {
        "control": VariantConfig(
            experiment_id="exp_cta_copy",
            variant_id="control",
            cta_copy="Continuar",
        ),
        "treatment": VariantConfig(
            experiment_id="exp_cta_copy",
            variant_id="treatment",
            cta_copy="Configurar Agora",
        ),
    }
}

# Experimento 2: Resume Timing
EXP_RESUME_TIMING = {
    "experiment_id": "exp_resume_timing",
    "name": "Resume Prompt Timing",
    "description": "Testa delay no prompt de resume para reduzir cognitive load",
    "hypothesis": "Delay de 2s no resume prompt melhora decisão do usuário",
    "variants": {
        "control": VariantConfig(
            experiment_id="exp_resume_timing",
            variant_id="control",
            resume_delay_ms=0,
        ),
        "delay_2s": VariantConfig(
            experiment_id="exp_resume_timing",
            variant_id="delay_2s",
            resume_delay_ms=2000,
        ),
    }
}


@dataclass
class ExperimentResult:
    """Results from a single experiment run."""
    experiment_id: str
    variant_id: str
    metrics_list: List[JourneyMetrics] = field(default_factory=list)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Calculate statistics from metrics."""
        return calculate_statistics(self.metrics_list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "sample_size": len(self.metrics_list),
            "stats": self.stats,
            "metrics": [m.to_dict() for m in self.metrics_list],
        }


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""
    simulations_per_variant: int = 30
    fast_test_mode: bool = True
    random_seed: Optional[int] = 42
    journey_type: JourneyType = JourneyType.HAPPY_PATH
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulations_per_variant": self.simulations_per_variant,
            "fast_test_mode": self.fast_test_mode,
            "random_seed": self.random_seed,
            "journey_type": self.journey_type.value,
        }


class ExperimentBenchmarkRunner:
    """Runner for experiment benchmarks with reproducible results."""
    
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.results: Dict[str, Dict[str, ExperimentResult]] = {}
        self._set_random_seed()
        
    def _set_random_seed(self) -> None:
        """Set random seed for reproducibility."""
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)
    
    def run_experiment(
        self,
        experiment_def: Dict[str, Any],
        journey_type: Optional[JourneyType] = None,
    ) -> Dict[str, ExperimentResult]:
        """Run a single experiment with all its variants.
        
        Args:
            experiment_def: Experiment definition with variants
            journey_type: Type of journey to simulate (default from config)
            
        Returns:
            Dict mapping variant_id to ExperimentResult
        """
        experiment_id = experiment_def["experiment_id"]
        variants = experiment_def["variants"]
        journey_type = journey_type or self.config.journey_type
        
        print(f"\n🧪 Running experiment: {experiment_def['name']}")
        print(f"   Hypothesis: {experiment_def['hypothesis']}")
        print(f"   Variants: {list(variants.keys())}")
        
        results = {}
        
        for variant_id, variant_config in variants.items():
            print(f"\n   ▶️  Variant '{variant_id}': ", end="", flush=True)
            
            # Create simulator with variant config
            sim_config = SimulationConfig(
                fast_test_mode=self.config.fast_test_mode,
                variant_config=variant_config,
            )
            simulator = OnboardingSimulator(sim_config)
            
            # Run simulations
            metrics_list = []
            for i in range(self.config.simulations_per_variant):
                user_id = f"{experiment_id}_{variant_id}_user_{i}"
                metrics = simulator.run_simulation(journey_type, user_id)
                metrics_list.append(metrics)
            
            # Create result
            result = ExperimentResult(
                experiment_id=experiment_id,
                variant_id=variant_id,
                metrics_list=metrics_list,
            )
            results[variant_id] = result
            
            stats = result.stats
            print(f"✓ n={len(metrics_list)}, TTFV={stats['avg_ttfv_ms']:.0f}ms, "
                  f"completion={stats['completion_rate']:.1%}")
        
        self.results[experiment_id] = results
        return results
    
    def run_all_experiments(
        self,
        experiments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Dict[str, ExperimentResult]]:
        """Run all defined experiments.
        
        Args:
            experiments: List of experiment definitions (default: all predefined)
            
        Returns:
            Dict mapping experiment_id to variant results
        """
        if experiments is None:
            experiments = [EXP_CTA_COPY, EXP_RESUME_TIMING]
        
        print("=" * 70)
        print("v44 Experiment Benchmark Runner")
        print("=" * 70)
        print(f"Config: {self.config.simulations_per_variant} sims/variant, "
              f"seed={self.config.random_seed}, fast_mode={self.config.fast_test_mode}")
        
        for exp in experiments:
            self.run_experiment(exp)
        
        return self.results
    
    def get_variant_comparison(
        self,
        experiment_id: str,
    ) -> List[Dict[str, Any]]:
        """Get comparison data for an experiment's variants.
        
        Args:
            experiment_id: ID of the experiment
            
        Returns:
            List of variant comparison data sorted by score
        """
        if experiment_id not in self.results:
            return []
        
        comparison = []
        results = self.results[experiment_id]
        
        # Get control/baseline stats for relative scoring
        control_result = results.get("control") or results.get("baseline")
        control_ttfv = control_result.stats["avg_ttfv_ms"] if control_result else 25000
        
        for variant_id, result in results.items():
            stats = result.stats
            
            # Calculate score similar to v42
            ttfv_efficiency = control_ttfv / max(stats["avg_ttfv_ms"], 1)
            completion = stats["completion_rate"]
            abandonment = 1.0 - completion
            
            # Weighted score (higher is better)
            score = (
                0.50 * ttfv_efficiency +
                0.35 * completion +
                0.15 * (1.0 - abandonment)
            )
            
            comparison.append({
                "variant_id": variant_id,
                "experiment_id": experiment_id,
                "sample_size": len(result.metrics_list),
                "ttfv_avg_ms": stats["avg_ttfv_ms"],
                "ttfv_min_ms": stats["min_ttfv_ms"],
                "ttfv_max_ms": stats["max_ttfv_ms"],
                "completion_rate": stats["completion_rate"],
                "abandonment_rate": abandonment,
                "prefill_adoption": stats["prefill_adoption"],
                "fast_lane_adoption": stats["fast_lane_adoption"],
                "score": round(score, 4),
            })
        
        # Sort by score descending
        comparison.sort(key=lambda x: x["score"], reverse=True)
        return comparison


def generate_experiment_report(
    results: Dict[str, Dict[str, ExperimentResult]],
    output_dir: str = "reports",
) -> Dict[str, str]:
    """Generate JSON and Markdown reports from benchmark results.
    
    Args:
        results: Benchmark results from ExperimentBenchmarkRunner
        output_dir: Directory to save reports
        
    Returns:
        Dict with paths to generated files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Build report data
    report_data = {
        "generated_at": datetime.utcnow().isoformat(),
        "version": "v44",
        "methodology": {
            "simulations_per_variant": 30,
            "score_formula": "0.50*TTFV_efficiency + 0.35*completion + 0.15*(1-abandonment)",
            "random_seed": 42,
        },
        "experiments": {},
        "ranking": [],
    }
    
    # Process each experiment
    all_rankings = []
    for experiment_id, variant_results in results.items():
        experiment_data = {
            "variants": {},
            "comparison": [],
        }
        
        # Get control for baseline
        control = variant_results.get("control") or variant_results.get("baseline")
        control_ttfv = control.stats["avg_ttfv_ms"] if control else 25000
        
        for variant_id, result in variant_results.items():
            stats = result.stats
            
            # Calculate metrics
            ttfv_efficiency = control_ttfv / max(stats["avg_ttfv_ms"], 1)
            completion = stats["completion_rate"]
            abandonment = 1.0 - completion
            
            score = (
                0.50 * ttfv_efficiency +
                0.35 * completion +
                0.15 * (1.0 - abandonment)
            )
            
            variant_data = {
                "sample_size": len(result.metrics_list),
                "ttfv_avg_ms": round(stats["avg_ttfv_ms"], 2),
                "ttfv_avg_s": round(stats["avg_ttfv_ms"] / 1000, 2),
                "ttfv_min_ms": stats["min_ttfv_ms"],
                "ttfv_max_ms": stats["max_ttfv_ms"],
                "completion_rate": round(stats["completion_rate"], 4),
                "abandonment_rate": round(abandonment, 4),
                "prefill_adoption": round(stats["prefill_adoption"], 4),
                "fast_lane_adoption": round(stats["fast_lane_adoption"], 4),
                "score": round(score, 4),
            }
            
            experiment_data["variants"][variant_id] = variant_data
            
            # Add to global ranking
            all_rankings.append({
                "experiment_id": experiment_id,
                "variant_id": variant_id,
                "score": round(score, 4),
                "ttfv_avg_s": round(stats["avg_ttfv_ms"] / 1000, 2),
                "completion_rate": round(stats["completion_rate"], 4),
            })
        
        # Generate comparison ranking for this experiment
        comparison = [
            {
                "rank": i + 1,
                "variant_id": v_id,
                **experiment_data["variants"][v_id],
            }
            for i, (v_id, _) in enumerate(
                sorted(
                    experiment_data["variants"].items(),
                    key=lambda x: x[1]["score"],
                    reverse=True,
                )
            )
        ]
        experiment_data["comparison"] = comparison
        report_data["experiments"][experiment_id] = experiment_data
    
    # Global ranking across all experiments
    all_rankings.sort(key=lambda x: x["score"], reverse=True)
    report_data["ranking"] = [
        {"rank": i + 1, **r}
        for i, r in enumerate(all_rankings)
    ]
    
    # Save JSON report
    json_path = output_path / "v44_experiment_report.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)
    
    # Generate Markdown report
    md_content = _generate_markdown_report(report_data)
    md_path = output_path / "v44_experiment_report.md"
    with open(md_path, "w") as f:
        f.write(md_content)
    
    return {
        "json": str(json_path),
        "markdown": str(md_path),
    }


def _generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """Generate Markdown content from report data."""
    
    md = f"""# v44 Experiment Benchmark Report

**Generated:** {report_data['generated_at']}  
**Version:** {report_data['version']}

---

## 📊 Methodology

- **Simulations per variant:** {report_data['methodology']['simulations_per_variant']}
- **Score Formula:** `{report_data['methodology']['score_formula']}`
- **Random Seed:** {report_data['methodology']['random_seed']} (for reproducibility)

---

## 🏆 Global Ranking

| Rank | Experiment | Variant | Score | TTFV | Completion |
|------|------------|---------|-------|------|------------|
"""
    
    for item in report_data['ranking']:
        md += (f"| {item['rank']} | {item['experiment_id']} | {item['variant_id']} | "
               f"{item['score']:.4f} | {item['ttfv_avg_s']:.2f}s | "
               f"{item['completion_rate']*100:.1f}% |\n")
    
    # Per-experiment details
    md += "\n---\n\n## 🔬 Experiment Details\n"
    
    for exp_id, exp_data in report_data['experiments'].items():
        md += f"\n### {exp_id}\n\n"
        md += "| Variant | Score | TTFV | Completion | Abandonment | Prefill | Fast Lane |\n"
        md += "|---------|-------|------|------------|-------------|---------|-----------|\n"
        
        for comp in exp_data['comparison']:
            v = comp['variant_id']
            md += (f"| {v} | {comp['score']:.4f} | {comp['ttfv_avg_s']:.2f}s | "
                   f"{comp['completion_rate']*100:.1f}% | {comp['abandonment_rate']*100:.1f}% | "
                   f"{comp['prefill_adoption']*100:.1f}% | {comp['fast_lane_adoption']*100:.1f}% |\n")
    
    md += f"""

---

## 📝 Summary

Total experiments: {len(report_data['experiments'])}  
Total variants tested: {len(report_data['ranking'])}  
Best performing: {report_data['ranking'][0]['experiment_id']}/{report_data['ranking'][0]['variant_id']} (score: {report_data['ranking'][0]['score']:.4f})

---
*Generated by v44 Experiment Benchmark Runner*
"""
    
    return md


def main():
    """Main entry point for benchmark."""
    # Create runner with default config
    config = BenchmarkConfig(
        simulations_per_variant=30,
        fast_test_mode=True,
        random_seed=42,
    )
    
    runner = ExperimentBenchmarkRunner(config)
    
    # Run all experiments
    results = runner.run_all_experiments()
    
    # Generate reports
    report_paths = generate_experiment_report(results)
    
    print("\n" + "=" * 70)
    print("📊 BENCHMARK COMPLETE")
    print("=" * 70)
    
    # Print global ranking
    print("\n🏆 Global Ranking:")
    for exp_id, exp_results in results.items():
        comparison = runner.get_variant_comparison(exp_id)
        print(f"\n  {exp_id}:")
        for i, variant in enumerate(comparison):
            winner = "✓" if i == 0 else " "
            print(f"    [{winner}] {variant['variant_id']}: "
                  f"score={variant['score']:.4f}, "
                  f"ttfv={variant['ttfv_avg_ms']:.0f}ms, "
                  f"completion={variant['completion_rate']:.1%}")
    
    print(f"\n📁 Reports generated:")
    print(f"   - {report_paths['json']}")
    print(f"   - {report_paths['markdown']}")
    print()
    
    return results, report_paths


if __name__ == "__main__":
    main()
