"""Editorial drift detector for governance quality monitoring.

Detects when editorial governance metrics deviate from expected thresholds
and provides actionable recommendations for remediation.
"""

from dataclasses import dataclass
from typing import Literal

DriftSeverity = Literal["none", "low", "medium", "high"]


@dataclass
class DriftResult:
    """Result of drift detection analysis."""
    
    drift_score: int  # 0-100
    drift_severity: DriftSeverity
    drift_flags: list[str]
    primary_driver: str
    recommended_actions: list[str]
    details: dict


# Drift detection thresholds
DRIFT_THRESHOLDS = {
    "baseline_none_rate": {"warning": 0.4, "critical": 0.6},
    "policy_denied_rate": {"warning": 0.15, "critical": 0.25},
    "confidence": {"warning": 0.5, "critical": 0.3},
    "volatility": {"warning": 60, "critical": 80},
}

# Drift score weights
DRIFT_WEIGHTS = {
    "baseline_none_rate": 25,
    "policy_denied_rate": 20,
    "low_confidence": 20,
    "high_volatility": 20,
    "slo_violation": 15,
}


def detect_drift(
    insights_data: dict,
    forecast_data: dict,
    slo_config: dict | None = None,
) -> DriftResult:
    """Detect editorial governance drift based on metrics and forecast.
    
    Args:
        insights_data: Thread insights with totals, policy, baseline
        forecast_data: Forecast data with confidence, volatility
        slo_config: SLO configuration (optional, uses defaults if not provided)
    
    Returns:
        DriftResult with score, severity, flags, and recommendations
    """
    drift_flags: list[str] = []
    details: dict = {}
    drift_score = 0
    
    # Use SLO config or defaults
    slo = slo_config or {
        "max_baseline_none_rate": 0.5,
        "max_policy_denied_rate": 0.2,
        "min_confidence": 0.4,
    }
    
    # Analyze baseline none rate
    baseline = insights_data.get("baseline", {})
    by_source = baseline.get("by_source", {})
    resolved_total = sum(by_source.values()) if by_source else 0
    none_count = by_source.get("none", 0)
    
    if resolved_total > 0:
        baseline_none_rate = none_count / resolved_total
        max_none_rate = slo.get("max_baseline_none_rate", 0.5)
        
        details["baseline_none_rate"] = baseline_none_rate
        details["baseline_none_count"] = none_count
        details["baseline_resolved_total"] = resolved_total
        
        if baseline_none_rate > max_none_rate:
            drift_flags.append("baseline_none_rate_exceeded")
            drift_score += DRIFT_WEIGHTS["baseline_none_rate"]
        elif baseline_none_rate > max_none_rate * 0.8:
            drift_flags.append("baseline_none_rate_warning")
            drift_score += DRIFT_WEIGHTS["baseline_none_rate"] // 2
    
    # Analyze policy denied rate
    policy = insights_data.get("policy", {})
    denied_total = policy.get("denied_total", 0)
    marked_total = insights_data.get("totals", {}).get("marked_total", 0)
    total_attempts = denied_total + marked_total
    
    if total_attempts > 0:
        denied_rate = denied_total / total_attempts
        max_denied_rate = slo.get("max_policy_denied_rate", 0.2)
        
        details["policy_denied_rate"] = denied_rate
        details["policy_denied_total"] = denied_total
        details["policy_total_attempts"] = total_attempts
        
        if denied_rate > max_denied_rate:
            drift_flags.append("policy_denied_rate_exceeded")
            drift_score += DRIFT_WEIGHTS["policy_denied_rate"]
        elif denied_rate > max_denied_rate * 0.8:
            drift_flags.append("policy_denied_rate_warning")
            drift_score += DRIFT_WEIGHTS["policy_denied_rate"] // 2
    
    # Analyze forecast confidence
    confidence = forecast_data.get("confidence", 0.0)
    min_confidence = slo.get("min_confidence", 0.4)
    
    details["forecast_confidence"] = confidence
    
    if confidence < min_confidence:
        drift_flags.append("low_confidence")
        drift_score += DRIFT_WEIGHTS["low_confidence"]
        # Additional score based on how far below threshold
        confidence_gap = min_confidence - confidence
        drift_score += int(confidence_gap * 50)  # Up to 25 additional points
    
    # Analyze volatility
    volatility = forecast_data.get("volatility", 0)
    details["forecast_volatility"] = volatility
    
    if volatility > DRIFT_THRESHOLDS["volatility"]["critical"]:
        drift_flags.append("high_volatility_critical")
        drift_score += DRIFT_WEIGHTS["high_volatility"]
    elif volatility > DRIFT_THRESHOLDS["volatility"]["warning"]:
        drift_flags.append("high_volatility_warning")
        drift_score += DRIFT_WEIGHTS["high_volatility"] // 2
    
    # Check forecast risk score trend
    risk_score = forecast_data.get("risk_score", 0)
    trend = forecast_data.get("trend", "stable")
    
    details["forecast_risk_score"] = risk_score
    details["forecast_trend"] = trend
    
    if risk_score > 70 and trend == "degrading":
        drift_flags.append("high_risk_degrading")
        drift_score += DRIFT_WEIGHTS["slo_violation"]
    elif risk_score > 50 and trend == "degrading":
        drift_flags.append("moderate_risk_degrading")
        drift_score += DRIFT_WEIGHTS["slo_violation"] // 2
    
    # Determine severity
    drift_score = min(100, drift_score)  # Cap at 100
    
    if drift_score >= 70:
        severity: DriftSeverity = "high"
    elif drift_score >= 40:
        severity = "medium"
    elif drift_score >= 15:
        severity = "low"
    else:
        severity = "none"
    
    # Determine primary driver
    primary_driver = _determine_primary_driver(drift_flags, details)
    
    # Generate recommendations
    recommended_actions = _generate_recommendations(drift_flags, details)
    
    return DriftResult(
        drift_score=drift_score,
        drift_severity=severity,
        drift_flags=drift_flags,
        primary_driver=primary_driver,
        recommended_actions=recommended_actions,
        details=details,
    )


