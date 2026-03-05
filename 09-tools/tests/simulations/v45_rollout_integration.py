"""v45 Rollout Integration Simulation - End-to-End Promotion/Rollback Scenarios.

This module provides a complete end-to-end simulation of:
- Fase 1: Control rodando (baseline)
- Fase 2: Treatment avaliado (promoção válida)
- Fase 3: Treatment promovido
- Fase 4: Treatment degrada (rollback)
- Fase 5: Rollback executado, volta para control

Uses v44 experiment benchmark results as input.
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import simulation models
from tests.simulations.simulation_models import (
    ExperimentMetrics,
    ExperimentPhase,
    GateCheck,
    JourneyMetrics,
    PhaseResult,
    PromotionPolicyConfig,
    RollbackPolicyConfig,
    RolloutDecisionType,
    SimulationReport,
    VariantMetrics,
)

# Import engines
from tests.simulations.rollout_engines import (
    PromotionEngine,
    RollbackEngine,
    PolicyPersistence,
)

# Import benchmark data structures
from tests.simulations.onboarding_simulation_runner import (
    JourneyType,
    SimulationConfig,
    VariantConfig,
    OnboardingSimulator,
    calculate_statistics,
)


def load_v44_benchmark_results() -> Optional[Dict[str, Any]]:
    """Load v44 experiment benchmark results if available."""
    report_path = Path("reports/v44_experiment_report.json")
    if report_path.exists():
        with open(report_path, "r") as f:
            return json.load(f)
    return None


def generate_synthetic_v44_results() -> Dict[str, Any]:
    """Generate synthetic v44-style results for simulation."""
    return {
        "experiments": {
            "exp_cta_copy": {
                "variants": {
                    "control": {
                        "sample_size": 100,
                        "ttfv_avg_ms": 25000.0,
                        "completion_rate": 0.70,
                        "abandonment_rate": 0.30,
                        "prefill_adoption": 0.40,
                        "fast_lane_adoption": 0.30,
                        "score": 0.75,
                    },
                    "treatment": {
                        "sample_size": 100,
                        "ttfv_avg_ms": 20000.0,
                        "completion_rate": 0.80,
                        "abandonment_rate": 0.20,
                        "prefill_adoption": 0.45,
                        "fast_lane_adoption": 0.35,
                        "score": 0.85,
                    },
                }
            },
            "exp_resume_timing": {
                "variants": {
                    "control": {
                        "sample_size": 100,
                        "ttfv_avg_ms": 26000.0,
                        "completion_rate": 0.68,
                        "abandonment_rate": 0.32,
                        "prefill_adoption": 0.38,
                        "fast_lane_adoption": 0.28,
                        "score": 0.72,
                    },
                    "delay_2s": {
                        "sample_size": 100,
                        "ttfv_avg_ms": 22000.0,
                        "completion_rate": 0.75,
                        "abandonment_rate": 0.25,
                        "prefill_adoption": 0.42,
                        "fast_lane_adoption": 0.32,
                        "score": 0.80,
                    },
                }
            }
        }
    }


def create_variant_metrics_from_benchmark(
    variant_data: Dict[str, Any],
    variant_id: str,
) -> VariantMetrics:
    """Create VariantMetrics from benchmark data."""
    return VariantMetrics(
        variant_id=variant_id,
        sample_size=variant_data["sample_size"],
        conversions=int(variant_data["sample_size"] * variant_data["completion_rate"]),
        total_time_to_value_ms=int(variant_data["sample_size"] * variant_data["ttfv_avg_ms"]),
        avg_time_to_value_ms=variant_data["ttfv_avg_ms"],
        completion_rate=variant_data["completion_rate"],
        abandonment_rate=variant_data["abandonment_rate"],
        prefill_adoption=variant_data["prefill_adoption"],
        fast_lane_adoption=variant_data["fast_lane_adoption"],
    )


class RolloutSimulationRunner:
    """Runner for end-to-end rollout simulations."""
    
    def __init__(
        self,
        experiment_id: str,
        promotion_config: Optional[PromotionPolicyConfig] = None,
        rollback_config: Optional[RollbackPolicyConfig] = None,
        random_seed: int = 42,
    ):
        self.experiment_id = experiment_id
        self.simulation_id = f"sim_{experiment_id}_{uuid.uuid4().hex[:8]}"
        self.promotion_config = promotion_config or PromotionPolicyConfig()
        self.rollback_config = rollback_config or RollbackPolicyConfig()
        self.random_seed = random_seed
        
        # Set random seed for reproducibility
        random.seed(random_seed)
        
        # Initialize engines
        self.promotion_engine = PromotionEngine(self.promotion_config)
        self.rollback_engine = RollbackEngine(self.rollback_config)
        
        # Initialize report
        self.report = SimulationReport(
            simulation_id=self.simulation_id,
            experiment_id=experiment_id,
            phases=[],
            final_decision=RolloutDecisionType.CONTINUE,
            final_state=ExperimentPhase.CONTROL_BASELINE,
            promotion_policy=self.promotion_config,
            rollback_policy=self.rollback_config,
        )
    
    def run_phase_1_control_baseline(
        self,
        control_metrics: VariantMetrics,
    ) -> PhaseResult:
        """
        Fase 1: Control rodando (baseline).
        
        Establish baseline metrics from control variant.
        """
        print("  📊 Fase 1: Control Baseline")
        print(f"     Sample: {control_metrics.sample_size}, Completion: {control_metrics.completion_rate:.1%}")
        
        # No gates to check - just recording baseline
        gate_checks = [
            GateCheck(
                gate_name="baseline_established",
                passed=True,
                value=float(control_metrics.sample_size),
                threshold=50.0,
                message=f"Baseline established with {control_metrics.sample_size} samples",
            )
        ]
        
        phase_result = PhaseResult(
            phase=ExperimentPhase.CONTROL_BASELINE,
            experiment_id=self.experiment_id,
            variant_id=control_metrics.variant_id,
            metrics=control_metrics,
            gate_checks=gate_checks,
            decision=RolloutDecisionType.CONTINUE,
            decision_reason="Baseline established, ready for treatment evaluation",
        )
        
        self.report.add_phase(phase_result)
        return phase_result
    
    def run_phase_2_treatment_evaluation(
        self,
        experiment_metrics: ExperimentMetrics,
        treatment_id: str = "treatment",
    ) -> PhaseResult:
        """
        Fase 2: Treatment avaliado (promoção válida).
        
        Evaluate treatment against control using promotion engine.
        """
        print("  🧪 Fase 2: Treatment Evaluation")
        
        treatment_metrics = experiment_metrics.get_treatment_metrics(treatment_id)
        if not treatment_metrics:
            raise ValueError(f"Treatment {treatment_id} not found")
        
        print(f"     Sample: {treatment_metrics.sample_size}, Completion: {treatment_metrics.completion_rate:.1%}")
        
        # Run promotion decision
        decision, reason = self.promotion_engine.decide(experiment_metrics, treatment_id)
        
        # Collect gate checks
        gate_checks = [
            self.promotion_engine.check_sample_size_gate(experiment_metrics, treatment_id),
            self.promotion_engine.check_lift_gate(experiment_metrics, treatment_id),
        ]
        
        print(f"     Decision: {decision.value.upper()}")
        print(f"     Reason: {reason}")
        
        phase_result = PhaseResult(
            phase=ExperimentPhase.TREATMENT_EVALUATION,
            experiment_id=self.experiment_id,
            variant_id=treatment_id,
            metrics=treatment_metrics,
            gate_checks=gate_checks,
            decision=decision,
            decision_reason=reason,
        )
        
        self.report.add_phase(phase_result)
        return phase_result
    
    def run_phase_3_treatment_promoted(
        self,
        experiment_metrics: ExperimentMetrics,
        treatment_id: str = "treatment",
    ) -> PhaseResult:
        """
        Fase 3: Treatment promovido.
        
        Treatment has been promoted to production.
        """
        print("  🚀 Fase 3: Treatment Promoted")
        
        treatment_metrics = experiment_metrics.get_treatment_metrics(treatment_id)
        
        print(f"     Treatment {treatment_id} is now live")
        print(f"     Completion: {treatment_metrics.completion_rate:.1%}, TTFV: {treatment_metrics.avg_time_to_value_ms:.0f}ms")
        
        gate_checks = [
            GateCheck(
                gate_name="promotion_successful",
                passed=True,
                value=1.0,
                threshold=1.0,
                message=f"Treatment {treatment_id} successfully promoted",
            )
        ]
        
        phase_result = PhaseResult(
            phase=ExperimentPhase.TREATMENT_PROMOTED,
            experiment_id=self.experiment_id,
            variant_id=treatment_id,
            metrics=treatment_metrics,
            gate_checks=gate_checks,
            decision=RolloutDecisionType.PROMOTE,
            decision_reason="Treatment promoted to production",
        )
        
        self.report.add_phase(phase_result)
        return phase_result
    
    def run_phase_4_treatment_degraded(
        self,
        healthy_metrics: ExperimentMetrics,
        degradation_factor: float = 0.75,
    ) -> Tuple[ExperimentMetrics, PhaseResult]:
        """
        Fase 4: Treatment degrada (rollback).
        
        Simulate treatment degradation by reducing metrics.
        """
        print("  ⚠️  Fase 4: Treatment Degraded")
        
        # Create degraded copy of metrics
        degraded_metrics = ExperimentMetrics(
            experiment_id=healthy_metrics.experiment_id,
            control_variant_id=healthy_metrics.control_variant_id,
            variant_metrics={},
        )
        
        # Copy control metrics (unchanged)
        control = healthy_metrics.get_control_metrics()
        if control:
            degraded_metrics.variant_metrics[control.variant_id] = VariantMetrics(
                variant_id=control.variant_id,
                sample_size=control.sample_size,
                conversions=control.conversions,
                total_time_to_value_ms=control.total_time_to_value_ms,
                avg_time_to_value_ms=control.avg_time_to_value_ms,
                completion_rate=control.completion_rate,
                abandonment_rate=control.abandonment_rate,
                prefill_adoption=control.prefill_adoption,
                fast_lane_adoption=control.fast_lane_adoption,
            )
        
        # Degrade treatment metrics
        treatment = healthy_metrics.get_treatment_metrics()
        if treatment:
            degraded_completion = treatment.completion_rate * degradation_factor
            degraded_ttfv = treatment.avg_time_to_value_ms / degradation_factor
            
            degraded_metrics.variant_metrics[treatment.variant_id] = VariantMetrics(
                variant_id=treatment.variant_id,
                sample_size=treatment.sample_size,
                conversions=int(treatment.sample_size * degraded_completion),
                total_time_to_value_ms=int(treatment.sample_size * degraded_ttfv),
                avg_time_to_value_ms=degraded_ttfv,
                completion_rate=degraded_completion,
                abandonment_rate=1.0 - degraded_completion,
                prefill_adoption=treatment.prefill_adoption * degradation_factor,
                fast_lane_adoption=treatment.fast_lane_adoption * degradation_factor,
            )
            
            print(f"     Degraded completion: {degraded_completion:.1%} (was {treatment.completion_rate:.1%})")
            print(f"     Degraded TTFV: {degraded_ttfv:.0f}ms (was {treatment.avg_time_to_value_ms:.0f}ms)")
        
        # Run rollback check (use the actual treatment variant_id)
        treatment_id = treatment.variant_id if treatment else "treatment"
        decision, reason = self.rollback_engine.decide(degraded_metrics, treatment_id)
        
        gate_checks = [
            self.rollback_engine.check_completion_rate(degraded_metrics, treatment_id),
            self.rollback_engine.check_ttfv_increase(degraded_metrics, treatment_id),
        ]
        
        print(f"     Decision: {decision.value.upper()}")
        print(f"     Reason: {reason}")
        
        treatment_metrics = degraded_metrics.variant_metrics.get(treatment_id)
        phase_result = PhaseResult(
            phase=ExperimentPhase.TREATMENT_DEGRADED,
            experiment_id=self.experiment_id,
            variant_id=treatment_id,
            metrics=treatment_metrics,
            gate_checks=gate_checks,
            decision=decision,
            decision_reason=reason,
        )
        
        self.report.add_phase(phase_result)
        return degraded_metrics, phase_result
    
    def run_phase_5_rollback_executed(
        self,
        control_metrics: VariantMetrics,
    ) -> PhaseResult:
        """
        Fase 5: Rollback executado, volta para control.
        
        System has rolled back to control variant.
        """
        print("  ↩️  Fase 5: Rollback Executed")
        print(f"     Restored control variant: {control_metrics.variant_id}")
        print(f"     Completion: {control_metrics.completion_rate:.1%}, TTFV: {control_metrics.avg_time_to_value_ms:.0f}ms")
        
        gate_checks = [
            GateCheck(
                gate_name="rollback_successful",
                passed=True,
                value=1.0,
                threshold=1.0,
                message=f"Successfully rolled back to {control_metrics.variant_id}",
            )
        ]
        
        phase_result = PhaseResult(
            phase=ExperimentPhase.ROLLED_BACK,
            experiment_id=self.experiment_id,
            variant_id=control_metrics.variant_id,
            metrics=control_metrics,
            gate_checks=gate_checks,
            decision=RolloutDecisionType.ROLLBACK,
            decision_reason="Rollback executed - system restored to control",
        )
        
        self.report.add_phase(phase_result)
        return phase_result
    
    def run_full_simulation(
        self,
        experiment_metrics: ExperimentMetrics,
        force_rollback: bool = True,
        degradation_factor: float = 0.70,
    ) -> SimulationReport:
        """
        Run complete 5-phase simulation.
        
        Args:
            experiment_metrics: Initial experiment metrics
            force_rollback: Whether to simulate degradation and rollback
            degradation_factor: How much to degrade metrics (0.7 = 70% of original)
        """
        print(f"\n{'='*70}")
        print(f"🎬 Starting Rollout Simulation: {self.simulation_id}")
        print(f"   Experiment: {self.experiment_id}")
        print(f"   Random Seed: {self.random_seed}")
        print(f"{'='*70}")
        
        control_metrics = experiment_metrics.get_control_metrics()
        treatment_metrics = experiment_metrics.get_treatment_metrics()
        
        if not control_metrics or not treatment_metrics:
            raise ValueError("Both control and treatment metrics required")
        
        # Phase 1: Control Baseline
        self.run_phase_1_control_baseline(control_metrics)
        
        # Phase 2: Treatment Evaluation
        phase2 = self.run_phase_2_treatment_evaluation(experiment_metrics)
        
        if phase2.decision != RolloutDecisionType.PROMOTE:
            print("\n   ⚠️  Treatment not promoted - simulation ending early")
            self.report.final_decision = phase2.decision
            self.report.final_state = ExperimentPhase.TREATMENT_EVALUATION
            self.report.complete()
            return self.report
        
        # Phase 3: Treatment Promoted
        self.run_phase_3_treatment_promoted(experiment_metrics)
        
        if force_rollback:
            # Phase 4: Treatment Degraded
            degraded_metrics, phase4 = self.run_phase_4_treatment_degraded(
                experiment_metrics,
                degradation_factor=degradation_factor,
            )
            
            if phase4.decision == RolloutDecisionType.ROLLBACK:
                # Phase 5: Rollback Executed
                self.run_phase_5_rollback_executed(control_metrics)
                self.report.final_decision = RolloutDecisionType.ROLLBACK
                self.report.final_state = ExperimentPhase.ROLLED_BACK
            else:
                # Degradation detected but not enough to rollback
                self.report.final_decision = RolloutDecisionType.CONTINUE
                self.report.final_state = ExperimentPhase.TREATMENT_DEGRADED
        else:
            # No degradation - treatment remains promoted
            self.report.final_decision = RolloutDecisionType.PROMOTE
            self.report.final_state = ExperimentPhase.TREATMENT_PROMOTED
        
        self.report.complete()
        
        print(f"\n{'='*70}")
        print(f"✅ Simulation Complete")
        print(f"   Final Decision: {self.report.final_decision.value}")
        print(f"   Final State: {self.report.final_state.value}")
        print(f"   Duration: {self.report.duration_seconds:.2f}s")
        print(f"{'='*70}")
        
        return self.report


def run_cta_copy_simulation() -> SimulationReport:
    """Run simulation for CTA Copy experiment."""
    print("\n" + "="*70)
    print("📊 CTA Copy Experiment Simulation")
    print("="*70)
    
    benchmark = generate_synthetic_v44_results()
    exp_data = benchmark["experiments"]["exp_cta_copy"]
    
    control_metrics = create_variant_metrics_from_benchmark(
        exp_data["variants"]["control"],
        "control"
    )
    treatment_metrics = create_variant_metrics_from_benchmark(
        exp_data["variants"]["treatment"],
        "treatment"
    )
    
    experiment_metrics = ExperimentMetrics(
        experiment_id="exp_cta_copy",
        control_variant_id="control",
        variant_metrics={
            "control": control_metrics,
            "treatment": treatment_metrics,
        },
    )
    
    runner = RolloutSimulationRunner(
        experiment_id="exp_cta_copy",
        random_seed=42,
    )
    
    return runner.run_full_simulation(experiment_metrics, force_rollback=True)


def run_resume_timing_simulation() -> SimulationReport:
    """Run simulation for Resume Timing experiment."""
    print("\n" + "="*70)
    print("⏱️  Resume Timing Experiment Simulation")
    print("="*70)
    
    benchmark = generate_synthetic_v44_results()
    exp_data = benchmark["experiments"]["exp_resume_timing"]
    
    control_metrics = create_variant_metrics_from_benchmark(
        exp_data["variants"]["control"],
        "control"
    )
    treatment_metrics = create_variant_metrics_from_benchmark(
        exp_data["variants"]["delay_2s"],
        "delay_2s"
    )
    
    experiment_metrics = ExperimentMetrics(
        experiment_id="exp_resume_timing",
        control_variant_id="control",
        variant_metrics={
            "control": control_metrics,
            "treatment": treatment_metrics,  # Map to 'treatment' key
        },
    )
    
    runner = RolloutSimulationRunner(
        experiment_id="exp_resume_timing",
        random_seed=42,
    )
    
    return runner.run_full_simulation(experiment_metrics, force_rollback=True)


def run_successful_promotion_simulation() -> SimulationReport:
    """Run simulation where treatment succeeds (no rollback)."""
    print("\n" + "="*70)
    print("🎉 Successful Promotion Simulation (No Rollback)")
    print("="*70)
    
    benchmark = generate_synthetic_v44_results()
    exp_data = benchmark["experiments"]["exp_cta_copy"]
    
    control_metrics = create_variant_metrics_from_benchmark(
        exp_data["variants"]["control"],
        "control"
    )
    treatment_metrics = create_variant_metrics_from_benchmark(
        exp_data["variants"]["treatment"],
        "treatment"
    )
    
    experiment_metrics = ExperimentMetrics(
        experiment_id="exp_success",
        control_variant_id="control",
        variant_metrics={
            "control": control_metrics,
            "treatment": treatment_metrics,
        },
    )
    
    runner = RolloutSimulationRunner(
        experiment_id="exp_success",
        random_seed=42,
    )
    
    return runner.run_full_simulation(
        experiment_metrics,
        force_rollback=False,
    )


def generate_simulation_report(reports: List[SimulationReport], output_dir: str = "reports") -> str:
    """Generate consolidated simulation report."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    report_data = {
        "generated_at": datetime.utcnow().isoformat(),
        "version": "v45",
        "simulation_count": len(reports),
        "simulations": [r.to_dict() for r in reports],
    }
    
    # Summary statistics
    summary = {
        "total_simulations": len(reports),
        "promotions": sum(1 for r in reports if r.final_decision == RolloutDecisionType.PROMOTE),
        "rollbacks": sum(1 for r in reports if r.final_decision == RolloutDecisionType.ROLLBACK),
        "continues": sum(1 for r in reports if r.final_decision == RolloutDecisionType.CONTINUE),
    }
    report_data["summary"] = summary
    
    # Save JSON report
    report_file = output_path / "v45_rollout_simulation_report.json"
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)
    
    # Generate Markdown report
    md_content = generate_markdown_report(report_data)
    md_file = output_path / "v45_rollout_simulation_report.md"
    with open(md_file, "w") as f:
        f.write(md_content)
    
    print(f"\n📁 Reports generated:")
    print(f"   - {report_file}")
    print(f"   - {md_file}")
    
    return str(report_file)


