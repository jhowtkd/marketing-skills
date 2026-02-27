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

    # Determinar foco recomendado
    recommended_focus = _determine_recommended_focus(drivers, risk_score)

    return EditorialForecast(
        risk_score=risk_score,
        trend=trend,
        drivers=drivers,
        recommended_focus=recommended_focus,
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
    }
