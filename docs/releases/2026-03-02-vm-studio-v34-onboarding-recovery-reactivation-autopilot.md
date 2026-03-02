# VM Studio v34 - Onboarding Recovery & Reactivation Autopilot

**Release Date:** 2026-03-02  
**Version:** v34.0.0  
**Status:** Ready for Production

## Overview

O v34 introduz o **Onboarding Recovery & Reactivation Autopilot**, um sistema automatizado para detectar, priorizar e recuperar usuários que abandonaram o processo de onboarding. O sistema utiliza estratégias inteligentes de reativação com caminhos de resumo otimizados para maximizar a taxa de conclusão.

## Goals (6 Weeks)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| setup_dropoff_rate | -20% | -8% | 🟡 On Track |
| resume_completion_rate | +25% | +12% | 🟡 On Track |
| time_to_resume_after_dropoff | -40% | -22% | 🟡 On Track |
| first_run_after_resume_rate | +15% | +7% | 🟡 On Track |
| incident_rate | no increase | baseline | 🟢 OK |

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Detection     │───▶│  Prioritization  │───▶│    Strategy     │
│   (Dropoff)     │    │  (High/Med/Low)  │    │   Selection     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
        ┌────────────────────────────────────────────────┘
        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Auto-Apply    │    │  Human Approval  │    │   Rollback      │
│   (Low Touch)   │    │  (High Touch)    │    │   (Emergency)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Cadence:** Weekly cycle (detect → prioritize → propose → apply/review → measure)  
**Max Adjustment:** ±10% per cycle

## Features

### 1. Dropoff Detection Engine
- **Detection Rules:**
  - Step abandonment (>60 min without activity)
  - Session timeout (>24 hours)
  - Error-induced dropoffs
  - External interruptions
  - User-initiated exits
- **Priority Calculation:**
  - HIGH: Late-stage (>70%), errors
  - MEDIUM: Mid-stage (30-70%)
  - LOW: Early-stage (<30%)
- **Case States:** active → recoverable → recovered/expired

### 2. Reactivation Strategy Engine
- **4 Recovery Strategies:**
  - **Reminder:** Simple nudge for early-stage (Low Touch)
  - **Fast Lane:** Skip completed steps (Medium Touch)
  - **Template Boost:** Highlight new templates (Medium Touch)
  - **Guided Resume:** Human-assisted recovery (High Touch)
- **Smart Resume Path:**
  - Dynamic entry point calculation
  - Step skipping based on progress
  - Form prefill from metadata
  - Friction scoring (0-1)
  - Completion time estimation

### 3. API v2 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/brands/{id}/onboarding-recovery/status` | Metrics & cases |
| POST | `/api/v2/brands/{id}/onboarding-recovery/run` | Detect & propose |
| GET | `/api/v2/brands/{id}/onboarding-recovery/cases` | List with filters |
| POST | `/api/v2/brands/{id}/onboarding-recovery/cases/{id}/apply` | Apply recovery |
| POST | `/api/v2/brands/{id}/onboarding-recovery/cases/{id}/reject` | Reject case |
| POST | `/api/v2/brands/{id}/onboarding-recovery/freeze` | Emergency freeze |
| POST | `/api/v2/brands/{id}/onboarding-recovery/rollback` | Rollback actions |

### 4. Approval Gates
- **Auto-Apply:** Low-touch strategies (LOW priority)
- **Human Approval Required:** High-touch strategies (HIGH priority, errors)
- **Pending Approvals Queue:** Managed per brand

### 5. Observability
- **Metrics Tracked:**
  - Cases: detected, recoverable, recovered, expired
  - Priority distribution: high, medium, low
  - Dropoff reasons: abandoned, timeout, error, external, exit
  - Proposals: generated, auto-applied, approved, rejected
  - Strategies: reminder, fast_lane, template_boost, guided_resume
  - Resume paths: generated, avg friction score
- **Nightly Report Section:** v34 goals progress tracking
- **Prometheus Integration:** All metrics exportable

### 6. Studio Recovery Inbox Panel
- React + TypeScript + Tailwind CSS
- Real-time case listing with polling
- Priority badges (HIGH/MEDIUM/LOW)
- Strategy preview with expected impact
- One-click Apply/Reject actions
- Freeze/Rollback emergency controls
- Metrics dashboard

## Files Added/Modified

```
09-tools/vm_webapp/onboarding_recovery.py                 (+288 lines)
09-tools/vm_webapp/onboarding_recovery_strategy.py        (+425 lines)
09-tools/vm_webapp/api_onboarding_recovery.py             (+389 lines)
09-tools/vm_webapp/observability.py                       (+180 lines v34 additions)
09-tools/scripts/editorial_ops_report.py                  (+78 lines)
09-tools/tests/test_vm_webapp_onboarding_recovery.py      (+402 lines)
09-tools/tests/test_vm_webapp_onboarding_recovery_strategy.py (+433 lines)
09-tools/tests/test_vm_webapp_api_v2_v34_additions.py     (+386 lines)
09-tools/tests/test_vm_webapp_metrics_v34_recovery.py     (+271 lines)
09-tools/web/vm-ui/src/features/workspace/hooks/useOnboardingRecovery.ts (+262 lines)
09-tools/web/vm-ui/src/features/workspace/components/OnboardingRecoveryPanel.tsx (+372 lines)
09-tools/web/vm-ui/src/features/workspace/components/OnboardingRecoveryPanel.test.tsx (+478 lines)
.github/workflows/v34-ci-gate.yml                         (+174 lines)
docs/releases/2026-03-02-vm-studio-v34-onboarding-recovery-reactivation-autopilot.md
CHANGELOG.md                                              (+63 lines)
```

## Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| onboarding_recovery | 20 | ✅ PASS |
| onboarding_recovery_strategy | 21 | ✅ PASS |
| api_onboarding_recovery | 14 | ✅ PASS |
| metrics_v34_recovery | 14 | ✅ PASS |
| OnboardingRecoveryPanel | 8 | ✅ PASS |
| **Total v34** | **77** | **✅ PASS** |

## Deployment Checklist

- [x] All tests passing
- [x] Type checking passed
- [x] Lint checks passed
- [x] Frontend build successful
- [x] CI gate validated
- [x] Documentation updated
- [x] CHANGELOG.md updated
- [x] Release notes created

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| False positive dropoff detection | Medium | Low | 60min threshold + session validation |
| Strategy misfit | Low | Medium | Human approval for high-touch |
| User fatigue from recovery nudges | Medium | Medium | 7-day expiry + priority filtering |
| Integration complexity | Low | Low | Modular design with clear interfaces |

## Rollback Plan

1. **Soft Rollback:** Use `/freeze` endpoint to pause new recoveries
2. **Full Rollback:** Use `/rollback` endpoint to revert all active cases
3. **Code Rollback:** Revert to v33 tag if needed

## Support

- **Technical Lead:** TBD
- **On-Call:** TBD
- **Documentation:** See `docs/releases/` folder
- **Metrics Dashboard:** Prometheus `/metrics` endpoint

---

**Release Tag:** `v34.0.0`  
**Next Version:** v35 (TBD)
