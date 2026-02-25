# Workflow Approval Grant-and-Resume Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the two-step approval flow with one backend-orchestrated action (`grant-and-resume`) and migrate UI/API clients to this single action.

**Architecture:** Keep the event-driven workflow runtime as source of truth and add one write command path that grants approvals and returns run-aware outcome metadata. Remove legacy write endpoints (`/grant`, `/resume`) so clients have exactly one path. Update the VM web UI to surface all pending approvals prominently and fire only one action per approval.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy/SQLite, event-store runtime (`orchestrator_v2`/`workflow_runtime_v2`), vanilla JS UI (`09-tools/web/vm`), pytest.

---

### Task 1: Add backend command contract for `grant-and-resume`

**Files:**
- Modify: `09-tools/vm_webapp/commands_v2.py`
- Test: `09-tools/tests/test_vm_webapp_commands_v2.py`

**Step 1: Write the failing test**

```python
def test_grant_and_resume_workflow_gate_returns_run_metadata(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        # seed thread/run/approval gate for workflow
        # reason format: workflow_gate:<run_id>:<stage_key>
        ...
        result = grant_and_resume_approval_command(
            session,
            approval_id="apr-run-1",
            actor_id="workspace-owner",
            idempotency_key="idem-grant-resume-1",
        )

    payload = json.loads(result.response_json)
    assert payload["approval_id"] == "apr-run-1"
    assert payload["run_id"] == "run-1"
    assert payload["resume_applied"] is True
    assert payload["approval_status"] in {"granted", "already_granted"}
    assert isinstance(payload["event_ids"], list)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_commands_v2.py::test_grant_and_resume_workflow_gate_returns_run_metadata -v`  
Expected: FAIL because `grant_and_resume_approval_command` does not exist.

**Step 3: Write minimal implementation**

```python
def grant_and_resume_approval_command(...):
    dedup = get_command_dedup(session, idempotency_key=idempotency_key)
    if dedup is not None:
        return dedup

    approval = get_approval_view(session, approval_id)
    if approval is None:
        raise ValueError(f"approval not found: {approval_id}")

    # Parse workflow gate reason: workflow_gate:<run_id>:<stage>
    run_id = _extract_run_id_from_reason(approval.reason)

    grant = _append_approval_granted_event(...)
    response = {
        "approval_id": approval_id,
        "run_id": run_id,
        "approval_status": "granted",
        "run_status": "waiting_approval",
        "resume_applied": bool(run_id),
        "event_ids": [grant.event_id],
    }
    save_command_dedup(..., command_name="grant_and_resume_approval", response=response)
    return get_command_dedup(session, idempotency_key=idempotency_key)
```

