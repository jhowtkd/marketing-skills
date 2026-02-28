# VM Studio v17 - Safety Gates Auto-Tuning

**Release Date:** 2026-02-28  
**Version:** v17.0.0  
**Codename:** Safety Auto-Tuning

## Overview

Implementação de auto-tuning semanal semi-automático dos safety gates, com limites rígidos, autoapply seguro e rollback automático em 48h.

## Goals (6 weeks)

- **False positives de bloqueio:** -30%
- **Incidentes reais não bloqueados:** Sem aumento
- **Approval_without_regen_24h:** +3 p.p.

## Architecture

- **Tuner determinístico:** analyze/propose/apply
- **Auditoria completa:** Todos os ciclos registrados
- **Integração Studio:** Ações manuais de apply/revert/freeze

## New Components

### Backend

| Component | Description |
|-----------|-------------|
| `safety_autotuning.py` | Core auto-tuner engine (analyze/propose) |
| `safety_autotuning_apply.py` | Apply/rollback with safety guards |
| `safety_tuning_audit.py` | Audit trail persistence |
| `safety_tuning_metrics.py` | Prometheus metrics collection |
| `api_safety_tuning.py` | API v2 endpoints |

### Frontend

| Component | Description |
|-----------|-------------|
| `SafetyAutotuningCard.tsx` | Control Center card |
| `useSafetyAutotuning.ts` | Hook for API integration |

## API Endpoints

```
GET  /api/v2/safety-tuning/status
POST /api/v2/safety-tuning/run
POST /api/v2/safety-tuning/{proposal_id}/apply
POST /api/v2/safety-tuning/{proposal_id}/revert
POST /api/v2/safety-tuning/gates/{gate_name}/freeze
POST /api/v2/safety-tuning/gates/{gate_name}/unfreeze
GET  /api/v2/safety-tuning/audit
```

## Safety Features

### Auto-Tuning Limits
- **Max adjustment per cycle:** ±10%
- **Min volume threshold:** 50 decisions
- **Cadence:** Weekly
- **Mode:** Semi-automático

### Apply Guards
- Autoapply apenas para **low-risk**
- Rollback automático em 48h em caso de degradação
- Bloqueio com canary/rollback ativo
- Freeze manual por gate

### Rollback Triggers
- FP rate spike (>5% increase)
- Incidents increased (>3% increase)
- Approval rate drop (>5% decrease)
- Manual revert

## Metrics

### Prometheus Counters
- `vm_safety_tuning_cycles_completed`
- `vm_safety_tuning_proposals_generated`
- `vm_safety_tuning_adjustments_applied`
- `vm_safety_tuning_adjustments_blocked`
- `vm_safety_tuning_rollbacks_triggered`

### Gauges
- `vm_safety_tuning_frozen_gates`
- `vm_safety_tuning_fp_rate_delta`
- `vm_safety_tuning_incidents_delta`

## Tests

```bash
# Backend tests
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_safety_autotuning.py -q
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_safety_autotuning_apply.py -q
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_api_v2_additions.py -q
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_metrics_prometheus_v17.py -q

# Frontend tests
cd 09-tools/web/vm-ui
npm run test -- --run src/features/workspace/components/SafetyAutotuningCard.test.tsx
npm run build
```

## CI Gate

```yaml
safety-autotuning-gate-v17:
  - Test safety auto-tuning backend
  - Test safety auto-tuning UI
  - Build frontend
```

## Migration Notes

No breaking changes. Auto-tuning é opt-in via API.

## Related PRs

- feat(v17): add safety auto-tuning propose engine
- feat(v17): add guarded auto-apply and 48h rollback
- feat(api-v2): add safety gate auto-tuning endpoints
- feat(observability): add v17 auto-tuning metrics
- feat(studio): add safety auto-tuning card

## Team

- **Owner:** Platform Team
- **Stakeholders:** Editorial, Data Science
- **Reviewers:** @platform-leads
