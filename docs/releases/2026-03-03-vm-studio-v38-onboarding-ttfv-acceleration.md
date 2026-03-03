# VM Studio v38 - Onboarding TTFV Acceleration

**Release Date:** 2026-03-03  
**Branch:** `feature/governance-v38-onboarding-ttfv-acceleration`  
**Target:** Reduce `median_ttfv_minutes` by 30% over 6 weeks

---

## Executive Summary

This release introduces three friction killers and a comprehensive experiment governance framework to accelerate Time-To-First-Value (TTFV) for new users while maintaining strict guardrails on activation, completion, and incident rates.

### North Star Metric
- **Target:** -30% `median_ttfv_minutes` (6 weeks)
- **Baseline:** TBD from first week of data collection

### Guardrails
| Metric | Threshold | Status |
|--------|-----------|--------|
| `activation_rate_d1` | >= -2 p.p. | 🟢 Monitored |
| `onboarding_completion_rate` | >= -3 p.p. | 🟢 Monitored |
| `incident_rate` | No increase | 🟢 Monitored |

---

## Friction Killers

### 1. Smart Prefill (Friction Killer #1)

**Objective:** Reduce onboarding setup time by inferring user intent from available signals.

**Implementation:**
- Backend: `09-tools/vm_webapp/onboarding_prefill.py`
- Frontend: `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.tsx`
- API: `POST /api/v2/onboarding/prefill`

**Features:**
- UTM campaign-based template pre-selection
- Referrer domain analysis for category inference
- Email domain segment classification
- User segment-based defaults
- Respects explicit user input (no overwriting)

**Estimated Impact:** -2 minutes TTFV

---

### 2. Fast Lane (Friction Killer #2)

**Objective:** Skip non-essential onboarding steps for eligible low-risk users.

**Implementation:**
- Backend: `09-tools/vm_webapp/onboarding_fast_lane.py`
- Frontend: `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.tsx`
- API: `POST /api/v2/onboarding/fast-lane`

**Eligibility Criteria:**
- Risk score below threshold (based on email domain, IP reputation, signup source)
- Complete minimum checklist (terms, email verification, privacy)
- Enterprise users automatically eligible

**Required Minimum Checklist (Non-skippable):**
- `terms_accepted`: Terms of service acceptance
- `email_verified`: Email verification completed
- `privacy_policy`: Privacy policy acknowledgment

**Skippable Steps:**
- Advanced settings
- Integrations
- Customization (for power users)

**Estimated Impact:** -4 minutes TTFV

---

### 3. One-Click First Run (Friction Killer #3)

**Objective:** Accelerate time-to-first-value with single-action content generation.

**Implementation:**
- Backend: `09-tools/vm_webapp/onboarding_first_run.py`
- Frontend: `09-tools/web/vm-ui/src/features/onboarding/TemplatePicker.tsx`
- API:
  - `POST /api/v2/onboarding/first-run/validate`
  - `POST /api/v2/onboarding/first-run/plan`
  - `POST /api/v2/onboarding/first-run/execute`
  - `POST /api/v2/onboarding/first-run/recommend`
  - `GET /api/v2/onboarding/first-run/templates`

**Security Features:**
- Input sanitization (XSS, SQL injection prevention)
- Parameter validation against safe templates
- Dangerous pattern detection and removal
- Template allowlist enforcement

**Templates Supported:**
- Blog Post
- Landing Page
- Social Media
- Email Marketing
- Google Ads
- Meta Ads

**Fallback Strategy:**
- Invalid template → Fallback to safe default
- Missing parameters → Prompt for input
- Execution error → Display fallback options

**Estimated Impact:** -5 minutes TTFV

---

## Experiment Governance

### Framework

**Implementation:**
- `09-tools/vm_webapp/onboarding_ttfv_experiments.py`
- `09-tools/vm_webapp/observability.py` (metrics export)
- `09-tools/scripts/editorial_ops_report.py` (nightly report integration)

**APIs:**
- `POST /api/v2/onboarding/experiments/assign`
- `POST /api/v2/onboarding/experiments/guardrails/check`
- `GET /api/v2/onboarding/experiments/guardrails/status`
- `POST /api/v2/onboarding/experiments/decision`
- `GET /api/v2/onboarding/experiments/active`

### User Assignment
- Deterministic 50/50 split using hash-based assignment
- Same user always gets same variant
- No user data stored, computed on-the-fly

### Guardrails

| Guardrail | Control | Treatment | Threshold | Action |
|-----------|---------|-----------|-----------|--------|
| Activation Rate D1 | 50% | Monitored | >= -2 p.p. | Rollback if violated |
| Onboarding Completion | 80% | Monitored | >= -3 p.p. | Rollback if violated |
| Incident Rate | 1% | Monitored | No increase | Rollback if increased |

### Decision Matrix

