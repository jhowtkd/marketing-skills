# VM Studio v28 - Auto-Recovery Orchestration

**Release Date:** 2026-03-02  
**Governance Version:** v28  
**Status:** Released

---

## Summary

Orquestração automática de recuperação com playbooks encadeados para handoff, SLA e qualidade. Sistema supervisionado com aprovação para ações de médio/alto risco e execução automática para baixo risco.

---

## Goals (6 weeks)

| Metric | Target | Measurement |
|--------|--------|-------------|
| `incident_rate` | -20% | Incidents per 1000 operations |
| `handoff_timeout_failures` | -30% | Handoff timeouts per day |
| `approval_sla_breach_rate` | -25% | Approvals past SLA threshold |
| `mttr` | -35% | Mean Time To Recovery (seconds) |

---

## Features

### Recovery Orchestrator Core
- Classificação automática de severidade de incidentes
- Planejamento de cadeia de recuperação baseado no tipo de incidente
- Suporte para 5 tipos de incidentes:
  - `handoff_timeout` - Timeouts em handoff entre agentes
  - `approval_sla_breach` - Violações de SLA em aprovações
  - `quality_regression` - Degradação de qualidade
  - `system_failure` - Falhas de sistema
  - `resource_exhaustion` - Esgotamento de recursos

### Playbook Chain Executor
- Execução sequencial de steps com dependências
- Timeout e retry configuráveis por step
- Idempotência garantida via execution store
- Detecção de dependências circulares
- Skip automático de steps quando dependências falham

### API v2 Recovery Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v2/brands/{brand_id}/recovery/status` | Status e métricas de recovery |
| `POST` | `/api/v2/brands/{brand_id}/recovery/run` | Inicia novo recovery |
| `GET` | `/api/v2/brands/{brand_id}/recovery/events` | Lista eventos de recovery |
| `POST` | `/api/v2/brands/{brand_id}/recovery/approve/{request_id}` | Aprova recovery pendente |
| `POST` | `/api/v2/brands/{brand_id}/recovery/reject/{request_id}` | Rejeita recovery pendente |
| `POST` | `/api/v2/brands/{brand_id}/recovery/freeze/{incident_id}` | Congela recovery em execução |
| `POST` | `/api/v2/brands/{brand_id}/recovery/rollback/{run_id}` | Faz rollback de recovery |

### Supervised Actions
| Severity | Action | Requires Approval |
|----------|--------|-------------------|
| `low` | Auto-execute | No |
| `medium` | Approve/execute | Yes |
| `high` | Approve/execute | Yes |
| `critical` | Approve/execute + escalation | Yes |

### Observability
- Métricas Prometheus para recovery
- MTTR tracking
- Contadores de runs (auto/manual, successful/failed)
- Contadores de steps (successful/failed/skipped)
- Contadores de aprovações (requested/granted/rejected)
- Classificação de incidentes por tipo

### Studio Panel
- Painel de orquestração de recovery no VM Studio
- Visualização de métricas em tempo real
- Lista de aprovações pendentes
- Ações: approve, reject, freeze, rollback, retry
- Indicadores de severidade e status coloridos

---

## Technical Implementation

### Files Created
```
09-tools/vm_webapp/recovery_orchestrator.py          # Core orchestrator
09-tools/vm_webapp/recovery_chain.py                 # Chain executor
09-tools/vm_webapp/api_recovery.py                   # API endpoints
09-tools/web/vm-ui/src/features/workspace/components/RecoveryOrchestrationPanel.tsx
09-tools/web/vm-ui/src/features/workspace/hooks/useRecoveryOrchestration.ts
09-tools/tests/test_vm_webapp_recovery_orchestrator.py
09-tools/tests/test_vm_webapp_recovery_chain.py
```

### Files Modified
```
09-tools/vm_webapp/observability.py                  # Added RecoveryOrchestrationMetrics
09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx
09-tools/scripts/nightly_report_v18.py               # Added v28 section
.github/workflows/vm-webapp-smoke.yml                # Added v28 gate
```

---

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Recovery Orchestrator | 15 | ✅ PASS |
| Recovery Chain | 16 | ✅ PASS |
| API v2 Endpoints | 17 | ✅ PASS |
| Metrics Prometheus | 15 | ✅ PASS |
| Studio Panel | 24 | ✅ PASS |
| **Total** | **87** | ✅ **PASS** |

---

## CI/CD Integration

### GitHub Actions Gate
```yaml
recovery-orchestration-gate-v28:
  tests:
    - test_vm_webapp_recovery_orchestrator.py
    - test_vm_webapp_recovery_chain.py
    - test_vm_webapp_api_v2.py
    - test_vm_webapp_metrics_prometheus.py
  ui-tests:
    - RecoveryOrchestrationPanel.test.tsx
  build:
    - npm run build
```

---

## Metrics Targets Validation

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| incident_rate | TBD | -20% | Prometheus counter |
| handoff_timeout_failures | TBD | -30% | Recovery metrics |
| approval_sla_breach_rate | TBD | -25% | Recovery metrics |
| mttr | TBD | -35% | MTTR avg seconds |

---

## Migration Notes

- No breaking changes
- All existing v27 features remain functional
- Recovery Orchestration runs alongside Predictive Resilience
- Nightly report v18 includes new v28 section

---

## References

- Implementation Plan: `docs/plans/2026-03-02-vm-studio-v28-auto-recovery-orchestration-implementation.md`
- Parent Feature: Governance v28
- Related: v27 Predictive Resilience

---

## Contributors

- VM Studio Engineering Team
- Auto-Recovery Working Group

---

*Released with ❤️ by the VM Studio Team*
