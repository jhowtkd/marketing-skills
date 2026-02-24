# VM LLM Chat + Foundation Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable real Kimi LLM execution for `/api/chat` and all Foundation workflow stages (`research`, `brand-voice`, `positioning`, `keywords`, final brief) with safe config and regression coverage.

**Architecture:** Keep state progression/gates in the existing Foundation executor (`run_until_gate`, `approve_stage`) and move content generation responsibility to `FoundationRunnerService` via injected LLM. Keep `WorkflowRuntimeV2` as async orchestrator and event source; it should call the service and persist stage artifacts/metadata exactly once per stage attempt. Use `.env`-driven boot (`KIMI_API_KEY`) and preserve deterministic fallback behavior when LLM is unavailable.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy/SQLite, httpx, pytest, existing VM Web App runtime and Foundation executor.

---

### Task 1: Add LLM contract to FoundationRunnerService constructor and stage API

**Files:**
- Modify: `09-tools/vm_webapp/foundation_runner_service.py`
- Modify: `09-tools/vm_webapp/app.py`
- Test: `09-tools/tests/test_vm_webapp_foundation_runner_service.py`

**Step 1: Write the failing test**

```python
def test_service_keeps_llm_handle_and_uses_default_model(tmp_path: Path) -> None:
    class FakeLLM:
        def __init__(self) -> None:
            self.calls = []
        def chat(self, **kwargs):
            self.calls.append(kwargs)
            return "ok"

    service = FoundationRunnerService(
        workspace_root=tmp_path,
        llm=FakeLLM(),
        llm_model="kimi-for-coding",
    )
    assert service.llm is not None
    assert service.llm_model == "kimi-for-coding"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py::test_service_keeps_llm_handle_and_uses_default_model -v`  
Expected: FAIL because constructor does not accept `llm`/`llm_model`.

**Step 3: Write minimal implementation**

```python
class FoundationRunnerService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        stack_path: str = FOUNDATION_STACK_PATH_DEFAULT,
        llm: Any | None = None,
        llm_model: str = "kimi-for-coding",
    ) -> None:
        self.llm = llm
        self.llm_model = llm_model
```

In app wiring:

```python
foundation_runner = FoundationRunnerService(
    workspace_root=workspace.root,
    llm=llm,
    llm_model=settings.kimi_model,
)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py -k \"llm_handle\" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/foundation_runner_service.py 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_foundation_runner_service.py
git commit -m "feat: inject llm contract into foundation runner service"
```

### Task 2: Implement stage prompt builders for all Foundation stages

**Files:**
- Modify: `09-tools/vm_webapp/foundation_runner_service.py`
- Test: `09-tools/tests/test_vm_webapp_foundation_runner_service.py`

**Step 1: Write the failing test**

```python
def test_stage_prompt_builder_has_contract_for_all_foundation_stages(tmp_path: Path) -> None:
    service = FoundationRunnerService(workspace_root=tmp_path)
    for stage in ("research", "brand-voice", "positioning", "keywords"):
        prompt = service._build_stage_prompt(
            stage_key=stage,
            request_text="crm para clinicas",
            previous_artifacts={"research/research-report.md": "insights"},
        )
        assert stage in prompt.lower()
        assert "request" in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py::test_stage_prompt_builder_has_contract_for_all_foundation_stages -v`  
Expected: FAIL because prompt builder does not exist.

**Step 3: Write minimal implementation**

```python
def _build_stage_prompt(...):
    if stage_key == "research":
        return "..."
    if stage_key == "brand-voice":
        return "..."
    if stage_key == "positioning":
        return "..."
    if stage_key == "keywords":
        return "..."
    return f"Generate markdown for stage {stage_key}."
```

Add `_build_final_brief_prompt(...)` for final brief generation after `keywords`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py -k \"prompt_builder\" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/foundation_runner_service.py 09-tools/tests/test_vm_webapp_foundation_runner_service.py
git commit -m "feat: add stage prompt contracts for foundation llm generation"
```

### Task 3: Generate LLM markdown artifacts for each stage with fallback behavior

**Files:**
- Modify: `09-tools/vm_webapp/foundation_runner_service.py`
- Test: `09-tools/tests/test_vm_webapp_foundation_runner_service.py`

**Step 1: Write the failing test**

```python
def test_execute_stage_generates_llm_artifact_when_llm_available(tmp_path: Path, monkeypatch) -> None:
    class FakeLLM:
        def __init__(self):
            self.calls = []
        def chat(self, **kwargs):
            self.calls.append(kwargs)
            return "# LLM output"

    service = FoundationRunnerService(workspace_root=tmp_path, llm=FakeLLM())
    # monkeypatch executor.run_until_gate to return deterministic state
    result = service.execute_stage(
        run_id="r1",
        thread_id="t1",
        project_id="p1",
        request_text="crm",
        stage_key="research",
    )
    assert any("LLM output" in content for content in result.artifacts.values())