def _determine_primary_driver(drift_flags: list[str], details: dict) -> str:
    """Determine the primary driver of drift."""
    if not drift_flags:
        return "none"
    
    # Priority order for primary driver
    priority_flags = [
        "baseline_none_rate_exceeded",
        "high_risk_degrading",
        "policy_denied_rate_exceeded",
        "low_confidence",
        "high_volatility_critical",
    ]
    
    for flag in priority_flags:
        if flag in drift_flags:
            return flag
    
    return drift_flags[0]


def _generate_recommendations(drift_flags: list[str], details: dict) -> list[str]:
    """Generate recommended actions based on drift flags."""
    recommendations: list[str] = []
    
    if "baseline_none_rate_exceeded" in drift_flags or "baseline_none_rate_warning" in drift_flags:
        rate = details.get("baseline_none_rate", 0)
        if rate > 0.7:
            recommendations.append("Criar golden references urgentemente")
        else:
            recommendations.append("Aumentar cobertura de golden marks")
    
    if "policy_denied_rate_exceeded" in drift_flags:
        recommendations.append("Revisar políticas de editorial e permissões")
    
    if "low_confidence" in drift_flags:
        recommendations.append("Coletar mais dados para aumentar confiança do forecast")
    
    if "high_volatility_critical" in drift_flags or "high_volatility_warning" in drift_flags:
        recommendations.append("Investigar fontes de instabilidade no padrão de eventos")
    
    if "high_risk_degrading" in drift_flags:
        recommendations.append("Executar revisão editorial completa imediatamente")
    elif "moderate_risk_degrading" in drift_flags:
        recommendations.append("Agendar revisão editorial preventiva")
    
    if not recommendations:
        recommendations.append("Manter monitoramento contínuo")
    
    return recommendations[:3]  # Limit to top 3 recommendations


def drift_to_dict(drift: DriftResult) -> dict:
    """Convert DriftResult to JSON-serializable dictionary."""
    return {
        "drift_score": drift.drift_score,
        "drift_severity": drift.drift_severity,
        "drift_flags": drift.drift_flags,
        "primary_driver": drift.primary_driver,
        "recommended_actions": drift.recommended_actions,
        "details": drift.details,
    }
