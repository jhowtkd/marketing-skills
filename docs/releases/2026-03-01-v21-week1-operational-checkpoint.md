# Operational Checkpoint v21 - Adaptive Escalation Intelligence

**Período:** 7 dias
**Gerado em:** 2026-03-01T11:50:32.125743+00:00

## Resumo Executivo

⚠️ **DADOS INSUFICIENTES:** Este checkpoint foi gerado sem dados completos de 7 dias de operação da v21. Os KPIs abaixo refletem estado atual conhecido mas não representam avaliação completa do período.

## KPIs vs Metas

| KPI | Valor Atual | Meta | Progresso | Status | Fórmula |
|-----|-------------|------|-----------|--------|---------|
| Approval Timeout Rate | N/A | -30.0 % | N/A | ⚪ INSUFFICIENT_DATA | (agent_approval_timeout_total / agent_steps_waiting_approval_total) × 100 |
| Mean Decision Latency (Medium/High) | N/A | -25.0 s | N/A | ⚪ INSUFFICIENT_DATA | AVG(decision_latency) WHERE complexity IN ('medium', 'high') |
| Incident Rate | N/A | No change | N/A | ⚪ INSUFFICIENT_DATA | (incident_count / total_operations) × 100 |
| Approval Without Regeneration (24h) | N/A | +2.0 p.p. | N/A | ⚪ INSUFFICIENT_DATA | approval_rate_24h - approval_rate_baseline |
| Total Agent Plans Created | N/A | No change | N/A | ⚪ INSUFFICIENT_DATA | COUNT(agent_plans) |
| Total Agent Steps Auto-Executed | N/A | No change | N/A | ⚪ INSUFFICIENT_DATA | COUNT(steps WHERE execution_mode = 'auto') |
| Total Agent Steps Waiting Approval | N/A | No change | N/A | ⚪ INSUFFICIENT_DATA | COUNT(steps WHERE status = 'waiting_approval') |
| Total Approval Timeouts | N/A | No change | N/A | ⚪ INSUFFICIENT_DATA | COUNT(approval_timeouts) |
| Agent Response Time | N/A | No change | N/A | ⚪ INSUFFICIENT_DATA | AVG(response_time), P95(response_time) |
| Escalation Distribution | N/A | No change | N/A | ⚪ INSUFFICIENT_DATA | COUNT(escalations BY tier) / total_escalations × 100 |

## Top Regressões

✅ Nenhuma regressão significativa identificada.

## Causas Prováveis

- Sem causas identificadas (sem regressões)

## Ações Recomendadas

| Prioridade | Ação | Responsável | ETA |
|------------|------|-------------|-----|
| P2 | Documentar padrões de escalonamento mais efetivos | Documentation | 2 semanas |
| P2 | Implementar alerting antecipado para timeout rate | SRE | 2 semanas |

---

**Metadados:**
- Versão: v21 (Adaptive Escalation Intelligence)
- Janela de análise: 7 dias
- Dados suficientes: Não

_Este relatório é gerado automaticamente pelo sistema de Operational Checkpoints._