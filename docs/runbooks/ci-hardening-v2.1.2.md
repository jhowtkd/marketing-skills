# CI Hardening v2.1.2 - Operational Runbook

> **Purpose:** Guide for triaging CI failures and making merge decisions

## Failure Classification

### 1. Setup Failures
**Indicators:**
- Dependency installation errors
- Environment setup failures
- Missing tools or binaries

**Examples:**
```
Error: pip install failed
Error: npm ci failed
Error: Python version not found
```

**Action:**
- Check if dependency file was modified
- Verify network connectivity
- Retry job (transient failure)
- If persistent: Block merge, investigate infrastructure

---

### 2. Contract Failures
**Indicators:**
- API endpoint returns unexpected status code
- Response format doesn't match expected contract
- New test failures in contract tests

**Examples:**
```
AssertionError: Expected 201, got 200
AssertionError: Response missing 'status' field
AssertionError: Expected {'status': 'live'}, got {'status': 'healthy'}
```

**Action:**
- **BLOCK MERGE** - Contract regression detected
- Check if API code was modified
- Verify test expectations match documented contract
- Fix code or test (depending on which is wrong)

---

### 3. Regression Failures
**Indicators:**
- Previously passing tests now fail
- New errors in existing functionality
- Performance degradation

**Examples:**
```
AssertionError: Expected 100 items, got 50
Error: Database connection timeout
AssertionError: Response time > 500ms
```

**Action:**
- **BLOCK MERGE** - Regression detected
- Identify changed code causing regression
- Fix before merge
- Add regression test if missing

---

### 4. Legacy Debt Failures
**Indicators:**
- Known flaky tests
- Pre-existing issues documented in release note
- Eventual consistency timing issues

**Examples:**
```
AssertionError: Campaign not found in list (timing issue)
AssertionError: Task count mismatch (projection delay)
```

**Action:**
- Check if failure matches known debt in release note
- If yes: Document, do not block merge
- If no: Treat as regression, investigate

---

## Artifact Checklist

### Frontend Build (`vm-ui-dist`)

- [ ] Artifact produced by `frontend-build` job
- [ ] Artifact downloaded by consumer jobs
- [ ] Path verified: `09-tools/web/vm-ui/dist`
- [ ] Build output contains expected files:
  ```
  dist/
  ├── index.html
  ├── assets/
  │   ├── index-*.js
  │   └── index-*.css
  ```

**Troubleshooting:**
```bash
# Check artifact exists
ls -la 09-tools/web/vm-ui/dist

# Verify artifact upload in job logs
# Look for: "Uploading artifact 'vm-ui-dist'"

# Verify artifact download in consumer job
# Look for: "Downloading artifact 'vm-ui-dist'"
```

---

## Lint Checklist

### Python (Ruff + Mypy)

- [ ] Only changed files are linted
- [ ] No new E, W, F, I errors in changed files
- [ ] Type check passes for changed files

**Troubleshooting:**
```bash
# Run locally on changed files
git diff --name-only origin/main...HEAD -- '09-tools/vm_webapp/**/*.py' | xargs ruff check

# Full lint (legacy debt)
ruff check 09-tools/vm_webapp/
```

### TypeScript (ESLint)

- [ ] Only changed files are linted
- [ ] No new ESLint errors in changed files
- [ ] Max warnings: 0

**Troubleshooting:**
```bash
# Run locally on changed files
cd 09-tools/web/vm-ui
npx eslint src/features/workspace/

# Full lint (legacy debt)
npm run lint
```

---

## Merge Decision Matrix

| Failure Type | Block Merge? | Required Action |
|-------------|--------------|-----------------|
| Setup | No (retry first) | Retry job, if persistent investigate |
| Contract | **YES** | Fix contract or test |
| Regression | **YES** | Fix regression |
| Legacy Debt | No | Document in PR, reference release note |

### Go/No-Go Decision Tree

```
CI Failed?
├── Yes
│   ├── Setup failure?
│   │   ├── Yes → Retry → If persistent: NO-GO
│   │   └── No → Continue
│   ├── Contract failure?
│   │   ├── Yes → NO-GO
│   │   └── No → Continue
│   ├── Regression failure?
│   │   ├── Yes → NO-GO
│   │   └── No → Continue
│   └── Legacy debt failure?
│       ├── Yes → Check release note → Document → GO
│       └── No → Unknown failure → NO-GO
└── No → GO
```

---

## Workflow Rollback

### When to Rollback

- CI hardening causing widespread failures
- False positives blocking legitimate PRs
- Performance degradation in CI

### Rollback Steps

1. **Identify commit to revert:**
   ```bash
   git log --oneline --grep="ci" -10
   ```

2. **Revert CI changes:**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

3. **Notify team:**
   - Post in #platform-team channel
   - Update incident log

4. **Emergency bypass (admin merge):**
   ```bash
   gh pr merge <pr-number> --admin --squash
   ```

### Partial Rollback

If only one workflow is problematic:

1. Disable specific workflow:
   - Go to GitHub Actions → Workflow
   - Click "..." → Disable workflow

2. Fix workflow in feature branch

3. Re-enable after fix

---

## Quick Reference

### Test Commands

```bash
# Run contract tests
PYTHONPATH=09-tools python3 -m pytest tests/test_vm_webapp_health_probes.py tests/test_vm_webapp_api_v2*.py -v

# Run specific test
PYTHONPATH=09-tools python3 -m pytest tests/test_vm_webapp_api_v2.py::TestEditorialDecisionsAPI -v
```

### Validation Commands

```bash
# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/testing-suite.yml'))"

# Check artifact path
ls -la 09-tools/web/vm-ui/dist/
```

### Emergency Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| Platform Team | @platform-oncall | @platform-leads |
| Backend Team | @backend-oncall | @backend-leads |
| Frontend Team | @frontend-oncall | @frontend-leads |

---

## References

- Release Note: `docs/releases/2026-03-03-vm-studio-v2-1-2-ci-hardening.md`
- CI Hardening Plan: `docs/plans/2026-03-03-vm-studio-v2-1-2-ci-hardening-implementation.md`
