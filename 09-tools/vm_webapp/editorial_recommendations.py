"""Motor de recomendações operacionais para governança editorial.

Analisa KPIs de insights e gera recomendações acionáveis com severidade,
motivo, ação sugerida e scores de priorização (impacto, esforço, prioridade).

Guardrails anti-ruído:
- Histerese mínima para evitar flapping de ações
- Cooldown por action_id baseado em eventos recentes
- Suppressão transparente com motivo
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

Severity = Literal["info", "warning", "critical"]

# Cooldown configuration: minimum time between same action recommendations
ACTION_COOLDOWN_EVENTS = 3  # Events that must pass before same action can reappear


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
    suppressed: bool = field(default=False)  # Whether action is suppressed
    suppression_reason: str = field(default="")  # Why action is suppressed

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


def _check_action_cooldown(
    action_id: str,
    recent_events: list[dict],
    cooldown_events: int = ACTION_COOLDOWN_EVENTS
) -> tuple[bool, str]:
    """Check if an action is in cooldown period.
    
    Args:
        action_id: The action ID to check
        recent_events: List of recent events (recommendations/actions taken)
        cooldown_events: Number of events that must pass before reappearance
    
    Returns:
        Tuple of (is_in_cooldown, reason)
    """
    if not recent_events:
        return False, ""
    
    # Count events since last occurrence of this action
    events_since_last = 0
    for event in recent_events:
        # Check if this event is the same action
        event_action = event.get("action_id") if isinstance(event, dict) else None
        if event_action == action_id:
            break
        events_since_last += 1
    
    # If action was found in recent events
    if events_since_last < len(recent_events):
        if events_since_last < cooldown_events:
            remaining = cooldown_events - events_since_last
            return True, f"Cooldown ativo: aguarde {remaining} eventos"
    
    return False, ""


def _apply_hysteresis(
    current_recommendations: list[EditorialRecommendation],
    previous_recommendations: list[EditorialRecommendation],
    threshold: int = 15
) -> list[EditorialRecommendation]:
    """Apply hysteresis to prevent flapping of recommendations.
    
    A recommendation will be kept if it was previously recommended and
    priority score hasn't changed significantly.
    
    Args:
        current_recommendations: Newly generated recommendations
        previous_recommendations: Previously shown recommendations
        threshold: Minimum priority score change to trigger update
    
    Returns:
        Stabilized list of recommendations
    """
    if not previous_recommendations:
        return current_recommendations
    
    # Build lookup for previous recommendations
    prev_by_action: dict[str, EditorialRecommendation] = {
        r.action_id: r for r in previous_recommendations
    }
    
    stabilized: list[EditorialRecommendation] = []
    
    for curr in current_recommendations:
        prev = prev_by_action.get(curr.action_id)
        
        if prev is None:
            # New recommendation, add as-is
            stabilized.append(curr)
        else:
            # Check if priority changed significantly
            priority_diff = abs(curr.priority_score - prev.priority_score)
            
            if priority_diff < threshold:
                # Keep previous state to prevent flapping
                # But update scores if they changed slightly
                stabilized.append(EditorialRecommendation(
                    severity=prev.severity,
                    reason=prev.reason,
                    action_id=prev.action_id,
                    title=prev.title,
                    description=prev.description,
                    impact_score=curr.impact_score,
                    effort_score=curr.effort_score,
                    suppressed=prev.suppressed,
                    suppression_reason=prev.suppression_reason,
                ))
            else:
                # Significant change, use current
                stabilized.append(curr)
    
    return stabilized


def analyze_baseline_none_rate(
    baseline_stats: dict,
    recent_events: list[dict] | None = None,
    threshold: float = 0.5
) -> EditorialRecommendation | None:
    """Analisa taxa de baseline none e recomenda criação de golden.

    Args:
        baseline_stats: dict com resolved_total e by_source
        recent_events: Lista de eventos recentes para cooldown check
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

    action_id = "create_objective_golden"
    
    # Check cooldown
    recent = recent_events or []
    in_cooldown, cooldown_reason = _check_action_cooldown(action_id, recent)

    metadata = _get_action_metadata(action_id)
    
    # Adjust impact based on severity
    impact = metadata["impact"]
    if rate > 0.8:
        impact = 10  # Critical

    return EditorialRecommendation(
        severity="warning" if rate < 0.8 else "critical",
        reason="baseline_none_rate_high",
        action_id=action_id,
        title="Criar Golden de Objetivo",
        description=f"{rate:.0%} das resoluções de baseline estão sem referência ({none_count}/{resolved}). Marque versões golden para melhorar a qualidade das comparações.",
        impact_score=impact,
        effort_score=metadata["effort"],
        suppressed=in_cooldown,
        suppression_reason=cooldown_reason if in_cooldown else "",
    )


