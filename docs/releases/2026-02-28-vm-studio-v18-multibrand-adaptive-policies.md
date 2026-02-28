# VM Studio v18 - Multi-Brand Adaptive Policies

**Release Date:** 2026-02-28  
**Version:** v18.0.0

## Overview

This release introduces a comprehensive multi-brand adaptive policy engine with hierarchical policy resolution, cross-brand divergence guards, and complete governance controls for the VM Studio platform.

## Key Features

### 🏛️ Hierarchical Policy Resolver

Policy resolution with precedence: **segment > brand > global**

- **Global policies**: Default baseline settings
- **Brand policies**: Brand-specific overrides
- **Segment policies**: Most specific, highest priority

```typescript
// Example effective policy resolution
GET /v2/brands/{brand_id}/policy/effective?segment=enterprise&objective_key=conversion

{
  "threshold": 0.75,
  "mode": "enterprise",
  "source": "segment",
  "source_brand_id": "brand1",
  "source_segment": "enterprise"
}
```

### 📝 Adaptive Policy Proposal Engine

Semi-automated policy adaptation with safety guardrails:

- **±10% max adjustment** per cycle
- **Cross-brand divergence guard** blocks proposals during incidents/canaries/rollbacks
- **P90-P10 gap monitoring** reduces aggressiveness when quality gap exceeds 15%

### 🎛️ Governance Controls

Complete operational controls for policy management:

| Action | Endpoint | Description |
|--------|----------|-------------|
| Approve | `POST /v2/brands/{id}/policy/proposals/{id}/approve` | Approve pending proposal |
| Reject | `POST /v2/brands/{id}/policy/proposals/{id}/reject` | Reject pending proposal |
| Freeze | `POST /v2/brands/{id}/policy/freeze` | Freeze all policy changes |
| Rollback | `POST /v2/brands/{id}/policy/rollback` | Rollback to previous version |

### 📊 Observability & Metrics

New Prometheus metrics for monitoring:

```
vm_policy_proposal_total       # Counter
vm_policy_applied_total        # Counter
vm_policy_blocked_total        # Counter
vm_policy_rollback_total       # Counter
vm_policy_freeze_total         # Counter
vm_cross_brand_gap_p90_p10     # Gauge
```

### 📈 Nightly Report Updates

New `multibrand_governance` section in nightly reports:

```json
{
  "multibrand_governance": {
    "policy_diffs": {
      "proposed": 5,
      "applied": 3,
      "rejected": 1,
      "blocked": 1
    },
    "guard_blocks": {
      "incident": 1,
      "canary": 0,
      "rollback": 0
    },
    "cross_brand_gap_p90_p10": 0.15,
    "goals": {
      "false_positives_reduction": {"target": -0.20, "current": -0.15},
      "approval_without_regen_improvement": {"target": 0.04, "current": 0.02},
      "quality_gap_reduction": {"target": -0.15, "current": -0.08}
    }
  }
}
```

## 6-Week Goals

| Goal | Target | Current Progress |
|------|--------|------------------|
| False positives cross-brand | -20% | -15% (on track) |
| Approval without regen 24h (eligible) | +4 p.p. | +2 p.p. (on track) |
| Quality gap P90-P10 across brands | -15% | -8% (on track) |

## API Endpoints

### Policy Operations

```
GET  /v2/brands/{brand_id}/policy/effective
GET  /v2/brands/{brand_id}/policy/proposals
POST /v2/brands/{brand_id}/policy/proposals
POST /v2/brands/{brand_id}/policy/proposals/{proposal_id}/approve
POST /v2/brands/{brand_id}/policy/proposals/{proposal_id}/reject
POST /v2/brands/{brand_id}/policy/proposals/{proposal_id}/apply
POST /v2/brands/{brand_id}/policy/freeze
POST /v2/brands/{brand_id}/policy/rollback
```

## Studio UI Updates

### New Policies Panel

The workspace now includes a dedicated **Policies** tab with:

- **Effective policy display** with source transparency
- **Pending proposals** list with approve/reject actions
- **Previous proposals** history
- **Freeze/Rollback** controls
- **Brand breakdown** view

