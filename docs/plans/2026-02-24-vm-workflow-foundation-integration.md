# VM Workflow Foundation Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn v2 workflow runs into real async Foundation execution with auditable mode resolution, automatic approval resume, and run-safe artifacts.

**Architecture:** Keep `WorkflowRuntimeV2` as the async coordinator and move real stage execution to a new `FoundationRunnerService` that wraps the existing `executor.py` API. Resolve each run into immutable snapshot fields (`requested_mode`, `effective_mode`, `profile_version`, `resolved_stages`) and execute all modes through Foundation fallback for this cycle. Preserve event-driven behavior (`queued -> running -> waiting_approval -> completed/failed`) with approval-triggered auto-resume.

**Tech Stack:** FastAPI, SQLAlchemy + SQLite, YAML profiles, event-log projector pattern, existing `executor.py` Foundation runtime, pytest.

---

### Task 1: Add mode resolution contract with Foundation fallback

**Files:**
- Modify: `09-tools/vm_webapp/workflow_profiles.yaml`
- Modify: `09-tools/vm_webapp/workflow_profiles.py:10-146`
- Modify: `09-tools/vm_webapp/settings.py:8-18`
- Test: `09-tools/tests/test_vm_webapp_workflow_profiles.py`

**Step 1: Write the failing test**

```python
def test_resolve_workflow_plan_uses_foundation_effective_mode_when_forced() -> None:
    profiles = load_workflow_profiles(DEFAULT_PROFILES_PATH)
    resolved = resolve_workflow_plan_with_contract(
        profiles,
        requested_mode="content_calendar",
        skill_overrides={},
        force_foundation_fallback=True,
        foundation_mode="foundation_stack",
    )
    assert resolved["requested_mode"] == "content_calendar"
    assert resolved["effective_mode"] == "foundation_stack"
    assert resolved["fallback_applied"] is True
    assert resolved["profile_version"] == "v1"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_profiles.py::test_resolve_workflow_plan_uses_foundation_effective_mode_when_forced -v`  
Expected: FAIL with `NameError` or `AttributeError` for missing contract resolver.

**Step 3: Write minimal implementation**

```python
FOUNDATION_MODE_DEFAULT = "foundation_stack"
PROFILES_VERSION_DEFAULT = "v1"

def resolve_workflow_plan_with_contract(
    profiles: dict[str, WorkflowModeProfile],
    *,
    requested_mode: str,
    skill_overrides: dict[str, list[str]] | None,
    force_foundation_fallback: bool,
    foundation_mode: str = FOUNDATION_MODE_DEFAULT,
) -> dict[str, Any]:
    effective_mode = foundation_mode if force_foundation_fallback else requested_mode
    if not force_foundation_fallback and effective_mode not in profiles:
        effective_mode = foundation_mode
    plan = resolve_workflow_plan(
        profiles,
        mode=effective_mode,
        skill_overrides=skill_overrides or {},
    )
    return {
        **plan,
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
        "fallback_applied": requested_mode != effective_mode,
        "profile_version": PROFILES_VERSION_DEFAULT,
    }
```

Also add `foundation_stack` profile in YAML with Foundation stage keys (`research`, `brand-voice`, `positioning`, `keywords`) and `approval_required` matching `06-stacks/foundation-stack/stack.yaml`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_profiles.py -v`  
Expected: PASS with new fallback tests and existing parser tests.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/workflow_profiles.yaml 09-tools/vm_webapp/workflow_profiles.py 09-tools/vm_webapp/settings.py 09-tools/tests/test_vm_webapp_workflow_profiles.py
git commit -m "feat: add workflow mode contract with foundation fallback"
```

### Task 2: Introduce FoundationRunnerService bridge

**Files:**
- Create: `09-tools/vm_webapp/foundation_runner_service.py`
- Modify: `09-tools/vm_webapp/__init__.py`
- Test: `09-tools/tests/test_vm_webapp_foundation_runner_service.py`

**Step 1: Write the failing test**

```python
def test_service_runs_research_with_run_until_gate_then_manual_stages(tmp_path, monkeypatch):
    service = FoundationRunnerService(workspace_root=tmp_path)
    # monkeypatch executor.run_until_gate / approve_stage with deterministic states
    stage1 = service.execute_stage(
        run_id="run-1", thread_id="t1", project_id="p1", request_text="crm", stage_key="research"
    )
    assert stage1.pipeline_status in {"running", "waiting_approval"}
    stage2 = service.execute_stage(
        run_id="run-1", thread_id="t1", project_id="p1", request_text="crm", stage_key="brand-voice"
    )
    assert stage2.stage_key == "brand-voice"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py::test_service_runs_research_with_run_until_gate_then_manual_stages -v`  
Expected: FAIL because `FoundationRunnerService` file/class does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class FoundationStageResult:
    stage_key: str
    pipeline_status: str
    output_payload: dict[str, Any]
    artifacts: dict[str, str]
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False

