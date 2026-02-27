"""Motor de recomendações operacionais para governança editorial.

Analisa KPIs de insights e gera recomendações acionáveis com severidade,
motivo, ação sugerida e scores de priorização (impacto, esforço, prioridade).
"""

from dataclasses import dataclass, field
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
    impact_score: int = field(default=5)  # 1-10 (higher = more impact)
    effort_score: int = field(default=5)  # 1-10 (higher = more effort)

    @property
    def priority_score(self) -> int:
        """Calculate priority score based on impact and effort.
        
        Formula: impact * 10 - effort * 3
        Higher impact increases priority, higher effort decreases it.
        Range: approximately -20 to 97
        """
        return self.impact_score * 10 - self.effort_score * 3

    @property
    def why_priority(self) -> str:
        """Generate human-readable explanation for priority."""
        if self.priority_score >= 70:
            return f"Alto impacto ({self.impact_score}/10) com esforço moderado ({self.effort_score}/10)"
        elif self.priority_score >= 50:
            return f"Bom equilíbrio entre impacto ({self.impact_score}/10) e esforço ({self.effort_score}/10)"
        elif self.priority_score >= 30:
            return f"Impacto moderado ({self.impact_score}/10) - considerar quando houver capacidade"
        else:
            return f"Requer mais esforço ({self.effort_score}/10) para o impacto ({self.impact_score}/10)"


# Impact and effort mapping for different action types
ACTION_METADATA: dict[str, dict[str, int]] = {
    "create_objective_golden": {"impact": 9, "effort": 4},
    "create_global_golden": {"impact": 8, "effort": 6},
    "review_brand_policy": {"impact": 7, "effort": 8},
    "run_editorial_review": {"impact": 8, "effort": 5},
}


def _get_action_metadata(action_id: str) -> dict[str, int]:
    """Get impact and effort scores for an action."""
    return ACTION_METADATA.get(action_id, {"impact": 5, "effort": 5})


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

    metadata = _get_action_metadata("create_objective_golden")
    
    # Adjust impact based on severity
    impact = metadata["impact"]
    if rate > 0.8:
        impact = 10  # Critical

    return EditorialRecommendation(
        severity="warning" if rate < 0.8 else "critical",
        reason="baseline_none_rate_high",
        action_id="create_objective_golden",
        title="Criar Golden de Objetivo",
        description=f"{rate:.0%} das resoluções de baseline estão sem referência ({none_count}/{resolved}). Marque versões golden para melhorar a qualidade das comparações.",
        impact_score=impact,
        effort_score=metadata["effort"],
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

    metadata = _get_action_metadata("review_brand_policy")
    
    # Adjust impact based on severity
    impact = metadata["impact"]
    if denied_total >= 10:
        impact = 9  # High impact due to severity

    return EditorialRecommendation(
        severity="warning" if denied_total < 10 else "critical",
        reason="policy_denials_increasing",
        action_id="review_brand_policy",
        title="Revisar Policy da Brand",
        description=f"{denied_total} tentativas de marcação foram bloqueadas por policy. Considere ajustar as regras ou revisar os critérios de autorização.",
        impact_score=impact,
        effort_score=metadata["effort"],
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
    metadata = _get_action_metadata("run_editorial_review")
    
    if last_marked_at is None:
        return EditorialRecommendation(
            severity="info",
            reason="no_golden_marks_yet",
            action_id="run_editorial_review",
            title="Rodar Revisão Editorial",
            description="Nenhuma marcação golden foi feita neste thread. Inicie uma revisão editorial para identificar versões de referência.",
            impact_score=metadata["impact"],
            effort_score=metadata["effort"],
        )

    try:
        last_dt = datetime.fromisoformat(last_marked_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_since = (now - last_dt).days

        if days_since < gap_days:
            return None

        # Adjust impact based on recency gap
        impact = metadata["impact"]
        if days_since > 14:
            impact = 9  # Higher impact for larger gaps

        return EditorialRecommendation(
            severity="info" if days_since < 14 else "warning",
            reason="recent_marks_absent",
            action_id="run_editorial_review",
            title="Rodar Revisão Editorial",
            description=f"Última marcação há {days_since} dias. Considere revisar novas versões para manter a qualidade do baseline.",
            impact_score=impact,
            effort_score=metadata["effort"],
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

    metadata = _get_action_metadata("create_global_golden")
    
    # Adjust impact based on coverage rate
    impact = metadata["impact"]
    if rate < 0.2:
        impact = 9  # Very low coverage

    return EditorialRecommendation(
        severity="info",
        reason="low_global_coverage",
        action_id="create_global_golden",
        title="Criar Golden Global",
        description=f"Apenas {rate:.0%} das marcações são globais. Considere marcar mais versões como referência global para o thread.",
        impact_score=impact,
        effort_score=metadata["effort"],
    )


def generate_recommendations(insights_data: dict) -> list[EditorialRecommendation]:
    """Gera lista de recomendações baseada em dados de insights.

    Args:
        insights_data: dict retornado pelo endpoint /insights

    Returns:
        Lista de recomendações acionáveis ordenadas por priority_score desc
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

    # Ordenar por priority_score descendente (maior prioridade primeiro)
    recommendations.sort(key=lambda r: r.priority_score, reverse=True)

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
            "impact_score": r.impact_score,
            "effort_score": r.effort_score,
            "priority_score": r.priority_score,
            "why_priority": r.why_priority,
        }
        for r in recommendations
    ]
