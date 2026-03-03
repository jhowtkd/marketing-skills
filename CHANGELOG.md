# Changelog

All notable changes to the Vibe Marketing platform.

## [v35.0.0] - Cross-Session Continuity Autopilot

### Added
- **Session State Graph**: Versioned checkpoints for deterministic continuity
  - `CheckpointStatus`: active, committed, rolled_back, expired
  - `SessionCheckpoint` with auto-incrementing versions
  - `HandoffBundle` for cross-session context transfer
  - `SourcePriority`: SESSION > RECOVERY > DEFAULT for conflict resolution
- **Resume Orchestrator**: Conflict detection and resolution
  - `ConflictType`: data_mismatch, step_regression, form_inconsistency, version_gap
  - `ConsistencyGuardrails`: max_version_gap (5), max_step_regression (2)
  - `ConflictResolution`: use_higher_priority, use_latest, merge, reject
  - Auto-apply for low risk, approval for high risk
- **API v2 Endpoints**:
  - `GET /api/v2/brands/{brand_id}/onboarding-continuity/status` - Continuity metrics
  - `POST /api/v2/brands/{brand_id}/onboarding-continuity/run` - Create checkpoint + bundle
  - `GET /api/v2/brands/{brand_id}/onboarding-continuity/handoffs` - List handoffs
  - `GET /api/v2/brands/{brand_id}/onboarding-continuity/handoffs/{id}` - Handoff detail
  - `POST /api/v2/brands/{brand_id}/onboarding-continuity/resume` - Execute resume
  - `POST /api/v2/brands/{brand_id}/onboarding-continuity/freeze` - Emergency freeze
  - `POST /api/v2/brands/{brand_id}/onboarding-continuity/rollback` - Rollback operations
- **Observability**:
  - `OnboardingContinuityMetrics`: checkpoints, bundles, context_loss, conflicts
  - Source distribution tracking: session, recovery, default
  - Nightly report section with v35 6-week goal tracking
- **Studio Continuity Ops Panel**:
  - `useOnboardingContinuity` hook with polling
  - `OnboardingContinuityPanel` component with handoff management
  - Context payload preview, conflict display, resume controls
- **CI Gate**: GitHub Actions workflow for v35 validation (6 jobs)

### Metrics

| Metric | Target | Method |
|--------|--------|--------|
| resume_completion_rate | +15 pp | Versioned checkpoints + conflict resolution |
| time_to_resume_after_dropoff | -25% | Deterministic handoff bundles |
| context_loss_rate | -40% | Consistency guardrails + validation |
| first_run_after_resume_rate | +10 pp | Source priority resolution |
| incident_rate | No increase | Approval gates + rollback support |

### Files Added/Modified

```
09-tools/vm_webapp/onboarding_continuity.py                      (+306 lines)
09-tools/vm_webapp/onboarding_resume_orchestrator.py             (+427 lines)
09-tools/vm_webapp/api_onboarding_continuity.py                  (+403 lines)
09-tools/vm_webapp/observability.py                              (+198 lines)
09-tools/scripts/editorial_ops_report.py                         (+70 lines)
09-tools/tests/test_vm_webapp_onboarding_continuity.py
09-tools/tests/test_vm_webapp_onboarding_resume_orchestrator.py
09-tools/tests/test_vm_webapp_api_v2_v35_additions.py
09-tools/tests/test_vm_webapp_metrics_v35_continuity.py
09-tools/web/vm-ui/src/features/workspace/hooks/useOnboardingContinuity.ts
09-tools/web/vm-ui/src/features/workspace/components/OnboardingContinuityPanel.tsx
09-tools/web/vm-ui/src/features/workspace/components/OnboardingContinuityPanel.test.tsx
.github/workflows/v35-ci-gate.yml
CHANGELOG.md
docs/releases/2026-03-02-vm-studio-v35-cross-session-continuity-autopilot.md
```

## [v34.0.0] - Onboarding Recovery & Reactivation Autopilot

### Added
- **Dropoff Detection Engine**: Automatic detection of onboarding abandonment
  - Detection rules: step abandonment (60min), timeout (24h), errors, external interruption
  - `RecoveryCase` with states: active → recoverable → recovered/expired
  - Priority calculation: HIGH (>70% or errors), MEDIUM (30-70%), LOW (<30%)
- **Reactivation Strategy Engine**: Intelligent recovery strategy selection
  - `ReactivationStrategy`: reminder, fast_lane, template_boost, guided_resume
  - `StrategyType`: low_touch (auto), medium_touch, high_touch (approval)
  - Rule-based selection by priority and dropoff reason
- **Smart Resume Path**: Optimized re-engagement flow
  - Dynamic entry point based on progress
  - Step skipping for completed sections
  - Form prefill from session metadata
  - Friction scoring (0.0-1.0) and completion time estimation
- **API v2 Endpoints**:
  - `GET /api/v2/brands/{brand_id}/onboarding-recovery/status` - Recovery metrics
  - `POST /api/v2/brands/{brand_id}/onboarding-recovery/run` - Detect & generate proposals
  - `GET /api/v2/brands/{brand_id}/onboarding-recovery/cases` - List recovery cases
  - `POST /api/v2/brands/{brand_id}/onboarding-recovery/cases/{id}/apply` - Apply recovery
  - `POST /api/v2/brands/{brand_id}/onboarding-recovery/cases/{id}/reject` - Reject case
  - `POST /api/v2/brands/{brand_id}/onboarding-recovery/freeze` - Emergency freeze
  - `POST /api/v2/brands/{brand_id}/onboarding-recovery/rollback` - Rollback actions
