# Changelog

All notable changes to the Vibe Marketing platform.

## [v23.0.0] - Approval Cost Optimizer

### Added
- **Risk Triage Refiner**: Risk level refinement with factor analysis for approval queue
- **Priority Scorer**: Deterministic priority calculation (impact × urgency × risk)
- **Batching Engine**: Intelligent batch creation with safety guards
  - Same-brand batching enforcement (isolation)
  - Risk level mixing checks (prevent incompatible risk levels)
  - Batch size limits (default: 10)
  - TTL expiration (default: 3600s)
  - Fallback to individual queue when batching fails
- **BatchGuard**: Validates batch safety constraints
- **API v2 Endpoints**:
  - `GET /api/v2/optimizer/queue` - Get prioritized queue
  - `POST /api/v2/optimizer/request` - Submit request
  - `POST /api/v2/optimizer/batch/create` - Create batch
  - `POST /api/v2/optimizer/batch/{id}/approve` - Approve batch
  - `POST /api/v2/optimizer/batch/{id}/reject` - Reject batch
  - `POST /api/v2/optimizer/batch/{id}/expand` - Expand batch to individuals
  - `POST /api/v2/optimizer/freeze` - Emergency freeze
  - `POST /api/v2/optimizer/unfreeze` - Unfreeze
- **Observability**:
  - Prometheus metrics: `approval_batches_created_total`, `approval_human_minutes_saved_total`, `approval_queue_length_p95`
  - Nightly savings section with batch efficiency tracking
- **UI Components**:
  - `ApprovalQueueOptimizerPanel` - React panel for queue management
  - `useApprovalOptimizer` hook with polling support
- **CI Gate**: GitHub Actions workflow for v23 tests and validation

### Metrics

| Metric | Target | Method |
|--------|--------|--------|
| approval_human_minutes_per_job | -35% | Batch processing |
| approval_queue_length_p95 | -30% | Priority triage |
| incident_rate | No increase | Risk guards |
| approval_throughput | +10% | Queue optimization |

### Files Added/Modified

```
09-tools/vm_webapp/approval_optimizer.py      (+250 lines)
09-tools/vm_webapp/api_approval_optimizer.py  (+180 lines)
09-tools/vm_webapp/agent_dag_audit.py         (+75 lines)
09-tools/web/vm-ui/src/features/workspace/components/ApprovalQueueOptimizerPanel.tsx
09-tools/web/vm-ui/src/features/workspace/hooks/useApprovalOptimizer.ts
09-tools/tests/test_vm_webapp_approval_optimizer.py
09-tools/tests/test_vm_webapp_api_v2.py
09-tools/tests/test_ui_approval_optimizer.py
.github/workflows/v23-ci-gate.yml
CHANGELOG.md
```

## Previous Versions

See git history for versions prior to v23.