class FoundationRunnerService:
    def execute_stage(..., stage_key: str) -> FoundationStageResult:
        # first stage -> run_until_gate(...)
        # manual stages -> approve_stage(...)
        # load generated artifact file(s), return normalized payload
```

Implementation rule: build an isolated Foundation thread key per run, for example `f"{thread_id}--{run_id}"`, so two runs from the same thread never overwrite each other.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py -v`  
Expected: PASS, including isolation and artifact extraction assertions.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/foundation_runner_service.py 09-tools/vm_webapp/__init__.py 09-tools/tests/test_vm_webapp_foundation_runner_service.py
git commit -m "feat: add foundation runner service bridge for v2 runtime"
```

### Task 3: Wire WorkflowRuntimeV2 to Foundation service and immutable run snapshot

**Files:**
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py:35-685`
- Modify: `09-tools/vm_webapp/app.py:20-61`
- Test: `09-tools/tests/test_vm_webapp_workflow_runtime_v2.py`

**Step 1: Write the failing test**

```python
def test_runtime_persists_requested_and_effective_mode_snapshot(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path, force_foundation=True)
    result = runtime.execute_thread_run(
        thread_id="t1", brand_id="b1", project_id="p1",
        request_text="Build assets", mode="content_calendar", actor_id="agent:test"
    )
    plan = json.loads((tmp_path / "runtime/vm/runs" / result["run_id"] / "plan.json").read_text())
    assert plan["requested_mode"] == "content_calendar"
    assert plan["effective_mode"] == "foundation_stack"
    assert plan["profile_version"] == "v1"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py::test_runtime_persists_requested_and_effective_mode_snapshot -v`  
Expected: FAIL because plan only stores `mode` today.

**Step 3: Write minimal implementation**

```python
resolved = resolve_workflow_plan_with_contract(...)
create_run(..., stack_path="foundation_stack")
for stage in resolved["stages"]:
    create_stage(... stage_id=stage["key"], ...)

result = self.foundation_runner.execute_stage(...)
manifest = write_stage_outputs(
    ...,
    output_payload=result.output_payload,
    artifacts=result.artifacts,
)
```

Update `plan.json` payload to store:
- `requested_mode`
- `effective_mode`
- `profile_version`
- `fallback_applied`
- `skill_overrides`
- `stages` (resolved)

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py -v`  
Expected: PASS, including no-overwrite behavior for repeated runs.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py
git commit -m "feat: execute workflow runtime stages through foundation service"
```

### Task 4: Auto-resume on approval and idempotent resume semantics

**Files:**
- Modify: `09-tools/vm_webapp/orchestrator_v2.py:65-134`
- Modify: `09-tools/vm_webapp/api.py:554-566`
- Modify: `09-tools/vm_webapp/commands_v2.py:596-639`
- Test: `09-tools/tests/test_vm_webapp_orchestrator_v2.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

```python
def test_workflow_gate_approval_auto_resumes_without_manual_resume(tmp_path: Path) -> None:
    # start run that reaches waiting_approval
    # grant approval only
    # assert run reaches completed without calling /resume
```

Add API idempotency test:

```python
def test_resume_endpoint_is_idempotent_when_run_already_completed(tmp_path: Path) -> None:
    # call /resume twice after completion
    # both return 200 with current run status
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_orchestrator_v2.py::test_workflow_gate_approval_auto_resumes_without_manual_resume -v`  
Expected: FAIL due hardcoded mode payload and missing auto-advance guarantee.

**Step 3: Write minimal implementation**

```python
# orchestrator_v2.py ApprovalGranted branch:
_workflow_executor(
    session=session,
    event_type="WorkflowRunResumed",
    payload={
        "thread_id": run.thread_id,
        "brand_id": run.brand_id,
        "project_id": run.product_id,
        "run_id": run.run_id,
        "request_text": run.user_request,
    },
    ...
)
```

For `/resume`, if run status in `completed|failed|canceled`, return current status without raising or emitting duplicate transitions.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_orchestrator_v2.py 09-tools/tests/test_vm_webapp_api_v2.py -k \"resume or approval\" -v`  
Expected: PASS for auto-resume + idempotent resume behavior.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/orchestrator_v2.py 09-tools/vm_webapp/api.py 09-tools/vm_webapp/commands_v2.py 09-tools/tests/test_vm_webapp_orchestrator_v2.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat: auto-resume workflow runs after approval grant"
```

### Task 5: Expand v2 API payloads with mode contract and stage metadata

**Files:**
- Modify: `09-tools/vm_webapp/api.py:394-552`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py:301-380`

**Step 1: Write the failing test**

```python
def test_start_workflow_run_returns_requested_and_effective_mode(tmp_path: Path) -> None:
    started = client.post(..., json={"request_text": "x", "mode": "content_calendar"})
    assert started.json()["requested_mode"] == "content_calendar"
    assert started.json()["effective_mode"] == "foundation_stack"
```

