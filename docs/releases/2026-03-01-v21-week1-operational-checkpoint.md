# Operational Checkpoint v21 - Adaptive Escalation Intelligence

**Período:** 7 dias
**Gerado em:** 2026-03-01T11:42:01.590955+00:00

## Resumo Executivo

Checkpoint v21 (Week 1): 3 KPIs em PASS, 2 em ATTENTION, 1 em FAIL. 
Principal preocupação: Incident Rate (CRITICAL). 
1 ação(ões) P0 requerem atenção imediata. 
Ver seções de regressões e ações recomendadas para detalhes.

## KPIs vs Metas

| KPI | Valor Atual | Meta | Progresso | Status | Fórmula |
|-----|-------------|------|-----------|--------|---------|
| Approval Timeout Rate | 5.20 % (-26.8%) | -30.0 % | 89% | ⚠️ ATTENTION | (agent_approval_timeout_total / agent_steps_waiting_approval_total) × 100 |
| Mean Decision Latency (Medium/High) | 2.80 s (-20.0%) | -25.0 s | 80% | ⚠️ ATTENTION | AVG(decision_latency) WHERE complexity IN ('medium', 'high') |
| Incident Rate | 0.80 % (+60.0%) | No change | 0% | ❌ FAIL | (incident_count / total_operations) × 100 |
| Approval Without Regeneration (24h) | 2.10 p.p. (+320.0%) | +2.0 p.p. | 100% | ✅ PASS | approval_rate_24h - approval_rate_baseline |
| Total Agent Plans Created | 150.00 count | No change | - | ⚪ INSUFFICIENT_DATA | COUNT(agent_plans) |
| Total Agent Steps Auto-Executed | 450.00 count | No change | - | ⚪ INSUFFICIENT_DATA | COUNT(steps WHERE execution_mode = 'auto') |
| Total Agent Steps Waiting Approval | 23.00 count | No change | - | ✅ PASS | COUNT(steps WHERE status = 'waiting_approval') |
| Total Approval Timeouts | 12.00 count | No change | - | ⚪ INSUFFICIENT_DATA | COUNT(approval_timeouts) |
| Agent Response Time | 1.20 s | No change | - | ⚪ INSUFFICIENT_DATA | AVG(response_time), P95(response_time) |
| Escalation Distribution | 35.00 % | No change | - | ✅ PASS | COUNT(escalations BY tier) / total_escalations × 100 |

## Top Regressões

| KPI | Severidade | Valor Atual | Target | Change |
|-----|------------|-------------|--------|--------|
| Incident Rate | CRITICAL | 0.8 | +0.0 | +60.0% |
| Approval Timeout Rate | MEDIUM | 5.2 | -30.0 | -26.8% |
| Mean Decision Latency (Medium/High) | MEDIUM | 2.8 | -25.0 | -20.0% |

## Causas Prováveis

- Timeout rate elevado: possível sobrecarga de aprovações ou falta de visibilidade das políticas de escalonamento
- Latência aumentada: complexidade dos workflows pode ter crescido ou há gargalos nos LLM calls
- Aumento de incidentes: possível interação não prevista entre escalonamento adaptativo e execução automática

## Ações Recomendadas

| Prioridade | Ação | Responsável | ETA |
|------------|------|-------------|-----|
| P0 | Revisar logs de incidentes e considerar rollback de políticas adaptativas | SRE/Platform | 24h |
| P1 | Otimizar prompts de decisão média/alta complexidade ou implementar caching | ML/Platform | 1 semana |
| P2 | Documentar padrões de escalonamento mais efetivos | Documentation | 2 semanas |
| P2 | Implementar alerting antecipado para timeout rate | SRE | 2 semanas |

---

**Metadados:**
- Versão: v21 (Adaptive Escalation Intelligence)
- Janela de análise: 7 dias
- Dados suficientes: Sim

_Este relatório é gerado automaticamente pelo sistema de Operational Checkpoints._