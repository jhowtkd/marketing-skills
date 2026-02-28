# VM Studio v19 - ROI-Weighted Policy Optimizer

**Release Date:** 2026-02-28  
**Branch:** `feature/governance-v19-roi-weighted-policy-optimizer`  
**Base:** v18 (Multibrand Adaptive Policies)

## Overview

Introduces an ROI-weighted policy optimizer with composite scoring across three pillars (Business 40%, Quality 35%, Efficiency 25%), semi-automatic weekly optimization cadence, hard guardrails, and Studio UI integration.

## Key Features

### 1. ROI Composite Score Engine (`vm_webapp/roi_optimizer.py`)

**Three weighted pillars:**
- **Business (40%)**: `approval_without_regen_24h`, revenue attribution
- **Quality (35%)**: `regen_per_job`, `quality_score_avg`  
- **Efficiency (25%)**: `avg_latency_ms`, `cost_per_job_usd`

**Score normalization:**
- All proxies normalized to 0-1 scale
- Inverted metrics (lower is better) properly handled
- Weighted contributions sum to total composite score

### 2. Proposal Optimizer with Guardrails

**Hard guardrails:**
- ❌ **Incident rate increase blocker**: Proposals that would increase `incident_rate` are automatically blocked
- ❌ **±10% adjustment clamp**: Per-cycle adjustment limits
- ❌ **Risk-based eligibility**: Only `low` risk proposals eligible for auto-apply

**Proposal lifecycle:**
```
PENDING → APPROVED → APPLIED
   ↓         ↓
REJECTED  ROLLED_BACK
   ↑
BLOCKED (by guardrail)
```

**Operation modes:**
- `semi-automatic` (default): Low-risk proposals eligible for auto-apply, manual approval for others
- `manual`: All proposals require explicit approval

### 3. API v2 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/roi/status` | GET | Optimizer status, current score, weights |
| `/api/v2/roi/proposals` | GET | List all proposals with optional status filter |
| `/api/v2/roi/run` | POST | Run optimization with current metrics |
| `/api/v2/roi/proposals/{id}/apply` | POST | Apply a pending proposal |
| `/api/v2/roi/proposals/{id}/reject` | POST | Reject a pending proposal |
| `/api/v2/roi/rollback` | POST | Rollback last applied proposal |

### 4. Studio ROI Optimizer Panel

**Features:**
- Real-time composite score display with pillar breakdown
- Proposal cards with risk indicators and delta projections
- Apply/Reject/Rollback actions
- Autoapply eligibility indicators
- Last run timestamp

**States handled:**
- Loading (initial fetch)
- Empty (no optimization run yet)
- Error (API failures)
- Data (normal operation with scores and proposals)

### 5. Observability Integration

**Metrics added to `observability.py`:**
- `cycles_total`: Number of optimization cycles run
- `proposals_generated_total`: Total proposals created
- `proposals_applied_total`: Successfully applied proposals
- `proposals_blocked_total`: Blocked by guardrails
- `proposals_rejected_total`: Rejected by users
- `rollbacks_total`: Rollback operations
- `roi_composite_score`: Current composite score gauge
- Pillar contribution gauges

**Nightly report section:**
- ROI score change (24h)
- Top ROI gains with proposal details
- Guardrails triggered summary

## Goals (6-week horizon)

| Metric | Target | Current |
|--------|--------|---------|
| ROI composite score | +12% | TBD |
| approval_without_regen_24h | +3 p.p. | TBD |
| regen/job | -10% | TBD |
| incident_rate | no increase | 🛡️ hard guardrail |

## Files Changed

```
09-tools/vm_webapp/
├── roi_optimizer.py                    [NEW] Core ROI engine
├── roi_operations.py                   [NEW] API service layer
├── policy_adaptation.py                [MOD] v19 exports added
├── api.py                              [MOD] v2 endpoints added
└── observability.py                    [MOD] v19 metrics added

09-tools/tests/
├── test_vm_webapp_roi_optimizer.py     [NEW] ROI engine tests
└── test_vm_webapp_api_v2.py            [MOD] API v2 tests

09-tools/web/vm-ui/src/features/workspace/
├── hooks/useRoiOptimizer.ts            [NEW] React hook
├── components/RoiOptimizerPanel.tsx    [NEW] Panel component
└── components/RoiOptimizerPanel.test.tsx [NEW] Tests

.github/workflows/
└── vm-webapp-smoke.yml                 [MOD] v19 gate added

docs/releases/
└── 2026-02-28-vm-studio-v19-roi-weighted-policy-optimizer.md [NEW]
```

## Testing

**Backend:**
```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_roi_optimizer.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q
```

**Frontend:**
```bash
cd 09-tools/web/vm-ui
npm run test -- --run src/features/workspace/components/RoiOptimizerPanel.test.tsx
npm run build
```

## Migration Notes

- No breaking changes to existing APIs
- ROI optimizer operates alongside existing policy adaptation
- Integration exports available from `policy_adaptation` module
- UI panel is additive (doesn't replace existing panels)

## Security & Guardrails

1. **Incident hard-stop**: Proposals increasing incident rate are blocked before any action
2. **Adjustment clamping**: Maximum ±10% change per cycle prevents aggressive oscillations
3. **Risk classification**: Only LOW risk proposals eligible for auto-apply
4. **Audit trail**: All proposals tracked with timestamps and status history

## Future Enhancements

- [ ] ML-based proposal ranking
- [ ] Multi-objective optimization
- [ ] A/B testing integration for proposals
- [ ] Custom weight configuration per brand
- [ ] Predictive incident rate modeling

---

**Commit Hash:** `TBD`  
**CI Gate:** `roi-weighted-policy-optimizer-gate-v19` ✅