Also assert `GET /api/v2/workflow-runs/{run_id}` includes both fields and per-stage error metadata keys (`error_code`, `error_message`, `retryable`) when present.

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_start_workflow_run_returns_requested_and_effective_mode -v`  
Expected: FAIL because current response only has `run_id` and `status`.

**Step 3: Write minimal implementation**

```python
queued = request.app.state.workflow_runtime.ensure_queued_run(...)
return {
    "run_id": queued["run_id"],
    "status": queued["status"],
    "requested_mode": queued["requested_mode"],
    "effective_mode": queued["effective_mode"],
}
```

Load `plan.json` in detail endpoint and expose:
- `requested_mode`
- `effective_mode`
- `profile_version`
- `fallback_applied`

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -k \"workflow_run\" -v`  
Expected: PASS with updated response contract.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat: expose requested/effective mode in workflow run APIs"
```

### Task 6: Update workspace UI for Foundation-effective runs

**Files:**
- Modify: `09-tools/web/vm/app.js`
- Modify: `09-tools/web/vm/index.html`
- Test: `09-tools/tests/test_vm_webapp_ui_assets.py`

**Step 1: Write the failing test**

```python
def test_ui_assets_include_effective_mode_and_stage_status_labels() -> None:
    html = (web_root / "index.html").read_text(encoding="utf-8")
    js = (web_root / "app.js").read_text(encoding="utf-8")
    assert "effective_mode" in js
    assert "requested_mode" in js
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_ui_assets_include_effective_mode_and_stage_status_labels -v`  
Expected: FAIL until renderers include the new fields.

**Step 3: Write minimal implementation**

```javascript
label.textContent =
  `${run.run_id} (${run.status}) mode=${run.requested_mode} -> ${run.effective_mode}`;
```

In detail renderer, show `requested_mode`, `effective_mode`, and per-stage status/error line when available.  
Keep existing override JSON input and profile preview, but render fallback notice when selected mode is not effective mode.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`  
Expected: PASS static asset assertions.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat: show foundation-effective workflow mode metadata in UI"
```

### Task 7: End-to-end validation and README update

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_event_driven_e2e.py`
- Modify: `README.md`

**Step 1: Write the failing test**

```python
def test_any_mode_falls_back_to_foundation_and_completes_after_grant(tmp_path: Path) -> None:
    # start with mode content_calendar
    # assert run detail shows effective_mode foundation_stack
    # grant approval and wait for completed (without explicit resume call)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py::test_any_mode_falls_back_to_foundation_and_completes_after_grant -v`  
Expected: FAIL before fallback + auto-resume are fully wired.

**Step 3: Write minimal implementation**

Update README v2 section to document:
- Foundation-backed execution path
- fallback semantics (`requested_mode` vs `effective_mode`)
- automatic resume on `ApprovalGranted`
- `resume` endpoint retained as idempotent safety control

**Step 4: Run full target regression**

Run:

```bash
uv run pytest \
  09-tools/tests/test_vm_webapp_workflow_profiles.py \
  09-tools/tests/test_vm_webapp_workflow_runtime_v2.py \
  09-tools/tests/test_vm_webapp_api_v2.py \
  09-tools/tests/test_vm_webapp_event_driven_e2e.py \
  09-tools/tests/test_vm_webapp_ui_assets.py -v
```

Expected: PASS for all selected regression suites.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_event_driven_e2e.py README.md
git commit -m "test+docs: validate foundation fallback flow and document runtime contract"
```

### Task 8: Final verification and integration prep

**Files:**
- Modify: none (verification only unless fixes required)

**Step 1: Run complete v2 and event suites**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py 09-tools/tests/test_vm_webapp_event_driven_e2e.py 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py 09-tools/tests/test_vm_webapp_ui_assets.py -v
```

Expected: PASS.

**Step 2: Smoke test web app startup**

Run:

```bash
uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766
```

Expected: server boots, `/api/v1/health` returns `{"status":"ok"}`.

**Step 3: Verify git diff and commit integrity**

Run:

```bash
git status --short
git log --oneline -n 8
```

Expected: only intended files changed; commit history follows task sequence.

**Step 4: If verification finds regressions, fix with smallest scoped commit**

Run targeted tests per failing module until green.

**Step 5: Final integration commit (if needed)**

```bash
git add <only regression-fix files>
git commit -m "fix: close regression gaps in foundation-integrated workflow runtime"
```

## Execution Notes

- Use `@test-driven-development` before each task implementation step.
- Use `@verification-before-completion` before claiming a task complete.
- Keep changes DRY and YAGNI: do not add external worker process in this cycle.
- Prefer preserving existing endpoints/DTO shapes and adding fields over breaking contracts.
