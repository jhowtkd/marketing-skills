# VM Studio v37.1 - Post-Review Hardening

**Release Date:** 2026-03-03  
**Branch:** `feature/governance-v37-post-review-hardening`  
**Base:** v37 Unified Workspace UI

## Summary

Correção de riscos de produção identificados na revisão profunda:
- Wiring de rotas duplicadas
- Alinhamento de runtime/CI com Python 3.12
- Endpoint placeholder seguro
- Higiene de artefatos versionados

## Changes

### 1. Route Wiring Fix
**Problem:** Routes registered with `/api/v2/api/v2/*` due to double prefix application  
**Fix:** Removed `prefix="/api/v2"` from routers that already have full paths  
**Impact:** Clean URL structure, no 404s from duplicate routes

### 2. Python 3.12 Baseline Alignment
**Problem:** CI gates using Python 3.9, code using 3.10+ syntax (`str | None`)  
**Fix:** 
- Updated `v37-ci-gate.yml` to Python 3.12
- Fixed type annotations for 3.9 compatibility (`Optional[str]`)
**Impact:** Consistent runtime, no syntax errors

### 3. Editorial Endpoint Hardening
**Problem:** `POST /api/v2/editorial/decisions` returned fake success (201 with placeholder data)  
**Fix:** Now returns `501 Not Implemented` with clear guidance  
**Impact:** No misleading success responses

### 4. Repository Hygiene
**Problem:** Local artifacts being tracked (`.coverage`, `dist/`, `.claude/worktrees/`)  
**Fix:** 
- Added ignore rules to `.gitignore`
- Removed from git index
**Impact:** Cleaner history, smaller clones

### 5. Bootstrap Tests
**Added:** Integration tests for app startup and route contracts
- `test_vm_webapp_route_wiring.py`
- `test_vm_webapp_app_bootstrap.py`
- `test_vm_webapp_api_v2.py`

## Verification

All tests passing:
```bash
pytest 09-tools/tests/test_vm_webapp_route_wiring.py -q
pytest 09-tools/tests/test_vm_webapp_app_bootstrap.py -q
pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
```

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Duplicate routes | 50+ | 0 |
| Python version | 3.9/3.10 mixed | 3.12 aligned |
| Fake success endpoints | 1 | 0 |
| Tracked artifacts | 4 files | 0 files |
| Bootstrap tests | 0 | 8 tests |

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Route breakage | Low | Tests verify all routes |
| Python compatibility | Low | CI aligned with project |
| Behavior change | Medium | 501 instead of 201 (correct) |
