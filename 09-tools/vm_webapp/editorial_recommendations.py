"""Motor de recomendações operacionais para governança editorial.

Analisa KPIs de insights e gera recomendações acionáveis com severidade,
motivo e ação sugerida.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

Severity = Literal["info", "warning", "critical"]


@dataclass
class EditorialRecommendation:
    """Recomendação acionável para governança editorial."""

    severity: Severity
    reason: str
    action_id: str
    title: str
    description: str


def analyze_baseline_none_rate(
    baseline_stats: dict, threshold: float = 0.5
) -> EditorialRecommendation | None:
    """Analisa taxa de baseline none e recomenda criação de golden.

    Args:
        baseline_stats: dict com resolved_total e by_source
        threshold: limite para considerar alta (default 50%)

    Returns:
        Recomendação se taxa acima do threshold, None caso contrário
    """
    resolved = baseline_stats.get("resolved_total", 0)
    none_count = baseline_stats.get("by_source", {}).get("none", 0)

    if resolved == 0:
        return None

    rate = none_count / resolved
    if rate < threshold:
        return None

    return EditorialRecommendation(
        severity="warning" if rate < 0.8 else "critical",
        reason="baseline_none_rate_high",
        action_id="create_objective_golden",
        title="Criar Golden de Objetivo",
        description=f"{rate:.0%} das resoluções de baseline estão sem referência ({none_count}/{resolved}). Marque versões golden para melhorar a qualidade das comparações.",
    )


def analyze_policy_denials(
    denied_total: int, threshold: int = 3
) -> EditorialRecommendation | None:
    """Analisa denúncias de policy e recomenda revisão.

    Args:
        denied_total: total de tentativas negadas por policy
        threshold: limite para considerar problemático (default 3)

    Returns:
        Recomendação se acima do threshold, None caso contrário
    """
    if denied_total < threshold:
        return None

    return EditorialRecommendation(
        severity="warning" if denied_total < 10 else "critical",
        reason="policy_denials_increasing",
        action_id="review_brand_policy",
        title="Revisar Policy da Brand",
        description=f"{denied_total} tentativas de marcação foram bloqueadas por policy. Considere ajustar as regras ou revisar os critérios de autorização.",
    )


def analyze_recency_gap(
    last_marked_at: str | None, gap_days: int = 7
) -> EditorialRecommendation | None:
    """Analisa ausência de marcações recentes.

    Args:
        last_marked_at: timestamp da última marcação ou None
        gap_days: dias para considerar inatividade (default 7)

    Returns:
        Recomendação se inatividade detectada, None caso contrário
    """
    if last_marked_at is None:
        return EditorialRecommendation(
            severity="info",
            reason="no_golden_marks_yet",
            action_id="run_editorial_review",
            title="Rodar Revisão Editorial",
            description="Nenhuma marcação golden foi feita neste thread. Inicie uma revisão editorial para identificar versões de referência.",
        )

    try:
        last_dt = datetime.fromisoformat(last_marked_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_since = (now - last_dt).days

        if days_since < gap_days:
            return None

        return EditorialRecommendation(
            severity="info" if days_since < 14 else "warning",
            reason="recent_marks_absent",
            action_id="run_editorial_review",
            title="Rodar Revisão Editorial",
            description=f"Última marcação há {days_since} dias. Considere revisar novas versões para manter a qualidade do baseline.",
        )
    except (ValueError, TypeError):
        return None


def analyze_low_global_coverage(
    by_scope: dict, marked_total: int, threshold: float = 0.3
) -> EditorialRecommendation | None:
    """Analisa cobertura de golden global vs objetivo.

    Args:
        by_scope: dict com counts por scope
        marked_total: total de marcações
        threshold: proporção mínima de global (default 30%)

    Returns:
        Recomendação se cobertura baixa, None caso contrário
    """
    if marked_total == 0:
        return None

    global_count = by_scope.get("global", 0)
    rate = global_count / marked_total

    if rate >= threshold:
        return None

    return EditorialRecommendation(
        severity="info",
        reason="low_global_coverage",
        action_id="create_global_golden",
        title="Criar Golden Global",
        description=f"Apenas {rate:.0%} das marcações são globais. Considere marcar mais versões como referência global para o thread.",
    )


def generate_recommendations(insights_data: dict) -> list[EditorialRecommendation]:
    """Gera lista de recomendações baseada em dados de insights.

    Args:
        insights_data: dict retornado pelo endpoint /insights

    Returns:
        Lista de recomendações acionáveis (pode ser vazia)
    """
    recommendations: list[EditorialRecommendation] = []

    # Análise de baseline none
    baseline = insights_data.get("baseline", {})
    if rec := analyze_baseline_none_rate(baseline):
        recommendations.append(rec)

    # Análise de policy denials
    policy = insights_data.get("policy", {})
    if rec := analyze_policy_denials(policy.get("denied_total", 0)):
        recommendations.append(rec)

    # Análise de recency
    recency = insights_data.get("recency", {})
    if rec := analyze_recency_gap(recency.get("last_marked_at")):
        recommendations.append(rec)

    # Análise de cobertura global
    totals = insights_data.get("totals", {})
    if rec := analyze_low_global_coverage(
        totals.get("by_scope", {}), totals.get("marked_total", 0)
    ):
        recommendations.append(rec)

    # Ordenar por severidade: critical > warning > info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    recommendations.sort(key=lambda r: severity_order.get(r.severity, 3))

    return recommendations


def recommendations_to_dict(recommendations: list[EditorialRecommendation]) -> list[dict]:
    """Converte lista de recomendações para formato JSON serializável."""
    return [
        {
            "severity": r.severity,
            "reason": r.reason,
            "action_id": r.action_id,
            "title": r.title,
            "description": r.description,
        }
        for r in recommendations
    ]
