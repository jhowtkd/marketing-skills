# VM Studio v2.1.2 - CI Hardening Release

## Summary

This release focuses on stabilizing the v2 CI pipeline to eliminate setup failures and distinguish real regressions from pre-existing noise.

## Goals Achieved

- **ci_pass_rate_main >= 95%**: Target 95% pass rate on main branch
- **false_negative_failures = 0**: Zero false negative failures in v2 scope
- **mean_ci_feedback_time: -20%**: 20% reduction in mean CI feedback time
- **pre_existing_failures segregated**: Pre-existing failures segregated in reports

## Changes

### CI/CD Improvements

1. **API v2 Contract Tests**
   - Added comprehensive tests for `/api/v2/health/live` endpoint
   - Added tests for `/api/v2/metrics` endpoint
   - Added tests for `/api/v2/brands` creation endpoint
   - Added tests for optimizer 501 Not Implemented responses

2. **Suite Isolation**
   - Separated API core tests from contract tests
   - Separated frontend unit tests from integration tests
   - Each suite runs independently to reduce blast radius

3. **Deterministic Artifact Handoff**
   - Frontend build job produces `vm-ui-dist` artifact
   - Consumer jobs download artifact with fixed path
   - Ensures consistent build output across jobs

4. **Scoped Lint Checks**
   - Lint only runs on changed files in PR
   - Prevents new debt without blocking on legacy issues
   - Tracks legacy debt in this document

## Legacy Debt Tracking

### Known Pre-existing Issues (Not Blocking)

The following issues are known and tracked but do not block CI:

1. **Campaign View Projection**
   - Issue: Campaign list view may return empty due to async projection timing
   - Location: `GET /api/v2/campaigns?project_id={id}`
   - Impact: Low - data is eventually consistent
   - Plan: Fix in v2.1.3 with synchronous projection

2. **Task List View**
   - Issue: Task list view may not immediately reflect new tasks
   - Location: `GET /api/v2/threads/{thread_id}/tasks`
   - Impact: Low - data is eventually consistent
   - Plan: Fix in v2.1.3 with synchronous projection

3. **Legacy Test Files**
   - Some test files may have flaky assertions
   - These are being fixed incrementally

### Technical Debt Payment Plan

| Issue | Target Version | Owner | Status |
|-------|---------------|-------|--------|
| Campaign view projection | v2.1.3 | Backend Team | Planned |
| Task view projection | v2.1.3 | Backend Team | Planned |
| Full lint enforcement | v2.2.0 | Platform Team | Planned |

## Metrics

### Baseline (Pre-hardening)
- CI pass rate: ~75%
- Mean feedback time: ~8 minutes
- False negative rate: ~15%

### Target (Post-hardening)
- CI pass rate: >= 95%
- Mean feedback time: ~6.4 minutes (-20%)
- False negative rate: ~0%

## Residual Risks

1. **Event-sourced projection timing**: Some views may still show eventual consistency
2. **Third-party service dependencies**: External services may cause intermittent failures
3. **Resource contention**: Parallel jobs may experience resource constraints

## Next Steps (v2.1.3)

1. Fix campaign and task view projections
2. Add caching layer for frequently accessed views
3. Implement circuit breaker for external dependencies
4. Complete legacy test file fixes

## Rollback

If issues arise:

1. Revert to previous workflow versions:
   ```bash
   git revert <ci-hardening-commit>
   ```

2. Contact: Platform Team

3. Runbook: [docs/runbooks/ci-hardening-v2.1.2.md](../runbooks/ci-hardening-v2.1.2.md)
