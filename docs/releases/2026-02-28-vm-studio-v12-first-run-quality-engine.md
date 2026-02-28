# VM Studio v12 - First-Run Quality Engine

**Release Date:** 2026-02-28  
**Branch:** `feature/governance-v12-first-run-quality-engine`  
**Base Branch:** `main`  

## Goal

Increase `approval_without_regen_24h` KPI from 45% to 65% with structured first-run recommendation (`profile+mode`) and editable preselection in Studio.

## Architecture

- **Read-model:** `FirstRunOutcomeAggregate` - aggregates V1 outcomes by profile/mode
- **Engine:** Deterministic ranking with fallback chain (objective -> brand -> global -> default)
- **Projector:** Computes 24h success outcome based on whether a new run was created within 24h
- **Integration:** Workspace hook loads recommendation data; Studio UI shows confidence badge and reason codes

## New Endpoints

### GET /api/v2/threads/{thread_id}/first-run-recommendation

Returns top 3 profile/mode combinations ranked by success rate, quality score, and speed.

**Response:**
```json
{
  "thread_id": "t1",
  "scope": "objective",
  "recommendations": [
    {
      "profile": "engagement",
      "mode": "fast",
      "score": 0.85,
      "confidence": 0.75,
      "reason_codes": ["high_success_rate", "quality"]
    }
  ]
}
```

### GET /api/v2/threads/{thread_id}/first-run-outcomes

Returns aggregated outcome data for each profile/mode combination.

**Response:**
```json
{
  "thread_id": "t1",
  "aggregates": [
    {
      "profile": "engagement",
      "mode": "fast",
      "total_runs": 10,
      "success_24h_count": 8,
      "success_rate": 0.8,
      "avg_quality_score": 0.85,
      "avg_duration_ms": 4000
    }
  ]
}
```

## New Metrics

- `first_run_recommendation_requested_total` - Counter for recommendation API calls
- `first_run_outcomes_requested_total` - Counter for outcomes API calls

## UI Changes

### Studio Workspace Panel

- **Auto-preselection:** When confidence >= 0.55, the recommended profile is automatically selected
- **Confidence badge:** Shows confidence percentage with color coding:
  - Green (>= 55%): High confidence, auto-selected
  - Amber (>= 30%): Medium confidence, shown as suggestion
  - Gray (< 30%): Low confidence, informational only
- **Reason codes:** Displayed below the profile selector for transparency
- **Manual override:** User can always manually select a different profile

## Test Coverage

### Backend Tests
- `test_vm_webapp_first_run_recommendation.py` - 9 tests covering aggregate, ranker, and recommendation logic
- `test_vm_webapp_projectors_v2.py` - 5 tests including first-run outcome projection
- `test_vm_webapp_api_v2_additions.py` - 3 tests for new API endpoints
- `test_vm_webapp_metrics_prometheus.py` - 2 tests for new metrics

### Frontend Tests
- `useWorkspace.firstRunRecommendation.test.tsx` - 4 tests for hook integration
- All existing workspace tests continue to pass (131 tests total)

## CI Gate

New CI job: `first-run-quality-gate-v12`

```yaml
- uv run pytest 09-tools/tests/test_vm_webapp_first_run_recommendation.py -q
- uv run pytest 09-tools/tests/test_vm_webapp_projectors_v2.py -q
- uv run pytest 09-tools/tests/test_vm_webapp_api_v2_additions.py -q
- uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -k "first_run" -q
- npm run test -- --run src/features/workspace/useWorkspace.firstRunRecommendation.test.tsx
```

## Limitations

- Fallback to default recommendation when no historical data available
- Confidence threshold for auto-selection is fixed at 0.55 (may be configurable in future)
- Sample size penalty applied when total_runs < 10

## Evidence Template

To verify the KPI improvement after deployment:

```sql
-- Success rate calculation
SELECT 
  COUNT(*) FILTER (WHERE success_24h) AS success_count,
  COUNT(*) AS total_count,
  ROUND(100.0 * COUNT(*) FILTER (WHERE success_24h) / COUNT(*), 2) AS success_rate_pct
FROM first_run_outcomes_view
WHERE completed_at >= '2026-02-28';
```

## Migration Notes

No breaking changes. New tables are created automatically:
- `first_run_outcomes_view`
- `first_run_outcome_aggregates`

## Commits

1. `7b73846` - feat(v12): add first-run outcomes read model
2. `bcac0fe` - feat(v12): compute first-run success outcome with 24h window
3. `c70611c` - feat(api-v2): add first-run recommendation and outcomes endpoints
4. `abac71d` - feat(observability): add v12 first-run recommendation and outcome metrics
5. `6723045` - feat(vm-ui): load first-run recommendation data in workspace hook
6. `1299812` - feat(vm-ui): add editable first-run preselection with confidence guardrail
