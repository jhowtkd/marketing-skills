# VM Web App Approve Button Guard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent duplicate `Approve` actions for the same run by locking the button while the request is in flight and ignoring concurrent clicks.

**Architecture:** Keep the fix fully in the VM web frontend (`app.js`) with no backend contract changes. Add an in-memory guard (`Set`) keyed by `run_id` and wrap button state changes in `try/finally` so UI state is restored on both success and error. Validate via asset-level tests that assert required guard markers in JavaScript.

**Tech Stack:** Vanilla JavaScript UI (`09-tools/web/vm/app.js`), pytest asset tests (`09-tools/tests/test_vm_webapp_ui_assets.py`), git.

---

### Task 1: Disable Approve Button During Request

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/app.js`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_vm_app_js_disables_approve_button_while_request_in_flight() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "buttonEl.disabled = true" in js
    assert "buttonEl.disabled = false" in js
```

**Step 2: Run test to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_disables_approve_button_while_request_in_flight -v`  
Expected: FAIL with assertion error because disable/enable markers are not present yet.

**Step 3: Write minimal implementation**

```javascript
async function approveRun(runId, buttonEl = null) {
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Approving...";
  }
  try {
    await fetchJson(`${API_BASE}/runs/${encodeURIComponent(runId)}/approve`, {
      method: "POST",
    });
    await loadRuns();
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = "Approve";
    }
  }
}
```

Also pass the button reference when wiring the click:

```javascript
button.addEventListener("click", async () => {
  await approveRun(run.run_id, button);
});
```

**Step 4: Run test to verify it passes**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_disables_approve_button_while_request_in_flight -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/app.js
git commit -m "fix(vm-webapp): disable approve button while request is in flight"
```

### Task 2: Guard Duplicate Approve Requests Per Run

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/app.js`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_vm_app_js_guards_duplicate_approve_requests_per_run_id() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "const approvingRunIds = new Set();" in js
    assert "if (approvingRunIds.has(runId))" in js
    assert "approvingRunIds.add(runId)" in js
    assert "approvingRunIds.delete(runId)" in js
```

**Step 2: Run test to verify it fails**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_guards_duplicate_approve_requests_per_run_id -v`  
Expected: FAIL with assertion error because guard markers are missing.

**Step 3: Write minimal implementation**

```javascript
const approvingRunIds = new Set();

async function approveRun(runId, buttonEl = null) {
  if (approvingRunIds.has(runId)) {
    return;
  }
  approvingRunIds.add(runId);
  try {
    // existing approve request
  } finally {
    approvingRunIds.delete(runId);
  }
}
```

**Step 4: Run test to verify it passes**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_guards_duplicate_approve_requests_per_run_id -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/app.js
git commit -m "fix(vm-webapp): prevent duplicate approve requests per run"
```

### Task 3: Regression Verification and Branch Hygiene

**Files:**
- Verify only: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Verify only: `09-tools/web/vm/app.js`

**Step 1: Run full UI asset test file**

Run: `pytest 09-tools/tests/test_vm_webapp_ui_assets.py -q`  
Expected: all tests PASS.

**Step 2: Validate staged diff is scoped**

Run: `git status --short`  
Expected: only intended files staged/modified for this fix (`09-tools/tests/test_vm_webapp_ui_assets.py`, `09-tools/web/vm/app.js`), with local artifacts intentionally untracked.

**Step 3: Push branch and open PR**

Run: `git push -u origin <feature-branch>`  
Run: `gh pr create --fill`  
Expected: PR URL created with scope limited to approve-button duplicate-click protection.

**Step 4: Final commit/checkpoint note**

```bash
git log --oneline -n 3
```

Expected: recent commits show small, task-scoped history for review.

### Execution Notes

- Use @superpowers/test-driven-development for each task loop.
- Use @superpowers/verification-before-completion before announcing success.
- Keep YAGNI: no backend changes, no new endpoints, no non-foundation run changes.