```

Add fallback test:

```python
def test_execute_stage_keeps_executor_artifact_when_llm_not_configured(...):
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py -k \"llm_artifact\" -v`  
Expected: FAIL until stage generation uses LLM output.

**Step 3: Write minimal implementation**

```python
def _render_stage_markdown(...):
    if self.llm is None:
        return existing_markdown
    return self.llm.chat(
        model=self.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1200,
    )
```

Load existing executor artifact as context, generate LLM markdown, and replace selected stage artifact value in `FoundationStageResult.artifacts`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py -v`  
Expected: PASS for LLM and fallback paths.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/foundation_runner_service.py 09-tools/tests/test_vm_webapp_foundation_runner_service.py
git commit -m "feat: generate foundation stage artifacts with llm and safe fallback"
```

### Task 4: Add final brief LLM generation at pipeline completion

**Files:**
- Modify: `09-tools/vm_webapp/foundation_runner_service.py`
- Test: `09-tools/tests/test_vm_webapp_foundation_runner_service.py`

**Step 1: Write the failing test**

```python
def test_keywords_stage_also_returns_llm_final_brief_when_pipeline_completed(tmp_path: Path, monkeypatch) -> None:
    class FakeLLM:
        def chat(self, **kwargs):
            prompt = kwargs["messages"][0]["content"]
            if "foundation brief" in prompt.lower():
                return "# Final Brief"
            return "# Stage Output"
    service = FoundationRunnerService(workspace_root=tmp_path, llm=FakeLLM())
    # monkeypatch executor.approve_stage to return completed state with final artifact
    result = service.execute_stage(..., stage_key="keywords")
    assert "final/foundation-brief.md" in result.artifacts
    assert "Final Brief" in result.artifacts["final/foundation-brief.md"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py::test_keywords_stage_also_returns_llm_final_brief_when_pipeline_completed -v`  
Expected: FAIL until final brief prompt/render exists.

**Step 3: Write minimal implementation**

```python
if stage_key == "keywords" and state.get("status") == "completed":
    brief_prompt = self._build_final_brief_prompt(...)
    brief_md = self._render_with_llm_or_fallback(prompt=brief_prompt, fallback=existing_brief)
    artifacts["final/foundation-brief.md"] = brief_md
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_foundation_runner_service.py -k \"final_brief\" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/foundation_runner_service.py 09-tools/tests/test_vm_webapp_foundation_runner_service.py
git commit -m "feat: generate llm final foundation brief on completed pipeline"
```

### Task 5: Propagate LLM metadata into runtime stage output contract

**Files:**
- Modify: `09-tools/vm_webapp/foundation_runner_service.py`
- Modify: `09-tools/vm_webapp/workflow_runtime_v2.py`
- Modify: `09-tools/vm_webapp/api.py`
- Test: `09-tools/tests/test_vm_webapp_workflow_runtime_v2.py`
- Test: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

```python
def test_runtime_stage_output_includes_llm_metadata(tmp_path: Path) -> None:
    # run workflow with fake llm
    detail = client.get(f"/api/v2/workflow-runs/{run_id}").json()
    stage = detail["stages"][0]
    assert "manifest" in stage
    assert stage["manifest"]["output"]["llm"]["model"] == "kimi-for-coding"
```

(Adjust expected field shape to current manifest contract.)

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py 09-tools/tests/test_vm_webapp_api_v2.py -k \"llm_metadata\" -v`  
Expected: FAIL because metadata is not written yet.

**Step 3: Write minimal implementation**

In `FoundationStageResult.output_payload`, include:

```python
{
  "stage_key": stage_key,
  "pipeline_status": ...,
  "llm": {
    "enabled": self.llm is not None,
    "model": self.llm_model if self.llm is not None else None
  }
}
```