```typescript
import { PoliciesPanel } from './components/PoliciesPanel';
import { usePolicies } from './hooks/usePolicies';

// Hook provides complete policy management
const {
  policy,
  proposals,
  isLoading,
  error,
  isFrozen,
  fetchPolicy,
  approveProposal,
  rejectProposal,
  freezePolicy,
  rollbackPolicy,
} = usePolicies();
```

## Files Added/Modified

### Backend
- `09-tools/vm_webapp/policy_hierarchy.py` - Hierarchical policy resolver
- `09-tools/vm_webapp/policy_adaptation.py` - Proposal engine & divergence guard
- `09-tools/vm_webapp/policy_operations.py` - Operations service layer
- `09-tools/vm_webapp/nightly_report_v18.py` - Report generation v18
- `09-tools/vm_webapp/models.py` - Added Policy model

### Frontend
- `09-tools/web/vm-ui/src/features/workspace/components/PoliciesPanel.tsx`
- `09-tools/web/vm-ui/src/features/workspace/components/PoliciesPanel.test.tsx`
- `09-tools/web/vm-ui/src/features/workspace/hooks/usePolicies.ts`

### Tests
- `09-tools/tests/test_vm_webapp_policy_hierarchy.py` (12 tests)
- `09-tools/tests/test_vm_webapp_policy_adaptation.py` (19 tests)
- `09-tools/tests/test_vm_webapp_api_v2.py` (18 tests)
- `09-tools/tests/test_vm_webapp_metrics_prometheus.py` (18 tests)
- `09-tools/tests/test_editorial_ops_report.py` (17 tests)

### CI/CD
- `.github/workflows/vm-webapp-smoke.yml` - Added `multibrand-adaptive-policies-gate-v18`

## Migration Guide

### Database Migration

```sql
-- Create policies table
CREATE TABLE policies (
    policy_id VARCHAR(64) PRIMARY KEY,
    level VARCHAR(32) NOT NULL,
    brand_id VARCHAR(64),
    segment VARCHAR(64),
    objective_key VARCHAR(128),
    params_json TEXT NOT NULL DEFAULT '{}',
    created_at VARCHAR(64) NOT NULL,
    updated_at VARCHAR(64) NOT NULL
);

CREATE INDEX idx_policies_level ON policies(level);
CREATE INDEX idx_policies_brand ON policies(brand_id);
CREATE INDEX idx_policies_segment ON policies(segment);
CREATE INDEX idx_policies_objective ON policies(objective_key);
```

### Configuration

No configuration changes required. The policy engine uses sensible defaults:

- Max adjustment: ±10%
- Max P90-P10 gap: 15%
- Critical gap threshold: 25%

## Testing

Run the full v18 test suite:

```bash
# Backend tests
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_policy_hierarchy.py -q
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_policy_adaptation.py -q
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
PYTHONPATH=09-tools pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q
PYTHONPATH=09-tools pytest 09-tools/tests/test_editorial_ops_report.py -q

# Frontend tests
cd 09-tools/web/vm-ui
npm run test -- --run src/features/workspace/components/PoliciesPanel.test.tsx

# Build verification
npm run build
```

## Known Limitations

1. **Policy history**: Currently keeps in-memory history; persistent storage planned for v19
2. **Gap calculation**: Computed from thresholds only; full metric support planned
3. **Concurrent modifications**: No optimistic locking yet; last-write-wins

## Future Enhancements (v19)

- [ ] Persistent policy history with audit trail
- [ ] A/B testing integration for policy changes
- [ ] ML-based policy recommendation engine
- [ ] Cross-brand policy templates
- [ ] Scheduled policy changes

## Contributors

- VM Studio Engineering Team

## Changelog

### v18.0.0 (2026-02-28)
- ✅ Hierarchical policy resolver (segment > brand > global)
- ✅ Adaptive policy proposal engine with ±10% clamp
- ✅ Cross-brand divergence guard (incident/canary/rollback blocks)
- ✅ Complete governance controls (approve/reject/freeze/rollback)
- ✅ New v18 metrics and nightly report section
- ✅ Policies panel in Studio UI
- ✅ CI gate v18 with full test coverage
