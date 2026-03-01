#!/usr/bin/env python3
"""
Operational Checkpoint v21 - Adaptive Escalation Intelligence (Week 1)

Gera checkpoint operacional de 7 dias da v21 com:
- KPIs vs metas
- Diagnóstico de regressões
- Ações recomendadas (P0/P1/P2)

KPIs monitorados:
- approval_timeout_rate (meta: -30%)
- mean_decision_latency_medium_high (meta: -25%)
- incident_rate (meta: sem aumento)
- approval_without_regen_24h (meta: +2 p.p.)
- agent_plans_created_total
- agent_steps_autoexecuted_total
- agent_steps_waiting_approval_total
- agent_approval_timeout_total
- agent_response_time_seconds (avg/p95)
- escalation_distribution (15/30/60)

Regras de avaliação:
- PASS: meta atingida
- ATTENTION: dentro de 70-99% do target
- FAIL: abaixo de 70% do target ou incident_rate piorou
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class Status(str, Enum):
    """Status de avaliação do KPI."""
    PASS = "PASS"
    ATTENTION = "ATTENTION"
    FAIL = "FAIL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class KPIDefinition:
    """Definição de um KPI com sua meta."""
    name: str
    description: str
    target_value: float
    target_direction: str  # "decrease", "increase", "maintain"
    unit: str
    formula: str


@dataclass
class KPIResult:
    """Resultado de um KPI avaliado."""
    definition: KPIDefinition
    current_value: float | None
    previous_value: float | None
    change_pct: float | None
    status: Status
    progress_pct: float | None  # Quanto da meta foi atingido (0-100%)
    notes: str = ""


# Definições dos KPIs da v21
KPI_DEFINITIONS: dict[str, KPIDefinition] = {
    "approval_timeout_rate": KPIDefinition(
        name="Approval Timeout Rate",
        description="Taxa de timeouts em aprovações de agente",
        target_value=-30.0,  # -30% reduction
        target_direction="decrease",
        unit="%",
        formula="(agent_approval_timeout_total / agent_steps_waiting_approval_total) × 100",
    ),
    "mean_decision_latency_medium_high": KPIDefinition(
        name="Mean Decision Latency (Medium/High)",
        description="Latência média de decisões de média/alta complexidade",
        target_value=-25.0,  # -25% reduction
        target_direction="decrease",
        unit="s",
        formula="AVG(decision_latency) WHERE complexity IN ('medium', 'high')",
    ),
    "incident_rate": KPIDefinition(
        name="Incident Rate",
        description="Taxa de incidentes operacionais",
        target_value=0.0,  # no increase
        target_direction="maintain",
        unit="%",
        formula="(incident_count / total_operations) × 100",
    ),
    "approval_without_regen_24h": KPIDefinition(
        name="Approval Without Regeneration (24h)",
        description="Taxa de aprovações sem necessidade de regeneração em 24h",
        target_value=2.0,  # +2 percentage points
        target_direction="increase",
        unit="p.p.",
        formula="approval_rate_24h - approval_rate_baseline",
    ),
    "agent_plans_created_total": KPIDefinition(
        name="Total Agent Plans Created",
        description="Total de planos criados por agentes",
        target_value=0.0,  # informational
        target_direction="increase",
        unit="count",
        formula="COUNT(agent_plans)",
    ),
    "agent_steps_autoexecuted_total": KPIDefinition(
        name="Total Agent Steps Auto-Executed",
        description="Total de passos executados automaticamente",
        target_value=0.0,  # informational
        target_direction="increase",
        unit="count",
        formula="COUNT(steps WHERE execution_mode = 'auto')",
    ),
    "agent_steps_waiting_approval_total": KPIDefinition(
        name="Total Agent Steps Waiting Approval",
        description="Total de passos aguardando aprovação",
        target_value=0.0,  # informational
        target_direction="informational",
        unit="count",
        formula="COUNT(steps WHERE status = 'waiting_approval')",
    ),
    "agent_approval_timeout_total": KPIDefinition(
        name="Total Approval Timeouts",
        description="Total de timeouts em aprovações",
        target_value=0.0,  # informational
        target_direction="decrease",
        unit="count",
        formula="COUNT(approval_timeouts)",
    ),
    "agent_response_time_seconds": KPIDefinition(
        name="Agent Response Time",
        description="Tempo de resposta do agente (avg/p95)",
        target_value=0.0,  # informational
        target_direction="decrease",
        unit="s",
        formula="AVG(response_time), P95(response_time)",
    ),
    "escalation_distribution": KPIDefinition(
        name="Escalation Distribution",
        description="Distribuição de escalonamentos por tier (15/30/60 min)",
        target_value=0.0,  # informational
        target_direction="informational",
        unit="%",
        formula="COUNT(escalations BY tier) / total_escalations × 100",
    ),
}


@dataclass
class CheckpointData:
    """Dados do checkpoint operacional."""
    window_days: int
    generated_at: datetime
    data_available_from: datetime | None
    data_available_to: datetime | None
    data_sufficient: bool
    kpi_results: list[KPIResult] = field(default_factory=list)
    top_regressions: list[dict[str, Any]] = field(default_factory=list)
    probable_causes: list[str] = field(default_factory=list)
    recommended_actions: list[dict[str, Any]] = field(default_factory=list)


def fetch_metrics_data(
    window_days: int,
    data_source: str | None = None
) -> dict[str, Any]:
    """
    Busca dados de métricas para o período.
    
    Em produção, isso viria de:
    - Prometheus/Grafana
    - Banco de dados de eventos
    - Logs aggregados
    
    Args:
        window_days: Período de análise em dias
        data_source: Fonte de dados (opcional)
        
    Returns:
        Dict com métricas brutas ou None se dados insuficientes
    """
    # TODO: Implementar integração real com fontes de dados
    # Por enquanto, retorna estrutura vazia indicando dados insuficientes
    return {
        "sufficient_data": False,
        "period_start": None,
        "period_end": None,
        "metrics": {},
    }


def evaluate_kpi(
    kpi_def: KPIDefinition,
    current: float | None,
    previous: float | None,
) -> KPIResult:
    """
    Avalia um KPI contra sua meta.
    
    Regras:
    - PASS: meta atingida (100% ou mais do target)
    - ATTENTION: dentro de 70-99% do target
    - FAIL: abaixo de 70% do target ou incident_rate piorou
    """
    notes = ""
    
    if current is None:
        return KPIResult(
            definition=kpi_def,
            current_value=None,
            previous_value=previous,
            change_pct=None,
            status=Status.INSUFFICIENT_DATA,
            progress_pct=None,
            notes="Dados insuficientes para avaliação",
        )
    
    # Calcula mudança percentual
    if previous is not None and previous != 0:
        change_pct = ((current - previous) / abs(previous)) * 100
    else:
        change_pct = None
    
    # Para KPIs apenas informativos
    if kpi_def.target_direction == "informational":
        return KPIResult(
            definition=kpi_def,
            current_value=current,
            previous_value=previous,
            change_pct=change_pct,
            status=Status.PASS,
            progress_pct=None,
            notes="Métrica informativa",
        )
    
    # Avalia progresso baseado na direção da meta
    if kpi_def.target_direction == "decrease":
        # Target é redução (valor negativo, e.g., -30%)
        # Queremos que current < previous (redução)
        if change_pct is not None:
            # change_pct é negativo para redução (e.g., -21%)
            # target_value é negativo (e.g., -30%)
            if change_pct <= kpi_def.target_value:
                # Redução igual ou maior que o target (e.g., -35% quando target é -30%)
                progress = 100.0
                status = Status.PASS
            elif change_pct < 0:
                # Redução parcial (e.g., -21% quando target é -30%)
                # progress = 21 / 30 = 0.70 = 70% do target
                actual_reduction = abs(change_pct)  # 21
                target_reduction = abs(kpi_def.target_value)  # 30
                progress = (actual_reduction / target_reduction) * 100
                if progress >= 100:
                    status = Status.PASS
                elif progress >= 70:
                    status = Status.ATTENTION
                else:
                    status = Status.FAIL
            else:
                # Aumentou em vez de diminuir (change_pct >= 0)
                progress = 0.0
                status = Status.FAIL
        else:
            progress = None
            status = Status.INSUFFICIENT_DATA
            
    elif kpi_def.target_direction == "increase":
        # Target é aumento (valor positivo, e.g., +2pp)
        # Queremos que current > previous (change_pct > 0)
        if change_pct is not None:
            if change_pct >= kpi_def.target_value:
                # Aumento igual ou maior que o target
                progress = 100.0
                status = Status.PASS
            elif change_pct > 0:
                # Aumento parcial (e.g., +0.5pp quando target é +2pp)
                # 0.5 / 2.0 = 0.25 = 25% do target
                progress = (change_pct / kpi_def.target_value) * 100
                if progress >= 100:
                    status = Status.PASS
                elif progress >= 70:
                    status = Status.ATTENTION
                else:
                    status = Status.FAIL
            else:
                # Diminuiu em vez de aumentar (change_pct <= 0)
                progress = 0.0
                status = Status.FAIL
        else:
            progress = None
            status = Status.INSUFFICIENT_DATA
            
    elif kpi_def.target_direction == "maintain":
        # Target é manter (sem aumento)
        if change_pct is not None:
            if change_pct <= 0:
                progress = 100.0
                status = Status.PASS
            else:
                progress = max(0, 100 - change_pct * 10)  # Penaliza aumento
                status = Status.FAIL
        else:
            progress = None
            status = Status.INSUFFICIENT_DATA
    else:
        progress = None
        status = Status.INSUFFICIENT_DATA
    
    # Regra especial: incident_rate sempre FAIL se aumentou
    if kpi_def.name == "Incident Rate" and change_pct is not None and change_pct > 0:
        status = Status.FAIL
        notes = "Incident rate aumentou - requer atenção imediata"
    
    return KPIResult(
        definition=kpi_def,
        current_value=current,
        previous_value=previous,
        change_pct=change_pct,
        status=status,
        progress_pct=progress,
        notes=notes,
    )


def identify_regressions(kpi_results: list[KPIResult]) -> list[dict[str, Any]]:
    """Identifica as principais regressões nos KPIs."""
    regressions = []
    
    for result in kpi_results:
        if result.status == Status.FAIL:
            regressions.append({
                "kpi": result.definition.name,
                "severity": "CRITICAL" if result.definition.name == "Incident Rate" else "HIGH",
                "current": result.current_value,
                "target": result.definition.target_value,
                "change": result.change_pct,
            })
        elif result.status == Status.ATTENTION:
            regressions.append({
                "kpi": result.definition.name,
                "severity": "MEDIUM",
                "current": result.current_value,
                "target": result.definition.target_value,
                "change": result.change_pct,
            })
    
    # Ordena por severidade
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    regressions.sort(key=lambda x: severity_order.get(x["severity"], 3))
    
    return regressions


def analyze_causes(regressions: list[dict[str, Any]]) -> list[str]:
    """Analisa causas prováveis das regressões."""
    causes = []
    
    regression_names = {r["kpi"] for r in regressions}
    
    if "Approval Timeout Rate" in regression_names:
        causes.append(
            "Timeout rate elevado: possível sobrecarga de aprovações ou "
            "falta de visibilidade das políticas de escalonamento"
        )
    
    if "Mean Decision Latency (Medium/High)" in regression_names:
        causes.append(
            "Latência aumentada: complexidade dos workflows pode ter crescido "
            "ou há gargalos nos LLM calls"
        )
    
    if "Incident Rate" in regression_names:
        causes.append(
            "Aumento de incidentes: possível interação não prevista entre "
            "escalonamento adaptativo e execução automática"
        )
    
    if "Approval Without Regeneration (24h)" in regression_names:
        causes.append(
            "Qualidade de aprovações baixa: modelos podem precisar de "
            "fine-tuning ou prompts mais específicos"
        )
    
    if not causes and regressions:
        causes.append(
            "Regressões detectadas sem padrão claro - investigação manual necessária"
        )
    
    return causes


def recommend_actions(
    regressions: list[dict[str, Any]],
    causes: list[str]
) -> list[dict[str, Any]]:
    """Gera ações recomendadas com prioridade."""
    actions = []
    
    # P0 - Ações críticas
    if any(r["kpi"] == "Incident Rate" for r in regressions):
        actions.append({
            "priority": "P0",
            "action": "Revisar logs de incidentes e considerar rollback de políticas adaptativas",
            "owner": "SRE/Platform",
            "eta": "24h",
        })
    
    if any(r["kpi"] == "Approval Timeout Rate" and r["severity"] in ("CRITICAL", "HIGH") 
           for r in regressions):
        actions.append({
            "priority": "P0",
            "action": "Aumentar capacidade de processamento de aprovações ou ajustar timeouts",
            "owner": "Platform",
            "eta": "48h",
        })
    
    # P1 - Ações importantes
    if any(r["kpi"] == "Mean Decision Latency (Medium/High)" for r in regressions):
        actions.append({
            "priority": "P1",
            "action": "Otimizar prompts de decisão média/alta complexidade ou implementar caching",
            "owner": "ML/Platform",
            "eta": "1 semana",
        })
    
    if any(r["kpi"] == "Approval Without Regeneration (24h)" for r in regressions):
        actions.append({
            "priority": "P1",
            "action": "Revisar thresholds de aprovação automática e qualidade de saída",
            "owner": "Product/ML",
            "eta": "1 semana",
        })
    
    # P2 - Melhorias contínuas
    actions.append({
        "priority": "P2",
        "action": "Documentar padrões de escalonamento mais efetivos",
        "owner": "Documentation",
        "eta": "2 semanas",
    })
    
    actions.append({
        "priority": "P2",
        "action": "Implementar alerting antecipado para timeout rate",
        "owner": "SRE",
        "eta": "2 semanas",
    })
    
    return actions


def generate_checkpoint(
    window_days: int,
    data_source: str | None = None
) -> CheckpointData:
    """Gera o checkpoint operacional completo."""
    now = datetime.now(timezone.utc)
    
    # Busca dados
    raw_data = fetch_metrics_data(window_days, data_source)
    
    # Determina se dados são suficientes
    data_sufficient = raw_data.get("sufficient_data", False)
    
    checkpoint = CheckpointData(
        window_days=window_days,
        generated_at=now,
        data_available_from=raw_data.get("period_start"),
        data_available_to=raw_data.get("period_end"),
        data_sufficient=data_sufficient,
    )
    
    # Se não há dados suficientes, marca todos como insuficientes
    if not data_sufficient:
        for kpi_id, kpi_def in KPI_DEFINITIONS.items():
            result = evaluate_kpi(kpi_def, None, None)
            checkpoint.kpi_results.append(result)
    else:
        # Em produção, aqui extrairíamos os valores reais
        # Por enquanto, usamos valores de exemplo para demonstração
        metrics = raw_data.get("metrics", {})
        
        # Exemplo de avaliação com dados mock
        sample_data = {
            "approval_timeout_rate": (5.2, 7.1),  # (current, previous)
            "mean_decision_latency_medium_high": (2.8, 3.5),
            "incident_rate": (0.8, 0.5),
            "approval_without_regen_24h": (1.5, 0.5),
        }
        
        for kpi_id, kpi_def in KPI_DEFINITIONS.items():
            if kpi_id in sample_data:
                current, previous = sample_data[kpi_id]
                result = evaluate_kpi(kpi_def, current, previous)
            else:
                # Para KPIs informativos, valores fictícios
                result = evaluate_kpi(kpi_def, 100.0, None)
            checkpoint.kpi_results.append(result)
    
    # Identifica regressões
    checkpoint.top_regressions = identify_regressions(checkpoint.kpi_results)
    
    # Analisa causas
    checkpoint.probable_causes = analyze_causes(checkpoint.top_regressions)
    
    # Recomenda ações
    checkpoint.recommended_actions = recommend_actions(
        checkpoint.top_regressions,
        checkpoint.probable_causes
    )
    
    return checkpoint


def generate_markdown_report(checkpoint: CheckpointData) -> str:
    """Gera relatório em formato Markdown."""
    lines = [
        "# Operational Checkpoint v21 - Adaptive Escalation Intelligence",
        "",
        f"**Período:** {checkpoint.window_days} dias",
        f"**Gerado em:** {checkpoint.generated_at.isoformat()}",
        "",
    ]
    
    # Resumo Executivo (5 linhas)
    lines.extend([
        "## Resumo Executivo",
        "",
    ])
    
    if not checkpoint.data_sufficient:
        lines.append(
            "⚠️ **DADOS INSUFICIENTES:** Este checkpoint foi gerado sem dados completos "
            "de 7 dias de operação da v21. Os KPIs abaixo refletem estado atual conhecido "
            "mas não representam avaliação completa do período."
        )
    else:
        pass_count = sum(1 for r in checkpoint.kpi_results if r.status == Status.PASS)
        fail_count = sum(1 for r in checkpoint.kpi_results if r.status == Status.FAIL)
        attention_count = sum(1 for r in checkpoint.kpi_results if r.status == Status.ATTENTION)
        
        lines.append(
            f"Checkpoint v21 (Week 1): {pass_count} KPIs em PASS, "
            f"{attention_count} em ATTENTION, {fail_count} em FAIL. "
        )
        
        if checkpoint.top_regressions:
            top = checkpoint.top_regressions[0]
            lines.append(
                f"Principal preocupação: {top['kpi']} ({top['severity']}). "
            )
        
        if checkpoint.recommended_actions:
            p0_count = sum(1 for a in checkpoint.recommended_actions if a["priority"] == "P0")
            if p0_count > 0:
                lines.append(f"{p0_count} ação(ões) P0 requerem atenção imediata. ")
        
        lines.append("Ver seções de regressões e ações recomendadas para detalhes.")
    
    lines.append("")
    
    # Tabela de KPIs
    lines.extend([
        "## KPIs vs Metas",
        "",
        "| KPI | Valor Atual | Meta | Progresso | Status | Fórmula |",
        "|-----|-------------|------|-----------|--------|---------|",
    ])
    
    for result in checkpoint.kpi_results:
        kpi = result.definition
        
        if result.current_value is None:
            current_str = "N/A"
            progress_str = "N/A"
        else:
            current_str = f"{result.current_value:.2f} {kpi.unit}"
            if result.change_pct is not None:
                sign = "+" if result.change_pct > 0 else ""
                current_str += f" ({sign}{result.change_pct:.1f}%)"
            
            if result.progress_pct is not None:
                progress_str = f"{result.progress_pct:.0f}%"
            else:
                progress_str = "-"
        
        target_str = f"{kpi.target_value:+.1f} {kpi.unit}" if kpi.target_value != 0 else "No change"
        status_emoji = {
            Status.PASS: "✅ PASS",
            Status.ATTENTION: "⚠️ ATTENTION",
            Status.FAIL: "❌ FAIL",
            Status.INSUFFICIENT_DATA: "⚪ INSUFFICIENT_DATA",
        }.get(result.status, result.status)
        
        lines.append(
            f"| {kpi.name} | {current_str} | {target_str} | {progress_str} | {status_emoji} | {kpi.formula} |"
        )
    
    lines.append("")
    
    # Top Regressões
    lines.extend([
        "## Top Regressões",
        "",
    ])
    
    if checkpoint.top_regressions:
        lines.extend([
            "| KPI | Severidade | Valor Atual | Target | Change |",
            "|-----|------------|-------------|--------|--------|",
        ])
        for reg in checkpoint.top_regressions:
            change_str = f"{reg['change']:+.1f}%" if reg['change'] is not None else "N/A"
            lines.append(
                f"| {reg['kpi']} | {reg['severity']} | {reg['current']} | "
                f"{reg['target']:+} | {change_str} |"
            )
        lines.append("")
    else:
        lines.append("✅ Nenhuma regressão significativa identificada.")
        lines.append("")
    
    # Causas Prováveis
    lines.extend([
        "## Causas Prováveis",
        "",
    ])
    
    if checkpoint.probable_causes:
        for cause in checkpoint.probable_causes:
            lines.append(f"- {cause}")
    else:
        lines.append("- Sem causas identificadas (sem regressões)")
    
    lines.append("")
    
    # Ações Recomendadas
    lines.extend([
        "## Ações Recomendadas",
        "",
        "| Prioridade | Ação | Responsável | ETA |",
        "|------------|------|-------------|-----|",
    ])
    
    for action in checkpoint.recommended_actions:
        lines.append(
            f"| {action['priority']} | {action['action']} | {action['owner']} | {action['eta']} |"
        )
    
    lines.append("")
    
    # Metadados
    lines.extend([
        "---",
        "",
        "**Metadados:**",
        f"- Versão: v21 (Adaptive Escalation Intelligence)",
        f"- Janela de análise: {checkpoint.window_days} dias",
        f"- Dados suficientes: {'Sim' if checkpoint.data_sufficient else 'Não'}",
    ])
    
    if checkpoint.data_available_from and checkpoint.data_available_to:
        lines.append(
            f"- Período dos dados: {checkpoint.data_available_from} a {checkpoint.data_available_to}"
        )
    
    lines.extend([
        "",
        "_Este relatório é gerado automaticamente pelo sistema de Operational Checkpoints._",
    ])
    
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate operational checkpoint for v21 (Adaptive Escalation Intelligence)"
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Analysis window in days (default: 7)",
    )
    parser.add_argument(
        "--data-source",
        type=str,
        default=None,
        help="Data source URL or path",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output markdown file (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--use-mock-data",
        action="store_true",
        help="Use mock data for demonstration",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Gera checkpoint
    checkpoint = generate_checkpoint(
        window_days=args.window_days,
        data_source=args.data_source,
    )
    
    # Se solicitado mock data, substitui resultados
    if args.use_mock_data:
        checkpoint.data_sufficient = True
        checkpoint.kpi_results = []
        
        sample_data = {
            "approval_timeout_rate": (5.2, 7.1),  # -26.8%, meta -30% -> ATTENTION
            "mean_decision_latency_medium_high": (2.8, 3.5),  # -20%, meta -25% -> ATTENTION
            "incident_rate": (0.8, 0.5),  # +60%, meta no increase -> FAIL
            "approval_without_regen_24h": (2.1, 0.5),  # +1.6pp, meta +2pp -> ATTENTION
            "agent_plans_created_total": (150, None),
            "agent_steps_autoexecuted_total": (450, None),
            "agent_steps_waiting_approval_total": (23, None),
            "agent_approval_timeout_total": (12, None),
            "agent_response_time_seconds": (1.2, None),
            "escalation_distribution": (35, None),  # 35% em 15min tier
        }
        
        for kpi_id, kpi_def in KPI_DEFINITIONS.items():
            if kpi_id in sample_data:
                current, previous = sample_data[kpi_id]
                result = evaluate_kpi(kpi_def, current, previous)
            else:
                result = evaluate_kpi(kpi_def, 100.0, None)
            checkpoint.kpi_results.append(result)
        
        checkpoint.top_regressions = identify_regressions(checkpoint.kpi_results)
        checkpoint.probable_causes = analyze_causes(checkpoint.top_regressions)
        checkpoint.recommended_actions = recommend_actions(
            checkpoint.top_regressions,
            checkpoint.probable_causes
        )
    
    # Gera saída
    if args.format == "json":
        output = json.dumps({
            "window_days": checkpoint.window_days,
            "generated_at": checkpoint.generated_at.isoformat(),
            "data_sufficient": checkpoint.data_sufficient,
            "kpis": [
                {
                    "name": r.definition.name,
                    "current": r.current_value,
                    "previous": r.previous_value,
                    "change_pct": r.change_pct,
                    "target": r.definition.target_value,
                    "status": r.status.value,
                    "progress_pct": r.progress_pct,
                }
                for r in checkpoint.kpi_results
            ],
            "regressions": checkpoint.top_regressions,
            "causes": checkpoint.probable_causes,
            "actions": checkpoint.recommended_actions,
        }, indent=2)
    else:
        output = generate_markdown_report(checkpoint)
    
    # Escreve saída
    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
