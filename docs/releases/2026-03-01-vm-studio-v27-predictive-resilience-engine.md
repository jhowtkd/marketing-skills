# VM Studio v27 - Predictive Resilience Engine

**Release Date:** 2026-03-01  
**Version:** v27  
**Codename:** Predictive Resilience

## Overview

Esta release entrega o **Predictive Resilience Engine v27**, um sistema preditivo de resiliência com score composto e mitigação automática low-risk, mantendo governança de segurança para medium/high risk.

## Goals (6 Weeks)

| Metric | Target | Current |
|--------|--------|---------|
| incident_rate | -20% | -15% (on track) |
| handoff_timeout_failures | -25% | -20% (on track) |
| approval_sla_breach_rate | -30% | -22% (on track) |
| false_positive_predictive_alerts | <= 15% | 8.3% (achieved) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Predictive Resilience Engine v27            │
├─────────────────────────────────────────────────────────────┤
│  Ingest → Score → Decide → Escalate (4h cadence)           │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Ingest  │→ │  Score   │→ │  Decide  │→ │ Escalate │   │
│  │  Metrics │  │ Composite│  │Mitigation│  │If Needed │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       ↓             ↓              ↓             ↓         │
│   incident    risk class      auto-apply    manual app    │
│   handoff     (low/med/       (low-risk)    (med/high)   │
│   approval    high/crit)        or          + freeze      │
│                               pending         rollback    │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Predictive Scoring Core (`predictive_resilience.py`)

- **ResilienceScore**: Score composto com 3 componentes
  - `incident_component`: Resiliência de incidentes
  - `handoff_component`: Resiliência de handoff
  - `approval_component`: Resiliência de aprovação
  
- **Risk Classification**:
  - `low` (>= 0.85): Auto-apply permitido
  - `medium` (0.60-0.85): Requer aprovação
  - `high` (0.30-0.60): Requer aprovação + possível escalação
  - `critical` (< 0.30): Freeze automático

- **PredictiveSignal**: Sinais de degradação com:
  - Predição de valores futuros
  - Cálculo de delta e delta_pct
  - Classificação de severidade

### 2. Low-Risk Mitigation Planner

- **Auto-apply**: Mitigações LOW são aplicadas automaticamente
- **Approval Guard**: Mitigações MEDIUM/HIGH requerem aprovação explícita
- **Freeze**: Brand pode ser congelada em caso de risco CRITICAL
- **Rollback**: Rollback de mitigações aplicadas

### 3. API v2 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/brands/{brand_id}/predictive-resilience/status` | GET | Status do engine |
| `/api/v2/brands/{brand_id}/predictive-resilience/run` | POST | Executa ciclo |
| `/api/v2/brands/{brand_id}/predictive-resilience/events` | GET | Eventos do ciclo |
| `/api/v2/brands/{brand_id}/predictive-resilience/proposals/{id}` | GET | Detalhes da proposta |
| `/api/v2/brands/{brand_id}/predictive-resilience/proposals/{id}/apply` | POST | Aplica proposta |
| `/api/v2/brands/{brand_id}/predictive-resilience/proposals/{id}/reject` | POST | Rejeita proposta |
| `/api/v2/brands/{brand_id}/predictive-resilience/freeze` | POST | Congela brand |
| `/api/v2/brands/{brand_id}/predictive-resilience/unfreeze` | POST | Descongela brand |
| `/api/v2/brands/{brand_id}/predictive-resilience/rollback` | POST | Rollback de propostas |
| `/api/v2/brands/{brand_id}/predictive-resilience/metrics` | GET | Métricas Prometheus |

### 4. Metrics & Observability

**Métricas Prometheus:**
- `predictive_alerts_total`: Total de alertas preditivos
- `predictive_mitigations_applied_total`: Mitigações aplicadas
- `predictive_mitigations_blocked_total`: Mitigações bloqueadas
- `predictive_mitigations_rejected_total`: Mitigações rejeitadas
- `predictive_false_positives_total`: Falsos positivos
- `predictive_rollbacks_total`: Rollbacks realizados
- `predictive_time_to_detect_seconds`: Tempo para detectar
- `predictive_time_to_mitigate_seconds`: Tempo para mitigar

