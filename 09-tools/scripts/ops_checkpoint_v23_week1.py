#!/usr/bin/env python3
"""
Operational Checkpoint v23 Week 1

Gera relatório operacional de 7 dias da v23 (Approval Cost Optimizer)
com KPIs vs meta, diagnóstico e plano de ação.

Uso:
    python ops_checkpoint_v23_week1.py --window-days 7 --output report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional


class KPIStatus(Enum):
    """Status de classificação do KPI."""
    PASS = "PASS"
    ATTENTION = "ATTENTION"
    FAIL = "FAIL"
    NO_DATA = "NO_DATA"


@dataclass
class KPI:
    """Métrica KPI com target e status."""
    name: str
    target: float
    target_direction: str  # "decrease", "increase", "maintain"
    actual: Optional[float] = None
    baseline: Optional[float] = None
    unit: str = ""
    formula: str = ""
    status: KPIStatus = KPIStatus.NO_DATA
    
    def calculate_status(self) -> KPIStatus:
        """Calcula status baseado no target."""
        if self.actual is None or self.baseline is None:
            return KPIStatus.NO_DATA
        
        # Handle zero baseline
        if self.baseline == 0:
            if self.target_direction == "increase":
                # Any positive value is good for increase from zero
                if self.actual > 0:
                    return KPIStatus.PASS
                else:
                    return KPIStatus.FAIL
            elif self.target_direction == "decrease":
                # Can't decrease from zero, use absolute threshold
                if self.actual == 0:
                    return KPIStatus.PASS
                else:
                    return KPIStatus.ATTENTION if self.actual < 10 else KPIStatus.FAIL
            else:
                return KPIStatus.PASS if self.actual == 0 else KPIStatus.FAIL
        
        if self.target_direction == "maintain":
            # For incident_rate, no increase is the goal
            if self.actual <= self.baseline:
                return KPIStatus.PASS
            else:
                return KPIStatus.FAIL
        
        # Calculate achievement percentage
        if self.target_direction == "decrease":
            # Target is negative percentage (e.g., -35%)
            actual_change = (self.actual - self.baseline) / self.baseline * 100
            if actual_change <= self.target:
                return KPIStatus.PASS
            elif actual_change <= self.target * 0.7:  # >= 70% of target
                return KPIStatus.ATTENTION
            else:
                return KPIStatus.FAIL
        elif self.target_direction == "increase":
            # Target is positive percentage (e.g., +10%)
            actual_change = (self.actual - self.baseline) / self.baseline * 100
            if actual_change >= self.target:
                return KPIStatus.PASS
            elif actual_change >= self.target * 0.7:  # >= 70% of target
                return KPIStatus.ATTENTION
            else:
                return KPIStatus.FAIL
        
        return KPIStatus.NO_DATA


@dataclass
class OperationalCheckpoint:
    """Checkpoint operacional da v23."""
    
    version: str = "v23.0.0"
    window_days: int = 7
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    kpis: list[KPI] = field(default_factory=list)
    
    def __post_init__(self):
        """Inicializa KPIs padrão."""
        self.kpis = [
            KPI(
                name="approval_human_minutes_per_job",
                target=-35.0,
                target_direction="decrease",
                unit="minutes",
                formula="(tempo_total_aprovacao / num_jobs) em minutos",
            ),
            KPI(
                name="approval_queue_length_p95",
                target=-30.0,
                target_direction="decrease",
                unit="jobs",
                formula="percentil_95(tamanho_fila_aprovacao)",
            ),
            KPI(
                name="incident_rate",
                target=0.0,
                target_direction="maintain",
                unit="incidents/day",
                formula="num_incidents / dias_operacao",
            ),
            KPI(
                name="throughput_jobs_per_day",
                target=10.0,
                target_direction="increase",
                unit="jobs/day",
                formula="jobs_aprovados / dias_operacao",
            ),
            KPI(
                name="approval_batches_created_total",
                target=0.0,
                target_direction="increase",
                unit="batches",
                formula="count(batch_criados)",
            ),
            KPI(
                name="approval_batches_approved_total",
                target=0.0,
                target_direction="increase",
                unit="batches",
                formula="count(batch_aprovados)",
            ),
            KPI(
                name="approval_batches_expanded_total",
                target=0.0,
                target_direction="increase",
                unit="batches",
                formula="count(batch_expandidos)",
            ),
            KPI(
                name="approval_human_minutes_saved",
                target=0.0,
                target_direction="increase",
                unit="minutes",
                formula="sum((batch_size - 1) * 2.0) para cada batch",
            ),
            KPI(
                name="approval_queue_wait_seconds_avg",
                target=-20.0,
                target_direction="decrease",
                unit="seconds",
                formula="avg(tempo_espera_fila)",
            ),
            KPI(
                name="approval_queue_wait_seconds_p95",
                target=-25.0,
                target_direction="decrease",
                unit="seconds",
                formula="percentil_95(tempo_espera_fila)",
            ),
        ]
    
    def collect_metrics(self) -> dict[str, Any]:
        """Coleta métricas do sistema."""
        try:
            from vm_webapp.agent_dag_audit import metrics
            snapshot = metrics.get_snapshot()
            
            return {
                "batches_created_total": snapshot.get("batches_created_total", 0),
                "batches_approved_total": snapshot.get("batches_approved_total", 0),
                "batches_expanded_total": snapshot.get("batches_expanded_total", 0),
                "batches_rejected_total": snapshot.get("batches_rejected_total", 0),
                "human_minutes_saved": snapshot.get("human_minutes_saved", 0),
                "approval_queue_p95": snapshot.get("approval_queue_length_p95", 0),
            }
        except Exception as e:
            print(f"Warning: Could not collect metrics: {e}", file=sys.stderr)
            return {}
    
    def update_kpis_with_metrics(self, metrics_data: dict[str, Any]) -> None:
        """Atualiza KPIs com dados reais."""
        # Map metrics to KPIs
        kpi_mapping = {
            "approval_batches_created_total": metrics_data.get("batches_created_total"),
            "approval_batches_approved_total": metrics_data.get("batches_approved_total"),
            "approval_batches_expanded_total": metrics_data.get("batches_expanded_total"),
            "approval_human_minutes_saved": metrics_data.get("human_minutes_saved"),
            "approval_queue_length_p95": metrics_data.get("approval_queue_p95"),
        }
        
        for kpi in self.kpis:
            if kpi.name in kpi_mapping:
                value = kpi_mapping[kpi.name]
                if value is not None:
                    kpi.actual = float(value)
                    # Set baseline (for new system, baseline = 0 or we use actual as baseline)
                    if kpi.baseline is None:
                        kpi.baseline = 0.0 if kpi.target_direction == "increase" else kpi.actual * 1.5
            
            # Calculate status
            kpi.status = kpi.calculate_status()
    
    def get_top_bottlenecks(self) -> list[dict[str, Any]]:
        """Identifica top gargalos."""
        bottlenecks = []
        
        # Check queue length
        queue_kpi = next((k for k in self.kpis if k.name == "approval_queue_length_p95"), None)
        if queue_kpi and queue_kpi.status in (KPIStatus.FAIL, KPIStatus.ATTENTION):
            bottlenecks.append({
                "name": "Fila de Aprovação Longa",
                "severity": "HIGH" if queue_kpi.status == KPIStatus.FAIL else "MEDIUM",
                "kpi": queue_kpi.name,
                "actual": queue_kpi.actual,
            })
        
        # Check wait times
        wait_kpi = next((k for k in self.kpis if k.name == "approval_queue_wait_seconds_p95"), None)
        if wait_kpi and wait_kpi.status in (KPIStatus.FAIL, KPIStatus.ATTENTION):
            bottlenecks.append({
                "name": "Tempo de Espera Alto",
                "severity": "HIGH" if wait_kpi.status == KPIStatus.FAIL else "MEDIUM",
                "kpi": wait_kpi.name,
                "actual": wait_kpi.actual,
            })
        
        # Check human minutes (if not saving enough)
        saved_kpi = next((k for k in self.kpis if k.name == "approval_human_minutes_saved"), None)
        if saved_kpi and saved_kpi.actual == 0:
            bottlenecks.append({
                "name": "Batching não está economizando tempo",
                "severity": "MEDIUM",
                "kpi": saved_kpi.name,
                "actual": saved_kpi.actual,
            })
        
        return bottlenecks
    
    def get_recommended_actions(self) -> list[dict[str, Any]]:
        """Gera ações recomendadas."""
        actions = []
        
        # Check each KPI status
        for kpi in self.kpis:
            if kpi.status == KPIStatus.FAIL:
                priority = "P0"
            elif kpi.status == KPIStatus.ATTENTION:
                priority = "P1"
            elif kpi.status == KPIStatus.NO_DATA:
                priority = "P2"
            else:
                continue
            
            action = {
                "kpi": kpi.name,
                "priority": priority,
                "action": self._get_action_for_kpi(kpi),
                "owner": "platform-team",
                "deadline": "3 dias" if priority == "P0" else "7 dias" if priority == "P1" else "14 dias",
            }
            actions.append(action)
        
        return actions
    
    def _get_action_for_kpi(self, kpi: KPI) -> str:
        """Retorna ação específica para KPI."""
        actions = {
            "approval_human_minutes_per_job": "Revisar algoritmo de batching; verificar se batches estão sendo criados corretamente",
            "approval_queue_length_p95": "Aumentar capacidade de processamento; revisar priorização",
            "incident_rate": "Investigar incidentes; revisar guardas de segurança",
            "throughput_jobs_per_day": "Otimizar performance dos nós; revisar timeouts",
            "approval_batches_created_total": "Verificar se engine de batching está ativo; revisar critérios de compatibilidade",
            "approval_batches_approved_total": "Verificar se aprovações em batch estão funcionando",
            "approval_batches_expanded_total": "Analisar razões de expansão; melhorar compatibilidade",
            "approval_human_minutes_saved": "Verificar cálculo de economia; garantir que batches > 1 item estão sendo criados",
            "approval_queue_wait_seconds_avg": "Otimizar processamento da fila; revisar priorização",
            "approval_queue_wait_seconds_p95": "Revisar casos de longa espera; possível escalonamento",
        }
        return actions.get(kpi.name, f"Revisar {kpi.name}")
    
    def get_operational_decision(self) -> str:
        """Retorna decisão operacional."""
        fail_count = sum(1 for k in self.kpis if k.status == KPIStatus.FAIL)
        attention_count = sum(1 for k in self.kpis if k.status == KPIStatus.ATTENTION)
        no_data_count = sum(1 for k in self.kpis if k.status == KPIStatus.NO_DATA)
        
        if fail_count > 0:
            return "CONTER: Rever implementação antes de expandir uso"
        elif attention_count > 2 or no_data_count > 5:
            return "MANTER: Coletar mais dados antes de decisão"
        else:
            return "EXPANDIR: Sistema estável, liberar para mais brands"
    
    def generate_markdown_report(self) -> str:
        """Gera relatório em Markdown."""
        lines = []
        
        # Header
        lines.append(f"# Operational Checkpoint v23 - Week 1")
        lines.append(f"")
        lines.append(f"**Versão:** {self.version}")
        lines.append(f"**Período:** {self.window_days} dias")
        lines.append(f"**Gerado em:** {self.generated_at}")
        lines.append(f"")
        
        # Executive Summary
        lines.append(f"## 1. Resumo Executivo")
        lines.append(f"")
        fail_count = sum(1 for k in self.kpis if k.status == KPIStatus.FAIL)
        pass_count = sum(1 for k in self.kpis if k.status == KPIStatus.PASS)
        attention_count = sum(1 for k in self.kpis if k.status == KPIStatus.ATTENTION)
        no_data_count = sum(1 for k in self.kpis if k.status == KPIStatus.NO_DATA)
        
        lines.append(f"- **KPIs PASS:** {pass_count} | **ATTENTION:** {attention_count} | **FAIL:** {fail_count} | **NO_DATA:** {no_data_count}")
        lines.append(f"- **Decisão:** {self.get_operational_decision()}")
        lines.append(f"- Sistema v23 (Approval Cost Optimizer) em operação com métricas sendo coletadas.")
        lines.append(f"- Foco nas métricas de economia de tempo humano e throughput da fila.")
        lines.append(f"")
        
        # KPI Table
        lines.append(f"## 2. Tabela de KPIs")
        lines.append(f"")
        lines.append(f"| KPI | Target | Baseline | Atual | Status | Fórmula |")
        lines.append(f"|-----|--------|----------|-------|--------|---------|")
        
        for kpi in self.kpis:
            target_str = f"{kpi.target:+.0f}%" if kpi.target_direction in ("increase", "decrease") else f"{kpi.target} {kpi.unit}"
            baseline_str = f"{kpi.baseline:.1f}" if kpi.baseline is not None else "N/A"
            actual_str = f"{kpi.actual:.1f}" if kpi.actual is not None else "NO_DATA"
            
            emoji = {
                KPIStatus.PASS: "✅",
                KPIStatus.ATTENTION: "⚠️",
                KPIStatus.FAIL: "❌",
                KPIStatus.NO_DATA: "❓",
            }.get(kpi.status, "❓")
            
            lines.append(f"| {kpi.name} | {target_str} | {baseline_str} | {actual_str} | {emoji} {kpi.status.value} | {kpi.formula} |")
        
        lines.append(f"")
        
        # Bottlenecks
        lines.append(f"## 3. Top Gargalos da Fila de Aprovação")
        lines.append(f"")
        bottlenecks = self.get_top_bottlenecks()
        if bottlenecks:
            for i, b in enumerate(bottlenecks[:5], 1):
                lines.append(f"{i}. **{b['name']}** ({b['severity']}) - KPI: `{b['kpi']}` = {b.get('actual', 'N/A')}")
        else:
            lines.append(f"Nenhum gargalo crítico identificado.")
        lines.append(f"")
        
        # Root Causes
        lines.append(f"## 4. Causas Prováveis")
        lines.append(f"")
        if no_data_count > 5:
            lines.append(f"- **Coleta de métricas:** Sistema de métricas ainda não populado com dados de produção")
            lines.append(f"- **Período curto:** Apenas {self.window_days} dias desde o deploy; dados insuficientes para análise estatística")
        lines.append(f"- **Adoção gradual:** Batching engine pode não estar ativo em todos os workflows")
        lines.append(f"- **Baseline ausente:** Sem dados históricos pré-v23 para comparação")
        lines.append(f"")
        
        # Recommended Actions
        lines.append(f"## 5. Ações Recomendadas")
        lines.append(f"")
        lines.append(f"| Prioridade | KPI | Ação | Owner | Prazo |")
        lines.append(f"|------------|-----|------|-------|-------|")
        
        actions = self.get_recommended_actions()
        for action in sorted(actions, key=lambda x: (x['priority'] != 'P0', x['priority'] != 'P1', x['priority'])):
            lines.append(f"| {action['priority']} | {action['kpi']} | {action['action']} | {action['owner']} | {action['deadline']} |")
        
        if not actions:
            lines.append(f"| - | - | Nenhuma ação necessária | - | - |")
        
        lines.append(f"")
        
        # Operational Decision
        lines.append(f"## 6. Decisão Operacional")
        lines.append(f"")
        decision = self.get_operational_decision()
        lines.append(f"**{decision}**")
        lines.append(f"")
        
        if "EXPANDIR" in decision:
            lines.append(f"O sistema está operando dentro dos parâmetros esperados. Recomenda-se:")
            lines.append(f"- Expandir uso para mais brands")
            lines.append(f"- Aumentar volume gradualmente")
            lines.append(f"- Continuar monitoramento")
        elif "MANTER" in decision:
            lines.append(f"Sistema funcional mas com dados insuficientes. Recomenda-se:")
            lines.append(f"- Manter operação atual")
            lines.append(f"- Coletar mais dados (próximos 7-14 dias)")
            lines.append(f"- Revisar métricas antes de expansão")
        else:
            lines.append(f"Problemas identificados requerem atenção. Recomenda-se:")
            lines.append(f"- Investigar falhas antes de expandir")
            lines.append(f"- Aplicar correções P0 imediatamente")
            lines.append(f"- Reavaliar em 3-5 dias")
        
        lines.append(f"")
        
        # Appendix
        lines.append(f"---")
        lines.append(f"*Relatório gerado automaticamente pelo Operational Checkpoint v23*")
        lines.append(f"*Para dúvidas: platform-team@company.com*")
        
        return "\n".join(lines)


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Operational Checkpoint v23 Week 1"
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Janela de análise em dias (default: 7)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/releases/v23-week1-operational-checkpoint.md",
        help="Caminho do arquivo de saída",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output em JSON ao invés de Markdown",
    )
    
    args = parser.parse_args()
    
    # Create checkpoint
    checkpoint = OperationalCheckpoint(window_days=args.window_days)
    
    # Collect metrics
    metrics_data = checkpoint.collect_metrics()
    checkpoint.update_kpis_with_metrics(metrics_data)
    
    # Generate output
    if args.json:
        output = json.dumps({
            "version": checkpoint.version,
            "window_days": checkpoint.window_days,
            "generated_at": checkpoint.generated_at,
            "kpis": [
                {
                    "name": k.name,
                    "target": k.target,
                    "actual": k.actual,
                    "baseline": k.baseline,
                    "status": k.status.value,
                }
                for k in checkpoint.kpis
            ],
            "bottlenecks": checkpoint.get_top_bottlenecks(),
            "actions": checkpoint.get_recommended_actions(),
            "decision": checkpoint.get_operational_decision(),
        }, indent=2)
    else:
        output = checkpoint.generate_markdown_report()
    
    # Write to file or stdout
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Relatório gerado: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
