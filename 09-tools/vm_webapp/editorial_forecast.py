"""Forecast preditivo para governança editorial.

Módulo de forecast determinístico e explicável para avaliação de risco
e tendências de governança editorial. Usa heurísticas baseadas em métricas
existentes sem depender de ML externo.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

Trend = Literal["improving", "stable", "degrading"]


@dataclass
class EditorialForecast:
    """Forecast de risco editorial para um thread."""

    risk_score: int  # 0-100
    trend: Trend
    drivers: list[str]
    recommended_focus: str
    confidence: float  # 0-1
    volatility: int  # 0-100
    calibration_notes: list[str]


def _calculate_window_metrics(events: list[dict], short_window: int = 7, long_window: int = 30) -> dict:
    """Calculate metrics for short and long windows.
    
    Args:
        events: List of event dicts with 'occurred_at' timestamp
        short_window: Short window size in days (default 7)
        long_window: Long window size in days (default 30)
    
    Returns:
        Dict with short_window_count, long_window_count, and recency_ratio
    """
    if not events:
        return {"short_window_count": 0, "long_window_count": 0, "recency_ratio": 0.0}
    
    now = datetime.now(timezone.utc)
    
    def days_since_event(event: dict) -> int:
        try:
            event_dt = datetime.fromisoformat(str(event.get("occurred_at", "")).replace("Z", "+00:00"))
            return (now - event_dt).days
        except (ValueError, TypeError):
            return long_window + 1  # Assume old if invalid
    
    short_count = sum(1 for e in events if days_since_event(e) <= short_window)
    long_count = sum(1 for e in events if days_since_event(e) <= long_window)
    
    # Recency ratio: how concentrated events are in short vs long window
    recency_ratio = short_count / long_count if long_count > 0 else 0.0
    
    return {
        "short_window_count": short_count,
        "long_window_count": long_count,
        "recency_ratio": recency_ratio,
    }


def _calculate_confidence(
    insights_data: dict,
    window_metrics: dict,
    driver_count: int
) -> float:
    """Calculate confidence score (0-1) based on data quality.
    
    Higher confidence when:
    - More data points (resolved_total)
    - More recent activity (recency_ratio)
    - Clear drivers (not ambiguous)
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    confidence = 0.5  # Base confidence
    
    # Data volume factor (0-0.3)
    resolved_total = insights_data.get("baseline", {}).get("resolved_total", 0)
    if resolved_total >= 10:
        confidence += 0.3
    elif resolved_total >= 5:
        confidence += 0.2
    elif resolved_total >= 1:
        confidence += 0.1
    
    # Recency factor (0-0.3)
    recency_ratio = window_metrics.get("recency_ratio", 0)
    if recency_ratio >= 0.5:
        confidence += 0.3
    elif recency_ratio >= 0.3:
        confidence += 0.2
    elif recency_ratio > 0:
        confidence += 0.1
    
    # Driver clarity factor (0-0.2)
    # More drivers = more signals = higher confidence
    if driver_count >= 3:
        confidence += 0.2
    elif driver_count >= 2:
        confidence += 0.1
    elif driver_count == 0:
        confidence -= 0.1  # No drivers reduces confidence
    
    # Golden marks factor (0-0.2)
    marked_total = insights_data.get("totals", {}).get("marked_total", 0)
    if marked_total >= 5:
        confidence += 0.2
    elif marked_total >= 2:
        confidence += 0.1
    elif marked_total == 0:
        confidence -= 0.1  # No golden marks reduces confidence
    
    return max(0.0, min(1.0, confidence))