def analyze_policy_denials(
    denied_total: int,
    recent_events: list[dict] | None = None,
    threshold: int = 3
) -> EditorialRecommendation | None:
    """Analisa denúncias de policy e recomenda revisão.

    Args:
        denied_total: total de tentativas negadas por policy
        recent_events: Lista de eventos recentes para cooldown check
        threshold: limite para considerar problemático (default 3)

    Returns:
        Recomendação se acima do threshold, None caso contrário
    """
    if denied_total < threshold:
        return None

    action_id = "review_brand_policy"
    
    # Check cooldown
    recent = recent_events or []
    in_cooldown, cooldown_reason = _check_action_cooldown(action_id, recent)

    metadata = _get_action_metadata(action_id)
    
    # Adjust impact based on severity
    impact = metadata["impact"]
    if denied_total >= 10:
        impact = 9  # High impact due to severity

    return EditorialRecommendation(
        severity="warning" if denied_total < 10 else "critical",
        reason="policy_denials_increasing",
        action_id=action_id,
        title="Revisar Policy da Brand",
        description=f"{denied_total} tentativas de marcação foram bloqueadas por policy. Considere ajustar as regras ou revisar os critérios de autorização.",
        impact_score=impact,
        effort_score=metadata["effort"],
        suppressed=in_cooldown,
        suppression_reason=cooldown_reason if in_cooldown else "",
    )


def analyze_recency_gap(
    last_marked_at: str | None,
    recent_events: list[dict] | None = None,
    gap_days: int = 7
) -> EditorialRecommendation | None:
    """Analisa ausência de marcações recentes.

    Args:
        last_marked_at: timestamp da última marcação ou None
        recent_events: Lista de eventos recentes para cooldown check
        gap_days: dias para considerar inatividade (default 7)

    Returns:
        Recomendação se inatividade detectada, None caso contrário
    """
    metadata = _get_action_metadata("run_editorial_review")
    
    action_id = "run_editorial_review"
    
    # Check cooldown
    recent = recent_events or []
    in_cooldown, cooldown_reason = _check_action_cooldown(action_id, recent)

    if last_marked_at is None:
        return EditorialRecommendation(
            severity="info",
            reason="no_golden_marks_yet",
            action_id=action_id,
            title="Rodar Revisão Editorial",
            description="Nenhuma marcação golden foi feita neste thread. Inicie uma revisão editorial para identificar versões de referência.",
            impact_score=metadata["impact"],
            effort_score=metadata["effort"],
            suppressed=in_cooldown,
            suppression_reason=cooldown_reason if in_cooldown else "",
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
            action_id=action_id,
            title="Rodar Revisão Editorial",
            description=f"Última marcação há {days_since} dias. Considere revisar novas versões para manter a qualidade do baseline.",
            impact_score=impact,
            effort_score=metadata["effort"],
            suppressed=in_cooldown,
            suppression_reason=cooldown_reason if in_cooldown else "",
        )
    except (ValueError, TypeError):
        return None


def analyze_low_global_coverage(
    by_scope: dict,
    marked_total: int,
    recent_events: list[dict] | None = None,
    threshold: float = 0.3
) -> EditorialRecommendation | None:
    """Analisa cobertura de golden global vs objetivo.

    Args:
        by_scope: dict com counts por scope
        marked_total: total de marcações
        recent_events: Lista de eventos recentes para cooldown check
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

    action_id = "create_global_golden"
    
    # Check cooldown
    recent = recent_events or []
    in_cooldown, cooldown_reason = _check_action_cooldown(action_id, recent)

    metadata = _get_action_metadata(action_id)
    
    # Adjust impact based on coverage rate
    impact = metadata["impact"]
    if rate < 0.2:
        impact = 9  # Very low coverage

    return EditorialRecommendation(
        severity="info",
        reason="low_global_coverage",
        action_id=action_id,
        title="Criar Golden Global",
        description=f"Apenas {rate:.0%} das marcações são globais. Considere marcar mais versões como referência global para o thread.",
        impact_score=impact,
        effort_score=metadata["effort"],
        suppressed=in_cooldown,
        suppression_reason=cooldown_reason if in_cooldown else "",
    )


def generate_recommendations(
    insights_data: dict,
    recent_events: list[dict] | None = None,
    previous_recommendations: list[EditorialRecommendation] | None = None
) -> list[EditorialRecommendation]:
    """Gera lista de recomendações baseada em dados de insights.

    Args:
        insights_data: dict retornado pelo endpoint /insights
        recent_events: Lista de eventos recentes para cooldown check
        previous_recommendations: Recomendações anteriores para histerese

    Returns:
        Lista de recomendações acionáveis ordenadas por priority_score desc
    """
    recommendations: list[EditorialRecommendation] = []

    # Análise de baseline none
    baseline = insights_data.get("baseline", {})
    if rec := analyze_baseline_none_rate(baseline, recent_events):
        recommendations.append(rec)

    # Análise de policy denials
    policy = insights_data.get("policy", {})
    if rec := analyze_policy_denials(policy.get("denied_total", 0), recent_events):
        recommendations.append(rec)

    # Análise de recency
    recency = insights_data.get("recency", {})
    if rec := analyze_recency_gap(recency.get("last_marked_at"), recent_events):
        recommendations.append(rec)

    # Análise de cobertura global
    totals = insights_data.get("totals", {})
    if rec := analyze_low_global_coverage(
        totals.get("by_scope", {}), totals.get("marked_total", 0), recent_events
    ):
        recommendations.append(rec)

    # Ordenar por priority_score descendente (maior prioridade primeiro)
    recommendations.sort(key=lambda r: r.priority_score, reverse=True)
    
    # Aplicar histerese para evitar flapping
    if previous_recommendations:
        recommendations = _apply_hysteresis(recommendations, previous_recommendations)

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
            "suppressed": r.suppressed,
            "suppression_reason": r.suppression_reason,
        }
        for r in recommendations
    ]
