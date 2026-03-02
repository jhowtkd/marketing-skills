# Changelog

All notable changes to the Vibe Marketing platform.

## [v33.0.0] - Onboarding Personalization Autopilot

### Added
- **Segment Profiler**: Hierarchical policy resolution (segment → brand → global)
  - `SegmentKey`: Company size, industry, experience level, acquisition channel
  - Exact match priority with wildcard fallbacks
  - `PolicyResult` with source attribution for observability
- **Personalization Policy Model**: Flexible policy configuration
  - `nudge_delay_ms`: Customizable nudge timing
  - `template_order`: Prioritized template sequence
  - `welcome_message`: Personalized welcome content
  - `RiskLevel`: LOW (auto-apply), MEDIUM/HIGH (needs approval)
  - `PolicyStatus`: DRAFT → ACTIVE → FROZEN/ROLLED_BACK
- **Policy Serving Engine**: Low-latency policy resolution
  - Sub-30ms serve latency target
  - Latency tracking per request
  - Fallback hierarchy with metrics attribution
- **Safe Rollout Manager**: Guarded promotion workflow
  - `CanaryConfig`: Gradual ramp percentage and duration
  - Guardrails: max_latency_ms (5000ms), max_steps (7), max_nudge_delay (10000ms)
  - Auto-apply for LOW risk, approval gate for MEDIUM/HIGH
  - Validation with structured failure reasons
- **API v2 Endpoints**:
  - `GET /api/v2/brands/{brand_id}/onboarding-personalization/status` - Serve metrics
  - `POST /api/v2/brands/{brand_id}/onboarding-personalization/run` - Execute rollouts
  - `GET /api/v2/brands/{brand_id}/onboarding-personalization/policies` - List policies
  - `GET /api/v2/brands/{brand_id}/onboarding-personalization/effective` - Get effective policy
  - `POST /api/v2/brands/{brand_id}/onboarding-personalization/policies/{id}/apply` - Apply policy
  - `POST /api/v2/brands/{brand_id}/onboarding-personalization/policies/{id}/reject` - Reject policy
  - `POST /api/v2/brands/{brand_id}/onboarding-personalization/freeze` - Emergency freeze
  - `POST /api/v2/brands/{brand_id}/onboarding-personalization/rollback` - Rollback policy
- **Observability**:
  - `OnboardingPersonalizationMetrics` dataclass with serve/rollout/guardrail metrics
  - Prometheus integration: serves_total, serve_latency, rollouts by decision type
  - Nightly report section with 6-week goal tracking
- **CI Gate**: GitHub Actions workflow for v33 validation

### Metrics

| Metric | Target | Method |
|--------|--------|--------|
| onboarding_completion_rate | +6 pp | Segment personalization |
| time_to_first_value | -15% | Optimized nudge timing |
| nudge_acceptance_rate | +12% | Template ordering |
| promotion_lead_time | -50% | Auto-apply for low risk |
| incident_rate | No increase | Guardrails + validation |

### Files Added/Modified

```
09-tools/vm_webapp/onboarding_personalization.py         (+180 lines)
09-tools/vm_webapp/onboarding_policy_rollout.py          (+220 lines)
09-tools/vm_webapp/api_onboarding_personalization.py     (+200 lines)
09-tools/vm_webapp/observability.py                      (+80 lines)
09-tools/scripts/editorial_ops_report.py                 (+60 lines)
09-tools/tests/test_vm_webapp_onboarding_personalization.py
09-tools/tests/test_vm_webapp_onboarding_policy_rollout.py
09-tools/tests/test_vm_webapp_api_v2.py                  (v33 additions)
09-tools/tests/test_vm_webapp_metrics_prometheus.py      (v33 additions)
.github/workflows/v33-ci-gate.yml
CHANGELOG.md
```

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