def _calculate_volatility(
    insights_data: dict,
    window_metrics: dict
) -> int:
    """Calculate volatility score (0-100) based on recent activity variance.
    
    Higher volatility when:
    - Big gap between short and long window activity
    - High policy denial rate
    - Inconsistent baseline resolution
    
    Returns:
        Volatility score between 0 and 100
    """
    volatility = 30  # Base volatility (moderate)
    
    # Recency volatility (0-40)
    short_count = window_metrics.get("short_window_count", 0)
    long_count = window_metrics.get("long_window_count", 0)
    
    if long_count > 0:
        activity_ratio = short_count / long_count
        # High ratio = recent burst = high volatility
        # Low ratio with long activity = stable = low volatility
        if activity_ratio > 0.8:
            volatility += 40  # Recent burst
        elif activity_ratio > 0.5:
            volatility += 25
        elif activity_ratio > 0.2:
            volatility += 10
        else:
            volatility -= 10  # Stable pattern
    
    # Policy denial volatility (0-20)
    denied_total = insights_data.get("policy", {}).get("denied_total", 0)
    marked_total = insights_data.get("totals", {}).get("marked_total", 0)
    total_attempts = denied_total + marked_total
    
    if total_attempts > 0:
        denial_rate = denied_total / total_attempts
        if denial_rate > 0.3:
            volatility += 20  # High denial rate = unstable
        elif denial_rate > 0.1:
            volatility += 10
    
    # Baseline source volatility (0-10)
    by_source = insights_data.get("baseline", {}).get("by_source", {})
    resolved_total = sum(by_source.values()) if by_source else 0
    if resolved_total > 0:
        none_rate = by_source.get("none", 0) / resolved_total
        if none_rate > 0.5:
            volatility += 10  # Unstable baseline
    
    return max(0, min(100, volatility))


def _generate_calibration_notes(
    insights_data: dict,
    window_metrics: dict,
    confidence: float,
    volatility: int
) -> list[str]:
    """Generate human-readable calibration notes.
    
    Returns:
        List of calibration notes explaining the forecast
    """
    notes: list[str] = []
    
    # Window analysis
    short_count = window_metrics.get("short_window_count", 0)
    long_count = window_metrics.get("long_window_count", 0)
    
    if short_count > 0 and long_count > short_count * 2:
        notes.append(f"Atividade concentrada: {short_count} eventos recentes vs {long_count} total")
    elif short_count == 0 and long_count > 0:
        notes.append("Sem atividade nos últimos 7 dias - risco de staleness")
    elif short_count >= 3:
        notes.append(f"Alta atividade recente: {short_count} eventos na última semana")
    
    # Confidence explanation
    if confidence >= 0.8:
        notes.append("Alta confiança: dados históricos robustos")
    elif confidence >= 0.6:
        notes.append("Confiança moderada: tendência consistente nos dados")
    elif confidence >= 0.4:
        notes.append("Confiança baixa: dados limitados ou inconsistentes")
    else:
        notes.append("Confiança muito baixa: insuficiência de dados")
    
    # Volatility explanation
    if volatility >= 70:
        notes.append("Alta volatilidade: padrões instáveis detectados")
    elif volatility >= 40:
        notes.append("Volatilidade moderada: alguma variabilidade nos eventos")
    else:
        notes.append("Baixa volatilidade: padrão estável")
    
    # Data volume note
    resolved_total = insights_data.get("baseline", {}).get("resolved_total", 0)
    if resolved_total < 3:
        notes.append(f"Amostra pequena: apenas {resolved_total} resoluções de baseline")
    
    return notes[:4]  # Limit to 4 notes max