Ensure `WorkflowRuntimeV2._execute_stage` persists this payload to `output.json`/manifest.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py 09-tools/tests/test_vm_webapp_api_v2.py -k \"workflow_run or llm_metadata\" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/foundation_runner_service.py 09-tools/vm_webapp/workflow_runtime_v2.py 09-tools/vm_webapp/api.py 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py 09-tools/tests/test_vm_webapp_api_v2.py
git commit -m "feat: expose llm metadata in workflow stage outputs"
```

### Task 6: Verify chat endpoint with configured LLM and add guardrail test

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_api.py`
- Modify: `09-tools/vm_webapp/api.py` (only if needed for clearer status messaging)

**Step 1: Write the failing test**

```python
def test_chat_uses_llm_when_configured() -> None:
    class FakeLLM:
        def __init__(self):
            self.called = False
        def chat(self, **kwargs):
            self.called = True
            return "LLM reply"
    app = create_app(memory=FakeMemory(), llm=FakeLLM())
    ...
    assert response.json()["message"] == "LLM reply"
```

Add negative test:

```python
def test_chat_returns_placeholder_when_llm_missing() -> None:
    ...
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api.py -k \"chat_uses_llm_when_configured or placeholder\" -v`  
Expected: FAIL if behavior/contract is inconsistent.

**Step 3: Write minimal implementation**

Only if needed:

```python
assistant_message = "(llm not configured)"
if llm is not None:
    assistant_message = llm.chat(...)
```

Keep chat contract stable and explicit.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api.py -k \"chat\" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_api.py 09-tools/vm_webapp/api.py
git commit -m "test: lock chat llm behavior for configured and unconfigured modes"
```

### Task 7: Document `.env` setup and run a full regression sweep

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-02-24-vm-llm-foundation-workflow-design.md` (only if minor clarifications needed)

**Step 1: Write the failing test (docs assertion)**

```python
def test_readme_mentions_kimi_env_vars_for_vm_webapp():
    content = Path("README.md").read_text(encoding="utf-8")
    assert "KIMI_API_KEY" in content
    assert "KIMI_MODEL" in content
    assert "KIMI_BASE_URL" in content
```

Add this to `09-tools/tests/test_vm_webapp_ui_assets.py` or a new lightweight docs test file if preferred.

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -k \"readme_mentions_kimi\" -v`  
Expected: FAIL until docs are updated.

**Step 3: Write minimal implementation**

README update section under v2 runtime:
- `.env` snippet:

```bash
KIMI_API_KEY=your_key_here
KIMI_MODEL=kimi-for-coding
KIMI_BASE_URL=https://api.kimi.com/coding/v1
```

- Add “LLM active/inactive” behavior notes.

**Step 4: Run full verification suite**

Run:

```bash
uv run pytest \
  09-tools/tests/test_vm_webapp_foundation_runner_service.py \
  09-tools/tests/test_vm_webapp_workflow_runtime_v2.py \
  09-tools/tests/test_vm_webapp_api_v2.py \
  09-tools/tests/test_vm_webapp_event_driven_e2e.py \
  09-tools/tests/test_vm_webapp_api.py \
  09-tools/tests/test_vm_webapp_ui_assets.py -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add README.md 09-tools/tests/test_vm_webapp_ui_assets.py docs/plans/2026-02-24-vm-llm-foundation-workflow-design.md
git commit -m "docs: add llm env setup and verification notes for vm webapp"
```

### Task 8: Real-key smoke validation (manual, non-committed secret)

**Files:**
- Modify: `.env` (local only, do not commit)

**Step 1: Configure local `.env`**

```bash
cat >> .env <<'EOF'
KIMI_API_KEY=<USER_PROVIDED_KEY>
KIMI_MODEL=kimi-for-coding
KIMI_BASE_URL=https://api.kimi.com/coding/v1
EOF
```

**Step 2: Start app**

Run: `uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766`  
Expected: server starts without config errors.

**Step 3: Smoke test chat**

Run:

```bash
curl -sS -X POST http://127.0.0.1:8766/api/chat \
  -H "Content-Type: application/json" \
  -d '{"brand_id":"b1","product_id":"p1","thread_id":"t1","message":"Crie um resumo estratégico em 3 bullets"}'
```

Expected: response with non-placeholder assistant text.

**Step 4: Smoke test workflow**

Use UI (`/`) to run workflow and grant approvals; verify artifacts for all Foundation stages contain generated text that differs from static placeholder wording.

**Step 5: Commit**

No commit for secret/config values.  
If code/docs/test changes were needed during smoke, commit only tracked source files.

## Execution Notes

- Use `@test-driven-development` before implementation edits.
- Use `@verification-before-completion` before claiming done.
- Keep API key out of logs, diffs, and commits.
- Do not change existing async event/state model unless a test proves necessity.