| Condition | Sample Size | Guardrails | TTFV Improvement | Decision |
|-----------|-------------|------------|------------------|----------|
| < 100 per variant | - | - | - | HOLD |
| >= 100 | ANY FAIL | - | - | ROLLBACK |
| >= 100 | ALL PASS | < 10% | - | HOLD |
| >= 100 | ALL PASS | >= 10% | - | PROMOTE |

---

## Telemetry

### Events Tracked
- `onboarding_started`: User begins onboarding
- `step_viewed`: User views a step
- `step_completed`: User completes a step
- `first_value_reached`: User achieves first value (TTFV)
- `dropoff_reason`: User drops off with reason

### Metrics Exported (Prometheus)
- `vm_onboarding_experiment_ttfv_median_minutes`
- `vm_onboarding_experiment_activation_rate_d1`
- `vm_onboarding_experiment_onboarding_completion_rate`
- `vm_onboarding_experiment_incident_rate`
- `vm_onboarding_experiment_guardrail_violations_total`
- `vm_onboarding_experiment_decisions_total`

---

## Rollout Plan

### Week 1-2: Telemetry Baseline
- Deploy telemetry layer
- Collect baseline TTFV metrics
- Validate event tracking

### Week 3: Smart Prefill
- Enable for 10% of new users
- Monitor prefill accuracy
- Adjust inference rules

### Week 4: Fast Lane
- Enable for eligible users (low risk)
- Monitor completion rates
- Validate guardrails

### Week 5: One-Click First Run
- Enable for recommended templates
- Monitor generation success rate
- Gather user feedback

### Week 6: Analysis & Decision
- Evaluate full experiment
- Check all guardrails
- Make promote/hold/rollback decision

---

## Testing

### Backend Tests
```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_onboarding_prefill.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_onboarding_fast_lane.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_onboarding_first_run.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_onboarding_ttfv_experiments.py -q
```

### Frontend Tests
```bash
cd 09-tools/web/vm-ui
npm run test -- --run src/features/onboarding/ttfvTelemetry.test.ts
npm run test -- --run src/features/onboarding/OnboardingWizard.test.tsx
npm run test -- --run src/features/onboarding/OneClickFirstRun.test.tsx
```

### Build Verification
```bash
cd 09-tools/web/vm-ui
npm run build
```

### YAML Validation
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/v38-onboarding-ttfv-gate.yml'))"
```

---

## CI/CD

### GitHub Actions Workflow
- `.github/workflows/v38-onboarding-ttfv-gate.yml`
- Runs on: Push to feature branch, PR to main
- Jobs:
  - Backend onboarding tests
  - Frontend onboarding tests
  - Frontend build verification
  - YAML validation
  - Integration gate

### Required Checks
- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] Frontend build succeeds
- [ ] YAML is valid
- [ ] Integration gate passes

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Guardrail violation | Medium | High | Automatic rollback triggers |
| Prefill inaccuracy | Medium | Low | User can override prefill |
| Fast lane security | Low | High | Risk scoring + minimum checklist |
| One-click failures | Medium | Medium | Fallback to manual flow |
| Sample size too small | Low | Medium | Hold decision until adequate |

---

## Files Changed

### New Files
- `09-tools/vm_webapp/onboarding_prefill.py`
- `09-tools/vm_webapp/onboarding_fast_lane.py`
- `09-tools/vm_webapp/onboarding_first_run.py`
- `09-tools/vm_webapp/onboarding_ttfv_experiments.py`
- `09-tools/tests/test_vm_webapp_onboarding_prefill.py`
- `09-tools/tests/test_vm_webapp_onboarding_fast_lane.py`
- `09-tools/tests/test_vm_webapp_onboarding_first_run.py`
- `09-tools/tests/test_vm_webapp_onboarding_ttfv_experiments.py`
- `09-tools/web/vm-ui/src/features/onboarding/ttfvTelemetry.ts`
- `09-tools/web/vm-ui/src/features/onboarding/ttfvTelemetry.test.ts`
- `09-tools/web/vm-ui/src/features/onboarding/OneClickFirstRun.test.tsx`
- `.github/workflows/v38-onboarding-ttfv-gate.yml`
- `docs/releases/2026-03-03-vm-studio-v38-onboarding-ttfv-acceleration.md`

### Modified Files
- `09-tools/vm_webapp/api_onboarding.py`
- `09-tools/vm_webapp/observability.py`
- `09-tools/scripts/editorial_ops_report.py`
- `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.tsx`
- `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.test.tsx`
- `09-tools/web/vm-ui/src/features/onboarding/TemplatePicker.tsx`

---

## Verification Checklist

- [ ] Telemetry events firing correctly
- [ ] Smart prefill inferring correct templates
- [ ] Fast lane skipping appropriate steps
- [ ] One-click generating content successfully
- [ ] Guardrails monitoring all metrics
- [ ] Decision engine making correct recommendations
- [ ] All tests passing
- [ ] Build successful
- [ ] Documentation complete

---

## Support

**Team:** Growth Team  
**Owner:** @growth-team  
**Experiment ID:** `v38-onboarding-ttfv-acceleration`
