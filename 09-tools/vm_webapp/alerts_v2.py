"""Agregador determinístico de alertas editoriais para SLO Alerts Hub.

Combina múltiplas fontes de alertas:
- SLO violations (baseline_none_rate, policy_denied_rate)
- Drift alerts (quando drift_severity é medium/high)
- Baseline-none alerts (quando source=none)
- Policy-denied alerts (tentativas negadas)

Retorna alertas ordenados por severidade com metadados ricos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Severity = Literal["critical", "warning", "info"]
AlertType = Literal["slo_violation", "drift_detected", "baseline_none", "policy_denied", "forecast_risk"]
AlertStatus = Literal["active", "acknowledged", "resolved"]


@dataclass
class EditorialAlert:
    """Alerta editorial com metadados completos para o Studio."""
    
    alert_id: str
    alert_type: AlertType
    severity: Severity
    status: AlertStatus
    title: str
    description: str
    causa: str
    recomendacao: str
    created_at: str
    updated_at: str
    metadata: dict = field(default_factory=dict)


def _now_iso() -> str:
    """Retorna timestamp ISO atual."""
    return datetime.now(timezone.utc).isoformat()


def _generate_alert_id(alert_type: str, suffix: str = "") -> str:
    """Gera ID único para o alerta."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    if suffix:
        return f"alert-{alert_type}-{suffix}-{timestamp}"
    return f"alert-{alert_type}-{timestamp}"


