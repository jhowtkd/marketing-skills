# VM Studio v13 - Editorial Copilot Release Notes

**Release Date:** 2026-02-28  
**Version:** v13 - Editorial Copilot

## Overview

VM Studio v13 introduces the **Editorial Copilot**, a deterministic suggestion engine that helps editors make better decisions across three phases of content creation: initial setup, refinement, and strategy. This feature aims to improve content quality and reduce regenerations by providing data-driven recommendations with explainability.

## KPI Goals (6 weeks)

- V1 average score: +10 points
- approval_without_regen_24h: +8 p.p.
- regenerations per job: -25%

---

## What's New

### 1. Editorial Copilot Engine (v13)

A deterministic suggestion engine with three phases:

#### Phase: Initial
- Uses v12 first-run ranking data to recommend optimal profile/mode combinations
- Provides confidence score, reason codes, and expected impact
- Integrates with existing first-run outcomes data

#### Phase: Refine
- Analyzes scorecard gaps from quality evaluations
- Suggests specific text improvements
- Shows expected quality delta and approval lift

#### Phase: Strategy
- Monitors high-risk signals from alerts and forecasts
- Provides strategic recommendations for editorial governance
- Triggers on drift, baseline issues, or quality degradation

### 2. API v2 Endpoints

New endpoints for copilot integration:

```
GET  /api/v2/threads/{thread_id}/copilot/suggestions?phase={initial|refine|strategy}
POST /api/v2/threads/{thread_id}/copilot/feedback
```

**Features:**
- Phase-based suggestion generation
- Feedback recording (accepted, edited, ignored)
- Guardrail for low-confidence situations
- Automatic metrics collection

### 3. UI Copilot Panel

New React component in the Workspace:

- **Phase tabs:** Switch between initial, refine, and strategy phases
- **Suggestion cards:** Display content, confidence, and reasoning
- **Action buttons:** Apply, Edit (with inline editing), Ignore
- **Guardrail messaging:** Clear feedback when confidence is insufficient
- **Humanized reason codes:** Portuguese labels for technical codes

### 4. Metrics and Observability

New Prometheus metrics for monitoring:

```
vm_copilot_suggestion_generated_total
vm_copilot_suggestion_phase_{phase}
vm_copilot_feedback_submitted_total
vm_copilot_feedback_action_{accepted|edited|ignored}
```

**Effective Acceptance Rate:**
Calculated as `(accepted + edited) / total_feedback` to measure copilot effectiveness.

### 5. Database Schema

New read-model tables:

- `copilot_suggestions_view`: Stores generated suggestions
- `copilot_feedback_view`: Stores editor feedback for continuous improvement

---

## Technical Architecture

### Deterministic Engine

The copilot engine follows deterministic rules:

1. **Confidence Threshold:** 0.4 minimum for active suggestions
2. **Guardrail:** Low confidence returns passive suggestions (empty content with guidance)
3. **Explainability:** Every suggestion includes `reason_codes` and `why`
4. **Impact Forecasting:** Expected quality delta and approval lift metrics

### Integration Points

| Component | Integration |
|-----------|-------------|
| v12 Ranking | `first_run_recommendation.py` outcomes |
| Alerts v2 | Risk signals for strategy phase |
| Quality Eval | Scorecard gaps for refine phase |
| Workspace Hook | `useWorkspace.ts` copilot methods |
| UI Panel | `CopilotPanel.tsx` component |

---

## Testing

### Backend Tests
- `test_vm_webapp_editorial_copilot.py`: 22 tests covering engine logic
- `test_vm_webapp_api_v2_copilot.py`: 5 tests for API endpoints
- `test_vm_webapp_metrics_prometheus_copilot.py`: 4 tests for metrics

### Frontend Tests
- `useWorkspace.copilot.test.tsx`: 6 tests for hook integration
- `CopilotPanel.test.tsx`: 9 tests for UI component

### CI Gate
New GitHub Actions job: `editorial-copilot-gate-v13`

---

## Migration Guide

### No Breaking Changes

This release is backward compatible:
- Existing APIs remain unchanged
- New endpoints are additive
- Database migrations are automatic (SQLAlchemy)

### Enabling the Copilot

The copilot is available immediately for all threads:

1. Open any thread in VM Studio
2. Look for the "Copilot Editorial" panel
3. Switch between phases to get contextual suggestions

---

## Configuration

No configuration required. The copilot uses existing data:
- First-run outcomes (v12)
- Quality evaluations
- Editorial alerts

---

## Known Limitations

1. **Refine Phase:** Currently returns passive suggestions (scorecard gap integration planned)
2. **Strategy Phase:** Basic risk signal detection (alert correlation improvements planned)
3. **Language:** Portuguese UI only (internationalization planned)

---

## Future Roadmap

- v13.1: Scorecard gap integration for refine phase
- v13.2: Alert correlation for strategy phase
- v13.3: Feedback loop analytics dashboard
- v13.4: Personalized suggestions per editor

---

## Related Documentation

- [VM Studio v12 First-Run Ranking](./2026-02-28-vm-studio-v12-first-run-ranking.md)
- [Editorial Policy v5](./2026-02-28-vm-studio-v5-editorial-policy.md)
- [SLO Alerts Hub v7](./2026-02-28-vm-studio-v7-slo-alerts-hub.md)

---

## Changelog

### Added
- `CopilotSuggestion` and `CopilotFeedback` types
- `SuggestionEngine` with phase-based generation
- API endpoints for suggestions and feedback
- `CopilotPanel` React component
- Copilot metrics collection
- CI gate for editorial copilot

### Changed
- `useWorkspace.ts`: Added copilot state and methods
- `api.py`: Added copilot endpoints
- `.github/workflows/vm-webapp-smoke.yml`: Added v13 gate

### Fixed
- N/A (new feature)
