# Release v15: Governance Rollout Decision (ROI Operations)

**Data:** 2026-02-28  
**Versão:** v15.0.0  
**Branch:** `feature/governance-v15-roi-rollout-governance`

---

## 🎯 Objetivo

Implementar governança operacional completa para rollout do v14 com painel de KPIs, alertas de regressão e decisão assistida de expand/hold/rollback.

---

## 📊 Targets Monitorados

| Métrica | Target v15 | vs v13 |
|---------|-----------|--------|
| `approval_without_regen_24h` | +5 p.p. | baseline +5% |
| `V1 score médio` | +6 pts | segmentos elegíveis |
| `regenerations/job` | -15% | segmentos elegíveis |

---

## 🚀 Funcionalidades

### Task A: Weekly KPI Scoreboard
- **Backend:** Endpoint v2 para KPI semanal agregado por segmento e global
- **Features:**
  - Comparação target vs atual
  - Status: `on_track`, `attention`, `off_track`
  - Delta percentual e absoluto
- **Script:** Seção "KPI Weekly Delta" no report noturno
- **Arquivos:**
  - `vm_webapp/kpi_scoreboard.py`
  - `tests/test_vm_webapp_kpi_scoreboard.py`

### Task B: Segment Regression Alerts
- **Backend:** Detector de regressão por segmento
- **Features:**
  - Janelas curtas (1h) e longas (24h)
  - Severidade padronizada: `critical`, `warning`, `info`
  - Reason codes: `approval_rate_drop`, `v1_score_decline`, `regeneration_spike`
  - Histerese e deduplicação de alertas
- **Observability:** Métricas Prometheus
  - `vm_regression_detected_total`
  - `vm_regression_confirmed_total`
  - `vm_regression_false_positive_total`
- **Arquivos:**
  - `vm_webapp/alerts_v2.py`
  - `vm_webapp/regression_alerts.py`
  - `tests/test_vm_webapp_regression_alerts.py`

### Task C: Rollout Decision Assistant
- **Backend:** Motor de decisão operacional
- **Decisions:**
  - `expand` - Expandir rollout (KPIs on_track, >=7 dias)
  - `hold` - Manter escopo atual (KPIs mistos ou alertas)
  - `rollback` - Reverter para v13 (KPIs off_track ou alertas críticos)
- **Features:**
  - Confidence scoring: `low`, `medium`, `high`
  - Required actions com prioridade e due date
  - Override manual com auditoria completa
- **Frontend:** Card no Studio Control Center
- **Arquivos:**
  - `vm_webapp/rollout_decision.py`
  - `tests/test_vm_webapp_rollout_decision.py`

### Task D: CI + Nightly + Release Note
- **CI Gate v15:** `rollout-governance-gate-v15`
  - Testes: backend + frontend + metrics
  - Build verification
- **Nightly:** Resumo de decisões + top segmentos críticos
- **Docs:** Playbook de resposta a incidentes

---

## 🔄 Playbook de Resposta

### Expand
```bash
# Quando: Todos KPIs on_track, >=7 dias, confidence=high
1. Aumentar cobertura para 50% dos segmentos elegíveis
2. Monitorar KPIs diariamente por 7 dias
3. Escalar gradualmente se mantiver estável
```

### Hold
```bash
# Quando: KPIs mistos, alertas ativos, ou <7 dias
1. Manter escopo atual
2. Investigar itens em attention (72h)
3. Reavaliar após resolução
```

### Rollback
```bash
# Quando: KPIs off_track ou alertas críticos
1. Iniciar rollback imediato para v13 (4h)
2. Notificar engenharia e documentar incidente (2h)
3. Preservar dados para RCA (8h)
4. Post-mortem obrigatório em 24h
```

### Override Manual
```bash
# Quando: Prioridade de negócio justifica
1. Documentar razão completa
2. Obter aprovação de segundo operador
3. Notificar stakeholders
4. Auditar em 48h
```

---

## 📈 Métricas de Sucesso

| Indicador | Target | Measurement |
|-----------|--------|-------------|
| Decision accuracy | >90% | Manual review semanal |
| False positive rate | <5% | Alertas confirmados vs total |
| Time to decision | <5min | API response time |
| Rollback time | <4h | Incident response |

---

## 🔧 APIs

### GET /api/v2/rollout/decision/{segment_key}
```json
{
  "segment_key": "brand1:awareness",
  "decision": "expand",
  "confidence": "high",
  "reasons": [
    {"code": "kpi_on_track", "description": "All KPIs meeting targets", "severity": "info"}
  ],
  "required_actions": [
    {
      "action_id": "act_abc123",
      "description": "Increase rollout coverage to 50%",
      "priority": "medium",
      "due_hours": 48,
      "auto_applicable": true
    }
  ],
  "generated_at": "2026-02-28T14:30:00Z"
}
```

### POST /api/v2/rollout/decision/{segment_key}/override
```json
{
  "new_decision": "rollback",
  "reason": "Critical issue detected in production",
  "overridden_by": "operator@example.com"
}
```

---

## 🧪 Testes

```bash
# Backend
PYTHONPATH=09-tools python -m pytest tests/test_vm_webapp_rollout_decision.py -v
PYTHONPATH=09-tools python -m pytest tests/test_vm_webapp_kpi_scoreboard.py -v
PYTHONPATH=09-tools python -m pytest tests/test_vm_webapp_regression_alerts.py -v

# Frontend
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/
cd 09-tools/web/vm-ui && npm run build
```

---

## 📝 Changelog

### Added
- Weekly KPI Scoreboard endpoint v2
- Segment regression detector com Prometheus metrics
- Rollout Decision Engine (expand/hold/rollback)
- Decision override com auditoria
- CI gate v15

### Changed
- Nightly report inclui resumo de decisões
- Models compatíveis com Python 3.9 (Optional[str])

### Fixed
- Type hints para Python 3.9

---

## 🔗 Referências

- v14: Segmented Copilot (#21)
- v13: Editorial Copilot
- v12: First Run Quality Engine
- v11: Alerting Playbooks E2E

---

**Operação aprovada para produção.** ✅