def calculate_forecast(insights_data: dict) -> EditorialForecast:
    """Calcula forecast editorial baseado em dados de insights.

    Heurísticas determinísticas:
    - baseline_none_rate > 0.5: +30 risco
    - policy_denied > 0: +20 risco
    - recency_gap > 7 dias: +15 risco
    - recency_gap > 14 dias: +25 risco
    - low_global_coverage (< 30%): +10 risco
    - no_golden_marks: +40 risco

    Trend:
    - improving: baseline_none_rate diminuindo OU marcas recentes
    - degrading: baseline_none_rate alto E sem marcas recentes
    - stable: outros casos
    
    Calibration:
    - confidence: baseado em volume de dados, recency, driver count
    - volatility: baseado em variação de atividade recente
    - calibration_notes: explicações operacionais
    """
    risk_score = 0
    drivers: list[str] = []

    # Análise de baseline none
    baseline = insights_data.get("baseline", {})
    resolved_total = baseline.get("resolved_total", 0)
    by_source = baseline.get("by_source", {})
    none_count = by_source.get("none", 0)

    if resolved_total > 0:
        none_rate = none_count / resolved_total
        if none_rate > 0.7:
            risk_score += 40
            drivers.append("baseline_none_rate_critical")
        elif none_rate > 0.5:
            risk_score += 30
            drivers.append("baseline_none_rate_high")
        elif none_rate > 0.3:
            risk_score += 15
            drivers.append("baseline_none_rate_moderate")
    else:
        # Sem dados de baseline = incerteza máxima
        risk_score += 30
        drivers.append("no_baseline_data")

    # Análise de policy denials
    policy = insights_data.get("policy", {})
    denied_total = policy.get("denied_total", 0)
    if denied_total > 5:
        risk_score += 25
        drivers.append("policy_denials_critical")
    elif denied_total > 0:
        risk_score += 15
        drivers.append("policy_denials_present")

    # Análise de recency
    recency = insights_data.get("recency", {})
    last_marked_at = recency.get("last_marked_at")
    marked_total = insights_data.get("totals", {}).get("marked_total", 0)

    if marked_total == 0:
        risk_score += 40
        drivers.append("no_golden_marks")
    elif last_marked_at is None:
        risk_score += 25
        drivers.append("recency_gap_unknown")
    else:
        try:
            last_dt = datetime.fromisoformat(last_marked_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_since = (now - last_dt).days

            if days_since > 14:
                risk_score += 25
                drivers.append("recency_gap_large")
            elif days_since > 7:
                risk_score += 15
                drivers.append("recency_gap_moderate")
        except (ValueError, TypeError):
            risk_score += 10
            drivers.append("recency_gap_invalid")

    # Análise de cobertura global
    totals = insights_data.get("totals", {})
    by_scope = totals.get("by_scope", {})
    global_count = by_scope.get("global", 0)
    marked_total_for_coverage = totals.get("marked_total", 0)

    if marked_total_for_coverage > 0:
        global_rate = global_count / marked_total_for_coverage
        if global_rate < 0.2:
            risk_score += 15
            drivers.append("low_global_coverage")
        elif global_rate < 0.3:
            risk_score += 10
            drivers.append("moderate_global_coverage")

    # Limitar score a 0-100
    risk_score = max(0, min(100, risk_score))

    # Determinar trend
    trend: Trend = "stable"
    if marked_total == 0:
        trend = "degrading"
    elif denied_total > 3:
        trend = "degrading"
    elif last_marked_at and days_since is not None and days_since < 3:  # type: ignore
        trend = "improving"
    elif none_rate < 0.3 and marked_total > 2:  # type: ignore
        trend = "improving"

    # Build events list for window analysis
    # Approximate events from insights data
    events: list[dict] = []
    
    # Add golden marked events (approximate)
    for _ in range(marked_total):
        if last_marked_at:
            events.append({"occurred_at": last_marked_at})
    
    # Add policy denied events
    for _ in range(denied_total):
        events.append({"occurred_at": last_marked_at or datetime.now(timezone.utc).isoformat()})
    
    # Calculate window metrics
    window_metrics = _calculate_window_metrics(events)
    
    # Calculate confidence and volatility
    confidence = _calculate_confidence(insights_data, window_metrics, len(drivers))
    volatility = _calculate_volatility(insights_data, window_metrics)
    
    # Generate calibration notes
    calibration_notes = _generate_calibration_notes(
        insights_data, window_metrics, confidence, volatility
    )

    # Determinar foco recomendado
    recommended_focus = _determine_recommended_focus(drivers, risk_score)

    return EditorialForecast(
        risk_score=risk_score,
        trend=trend,
        drivers=drivers,
        recommended_focus=recommended_focus,
        confidence=confidence,
        volatility=volatility,
        calibration_notes=calibration_notes,
    )


def _determine_recommended_focus(drivers: list[str], risk_score: int) -> str:
    """Determina o foco recomendado baseado nos drivers de risco."""
    if "baseline_none_rate_critical" in drivers:
        return "Criar golden references urgentemente"
    if "no_golden_marks" in drivers:
        return "Iniciar marcações golden no thread"
    if "policy_denials_critical" in drivers:
        return "Revisar políticas de editorial"
    if "recency_gap_large" in drivers:
        return "Atualizar marcações golden"
    if "baseline_none_rate_high" in drivers:
        return "Aumentar cobertura de golden"
    if risk_score > 50:
        return "Revisar governança editorial"
    if risk_score > 30:
        return "Monitorar métricas de baseline"
    return "Manter práticas atuais"


def forecast_to_dict(forecast: EditorialForecast) -> dict:
    """Converte forecast para formato JSON serializável."""
    return {
        "risk_score": forecast.risk_score,
        "trend": forecast.trend,
        "drivers": forecast.drivers,
        "recommended_focus": forecast.recommended_focus,
        "confidence": forecast.confidence,
        "volatility": forecast.volatility,
        "calibration_notes": forecast.calibration_notes,
    }