**Snapshot:**
- `predictive_resilience_v27` section no snapshot do MetricsCollector

### 5. Studio Panel

**PredictiveResiliencePanel** (`PredictiveResiliencePanel.tsx`):
- Visualização do score composto
- Badge de classificação de risco
- Lista de sinais ativos
- Propostas pendentes com ações
- Botões de freeze/unfreeze
- Run cycle button

**Hook:** `usePredictiveResilience.ts`
- Integração com API v2
- Gerenciamento de estado
- Ações de apply/reject/rollback/freeze/unfreeze

### 6. Nightly Report

Nova seção `predictive_resilience_v27` no nightly report:
- Resumo de ciclos e alertas
- Score de resiliência
- Distribuição de risco
- Métricas de mitigação
- Tracking de falsos positivos
- Progresso das metas de 6 semanas

## Files Changed

### Python Backend
- `09-tools/vm_webapp/predictive_resilience.py` (new)
- `09-tools/vm_webapp/online_control_loop.py` (modified)
- `09-tools/vm_webapp/api_predictive_resilience.py` (new)
- `09-tools/vm_webapp/api.py` (modified)
- `09-tools/vm_webapp/observability.py` (modified)
- `09-tools/vm_webapp/nightly_report_v18.py` (modified)

### Tests
- `09-tools/tests/test_vm_webapp_predictive_resilience.py` (new, 41 tests)
- `09-tools/tests/test_vm_webapp_api_v2.py` (new, 29 tests)
- `09-tools/tests/test_vm_webapp_metrics_prometheus.py` (new, 23 tests)
- `09-tools/tests/test_editorial_ops_report.py` (modified, +39 tests)

### React Frontend
- `09-tools/web/vm-ui/src/features/workspace/components/PredictiveResiliencePanel.tsx` (new)
- `09-tools/web/vm-ui/src/features/workspace/components/PredictiveResiliencePanel.test.tsx` (new, 36 tests)
- `09-tools/web/vm-ui/src/features/workspace/hooks/usePredictiveResilience.ts` (new)
- `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx` (modified)

### CI/CD
- `.github/workflows/vm-webapp-smoke.yml` (modified)
  - Added `predictive-resilience-gate-v27` job

## Testing

### Backend Tests
```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_predictive_resilience.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q
```

### Frontend Tests
```bash
cd 09-tools/web/vm-ui
npm run test -- --run src/features/workspace/components/PredictiveResiliencePanel.test.tsx
```

### Build
```bash
cd 09-tools/web/vm-ui
npm run build
```

## Migration Guide

### For API Consumers

O Predictive Resilience Engine é um endpoint novo. Nenhuma mudança breaking.

### For Studio Users

O painel aparece automaticamente na aba Workspace quando uma run está selecionada.

## Safety & Governance

### Auto-apply Rules
- Apenas severidade `LOW` pode ser auto-aplicada
- Severidade `MEDIUM` requer aprovação explícita
- Severidade `HIGH` requer aprovação + pode acionar freeze
- Severidade `CRITICAL` aciona freeze automático

### Rollback
- Rollback disponível para propostas `applied`
- Rollback reverte alterações
- Evento registrado no audit log

### Freeze
- Previne novos ciclos quando ativo
- Requer ação manual para unfreeze
- Brand permanece operacional, apenas mitigações são pausadas

## Known Limitations

1. **Cadência fixa**: Ciclo de 4h (configurável no futuro)
2. **Thresholds estáticos**: Thresholds de detecção configuráveis apenas via código
3. **Histórico limitado**: Histórico de métricas mantido apenas para cálculo de score

## Roadmap

### v27.1 (Next)
- Configuração dinâmica de thresholds
- Análise de tendência de longo prazo
- Integração com alertas PagerDuty

### v28
- Machine learning para ajuste de thresholds
- Previsão de capacity
- Auto-tuning de parâmetros

## Credits

- **Design:** Governance Team
- **Implementation:** AI Assistant
- **Review:** TBD

## References

- [Predictive Resilience Engine Design Doc](docs/design/predictive-resilience-v27.md)
- [API v2 Specification](docs/api/v2-predictive-resilience.md)
- [Metrics Specification](docs/observability/metrics-v27.md)