Implementation notes:
- Reuse existing event append/dedup patterns from `grant_approval_command`.
- Include parser helper for `workflow_gate:{run_id}:{stage_key}`.
- For non-workflow approvals, set `run_id=None` and `resume_applied=False`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_commands_v2.py -k "grant_and_resume" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/commands_v2.py 09-tools/tests/test_vm_webapp_commands_v2.py
git commit -m "feat: add grant-and-resume approval command contract"
```

### Task 2: Expose new API endpoint and remove legacy write endpoints

**Files:**
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing tests**

```python
def test_v2_grant_and_resume_endpoint_returns_orchestrated_payload(tmp_path: Path) -> None:
    client = TestClient(create_app(settings=Settings(...)))
    # seed run until waiting_approval
    ...
    response = client.post(
        f"/api/v2/approvals/{approval_id}/grant-and-resume",
        headers={"Idempotency-Key": "approval-gar-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approval_id"] == approval_id
    assert body["run_id"] == run_id
    assert "resume_applied" in body
    assert "run_status" in body


def test_v2_legacy_grant_and_resume_routes_are_removed(tmp_path: Path) -> None:
    client = TestClient(create_app(settings=Settings(...)))
    old_grant = client.post("/api/v2/approvals/apr-1/grant", headers={"Idempotency-Key": "x"})
    old_resume = client.post("/api/v2/workflow-runs/run-1/resume", headers={"Idempotency-Key": "y"})
    assert old_grant.status_code == 404
    assert old_resume.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -k "grant_and_resume_endpoint or legacy_grant_and_resume_routes" -v`  
Expected: FAIL because new endpoint is missing and old endpoints still exist.

**Step 3: Write minimal implementation**

```python
@router.post("/v2/approvals/{approval_id}/grant-and-resume")
def grant_and_resume_approval_v2(approval_id: str, request: Request) -> dict[str, object]:
    idem = require_idempotency(request)
    with session_scope(request.app.state.engine) as session:
        result = grant_and_resume_approval_command(
            session,
            approval_id=approval_id,
            actor_id="workspace-owner",
            idempotency_key=idem,
        )
        for event_id in json.loads(result.response_json).get("event_ids", []):
            if str(event_id).startswith("evt-"):
                project_command_event(session, event_id=event_id)

    pump_event_worker(request, max_events=40)

    with session_scope(request.app.state.engine) as session:
        payload = json.loads(result.response_json)
        run_id = payload.get("run_id")
        run = get_run(session, run_id) if run_id else None
    payload["run_status"] = run.status if run is not None else payload.get("run_status", "unknown")
    return payload
```

Also remove route handlers:
- `POST /v2/approvals/{approval_id}/grant`
- `POST /v2/workflow-runs/{run_id}/resume`

**Step 4: Run tests to verify they pass**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -k "grant_and_resume_endpoint or legacy_grant_and_resume_routes" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat: replace legacy approval writes with grant-and-resume endpoint"
```

### Task 3: Migrate UI to one-click grant and add fixed pending-approvals panel

**Files:**
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/styles.css`
- Modify: `09-tools/web/vm/app.js`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing UI asset tests**

```python
def test_vm_ui_uses_grant_and_resume_endpoint_only() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "/api/v2/approvals/" in js and "/grant-and-resume" in js
    assert "/api/v2/workflow-runs/" not in js or "/resume" not in js


def test_vm_index_contains_fixed_pending_approvals_panel() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="pending-approvals-panel"' in html
    assert 'id="pending-approvals-list"' in html
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k "grant_and_resume_endpoint_only or fixed_pending_approvals_panel" -v`  
Expected: FAIL because UI still uses legacy routes and no fixed panel exists.

**Step 3: Write minimal implementation**

```javascript
async function grantAndResume(approvalId) {
  await postV2(
    `/api/v2/approvals/${encodeURIComponent(approvalId)}/grant-and-resume`,
    {},
    "approval-grant-resume"
  );
  await loadThreadWorkspace();
}
```

```html
<section class="panel sticky-approvals" id="pending-approvals-panel">
  <h3>Aprovações pendentes</h3>
  <div id="pending-approvals-list" class="list"></div>
</section>
```

```css
.sticky-approvals {
  position: sticky;
  top: 8px;
  z-index: 4;
  border-color: #9dbbff;
}
```

Implementation notes:
- Remove all `Resume` actions in `renderWorkflowRuns` and `renderWorkflowRunDetail`.
- Use the new endpoint for every approval CTA (`Approvals`, `Run Detail`, top fixed panel).
- Auto-select first `waiting_approval` run in `loadWorkflowRuns`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/styles.css 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat(ui): show fixed pending approvals and use grant-and-resume only"
```

### Task 4: Update workflow integration tests to use the new endpoint only

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_event_driven_e2e.py`
- Modify: `09-tools/tests/test_vm_webapp_orchestrator_v2.py`
- Modify: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write/adjust failing assertions first**

```python
# helper replacement in tests
client.post(
    f"/api/v2/approvals/{approval_id}/grant-and-resume",
    headers={"Idempotency-Key": f"e2e-grant-{run_id}-{grants}"},
)
```

Add assertion in run loops:

```python
assert grant.json()["resume_applied"] in {True, False}
```

**Step 2: Run targeted integration tests to verify failures**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py 09-tools/tests/test_vm_webapp_api_v2.py -k "approval or waiting_approval or resume" -v`  
Expected: FAIL until all legacy route calls are migrated.

**Step 3: Implement minimal test migrations**

- Replace every `.../approvals/{id}/grant` with `.../approvals/{id}/grant-and-resume`.
- Remove `.../workflow-runs/{id}/resume` flows and replace with one-click approval loop assertions.
- Keep semantic coverage for idempotency and terminal status behavior.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py 09-tools/tests/test_vm_webapp_api_v2.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_event_driven_e2e.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "test: migrate workflow approval flows to grant-and-resume endpoint"
```

### Task 5: Document breaking API change and operator workflow

**Files:**
- Modify: `README.md`

**Step 1: Write failing docs expectation test**

```python
def test_readme_mentions_grant_and_resume_endpoint() -> None:
    content = Path("README.md").read_text(encoding="utf-8")
    assert "/api/v2/approvals/{approval_id}/grant-and-resume" in content
    assert "/api/v2/approvals/{approval_id}/grant" not in content
    assert "/api/v2/workflow-runs/{run_id}/resume" not in content
```

Add to `09-tools/tests/test_vm_webapp_ui_assets.py` (or a dedicated docs test module).

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k "readme_mentions_grant_and_resume_endpoint" -v`  
Expected: FAIL.

**Step 3: Write minimal implementation**

Update README sections:
- Endpoint list in v2 workflow section.
- One-click approval operational flow.
- Breaking change note for removed legacy endpoints.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k "readme_mentions_grant_and_resume_endpoint" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add README.md 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "docs: document grant-and-resume breaking change"
```

### Task 6: Final verification before merge

**Files:**
- No functional edits expected.

**Step 1: Run full targeted verification suite**

Run:

```bash
uv run pytest \
  09-tools/tests/test_vm_webapp_commands_v2.py \
  09-tools/tests/test_vm_webapp_api_v2.py \
  09-tools/tests/test_vm_webapp_event_driven_e2e.py \
  09-tools/tests/test_vm_webapp_orchestrator_v2.py \
  09-tools/tests/test_vm_webapp_ui_assets.py -v
```

Expected: PASS.

**Step 2: Run smoke check for local UI startup**

Run: `uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766`  
Expected: server starts and `GET /api/v1/health` returns `ok`.

**Step 3: Manual acceptance checklist**

1. Open UI and create `Brand -> Project -> Thread`.
2. Start workflow run and wait for `waiting_approval`.
3. Confirm fixed top panel lists pending approval(s).
4. Click one `Grant`; run progresses without manual `Resume`.
5. Confirm no `Resume` button exists.

**Step 4: Commit verification notes (if changed)**

```bash
git add -A
git commit -m "chore: verify grant-and-resume workflow migration" || true
```

**Step 5: Prepare PR update**

```bash
git push
```

Include in PR body:
- Breaking change summary.
- Endpoint migration notes.
- Test evidence.

---

**Execution notes:**
- Use `@test-driven-development` for each task start.
- Use `@systematic-debugging` if any flaky workflow status transitions occur.
- Use `@verification-before-completion` before claiming done.
