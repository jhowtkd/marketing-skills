from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class QualityOptimizerMetrics:
    """v25 Quality-First Constrained Optimizer metrics."""
    # Counters
    cycles_total: int = 0
    proposals_generated_total: int = 0
    proposals_applied_total: int = 0
    proposals_blocked_total: int = 0
    proposals_rejected_total: int = 0
    rollbacks_total: int = 0
    
    # Impact expectations
    quality_gain_expected: float = 0.0  # Total expected V1 score improvement
    cost_impact_expected_pct: float = 0.0  # Expected cost impact %
    time_impact_expected_pct: float = 0.0  # Expected MTTC impact %
    
    # Constraint compliance
    constraint_violations_cost: int = 0
    constraint_violations_time: int = 0
    constraint_violations_incident: int = 0
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_proposal_applied_at: Optional[str] = None


@dataclass
class ApprovalLearningMetrics:
    """v24 Approval Learning Loop metrics."""
    # Counters
    learning_cycles_total: int = 0
    proposals_generated_total: int = 0
    proposals_applied_total: int = 0
    proposals_blocked_total: int = 0
    proposals_rejected_total: int = 0
    rollbacks_total: int = 0
    
    # Learning impact
    batch_precision_percent: float = 0.0
    human_minutes_saved: float = 0.0
    queue_reduction_percent: float = 0.0
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_proposal_applied_at: Optional[str] = None


@dataclass
class ControlLoopMetrics:
    """v26 Online Control Loop metrics."""
    # Counters
    cycles_total: int = 0
    regressions_detected_total: int = 0
    mitigations_applied_total: int = 0
    mitigations_blocked_total: int = 0
    rollbacks_total: int = 0
    
    # Time-based metrics (in seconds)
    time_to_detect_seconds: float = 0.0
    time_to_mitigate_seconds: float = 0.0
    time_to_detect_count: int = 0  # Number of measurements
    time_to_mitigate_count: int = 0
    
    # Active state
    active_cycles: int = 0
    frozen_brands: int = 0
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_regression_detected_at: Optional[str] = None
    last_mitigation_applied_at: Optional[str] = None
    last_rollback_at: Optional[str] = None


@dataclass
class RecoveryOrchestrationMetrics:
    """v28 Recovery Orchestration metrics."""
    # Counters
    runs_total: int = 0
    runs_successful: int = 0
    runs_failed: int = 0
    runs_auto: int = 0
    runs_manual: int = 0
    steps_total: int = 0
    steps_successful: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0
    approval_requests_total: int = 0
    approvals_granted: int = 0
    approvals_rejected: int = 0
    frozen_incidents: int = 0
    rolled_back_runs: int = 0
    
    # Time-based metrics (MTTR in seconds)
    mttr_seconds_total: float = 0.0
    mttr_count: int = 0
    mttr_seconds_avg: float = 0.0
    
    # Incident classification counts
    incident_handoff_timeout: int = 0
    incident_approval_sla_breach: int = 0
    incident_quality_regression: int = 0
    incident_system_failure: int = 0
    
    # Active state
    active_runs: int = 0
    pending_approvals: int = 0
    
    # Timestamps
    last_run_at: Optional[str] = None
    last_successful_run_at: Optional[str] = None
    last_failed_run_at: Optional[str] = None
    last_approval_at: Optional[str] = None
    last_rejection_at: Optional[str] = None
    last_freeze_at: Optional[str] = None
    last_rollback_at: Optional[str] = None


@dataclass
class PredictiveResilienceMetrics:
    """v27 Predictive Resilience Engine metrics."""
    # Counters
    cycles_total: int = 0
    alerts_total: int = 0  # predictive_alerts_total
    mitigations_applied_total: int = 0
    mitigations_blocked_total: int = 0
    mitigations_rejected_total: int = 0
    rollbacks_total: int = 0
    false_positives_total: int = 0
    
    # Score metrics
    composite_score_avg: float = 0.0
    composite_score_min: float = 1.0
    composite_score_max: float = 0.0
    score_measurements: int = 0
    
    # Risk classification counts
    risk_low_count: int = 0
    risk_medium_count: int = 0
    risk_high_count: int = 0
    risk_critical_count: int = 0
    
    # Time-based metrics (in seconds)
    time_to_detect_seconds: float = 0.0
    time_to_mitigate_seconds: float = 0.0
    time_to_detect_count: int = 0
    time_to_mitigate_count: int = 0
    
    # Active state
    active_cycles: int = 0
    frozen_brands: int = 0
    pending_proposals: int = 0
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_alert_at: Optional[str] = None
    last_mitigation_applied_at: Optional[str] = None
    last_mitigation_rejected_at: Optional[str] = None
    last_rollback_at: Optional[str] = None
    last_false_positive_at: Optional[str] = None


@dataclass
class RoiOptimizerMetrics:
    """v19 ROI Optimizer metrics snapshot."""
    # Counters
    cycles_total: int = 0
    proposals_generated_total: int = 0
    proposals_applied_total: int = 0
    proposals_blocked_total: int = 0
    proposals_rejected_total: int = 0
    rollbacks_total: int = 0
    
    # Gauges - ROI composite
    roi_composite_score: float = 0.0
    roi_business_contribution: float = 0.0
    roi_quality_contribution: float = 0.0
    roi_efficiency_contribution: float = 0.0
    
    # Pillar scores
    business_pillar_score: float = 0.0
    quality_pillar_score: float = 0.0
    efficiency_pillar_score: float = 0.0
    
    # Timestamps
    last_run_at: Optional[str] = None
    last_applied_at: Optional[str] = None


@dataclass
class OnboardingActivationMetrics:
    """v31 Onboarding Activation Learning Loop metrics."""
    # Cycle counters
    cycles_total: int = 0
    proposals_generated_total: int = 0
    proposals_applied_total: int = 0
    proposals_auto_applied_total: int = 0
    proposals_rejected_total: int = 0
    rollbacks_total: int = 0
    freezes_total: int = 0
    
    # Risk distribution
    low_risk_proposals_total: int = 0
    medium_risk_proposals_total: int = 0
    high_risk_proposals_total: int = 0
    
    # Friction tracking
    total_abandons_tracked: int = 0
    total_returns_tracked: int = 0
    total_hesitations_tracked: int = 0
    
    # Impact metrics (6-week goals)
    onboarding_completion_rate: float = 0.0  # Target: +15 p.p.
    template_to_first_run_conversion: float = 0.0  # Target: +20%
    time_to_first_action_ms: float = 0.0  # Target: -20%
    step_1_dropoff_rate: float = 0.0  # Target: -25%
    
    # Weekly cadence tracking
    adjustments_this_week: int = 0
    max_adjustment_percent: float = 10.0  # ±10% per cycle
    
    # Timestamps
    last_cycle_at: Optional[str] = None
    last_proposal_applied_at: Optional[str] = None
    last_rollback_at: Optional[str] = None