- **Approval Gates**: 
  - Auto-apply for low-touch strategies (LOW priority)
  - Human approval required for high-touch (HIGH priority, errors)
  - Pending approvals queue per brand
- **Observability**:
  - `OnboardingRecoveryMetrics`: cases, priorities, dropoff reasons, proposals, strategies
  - Nightly report section with v34 6-week goal tracking
  - Prometheus integration with full metric export
- **Studio Recovery Inbox Panel**:
  - `useOnboardingRecovery` hook with polling
  - `OnboardingRecoveryPanel` component with case management
  - Priority badges, strategy preview, one-click actions
  - Freeze/Rollback emergency controls
  - Metrics dashboard
- **CI Gate**: GitHub Actions workflow for v34 validation (backend + frontend)

### Metrics

| Metric | Target | Method |
|--------|--------|--------|
| setup_dropoff_rate | -20% | Early detection + fast-lane |
| resume_completion_rate | +25% | Smart resume paths |
| time_to_resume_after_dropoff | -40% | Priority-based urgency |
| first_run_after_resume_rate | +15% | Guided resume for errors |
| incident_rate | No increase | Approval gates + validation |

### Files Added/Modified

```
09-tools/vm_webapp/onboarding_recovery.py                      (+288 lines)
09-tools/vm_webapp/onboarding_recovery_strategy.py             (+425 lines)
09-tools/vm_webapp/api_onboarding_recovery.py                  (+389 lines)
09-tools/vm_webapp/observability.py                            (+180 lines)
09-tools/scripts/editorial_ops_report.py                       (+78 lines)
09-tools/tests/test_vm_webapp_onboarding_recovery.py
09-tools/tests/test_vm_webapp_onboarding_recovery_strategy.py
09-tools/tests/test_vm_webapp_api_v2_v34_additions.py
09-tools/tests/test_vm_webapp_metrics_v34_recovery.py
09-tools/web/vm-ui/src/features/workspace/hooks/useOnboardingRecovery.ts
09-tools/web/vm-ui/src/features/workspace/components/OnboardingRecoveryPanel.tsx
09-tools/web/vm-ui/src/features/workspace/components/OnboardingRecoveryPanel.test.tsx
.github/workflows/v34-ci-gate.yml
CHANGELOG.md
docs/releases/2026-03-02-vm-studio-v34-onboarding-recovery-reactivation-autopilot.md
```

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

## [2.0.1] - 2026-03-03

### Fixed
- Register 14 missing API routers (previously 107+ endpoints returning 404)
- Add missing router imports for: onboarding-experiments, predictive-resilience, copilot, safety-tuning, etc.
- Add onboarding telemetry endpoints:
  - POST /api/v2/onboarding/events
  - GET /api/v2/onboarding/metrics  
  - GET /api/v2/onboarding/friction-metrics
- Fix Python 3.9 compatibility issues in api_copilot.py

### Added
- Onboarding experiments endpoints now accessible
- Predictive resilience endpoints now accessible
- Copilot suggestions endpoints now accessible
- Safety tuning endpoints now accessible
- Control loop endpoints now accessible
- Recovery endpoints now accessible
- Approval learning endpoints now accessible


## [2.0.2] - 2026-03-05

### Changed
- Remove duplicate copilot endpoints from api.py (consolidated in api_copilot.py)
- Standardize all v2 endpoints with `/api/v2/` prefix
- 58 endpoints migrated from `/v2/` to `/api/v2/` for consistency

### Fixed
- Fix 404 errors on `/api/v2/threads/{id}/alerts` and other thread sub-resources
- Remove 320 lines of duplicate code from api.py


## [2.1.0] - 2026-03-15

### Added
- New `api/v2/` directory structure organized by domain (core, workflow, editorial, copilot, optimizer, onboarding, resilience, insights, ops)
- Pydantic schemas with validation:
  - `schemas/base.py` - BaseModel, PaginatedResponse, ActionResponse
  - `schemas/core.py` - Brand, Project, Thread schemas
  - `schemas/workflow.py` - WorkflowRun, Task, Approval schemas
  - `schemas/editorial.py` - EditorialDecision, SLO, Policy schemas
- Auto-generated TypeScript API client via openapi-typescript (21,148 lines!)
- Onboarding telemetry endpoints:
  - `POST /api/v2/onboarding/events`
  - `GET /api/v2/onboarding/metrics`
  - `GET /api/v2/onboarding/friction-metrics`
- New v2 brands router with typed schemas
- Deprecation strategy documentation

### Changed
- Consolidate all copilot endpoints into `api_copilot.py` (removed from api.py)
- Standardize all v2 endpoints with `/api/v2/` prefix
- Reorganize 22+ api modules into structured `v2/` subdirectories
- Reduce api.py by 320 lines through deduplication

### Fixed
- Register 14 missing API routers (previously 107+ endpoints returning 404)
- Fix 404 errors for: onboarding-experiments, predictive-resilience, copilot, safety-tuning, etc.
- Fix prefix mismatch on thread endpoints (`/v2/` → `/api/v2/`)
- Python 3.9 compatibility fixes in `api_copilot.py`

### Deprecated
- Legacy v1 endpoints marked for removal in v2.2.0
- See `api/v1/DEPRECATION.md` for migration guide

### Stats
- Total endpoints: 337
- Backend routers: 17 (all registered)
- TypeScript client: 21,148 lines
- Schemas: 4 files, 30+ classes

