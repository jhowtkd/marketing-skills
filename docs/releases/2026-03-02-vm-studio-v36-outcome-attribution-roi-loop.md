# VM Studio v36.0.0 - Outcome Attribution & Hybrid ROI Loop

**Release Date:** 2026-03-02  
**Milestone:** v36 - Outcome Attribution & Hybrid ROI Loop

## Overview

O v36 introduz o Outcome Attribution & Hybrid ROI Loop, um sistema que otimiza onboarding/recovery/continuity por impacto real usando atribuição de outcome e score de ROI híbrido (financeiro + operacional).

## Architecture

**Ciclo semanal:** attribute → score → propose → apply/review

- Proposals low-risk podem ser autoaplicadas
- Medium/high risk exigem aprovação humana
- Guardrails evitam otimização parcial que degrade qualidade ou estabilidade

## New Features

### 1. Outcome Attribution Core
- Attribution graph com versioned checkpoints
- Multiple attribution methods: linear, first-touch, last-touch, time-decay
- Attribution window com filtro temporal
- Outcome tracking: activation, recovery, resume, first_run, feature_adoption

### 2. Hybrid ROI Scoring Engine
- Financial metrics: revenue, cost, ROI, payback time
- Operational metrics: human minutes, success rate, efficiency
- Hybrid ROI index: 60% financial + 40% operational
- Quality penalties: incident-based and degradation-based
- Risk classification: low/medium/high

### 3. Guardrails & Block Rules
- Min success rate: 80%
- Max incident rate: 5%
- Min user satisfaction: 70%
- Block on incident spikes
- Block on critical errors

### 4. API v2 Endpoints (9 endpoints)
- `GET /api/v2/brands/{brand_id}/outcome-roi/status`
- `POST /api/v2/brands/{brand_id}/outcome-roi/run`
- `GET /api/v2/brands/{brand_id}/outcome-roi/proposals`
- `GET /api/v2/brands/{brand_id}/outcome-roi/proposals/{id}`
- `GET /api/v2/brands/{brand_id}/outcome-roi/breakdown`
- `POST /api/v2/brands/{brand_id}/outcome-roi/proposals/{id}/apply`
- `POST /api/v2/brands/{brand_id}/outcome-roi/proposals/{id}/reject`
- `POST /api/v2/brands/{brand_id}/outcome-roi/freeze`
- `POST /api/v2/brands/{brand_id}/outcome-roi/rollback`

### 5. Observability & Metrics
- Attribution metrics: outcomes, methods, touchpoints
- Proposal metrics: generated, auto-applied, approved, rejected, blocked
- Hybrid ROI metrics: index avg/min/max, payback time
- Guardrail metrics: violations by type
- Quality metrics: penalties applied
- Rollback tracking

### 6. Studio Panel (React)
- Proposal cards with risk levels and hybrid index
- Metrics dashboard
- Risk distribution visualization
- Hybrid ROI summary
- Supervised actions: apply, reject, freeze, rollback
- Real-time polling

## Test Coverage

| Component | Tests |
|-----------|-------|
| Outcome Attribution Core | 22 passed |
| Hybrid ROI Engine | 38 passed |
| API v2 Endpoints | 18 passed |
| Observability Metrics | 26 passed |
| Studio Panel | 10 passed |
| **Total** | **114** |

## 6-Week Goals

| Metric | Target |
|--------|--------|
| hybrid_roi_index | +15% |
| payback_time_days | -20% |
| human_minutes_per_activation | -18% |
| revenue_per_successful_activation | +10% |
| incident_rate | no increase |

## Migration Notes

- No breaking changes
- New endpoints are additive
- Existing v35 continuity features remain unchanged

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Over-optimization degrading UX | Guardrails on success rate and user satisfaction |
| Financial model inaccuracy | Hybrid scoring (not just financial) |
| Incident rate increase | Block rules on incident spikes |

## Files Changed

```
09-tools/vm_webapp/
├── outcome_attribution.py              # NEW
├── hybrid_roi_engine.py                # NEW
├── api_outcome_roi.py                  # NEW
└── observability.py                    # MODIFIED

09-tools/tests/
├── test_vm_webapp_outcome_attribution.py       # NEW
├── test_vm_webapp_hybrid_roi_engine.py         # NEW
├── test_vm_webapp_api_v2_v36_additions.py      # NEW
└── test_vm_webapp_metrics_v36_outcome_roi.py   # NEW

09-tools/web/vm-ui/src/features/workspace/
├── hooks/useOutcomeRoi.ts                      # NEW
├── components/OutcomeRoiPanel.tsx              # NEW
└── components/OutcomeRoiPanel.test.tsx         # NEW

09-tools/scripts/
└── editorial_ops_report.py                     # MODIFIED

.github/workflows/
└── v36-ci-gate.yml                             # NEW

docs/releases/
└── 2026-03-02-vm-studio-v36-outcome-attribution-roi-loop.md  # NEW
```

## Contributors

- VM Studio Engineering Team

## References

- Implementation Plan: docs/plans/2026-03-02-vm-studio-v36-outcome-attribution-roi-loop-implementation.md