@dataclass
class OnboardingExperimentationMetrics:
    """v32 Onboarding Experimentation Layer metrics."""
    # Experiment counts
    experiments_total: int = 0
    experiments_running: int = 0
    experiments_completed: int = 0
    experiments_paused: int = 0
    experiments_rolled_back: int = 0
    
    # Assignment metrics
    assignments_total: int = 0
    assignments_today: int = 0
    
    # Promotion decision metrics
    promotions_auto_applied: int = 0
    promotions_approved: int = 0
    promotions_pending_approval: int = 0
    promotions_blocked: int = 0
    rollbacks_triggered: int = 0
    
    # Guardrail metrics
    guardrail_blocks_total: int = 0
    sample_size_violations: int = 0
    lift_threshold_violations: int = 0
    
    # Weekly evaluation metrics
    evaluations_run_total: int = 0
    significant_results: int = 0
    insignificant_results: int = 0
    
    # Timestamps
    last_assignment_at: Optional[str] = None
    last_evaluation_at: Optional[str] = None
    last_promotion_at: Optional[str] = None
    last_rollback_at: Optional[str] = None


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._latencies: dict[str, list[float]] = {}
        self._costs: dict[str, float] = {}
        self._roi_metrics = RoiOptimizerMetrics()
        self._learning_metrics = ApprovalLearningMetrics()
        self._quality_metrics = QualityOptimizerMetrics()
        self._control_loop_metrics = ControlLoopMetrics()
        self._predictive_metrics = PredictiveResilienceMetrics()  # v27
        self._recovery_metrics = RecoveryOrchestrationMetrics()  # v28
        self._onboarding_activation_metrics = OnboardingActivationMetrics()  # v31
        self._onboarding_experimentation_metrics = OnboardingExperimentationMetrics()  # v32
    
    # v24: Approval Learning Loop metrics
    def record_learning_cycle(self) -> None:
        """v24: Record a learning cycle run."""
        with self._lock:
            self._learning_metrics.learning_cycles_total += 1
            self._learning_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()
    
    def record_learning_proposal(self, status: str = "generated") -> None:
        """v24: Record a learning proposal."""
        with self._lock:
            self._learning_metrics.proposals_generated_total += 1
            if status == "blocked":
                self._learning_metrics.proposals_blocked_total += 1
            elif status == "rejected":
                self._learning_metrics.proposals_rejected_total += 1
    
    def record_learning_proposal_applied(self) -> None:
        """v24: Record a learning proposal being applied."""
        with self._lock:
            self._learning_metrics.proposals_applied_total += 1
            self._learning_metrics.last_proposal_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_learning_rollback(self) -> None:
        """v24: Record a learning rollback operation."""
        with self._lock:
            self._learning_metrics.rollbacks_total += 1
    
    def update_learning_impact(
        self,
        batch_precision: float,
        minutes_saved: float,
        queue_reduction: float,
    ) -> None:
        """v24: Update learning impact gauges."""
        with self._lock:
            self._learning_metrics.batch_precision_percent = batch_precision
            self._learning_metrics.human_minutes_saved = minutes_saved
            self._learning_metrics.queue_reduction_percent = queue_reduction
    
    def get_learning_metrics(self) -> ApprovalLearningMetrics:
        """v24: Get current learning metrics snapshot."""
        with self._lock:
            return ApprovalLearningMetrics(
                learning_cycles_total=self._learning_metrics.learning_cycles_total,
                proposals_generated_total=self._learning_metrics.proposals_generated_total,
                proposals_applied_total=self._learning_metrics.proposals_applied_total,
                proposals_blocked_total=self._learning_metrics.proposals_blocked_total,
                proposals_rejected_total=self._learning_metrics.proposals_rejected_total,
                rollbacks_total=self._learning_metrics.rollbacks_total,
                batch_precision_percent=self._learning_metrics.batch_precision_percent,
                human_minutes_saved=self._learning_metrics.human_minutes_saved,
                queue_reduction_percent=self._learning_metrics.queue_reduction_percent,
                last_cycle_at=self._learning_metrics.last_cycle_at,
                last_proposal_applied_at=self._learning_metrics.last_proposal_applied_at,
            )
    
    # v25: Quality-First Optimizer metrics
    def record_quality_cycle(self) -> None:
        """v25: Record a quality optimizer cycle run."""
        with self._lock:
            self._quality_metrics.cycles_total += 1
            self._quality_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()
    
    def record_quality_proposal(self, status: str) -> None:
        """v25: Record a proposal generated with given status."""
        with self._lock:
            self._quality_metrics.proposals_generated_total += 1
            if status == "blocked":
                self._quality_metrics.proposals_blocked_total += 1
            elif status == "rejected":
                self._quality_metrics.proposals_rejected_total += 1
    
    def record_quality_proposal_applied(self) -> None:
        """v25: Record a proposal being applied."""
        with self._lock:
            self._quality_metrics.proposals_applied_total += 1
            self._quality_metrics.last_proposal_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_quality_rollback(self) -> None:
        """v25: Record a rollback operation."""
        with self._lock:
            self._quality_metrics.rollbacks_total += 1
    
    def record_quality_impact(
        self,
        quality_gain: float,
        cost_impact_pct: float,
        time_impact_pct: float,
    ) -> None:
        """v25: Record expected impact metrics."""
        with self._lock:
            self._quality_metrics.quality_gain_expected += quality_gain
            self._quality_metrics.cost_impact_expected_pct = cost_impact_pct
            self._quality_metrics.time_impact_expected_pct = time_impact_pct
    
    def record_constraint_violation(self, violation_type: str) -> None:
        """v25: Record a constraint violation."""
        with self._lock:
            if violation_type == "cost":
                self._quality_metrics.constraint_violations_cost += 1
            elif violation_type == "time":
                self._quality_metrics.constraint_violations_time += 1
            elif violation_type == "incident":
                self._quality_metrics.constraint_violations_incident += 1
    
    def get_quality_metrics(self) -> QualityOptimizerMetrics:
        """v25: Get current quality optimizer metrics snapshot."""
        with self._lock:
            return QualityOptimizerMetrics(
                cycles_total=self._quality_metrics.cycles_total,
                proposals_generated_total=self._quality_metrics.proposals_generated_total,
                proposals_applied_total=self._quality_metrics.proposals_applied_total,
                proposals_blocked_total=self._quality_metrics.proposals_blocked_total,
                proposals_rejected_total=self._quality_metrics.proposals_rejected_total,
                rollbacks_total=self._quality_metrics.rollbacks_total,
                quality_gain_expected=self._quality_metrics.quality_gain_expected,
                cost_impact_expected_pct=self._quality_metrics.cost_impact_expected_pct,
                time_impact_expected_pct=self._quality_metrics.time_impact_expected_pct,
                constraint_violations_cost=self._quality_metrics.constraint_violations_cost,
                constraint_violations_time=self._quality_metrics.constraint_violations_time,
                constraint_violations_incident=self._quality_metrics.constraint_violations_incident,
                last_cycle_at=self._quality_metrics.last_cycle_at,
                last_proposal_applied_at=self._quality_metrics.last_proposal_applied_at,
            )
    
    # v26: Online Control Loop metrics
    def record_control_loop_cycle(self) -> None:
        """v26: Record a control loop cycle run."""
        with self._lock:
            self._control_loop_metrics.cycles_total += 1
            self._control_loop_metrics.active_cycles += 1
            self._control_loop_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()
    
    def record_regression_detected(self) -> None:
        """v26: Record a regression detection."""
        with self._lock:
            self._control_loop_metrics.regressions_detected_total += 1
            self._control_loop_metrics.last_regression_detected_at = datetime.now(timezone.utc).isoformat()
    
    def record_mitigation_applied(self) -> None:
        """v26: Record a mitigation being applied."""
        with self._lock:
            self._control_loop_metrics.mitigations_applied_total += 1
            self._control_loop_metrics.last_mitigation_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_mitigation_blocked(self) -> None:
        """v26: Record a mitigation being blocked."""
        with self._lock:
            self._control_loop_metrics.mitigations_blocked_total += 1
    
    def record_control_loop_rollback(self) -> None:
        """v26: Record a rollback operation."""
        with self._lock:
            self._control_loop_metrics.rollbacks_total += 1
            self._control_loop_metrics.last_rollback_at = datetime.now(timezone.utc).isoformat()
    
    def record_time_to_detect(self, seconds: float) -> None:
        """v26: Record time to detect regression (seconds)."""
        with self._lock:
            # Running average
            current = self._control_loop_metrics.time_to_detect_seconds
            count = self._control_loop_metrics.time_to_detect_count
            new_count = count + 1
            new_avg = (current * count + seconds) / new_count
            self._control_loop_metrics.time_to_detect_seconds = new_avg
            self._control_loop_metrics.time_to_detect_count = new_count
    
    def record_time_to_mitigate(self, seconds: float) -> None:
        """v26: Record time to mitigate regression (seconds)."""
        with self._lock:
            current = self._control_loop_metrics.time_to_mitigate_seconds
            count = self._control_loop_metrics.time_to_mitigate_count
            new_count = count + 1
            new_avg = (current * count + seconds) / new_count
            self._control_loop_metrics.time_to_mitigate_seconds = new_avg
            self._control_loop_metrics.time_to_mitigate_count = new_count
    
    def update_active_cycles(self, count: int) -> None:
        """v26: Update active cycles count."""
        with self._lock:
            self._control_loop_metrics.active_cycles = count
    
    def update_frozen_brands(self, count: int) -> None:
        """v26: Update frozen brands count."""
        with self._lock:
            self._control_loop_metrics.frozen_brands = count
    
    def get_control_loop_metrics(self) -> ControlLoopMetrics:
        """v26: Get current control loop metrics snapshot."""
        with self._lock:
            return ControlLoopMetrics(
                cycles_total=self._control_loop_metrics.cycles_total,
                regressions_detected_total=self._control_loop_metrics.regressions_detected_total,
                mitigations_applied_total=self._control_loop_metrics.mitigations_applied_total,
                mitigations_blocked_total=self._control_loop_metrics.mitigations_blocked_total,
                rollbacks_total=self._control_loop_metrics.rollbacks_total,
                time_to_detect_seconds=self._control_loop_metrics.time_to_detect_seconds,
                time_to_mitigate_seconds=self._control_loop_metrics.time_to_mitigate_seconds,
                time_to_detect_count=self._control_loop_metrics.time_to_detect_count,
                time_to_mitigate_count=self._control_loop_metrics.time_to_mitigate_count,
                active_cycles=self._control_loop_metrics.active_cycles,
                frozen_brands=self._control_loop_metrics.frozen_brands,
                last_cycle_at=self._control_loop_metrics.last_cycle_at,
                last_regression_detected_at=self._control_loop_metrics.last_regression_detected_at,
                last_mitigation_applied_at=self._control_loop_metrics.last_mitigation_applied_at,
                last_rollback_at=self._control_loop_metrics.last_rollback_at,
            )
    
    # v27: Predictive Resilience metrics
    def record_predictive_cycle(self) -> None:
        """v27: Record a predictive resilience cycle run."""
        with self._lock:
            self._predictive_metrics.cycles_total += 1
            self._predictive_metrics.active_cycles += 1
            self._predictive_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()
    
    def record_predictive_alert(self) -> None:
        """v27: Record a predictive alert generated."""
        with self._lock:
            self._predictive_metrics.alerts_total += 1
            self._predictive_metrics.last_alert_at = datetime.now(timezone.utc).isoformat()
    
    def record_predictive_mitigation_applied(self) -> None:
        """v27: Record a mitigation being applied."""
        with self._lock:
            self._predictive_metrics.mitigations_applied_total += 1
            self._predictive_metrics.last_mitigation_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_predictive_mitigation_blocked(self) -> None:
        """v27: Record a mitigation being blocked."""
        with self._lock:
            self._predictive_metrics.mitigations_blocked_total += 1
    
    def record_predictive_mitigation_rejected(self) -> None:
        """v27: Record a mitigation being rejected."""
        with self._lock:
            self._predictive_metrics.mitigations_rejected_total += 1
            self._predictive_metrics.last_mitigation_rejected_at = datetime.now(timezone.utc).isoformat()
    
    def record_predictive_rollback(self) -> None:
        """v27: Record a rollback operation."""
        with self._lock:
            self._predictive_metrics.rollbacks_total += 1
            self._predictive_metrics.last_rollback_at = datetime.now(timezone.utc).isoformat()
    
    def record_predictive_false_positive(self) -> None:
        """v27: Record a false positive alert."""
        with self._lock:
            self._predictive_metrics.false_positives_total += 1
            self._predictive_metrics.last_false_positive_at = datetime.now(timezone.utc).isoformat()
    
    def record_predictive_score(self, score: float, risk_class: str) -> None:
        """v27: Record a resilience score measurement."""
        with self._lock:
            # Update running average
            current = self._predictive_metrics.composite_score_avg
            count = self._predictive_metrics.score_measurements
            new_count = count + 1
            new_avg = (current * count + score) / new_count
            self._predictive_metrics.composite_score_avg = new_avg
            self._predictive_metrics.score_measurements = new_count
            
            # Update min/max
            self._predictive_metrics.composite_score_min = min(self._predictive_metrics.composite_score_min, score)
            self._predictive_metrics.composite_score_max = max(self._predictive_metrics.composite_score_max, score)
            
            # Update risk class counts
            if risk_class == "low":
                self._predictive_metrics.risk_low_count += 1
            elif risk_class == "medium":
                self._predictive_metrics.risk_medium_count += 1
            elif risk_class == "high":
                self._predictive_metrics.risk_high_count += 1
            elif risk_class == "critical":
                self._predictive_metrics.risk_critical_count += 1
    
    def record_predictive_time_to_detect(self, seconds: float) -> None:
        """v27: Record time to detect degradation (seconds)."""
        with self._lock:
            current = self._predictive_metrics.time_to_detect_seconds
            count = self._predictive_metrics.time_to_detect_count
            new_count = count + 1
            new_avg = (current * count + seconds) / new_count
            self._predictive_metrics.time_to_detect_seconds = new_avg
            self._predictive_metrics.time_to_detect_count = new_count
    
    def record_predictive_time_to_mitigate(self, seconds: float) -> None:
        """v27: Record time to mitigate degradation (seconds)."""
        with self._lock:
            current = self._predictive_metrics.time_to_mitigate_seconds
            count = self._predictive_metrics.time_to_mitigate_count
            new_count = count + 1
            new_avg = (current * count + seconds) / new_count
            self._predictive_metrics.time_to_mitigate_seconds = new_avg
            self._predictive_metrics.time_to_mitigate_count = new_count
    
    def update_predictive_active_cycles(self, count: int) -> None:
        """v27: Update active cycles count."""
        with self._lock:
            self._predictive_metrics.active_cycles = count
    
    def update_predictive_frozen_brands(self, count: int) -> None:
        """v27: Update frozen brands count."""
        with self._lock:
            self._predictive_metrics.frozen_brands = count
    
    def update_predictive_pending_proposals(self, count: int) -> None:
        """v27: Update pending proposals count."""
        with self._lock:
            self._predictive_metrics.pending_proposals = count
    
    def get_predictive_metrics(self) -> PredictiveResilienceMetrics:
        """v27: Get current predictive resilience metrics snapshot."""
        with self._lock:
            return PredictiveResilienceMetrics(
                cycles_total=self._predictive_metrics.cycles_total,
                alerts_total=self._predictive_metrics.alerts_total,
                mitigations_applied_total=self._predictive_metrics.mitigations_applied_total,
                mitigations_blocked_total=self._predictive_metrics.mitigations_blocked_total,
                mitigations_rejected_total=self._predictive_metrics.mitigations_rejected_total,
                rollbacks_total=self._predictive_metrics.rollbacks_total,
                false_positives_total=self._predictive_metrics.false_positives_total,
                composite_score_avg=self._predictive_metrics.composite_score_avg,
                composite_score_min=self._predictive_metrics.composite_score_min,
                composite_score_max=self._predictive_metrics.composite_score_max,
                score_measurements=self._predictive_metrics.score_measurements,
                risk_low_count=self._predictive_metrics.risk_low_count,
                risk_medium_count=self._predictive_metrics.risk_medium_count,
                risk_high_count=self._predictive_metrics.risk_high_count,
                risk_critical_count=self._predictive_metrics.risk_critical_count,
                time_to_detect_seconds=self._predictive_metrics.time_to_detect_seconds,
                time_to_mitigate_seconds=self._predictive_metrics.time_to_mitigate_seconds,
                time_to_detect_count=self._predictive_metrics.time_to_detect_count,
                time_to_mitigate_count=self._predictive_metrics.time_to_mitigate_count,
                active_cycles=self._predictive_metrics.active_cycles,
                frozen_brands=self._predictive_metrics.frozen_brands,
                pending_proposals=self._predictive_metrics.pending_proposals,
                last_cycle_at=self._predictive_metrics.last_cycle_at,
                last_alert_at=self._predictive_metrics.last_alert_at,
                last_mitigation_applied_at=self._predictive_metrics.last_mitigation_applied_at,
                last_mitigation_rejected_at=self._predictive_metrics.last_mitigation_rejected_at,
                last_rollback_at=self._predictive_metrics.last_rollback_at,
                last_false_positive_at=self._predictive_metrics.last_false_positive_at,
            )
    
    # v28: Recovery Orchestration metrics
    def record_recovery_run(self, auto: bool = False) -> None:
        """v28: Record a recovery run started."""
        with self._lock:
            self._recovery_metrics.runs_total += 1
            self._recovery_metrics.active_runs += 1
            self._recovery_metrics.last_run_at = datetime.now(timezone.utc).isoformat()
            if auto:
                self._recovery_metrics.runs_auto += 1
            else:
                self._recovery_metrics.runs_manual += 1
    
    def record_recovery_run_success(self, duration_seconds: float) -> None:
        """v28: Record a successful recovery run completion."""
        with self._lock:
            self._recovery_metrics.runs_successful += 1
            self._recovery_metrics.active_runs -= 1
            self._recovery_metrics.last_successful_run_at = datetime.now(timezone.utc).isoformat()
            # Update MTTR
            current = self._recovery_metrics.mttr_seconds_total
            count = self._recovery_metrics.mttr_count
            new_count = count + 1
            new_total = current + duration_seconds
            self._recovery_metrics.mttr_seconds_total = new_total
            self._recovery_metrics.mttr_count = new_count
            self._recovery_metrics.mttr_seconds_avg = new_total / new_count if new_count > 0 else 0.0
    
    def record_recovery_run_failure(self) -> None:
        """v28: Record a failed recovery run."""
        with self._lock:
            self._recovery_metrics.runs_failed += 1
            self._recovery_metrics.active_runs = max(0, self._recovery_metrics.active_runs - 1)
            self._recovery_metrics.last_failed_run_at = datetime.now(timezone.utc).isoformat()
    
    def record_recovery_step(self, status: str) -> None:
        """v28: Record a step execution with status."""
        with self._lock:
            self._recovery_metrics.steps_total += 1
            if status == "success":
                self._recovery_metrics.steps_successful += 1
            elif status == "failed":
                self._recovery_metrics.steps_failed += 1
            elif status == "skipped":
                self._recovery_metrics.steps_skipped += 1
    
    def record_approval_requested(self) -> None:
        """v28: Record an approval request created."""
        with self._lock:
            self._recovery_metrics.approval_requests_total += 1
            self._recovery_metrics.pending_approvals += 1
    
    def record_approval_granted(self) -> None:
        """v28: Record an approval being granted."""
        with self._lock:
            self._recovery_metrics.approvals_granted += 1
            self._recovery_metrics.pending_approvals = max(0, self._recovery_metrics.pending_approvals - 1)
            self._recovery_metrics.last_approval_at = datetime.now(timezone.utc).isoformat()
    
    def record_approval_rejected(self) -> None:
        """v28: Record an approval being rejected."""
        with self._lock:
            self._recovery_metrics.approvals_rejected += 1
            self._recovery_metrics.pending_approvals = max(0, self._recovery_metrics.pending_approvals - 1)
            self._recovery_metrics.last_rejection_at = datetime.now(timezone.utc).isoformat()
    
    def record_recovery_frozen(self) -> None:
        """v28: Record a recovery being frozen."""
        with self._lock:
            self._recovery_metrics.frozen_incidents += 1
            self._recovery_metrics.last_freeze_at = datetime.now(timezone.utc).isoformat()
    
    def record_recovery_rollback(self) -> None:
        """v28: Record a recovery rollback operation."""
        with self._lock:
            self._recovery_metrics.rolled_back_runs += 1
            self._recovery_metrics.last_rollback_at = datetime.now(timezone.utc).isoformat()
    
    def record_incident_classified(self, incident_type: str) -> None:
        """v28: Record an incident classification."""
        with self._lock:
            if incident_type == "handoff_timeout":
                self._recovery_metrics.incident_handoff_timeout += 1
            elif incident_type == "approval_sla_breach":
                self._recovery_metrics.incident_approval_sla_breach += 1
            elif incident_type == "quality_regression":
                self._recovery_metrics.incident_quality_regression += 1
            elif incident_type == "system_failure":
                self._recovery_metrics.incident_system_failure += 1
    
    def get_recovery_metrics(self) -> RecoveryOrchestrationMetrics:
        """v28: Get current recovery orchestration metrics snapshot."""
        with self._lock:
            return RecoveryOrchestrationMetrics(
                runs_total=self._recovery_metrics.runs_total,
                runs_successful=self._recovery_metrics.runs_successful,
                runs_failed=self._recovery_metrics.runs_failed,
                runs_auto=self._recovery_metrics.runs_auto,
                runs_manual=self._recovery_metrics.runs_manual,
                steps_total=self._recovery_metrics.steps_total,
                steps_successful=self._recovery_metrics.steps_successful,
                steps_failed=self._recovery_metrics.steps_failed,
                steps_skipped=self._recovery_metrics.steps_skipped,
                approval_requests_total=self._recovery_metrics.approval_requests_total,
                approvals_granted=self._recovery_metrics.approvals_granted,
                approvals_rejected=self._recovery_metrics.approvals_rejected,
                frozen_incidents=self._recovery_metrics.frozen_incidents,
                rolled_back_runs=self._recovery_metrics.rolled_back_runs,
                mttr_seconds_total=self._recovery_metrics.mttr_seconds_total,
                mttr_count=self._recovery_metrics.mttr_count,
                mttr_seconds_avg=self._recovery_metrics.mttr_seconds_avg,
                incident_handoff_timeout=self._recovery_metrics.incident_handoff_timeout,
                incident_approval_sla_breach=self._recovery_metrics.incident_approval_sla_breach,
                incident_quality_regression=self._recovery_metrics.incident_quality_regression,
                incident_system_failure=self._recovery_metrics.incident_system_failure,
                active_runs=self._recovery_metrics.active_runs,
                pending_approvals=self._recovery_metrics.pending_approvals,
                last_run_at=self._recovery_metrics.last_run_at,
                last_successful_run_at=self._recovery_metrics.last_successful_run_at,
                last_failed_run_at=self._recovery_metrics.last_failed_run_at,
                last_approval_at=self._recovery_metrics.last_approval_at,
                last_rejection_at=self._recovery_metrics.last_rejection_at,
                last_freeze_at=self._recovery_metrics.last_freeze_at,
                last_rollback_at=self._recovery_metrics.last_rollback_at,
            )
    
    # v19: ROI Optimizer metrics
    def record_roi_cycle(self) -> None:
        """v19: Record an ROI optimizer cycle run."""
        with self._lock:
            self._roi_metrics.cycles_total += 1
            self._roi_metrics.last_run_at = datetime.now(timezone.utc).isoformat()
    
    def record_roi_proposal(self, status: str) -> None:
        """v19: Record a proposal generated with given status."""
        with self._lock:
            self._roi_metrics.proposals_generated_total += 1
            if status == "blocked":
                self._roi_metrics.proposals_blocked_total += 1
            elif status == "rejected":
                self._roi_metrics.proposals_rejected_total += 1
    
    def record_roi_proposal_applied(self) -> None:
        """v19: Record a proposal being applied."""
        with self._lock:
            self._roi_metrics.proposals_applied_total += 1
            self._roi_metrics.last_applied_at = datetime.now(timezone.utc).isoformat()
    
    def record_roi_rollback(self) -> None:
        """v19: Record a rollback operation."""
        with self._lock:
            self._roi_metrics.rollbacks_total += 1
    
    def update_roi_scores(
        self,
        composite_score: float,
        business_contrib: float,
        quality_contrib: float,
        efficiency_contrib: float,
        business_pillar: float,
        quality_pillar: float,
        efficiency_pillar: float,
    ) -> None:
        """v19: Update ROI score gauges."""
        with self._lock:
            self._roi_metrics.roi_composite_score = composite_score
            self._roi_metrics.roi_business_contribution = business_contrib
            self._roi_metrics.roi_quality_contribution = quality_contrib
            self._roi_metrics.roi_efficiency_contribution = efficiency_contrib
            self._roi_metrics.business_pillar_score = business_pillar
            self._roi_metrics.quality_pillar_score = quality_pillar
            self._roi_metrics.efficiency_pillar_score = efficiency_pillar
    
    def get_roi_metrics(self) -> RoiOptimizerMetrics:
        """v19: Get current ROI metrics snapshot."""
        with self._lock:
            return RoiOptimizerMetrics(
                cycles_total=self._roi_metrics.cycles_total,
                proposals_generated_total=self._roi_metrics.proposals_generated_total,
                proposals_applied_total=self._roi_metrics.proposals_applied_total,
                proposals_blocked_total=self._roi_metrics.proposals_blocked_total,
                proposals_rejected_total=self._roi_metrics.proposals_rejected_total,
                rollbacks_total=self._roi_metrics.rollbacks_total,
                roi_composite_score=self._roi_metrics.roi_composite_score,
                roi_business_contribution=self._roi_metrics.roi_business_contribution,
                roi_quality_contribution=self._roi_metrics.roi_quality_contribution,
                roi_efficiency_contribution=self._roi_metrics.roi_efficiency_contribution,
                business_pillar_score=self._roi_metrics.business_pillar_score,
                quality_pillar_score=self._roi_metrics.quality_pillar_score,
                efficiency_pillar_score=self._roi_metrics.efficiency_pillar_score,
                last_run_at=self._roi_metrics.last_run_at,
                last_applied_at=self._roi_metrics.last_applied_at,
            )

    def record_count(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counts[name] = self._counts.get(name, 0) + value

    def record_latency(self, name: str, seconds: float) -> None:
        with self._lock:
            self._latencies.setdefault(name, []).append(seconds)

    def record_cost(self, name: str, amount: float) -> None:
        with self._lock:
            self._costs[name] = self._costs.get(name, 0.0) + amount

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_latencies = {
                key: sum(values) / len(values) if values else 0.0
                for key, values in self._latencies.items()
            }
            return {
                "counts": dict(self._counts),
                "avg_latencies": avg_latencies,
                "total_costs": dict(self._costs),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # v25 Quality Optimizer metrics
                "quality_optimizer_v25": {
                    "cycles_total": self._quality_metrics.cycles_total,
                    "proposals_generated_total": self._quality_metrics.proposals_generated_total,
                    "proposals_applied_total": self._quality_metrics.proposals_applied_total,
                    "proposals_blocked_total": self._quality_metrics.proposals_blocked_total,
                    "proposals_rejected_total": self._quality_metrics.proposals_rejected_total,
                    "rollbacks_total": self._quality_metrics.rollbacks_total,
                    "quality_gain_expected": self._quality_metrics.quality_gain_expected,
                    "cost_impact_expected_pct": self._quality_metrics.cost_impact_expected_pct,
                    "time_impact_expected_pct": self._quality_metrics.time_impact_expected_pct,
                    "constraint_violations_cost": self._quality_metrics.constraint_violations_cost,
                    "constraint_violations_time": self._quality_metrics.constraint_violations_time,
                    "constraint_violations_incident": self._quality_metrics.constraint_violations_incident,
                },
                # v26 Online Control Loop metrics
                "control_loop_v26": {
                    "cycles_total": self._control_loop_metrics.cycles_total,
                    "regressions_detected_total": self._control_loop_metrics.regressions_detected_total,
                    "mitigations_applied_total": self._control_loop_metrics.mitigations_applied_total,
                    "mitigations_blocked_total": self._control_loop_metrics.mitigations_blocked_total,
                    "rollbacks_total": self._control_loop_metrics.rollbacks_total,
                    "time_to_detect_seconds": self._control_loop_metrics.time_to_detect_seconds,
                    "time_to_mitigate_seconds": self._control_loop_metrics.time_to_mitigate_seconds,
                    "active_cycles": self._control_loop_metrics.active_cycles,
                    "frozen_brands": self._control_loop_metrics.frozen_brands,
                    "last_cycle_at": self._control_loop_metrics.last_cycle_at,
                    "last_regression_detected_at": self._control_loop_metrics.last_regression_detected_at,
                },
                # v27 Predictive Resilience metrics
                "predictive_resilience_v27": {
                    "cycles_total": self._predictive_metrics.cycles_total,
                    "alerts_total": self._predictive_metrics.alerts_total,
                    "mitigations_applied_total": self._predictive_metrics.mitigations_applied_total,
                    "mitigations_blocked_total": self._predictive_metrics.mitigations_blocked_total,
                    "mitigations_rejected_total": self._predictive_metrics.mitigations_rejected_total,
                    "rollbacks_total": self._predictive_metrics.rollbacks_total,
                    "false_positives_total": self._predictive_metrics.false_positives_total,
                    "composite_score_avg": self._predictive_metrics.composite_score_avg,
                    "composite_score_min": self._predictive_metrics.composite_score_min,
                    "composite_score_max": self._predictive_metrics.composite_score_max,
                    "risk_low_count": self._predictive_metrics.risk_low_count,
                    "risk_medium_count": self._predictive_metrics.risk_medium_count,
                    "risk_high_count": self._predictive_metrics.risk_high_count,
                    "risk_critical_count": self._predictive_metrics.risk_critical_count,
                    "time_to_detect_seconds": self._predictive_metrics.time_to_detect_seconds,
                    "time_to_mitigate_seconds": self._predictive_metrics.time_to_mitigate_seconds,
                    "active_cycles": self._predictive_metrics.active_cycles,
                    "frozen_brands": self._predictive_metrics.frozen_brands,
                    "pending_proposals": self._predictive_metrics.pending_proposals,
                    "last_cycle_at": self._predictive_metrics.last_cycle_at,
                    "last_alert_at": self._predictive_metrics.last_alert_at,
                    "last_false_positive_at": self._predictive_metrics.last_false_positive_at,
                },
                # v28 Recovery Orchestration metrics
                "recovery_orchestration_v28": {
                    "runs_total": self._recovery_metrics.runs_total,
                    "runs_successful": self._recovery_metrics.runs_successful,
                    "runs_failed": self._recovery_metrics.runs_failed,
                    "runs_auto": self._recovery_metrics.runs_auto,
                    "runs_manual": self._recovery_metrics.runs_manual,
                    "steps_total": self._recovery_metrics.steps_total,
                    "steps_successful": self._recovery_metrics.steps_successful,
                    "steps_failed": self._recovery_metrics.steps_failed,
                    "steps_skipped": self._recovery_metrics.steps_skipped,
                    "approval_requests_total": self._recovery_metrics.approval_requests_total,
                    "approvals_granted": self._recovery_metrics.approvals_granted,
                    "approvals_rejected": self._recovery_metrics.approvals_rejected,
                    "frozen_incidents": self._recovery_metrics.frozen_incidents,
                    "rolled_back_runs": self._recovery_metrics.rolled_back_runs,
                    "mttr_seconds_avg": self._recovery_metrics.mttr_seconds_avg,
                    "mttr_count": self._recovery_metrics.mttr_count,
                    "incident_handoff_timeout": self._recovery_metrics.incident_handoff_timeout,
                    "incident_approval_sla_breach": self._recovery_metrics.incident_approval_sla_breach,
                    "incident_quality_regression": self._recovery_metrics.incident_quality_regression,
                    "incident_system_failure": self._recovery_metrics.incident_system_failure,
                    "active_runs": self._recovery_metrics.active_runs,
                    "pending_approvals": self._recovery_metrics.pending_approvals,
                    "last_run_at": self._recovery_metrics.last_run_at,
                    "last_successful_run_at": self._recovery_metrics.last_successful_run_at,
                    "last_failed_run_at": self._recovery_metrics.last_failed_run_at,
                    "last_approval_at": self._recovery_metrics.last_approval_at,
                    "last_rejection_at": self._recovery_metrics.last_rejection_at,
                    "last_freeze_at": self._recovery_metrics.last_freeze_at,
                    "last_rollback_at": self._recovery_metrics.last_rollback_at,
                },
                # v31: Onboarding Activation Learning Loop metrics
                "onboarding_activation": {
                    "cycles_total": self._onboarding_activation_metrics.cycles_total,
                    "proposals_generated_total": self._onboarding_activation_metrics.proposals_generated_total,
                    "proposals_applied_total": self._onboarding_activation_metrics.proposals_applied_total,
                    "proposals_auto_applied_total": self._onboarding_activation_metrics.proposals_auto_applied_total,
                    "proposals_rejected_total": self._onboarding_activation_metrics.proposals_rejected_total,
                    "rollbacks_total": self._onboarding_activation_metrics.rollbacks_total,
                    "freezes_total": self._onboarding_activation_metrics.freezes_total,
                    "low_risk_proposals_total": self._onboarding_activation_metrics.low_risk_proposals_total,
                    "medium_risk_proposals_total": self._onboarding_activation_metrics.medium_risk_proposals_total,
                    "high_risk_proposals_total": self._onboarding_activation_metrics.high_risk_proposals_total,
                    "friction_tracking": {
                        "total_abandons": self._onboarding_activation_metrics.total_abandons_tracked,
                        "total_returns": self._onboarding_activation_metrics.total_returns_tracked,
                        "total_hesitations": self._onboarding_activation_metrics.total_hesitations_tracked,
                    },
                    "impact_metrics": {
                        "onboarding_completion_rate": self._onboarding_activation_metrics.onboarding_completion_rate,
                        "template_to_first_run_conversion": self._onboarding_activation_metrics.template_to_first_run_conversion,
                        "time_to_first_action_ms": self._onboarding_activation_metrics.time_to_first_action_ms,
                        "step_1_dropoff_rate": self._onboarding_activation_metrics.step_1_dropoff_rate,
                    },
                    "cadence": {
                        "adjustments_this_week": self._onboarding_activation_metrics.adjustments_this_week,
                        "max_adjustment_percent": self._onboarding_activation_metrics.max_adjustment_percent,
                    },
                    "timestamps": {
                        "last_cycle_at": self._onboarding_activation_metrics.last_cycle_at,
                        "last_proposal_applied_at": self._onboarding_activation_metrics.last_proposal_applied_at,
                        "last_rollback_at": self._onboarding_activation_metrics.last_rollback_at,
                    },
                },
                # v32: Onboarding Experimentation Layer metrics
                "onboarding_experimentation_v32": {
                    "experiments": {
                        "total": self._onboarding_experimentation_metrics.experiments_total,
                        "running": self._onboarding_experimentation_metrics.experiments_running,
                        "completed": self._onboarding_experimentation_metrics.experiments_completed,
                        "paused": self._onboarding_experimentation_metrics.experiments_paused,
                        "rolled_back": self._onboarding_experimentation_metrics.experiments_rolled_back,
                    },
                    "assignments": {
                        "total": self._onboarding_experimentation_metrics.assignments_total,
                        "today": self._onboarding_experimentation_metrics.assignments_today,
                    },
                    "promotions": {
                        "auto_applied": self._onboarding_experimentation_metrics.promotions_auto_applied,
                        "approved": self._onboarding_experimentation_metrics.promotions_approved,
                        "pending_approval": self._onboarding_experimentation_metrics.promotions_pending_approval,
                        "blocked": self._onboarding_experimentation_metrics.promotions_blocked,
                        "rollbacks": self._onboarding_experimentation_metrics.rollbacks_triggered,
                    },
                    "guardrails": {
                        "blocks_total": self._onboarding_experimentation_metrics.guardrail_blocks_total,
                        "sample_size_violations": self._onboarding_experimentation_metrics.sample_size_violations,
                        "lift_threshold_violations": self._onboarding_experimentation_metrics.lift_threshold_violations,
                    },
                    "evaluations": {
                        "total": self._onboarding_experimentation_metrics.evaluations_run_total,
                        "significant": self._onboarding_experimentation_metrics.significant_results,
                        "insignificant": self._onboarding_experimentation_metrics.insignificant_results,
                    },
                    "timestamps": {
                        "last_assignment_at": self._onboarding_experimentation_metrics.last_assignment_at,
                        "last_evaluation_at": self._onboarding_experimentation_metrics.last_evaluation_at,
                        "last_promotion_at": self._onboarding_experimentation_metrics.last_promotion_at,
                        "last_rollback_at": self._onboarding_experimentation_metrics.last_rollback_at,
                    },
                },
            }

    # v31: Onboarding Activation Learning Loop metrics
    def record_onboarding_activation_cycle(self) -> None:
        """v31: Record an activation cycle run."""
        with self._lock:
            self._onboarding_activation_metrics.cycles_total += 1
            self._onboarding_activation_metrics.last_cycle_at = datetime.now(timezone.utc).isoformat()

    def record_onboarding_proposal_generated(self, risk_level: str) -> None:
        """v31: Record a proposal generation."""
        with self._lock:
            self._onboarding_activation_metrics.proposals_generated_total += 1
            if risk_level == "low":
                self._onboarding_activation_metrics.low_risk_proposals_total += 1
            elif risk_level == "medium":
                self._onboarding_activation_metrics.medium_risk_proposals_total += 1
            elif risk_level == "high":
                self._onboarding_activation_metrics.high_risk_proposals_total += 1

    def record_onboarding_proposal_applied(self, auto_applied: bool = False) -> None:
        """v31: Record a proposal application."""
        with self._lock:
            self._onboarding_activation_metrics.proposals_applied_total += 1
            if auto_applied:
                self._onboarding_activation_metrics.proposals_auto_applied_total += 1
            self._onboarding_activation_metrics.last_proposal_applied_at = datetime.now(timezone.utc).isoformat()

    def record_onboarding_proposal_rejected(self) -> None:
        """v31: Record a proposal rejection."""
        with self._lock:
            self._onboarding_activation_metrics.proposals_rejected_total += 1

    def record_onboarding_rollback(self) -> None:
        """v31: Record a rollback."""
        with self._lock:
            self._onboarding_activation_metrics.rollbacks_total += 1
            self._onboarding_activation_metrics.last_rollback_at = datetime.now(timezone.utc).isoformat()

    def record_onboarding_freeze(self) -> None:
        """v31: Record a freeze."""
        with self._lock:
            self._onboarding_activation_metrics.freezes_total += 1

    def record_onboarding_friction(self, friction_type: str) -> None:
        """v31: Record friction telemetry."""
        with self._lock:
            if friction_type == "abandon":
                self._onboarding_activation_metrics.total_abandons_tracked += 1
            elif friction_type == "return":
                self._onboarding_activation_metrics.total_returns_tracked += 1
            elif friction_type == "hesitation":
                self._onboarding_activation_metrics.total_hesitations_tracked += 1

    def update_onboarding_impact_metrics(self, **metrics) -> None:
        """v31: Update impact metrics (6-week goals)."""
        with self._lock:
            if "completion_rate" in metrics:
                self._onboarding_activation_metrics.onboarding_completion_rate = metrics["completion_rate"]
            if "template_conversion" in metrics:
                self._onboarding_activation_metrics.template_to_first_run_conversion = metrics["template_conversion"]
            if "time_to_first_action_ms" in metrics:
                self._onboarding_activation_metrics.time_to_first_action_ms = metrics["time_to_first_action_ms"]
            if "step_1_dropoff_rate" in metrics:
                self._onboarding_activation_metrics.step_1_dropoff_rate = metrics["step_1_dropoff_rate"]
    
    # v32: Onboarding Experimentation Layer metrics
    def record_experiment_created(self) -> None:
        """v32: Record experiment creation."""
        with self._lock:
            self._onboarding_experimentation_metrics.experiments_total += 1
    
    def record_experiment_started(self) -> None:
        """v32: Record experiment started (running)."""
        with self._lock:
            self._onboarding_experimentation_metrics.experiments_running += 1
    
    def record_experiment_paused(self) -> None:
        """v32: Record experiment paused."""
        with self._lock:
            self._onboarding_experimentation_metrics.experiments_paused += 1
            self._onboarding_experimentation_metrics.experiments_running = max(
                0, self._onboarding_experimentation_metrics.experiments_running - 1
            )
    
    def record_experiment_completed(self) -> None:
        """v32: Record experiment completed."""
        with self._lock:
            self._onboarding_experimentation_metrics.experiments_completed += 1
            self._onboarding_experimentation_metrics.experiments_running = max(
                0, self._onboarding_experimentation_metrics.experiments_running - 1
            )
            self._onboarding_experimentation_metrics.last_promotion_at = datetime.now(timezone.utc).isoformat()
    
    def record_experiment_rolled_back(self) -> None:
        """v32: Record experiment rolled back."""
        with self._lock:
            self._onboarding_experimentation_metrics.experiments_rolled_back += 1
            self._onboarding_experimentation_metrics.rollbacks_triggered += 1
            self._onboarding_experimentation_metrics.experiments_running = max(
                0, self._onboarding_experimentation_metrics.experiments_running - 1
            )
            self._onboarding_experimentation_metrics.last_rollback_at = datetime.now(timezone.utc).isoformat()
    
    def record_assignment(self) -> None:
        """v32: Record variant assignment."""
        with self._lock:
            self._onboarding_experimentation_metrics.assignments_total += 1
            self._onboarding_experimentation_metrics.assignments_today += 1
            self._onboarding_experimentation_metrics.last_assignment_at = datetime.now(timezone.utc).isoformat()
    
    def record_promotion_decision(self, decision_type: str) -> None:
        """v32: Record promotion decision.
        
        Args:
            decision_type: One of 'auto_apply', 'approved', 'pending', 'blocked', 'rollback'
        """
        with self._lock:
            if decision_type == "auto_apply":
                self._onboarding_experimentation_metrics.promotions_auto_applied += 1
            elif decision_type == "approved":
                self._onboarding_experimentation_metrics.promotions_approved += 1
            elif decision_type == "pending":
                self._onboarding_experimentation_metrics.promotions_pending_approval += 1
            elif decision_type == "blocked":
                self._onboarding_experimentation_metrics.promotions_blocked += 1
                self._onboarding_experimentation_metrics.guardrail_blocks_total += 1
            elif decision_type == "rollback":
                self._onboarding_experimentation_metrics.rollbacks_triggered += 1
    
    def record_evaluation_run(self, significant_results: int = 0, insignificant_results: int = 0) -> None:
        """v32: Record weekly evaluation run."""
        with self._lock:
            self._onboarding_experimentation_metrics.evaluations_run_total += 1
            self._onboarding_experimentation_metrics.significant_results += significant_results
            self._onboarding_experimentation_metrics.insignificant_results += insignificant_results
            self._onboarding_experimentation_metrics.last_evaluation_at = datetime.now(timezone.utc).isoformat()
    
    def record_guardrail_block(self, violation_type: str) -> None:
        """v32: Record guardrail block."""
        with self._lock:
            self._onboarding_experimentation_metrics.guardrail_blocks_total += 1
            if violation_type == "sample_size":
                self._onboarding_experimentation_metrics.sample_size_violations += 1
            elif violation_type == "lift_threshold":
                self._onboarding_experimentation_metrics.lift_threshold_violations += 1
    
    def get_experimentation_metrics(self) -> OnboardingExperimentationMetrics:
        """v32: Get current experimentation metrics snapshot."""
        with self._lock:
            return OnboardingExperimentationMetrics(
                experiments_total=self._onboarding_experimentation_metrics.experiments_total,
                experiments_running=self._onboarding_experimentation_metrics.experiments_running,
                experiments_completed=self._onboarding_experimentation_metrics.experiments_completed,
                experiments_paused=self._onboarding_experimentation_metrics.experiments_paused,
                experiments_rolled_back=self._onboarding_experimentation_metrics.experiments_rolled_back,
                assignments_total=self._onboarding_experimentation_metrics.assignments_total,
                assignments_today=self._onboarding_experimentation_metrics.assignments_today,
                promotions_auto_applied=self._onboarding_experimentation_metrics.promotions_auto_applied,
                promotions_approved=self._onboarding_experimentation_metrics.promotions_approved,
                promotions_pending_approval=self._onboarding_experimentation_metrics.promotions_pending_approval,
                promotions_blocked=self._onboarding_experimentation_metrics.promotions_blocked,
                rollbacks_triggered=self._onboarding_experimentation_metrics.rollbacks_triggered,
                guardrail_blocks_total=self._onboarding_experimentation_metrics.guardrail_blocks_total,
                sample_size_violations=self._onboarding_experimentation_metrics.sample_size_violations,
                lift_threshold_violations=self._onboarding_experimentation_metrics.lift_threshold_violations,
                evaluations_run_total=self._onboarding_experimentation_metrics.evaluations_run_total,
                significant_results=self._onboarding_experimentation_metrics.significant_results,
                insignificant_results=self._onboarding_experimentation_metrics.insignificant_results,
                last_assignment_at=self._onboarding_experimentation_metrics.last_assignment_at,
                last_evaluation_at=self._onboarding_experimentation_metrics.last_evaluation_at,
                last_promotion_at=self._onboarding_experimentation_metrics.last_promotion_at,
                last_rollback_at=self._onboarding_experimentation_metrics.last_rollback_at,
            )


def _normalize_metric_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name.replace(":", "_"))
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if not sanitized:
        return "metric"
    if sanitized[0].isdigit():
        sanitized = f"m_{sanitized}"
    return sanitized.lower()


def render_prometheus(snapshot: dict[str, Any], *, prefix: str = "vm") -> str:
    lines: list[str] = []

    counts = snapshot.get("counts")
    if isinstance(counts, dict):
        for name in sorted(counts):
            metric_name = f"{prefix}_{_normalize_metric_name(str(name))}"
            value = int(counts[name])
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{metric_name} {value}")

    avg_latencies = snapshot.get("avg_latencies")
    if isinstance(avg_latencies, dict):
        for name in sorted(avg_latencies):
            metric_name = f"{prefix}_{_normalize_metric_name(str(name))}"
            value = float(avg_latencies[name])
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{metric_name} {value:.6f}")

    total_costs = snapshot.get("total_costs")
    if isinstance(total_costs, dict):
        for name in sorted(total_costs):
            metric_name = f"{prefix}_{_normalize_metric_name(str(name))}"
            value = float(total_costs[name])
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{metric_name} {value:.6f}")

    if not lines:
        lines.append("# no metrics recorded")
    return "\n".join(lines) + "\n"