def aggregate_alerts(
    insights_data: dict,
    drift_data: dict | None = None,
    forecast_data: dict | None = None,
    thread_id: str = "",
) -> list[EditorialAlert]:
    """Agrega alertas de múltiplas fontes em lista única ordenada por severidade.
    
    Args:
        insights_data: Dados de insights do thread (totals, policy, baseline)
        drift_data: Dados de drift detection (opcional)
        forecast_data: Dados de forecast (opcional)
        thread_id: ID do thread para metadados
        
    Returns:
        Lista de EditorialAlert ordenada por severidade (critical > warning > info)
    """
    alerts: list[EditorialAlert] = []
    now = _now_iso()
    
    # 1. Alertas de baseline_none (SLO violation)
    baseline = insights_data.get("baseline", {})
    by_source = baseline.get("by_source", {})
    resolved_total = baseline.get("resolved_total", 0)
    none_count = by_source.get("none", 0)
    
    if resolved_total > 0:
        none_rate = none_count / resolved_total
        
        if none_rate > 0.7:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("baseline_none", "critical"),
                alert_type="slo_violation",
                severity="critical",
                status="active",
                title="Taxa de Baseline None Crítica",
                description=f"{none_rate:.0%} das resoluções de baseline estão sem referência ({none_count}/{resolved_total}).",
                causa="baseline_none_rate_exceeded",
                recomendacao="Criar golden references urgentemente para estabilizar o baseline.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "rate": none_rate,
                    "count": none_count,
                    "total": resolved_total,
                }
            ))
        elif none_rate > 0.5:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("baseline_none", "warning"),
                alert_type="slo_violation",
                severity="warning",
                status="active",
                title="Taxa de Baseline None Alta",
                description=f"{none_rate:.0%} das resoluções de baseline estão sem referência ({none_count}/{resolved_total}).",
                causa="baseline_none_rate_high",
                recomendacao="Aumentar cobertura de golden marks para melhorar comparações.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "rate": none_rate,
                    "count": none_count,
                    "total": resolved_total,
                }
            ))
        elif none_rate > 0.3:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("baseline_none", "info"),
                alert_type="baseline_none",
                severity="info",
                status="active",
                title="Taxa de Baseline None Moderada",
                description=f"{none_rate:.0%} das resoluções estão sem referência ({none_count}/{resolved_total}).",
                causa="baseline_none_rate_moderate",
                recomendacao="Monitorar e considerar marcações golden quando apropriado.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "rate": none_rate,
                    "count": none_count,
                    "total": resolved_total,
                }
            ))
    
    # 2. Alertas de policy denied
    policy = insights_data.get("policy", {})
    denied_total = policy.get("denied_total", 0)
    marked_total = insights_data.get("totals", {}).get("marked_total", 0)
    total_attempts = denied_total + marked_total
    
    if total_attempts > 0:
        denied_rate = denied_total / total_attempts
        
        if denied_rate > 0.25 or denied_total > 10:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("policy_denied", "critical"),
                alert_type="policy_denied",
                severity="critical",
                status="active",
                title="Taxa de Negativas de Policy Crítica",
                description=f"{denied_total} tentativas foram negadas ({denied_rate:.0%} do total).",
                causa="policy_denied_rate_exceeded",
                recomendacao="Revisar políticas de editorial e critérios de autorização imediatamente.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "denied_count": denied_total,
                    "denied_rate": denied_rate,
                }
            ))
        elif denied_rate > 0.15 or denied_total > 5:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("policy_denied", "warning"),
                alert_type="policy_denied",
                severity="warning",
                status="active",
                title="Taxa de Negativas de Policy Alta",
                description=f"{denied_total} tentativas foram negadas ({denied_rate:.0%} do total).",
                causa="policy_denied_rate_warning",
                recomendacao="Avaliar ajustes nas políticas de permissão de marcação.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "denied_count": denied_total,
                    "denied_rate": denied_rate,
                }
            ))
        elif denied_total > 0:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("policy_denied", "info"),
                alert_type="policy_denied",
                severity="info",
                status="active",
                title="Negativas de Policy Detectadas",
                description=f"{denied_total} tentativas foram negadas por policy.",
                causa="policy_denials_present",
                recomendacao="Monitorar padrão de negativas e revisar se necessário.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "denied_count": denied_total,
                    "denied_rate": denied_rate,
                }
            ))
    
    # 3. Alertas de drift detection
    if drift_data:
        drift_severity = drift_data.get("drift_severity", "none")
        drift_score = drift_data.get("drift_score", 0)
        drift_flags = drift_data.get("drift_flags", [])
        
        if drift_severity == "high":
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("drift", "high"),
                alert_type="drift_detected",
                severity="critical",
                status="active",
                title="Drift Crítico Detectado",
                description=f"Drift score {drift_score}/100 com severidade alta. Flags: {', '.join(drift_flags[:3])}.",
                causa="drift_high_severity",
                recomendacao="Executar revisão editorial completa imediatamente.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "drift_score": drift_score,
                    "drift_severity": drift_severity,
                    "drift_flags": drift_flags,
                }
            ))
        elif drift_severity == "medium":
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("drift", "medium"),
                alert_type="drift_detected",
                severity="warning",
                status="active",
                title="Drift Moderado Detectado",
                description=f"Drift score {drift_score}/100. Flags: {', '.join(drift_flags[:2])}.",
                causa="drift_medium_severity",
                recomendacao="Agendar revisão editorial preventiva.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "drift_score": drift_score,
                    "drift_severity": drift_severity,
                    "drift_flags": drift_flags,
                }
            ))
        elif drift_severity == "low":
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("drift", "low"),
                alert_type="drift_detected",
                severity="info",
                status="active",
                title="Drift Leve Detectado",
                description=f"Drift score {drift_score}/100 - monitoramento recomendado.",
                causa="drift_low_severity",
                recomendacao="Manter monitoramento contínuo das métricas.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "drift_score": drift_score,
                    "drift_severity": drift_severity,
                    "drift_flags": drift_flags,
                }
            ))
    
    # 4. Alertas de forecast risk
    if forecast_data:
        risk_score = forecast_data.get("risk_score", 0)
        trend = forecast_data.get("trend", "stable")
        confidence = forecast_data.get("confidence", 0.0)
        
        if risk_score > 70 and trend == "degrading":
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("forecast", "critical"),
                alert_type="forecast_risk",
                severity="critical",
                status="active",
                title="Risco de Degradação Crítico",
                description=f"Risk score {risk_score}/100 com tendência degradação (confiança: {confidence:.0%}).",
                causa="high_risk_degrading",
                recomendacao="Intervenção imediata necessária - revisar governança editorial.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "risk_score": risk_score,
                    "trend": trend,
                    "confidence": confidence,
                }
            ))
        elif risk_score > 50:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("forecast", "warning"),
                alert_type="forecast_risk",
                severity="warning",
                status="active",
                title="Risco Editorial Elevado",
                description=f"Risk score {risk_score}/100 (confiança: {confidence:.0%}).",
                causa="elevated_risk_score",
                recomendacao="Revisar métricas de baseline e considerar ações preventivas.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "risk_score": risk_score,
                    "trend": trend,
                    "confidence": confidence,
                }
            ))
        elif risk_score > 30:
            alerts.append(EditorialAlert(
                alert_id=_generate_alert_id("forecast", "info"),
                alert_type="forecast_risk",
                severity="info",
                status="active",
                title="Risco Editorial Moderado",
                description=f"Risk score {risk_score}/100 - manter atenção.",
                causa="moderate_risk_score",
                recomendacao="Monitorar métricas de baseline regularmente.",
                created_at=now,
                updated_at=now,
                metadata={
                    "thread_id": thread_id,
                    "risk_score": risk_score,
                    "trend": trend,
                    "confidence": confidence,
                }
            ))
    
    # Ordenar por severidade: critical > warning > info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
    
    return alerts


def filter_alerts_by_severity(
    alerts: list[EditorialAlert],
    severity: Severity | None = None
) -> list[EditorialAlert]:
    """Filtra alertas por severidade.
    
    Args:
        alerts: Lista de alertas
        severity: Severidade para filtrar (None = todos)
        
    Returns:
        Lista filtrada de alertas
    """
    if severity is None:
        return alerts
    return [a for a in alerts if a.severity == severity]


def alerts_to_dict(alerts: list[EditorialAlert]) -> list[dict]:
    """Converte lista de EditorialAlert para formato JSON serializável."""
    return [
        {
            "alert_id": a.alert_id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "status": a.status,
            "title": a.title,
            "description": a.description,
            "causa": a.causa,
            "recomendacao": a.recomendacao,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
            "metadata": a.metadata,
        }
        for a in alerts
    ]


def get_alerts_summary(alerts: list[EditorialAlert]) -> dict:
    """Gera resumo de contagem por severidade."""
    return {
        "critical": sum(1 for a in alerts if a.severity == "critical"),
        "warning": sum(1 for a in alerts if a.severity == "warning"),
        "info": sum(1 for a in alerts if a.severity == "info"),
    }
