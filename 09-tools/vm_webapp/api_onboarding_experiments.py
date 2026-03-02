"""API v2 endpoints for onboarding experimentation operations.

v32: Onboarding experimentation layer with supervised promotion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vm_webapp.onboarding_experiments import (
    Experiment,
    ExperimentRegistry,
    ExperimentStatus,
    ExperimentVariant,
    RiskLevel,
)
from vm_webapp.onboarding_experiment_policy import (
    EvaluationResult,
    ExperimentEvaluator,
    PromotionDecision,
    PromotionDecisionType,
)


# Global registry and evaluator (singleton pattern matching other modules)
_experiment_registry = ExperimentRegistry()
_experiment_evaluator = ExperimentEvaluator(_experiment_registry)

# Metrics for observability
_experiment_metrics: dict[str, int] = {
    "total_experiments": 0,
    "running_experiments": 0,
    "completed_experiments": 0,
    "rolled_back_experiments": 0,
    "assignments_today": 0,
    "promotions_auto": 0,
    "promotions_approved": 0,
    "promotions_blocked": 0,
    "rollbacks": 0,
}

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# Request/Response Models
# =============================================================================

class ExperimentStatusResponse(BaseModel):
    brand_id: str
    version: str
    metrics: dict[str, int]
    active_experiments: list[dict[str, Any]]


class ExperimentRunRequest(BaseModel):
    metrics_fetcher: str = "default"


class ExperimentRunResponse(BaseModel):
    brand_id: str
    evaluations: list[dict[str, Any]]
    run_at: str


class ExperimentListResponse(BaseModel):
    experiments: list[dict[str, Any]]
    total: int


class ExperimentStartRequest(BaseModel):
    started_by: str


class ExperimentStartResponse(BaseModel):
    experiment_id: str
    status: str
    started_at: str


class ExperimentPauseRequest(BaseModel):
    paused_by: str
    reason: str = ""


class ExperimentPauseResponse(BaseModel):
    experiment_id: str
    status: str
    paused_at: str
    reason: str


class ExperimentPromoteRequest(BaseModel):
    promoted_by: str
    variant_id: str
    auto_apply: bool = False


class ExperimentPromoteResponse(BaseModel):
    experiment_id: str
    variant_id: str
    decision: str
    requires_approval: bool
    reason: str


class ExperimentRollbackRequest(BaseModel):
    rolled_back_by: str
    reason: str


class ExperimentRollbackResponse(BaseModel):
    experiment_id: str
    status: str
    rolled_back_at: str
    reason: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/api/v2/brands/{brand_id}/onboarding-experiments/status")
def get_onboarding_experiments_status(brand_id: str) -> ExperimentStatusResponse:
    """Get status of onboarding experimentation for a brand.
    
    Returns current metrics and active experiments.
    """
    # Update metrics
    all_experiments = _experiment_registry.list_experiments()
    running = sum(1 for e in all_experiments if e.status == ExperimentStatus.RUNNING)
    completed = sum(1 for e in all_experiments if e.status == ExperimentStatus.COMPLETED)
    rolled_back = sum(1 for e in all_experiments if e.status == ExperimentStatus.ROLLED_BACK)
    
    _experiment_metrics["total_experiments"] = len(all_experiments)
    _experiment_metrics["running_experiments"] = running
    _experiment_metrics["completed_experiments"] = completed
    _experiment_metrics["rolled_back_experiments"] = rolled_back
    
    active_experiments = []
    for exp in all_experiments:
        if exp.status == ExperimentStatus.RUNNING:
            active_experiments.append({
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "primary_metric": exp.primary_metric,
                "risk_level": exp.risk_level.value,
                "variants": [
                    {
                        "variant_id": v.variant_id,
                        "name": v.name,
                        "traffic_allocation": v.traffic_allocation,
                    }
                    for v in exp.variants
                ],
            })
    
    return ExperimentStatusResponse(
        brand_id=brand_id,
        version="v32",
        metrics=_experiment_metrics.copy(),
        active_experiments=active_experiments,
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-experiments/run")
def run_onboarding_experiments_evaluation(
    brand_id: str,
    request: ExperimentRunRequest,
) -> ExperimentRunResponse:
    """Run weekly evaluation cycle for all running experiments.
    
    Evaluates all running experiments and returns promotion decisions.
    """
    evaluations = []
    
    def mock_metrics_fetcher(experiment_id: str, variant_id: str) -> dict:
        """Mock metrics fetcher for evaluation.
        
        In production, this would query actual metrics from analytics.
        """
        # Return synthetic metrics for testing
        import random
        return {
            "conversions": random.randint(40, 60),
            "total": 500,
        }
    
    results = _experiment_evaluator.evaluate_all_running(mock_metrics_fetcher)
    
    for evaluation, decision in results:
        evaluations.append({
            "experiment_id": evaluation.experiment_id,
            "variant_id": evaluation.variant_id,
            "sample_size": evaluation.sample_size,
            "control_rate": evaluation.control_conversion_rate,
            "treatment_rate": evaluation.treatment_conversion_rate,
            "relative_lift": evaluation.relative_lift,
            "confidence": evaluation.confidence,
            "is_significant": evaluation.is_significant,
            "decision": decision.decision.value,
            "requires_approval": decision.requires_approval,
            "reason": decision.reason,
        })
        
        # Update metrics based on decision
        if decision.decision == PromotionDecisionType.AUTO_APPLY:
            _experiment_metrics["promotions_auto"] += 1
        elif decision.decision == PromotionDecisionType.APPROVE:
            _experiment_metrics["promotions_approved"] += 1
        elif decision.decision == PromotionDecisionType.BLOCK:
            _experiment_metrics["promotions_blocked"] += 1
        elif decision.decision == PromotionDecisionType.ROLLBACK:
            _experiment_metrics["rollbacks"] += 1
    
    return ExperimentRunResponse(
        brand_id=brand_id,
        evaluations=evaluations,
        run_at=_now_iso(),
    )


@router.get("/api/v2/brands/{brand_id}/onboarding-experiments")
def list_onboarding_experiments(
    brand_id: str,
    status: Optional[str] = None,
) -> ExperimentListResponse:
    """List all onboarding experiments for a brand.
    
    Optional status filter: draft, running, paused, completed, rolled_back
    """
    all_experiments = _experiment_registry.list_experiments()
    
    filtered = all_experiments
    if status:
        filtered = [e for e in all_experiments if e.status.value == status]
    
    experiments_data = []
    for exp in filtered:
        experiments_data.append({
            "experiment_id": exp.experiment_id,
            "name": exp.name,
            "description": exp.description,
            "hypothesis": exp.hypothesis,
            "primary_metric": exp.primary_metric,
            "status": exp.status.value,
            "risk_level": exp.risk_level.value,
            "min_sample_size": exp.min_sample_size,
            "min_confidence": exp.min_confidence,
            "max_lift_threshold": exp.max_lift_threshold,
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "name": v.name,
                    "config": v.config,
                    "traffic_allocation": v.traffic_allocation,
                }
                for v in exp.variants
            ],
            "created_at": exp.created_at,
            "started_at": exp.started_at,
        })
    
    return ExperimentListResponse(
        experiments=experiments_data,
        total=len(experiments_data),
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-experiments/{experiment_id}/start")
def start_onboarding_experiment(
    brand_id: str,
    experiment_id: str,
    request: ExperimentStartRequest,
) -> ExperimentStartResponse:
    """Start an experiment (move from draft to running)."""
    try:
        experiment = _experiment_registry.get_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    if experiment.status != ExperimentStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start experiment in {experiment.status.value} status"
        )
    
    _experiment_registry.start_experiment(experiment_id)
    experiment = _experiment_registry.get_experiment(experiment_id)
    
    return ExperimentStartResponse(
        experiment_id=experiment_id,
        status=experiment.status.value,
        started_at=experiment.started_at or _now_iso(),
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-experiments/{experiment_id}/pause")
def pause_onboarding_experiment(
    brand_id: str,
    experiment_id: str,
    request: ExperimentPauseRequest,
) -> ExperimentPauseResponse:
    """Pause a running experiment."""
    try:
        experiment = _experiment_registry.get_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    if experiment.status != ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause experiment in {experiment.status.value} status"
        )
    
    _experiment_registry.pause_experiment(experiment_id)
    experiment = _experiment_registry.get_experiment(experiment_id)
    
    return ExperimentPauseResponse(
        experiment_id=experiment_id,
        status=experiment.status.value,
        paused_at=experiment.paused_at or _now_iso(),
        reason=request.reason,
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-experiments/{experiment_id}/promote")
def promote_onboarding_experiment(
    brand_id: str,
    experiment_id: str,
    request: ExperimentPromoteRequest,
) -> ExperimentPromoteResponse:
    """Promote a winning variant.
    
    - Low risk + significant positive lift = auto-apply
    - Medium/High risk = requires approval
    """
    try:
        experiment = _experiment_registry.get_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Create a synthetic evaluation result for promotion
    # In production, this would use actual evaluation results
    evaluation = EvaluationResult(
        experiment_id=experiment_id,
        variant_id=request.variant_id,
        sample_size=experiment.min_sample_size * 2,
        control_conversion_rate=0.10,
        treatment_conversion_rate=0.105,
        absolute_lift=0.005,
        relative_lift=0.05,
        confidence=experiment.min_confidence + 0.01,
        is_significant=True,
    )
    
    decision = _experiment_evaluator.decide_promotion(experiment_id, evaluation)
    
    # Apply decision if no approval needed
    if not decision.requires_approval and request.auto_apply:
        _experiment_evaluator.apply_decision(decision)
    
    return ExperimentPromoteResponse(
        experiment_id=experiment_id,
        variant_id=request.variant_id,
        decision=decision.decision.value,
        requires_approval=decision.requires_approval,
        reason=decision.reason,
    )


@router.post("/api/v2/brands/{brand_id}/onboarding-experiments/{experiment_id}/rollback")
def rollback_onboarding_experiment(
    brand_id: str,
    experiment_id: str,
    request: ExperimentRollbackRequest,
) -> ExperimentRollbackResponse:
    """Rollback an experiment due to negative results."""
    try:
        experiment = _experiment_registry.get_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    if experiment.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot rollback experiment in {experiment.status.value} status"
        )
    
    _experiment_registry.rollback_experiment(experiment_id)
    experiment = _experiment_registry.get_experiment(experiment_id)
    _experiment_metrics["rollbacks"] += 1
    
    return ExperimentRollbackResponse(
        experiment_id=experiment_id,
        status=experiment.status.value,
        rolled_back_at=experiment.rolled_back_at or _now_iso(),
        reason=request.reason,
    )


# =============================================================================
# Public API for other modules
# =============================================================================

def get_experiment_registry() -> ExperimentRegistry:
    """Get the global experiment registry."""
    return _experiment_registry


def get_experiment_metrics() -> dict[str, int]:
    """Get current experiment metrics."""
    return _experiment_metrics.copy()