def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """Generate Markdown report from simulation data."""
    md = f"""# v45 Rollout Simulation Report

**Generated:** {report_data['generated_at']}  
**Version:** {report_data['version']}

---

## 📊 Summary

| Metric | Count |
|--------|-------|
| Total Simulations | {report_data['summary']['total_simulations']} |
| Promotions | {report_data['summary']['promotions']} |
| Rollbacks | {report_data['summary']['rollbacks']} |
| Continues | {report_data['summary']['continues']} |

---

## 🔬 Simulation Details

"""
    
    for sim in report_data['simulations']:
        md += f"""### {sim['simulation_id']}

**Experiment:** {sim['experiment_id']}  
**Final Decision:** {sim['final_decision']}  
**Final State:** {sim['final_state']}  
**Duration:** {sim['duration_seconds']:.2f}s

#### Phases

| Phase | Variant | Decision | Key Metric |
|-------|---------|----------|------------|
"""
        for phase in sim['phases']:
            metrics = phase['metrics']
            md += f"| {phase['phase']} | {phase['variant_id']} | {phase['decision']} | CR: {metrics['completion_rate']:.1%} |\n"
        
        md += "\n"
    
    md += """
---

## 📝 Phase Descriptions

1. **control_baseline**: Control variant running as baseline
2. **treatment_evaluation**: Treatment evaluated for promotion
3. **treatment_promoted**: Treatment promoted to production
4. **treatment_degraded**: Treatment metrics degraded
5. **rolled_back**: Rollback executed, restored to control

---
*Generated by v45 Rollout Integration Simulation*
"""
    
    return md


def main():
    """Main entry point for simulation."""
    print("="*70)
    print("🚀 v45 Rollout Integration Simulation")
    print("="*70)
    
    reports = []
    
    # Run different simulation scenarios
    reports.append(run_cta_copy_simulation())
    reports.append(run_resume_timing_simulation())
    reports.append(run_successful_promotion_simulation())
    
    # Generate consolidated report
    generate_simulation_report(reports)
    
    print("\n" + "="*70)
    print("✅ All Simulations Complete")
    print("="*70)
    
    return reports


if __name__ == "__main__":
    main()
