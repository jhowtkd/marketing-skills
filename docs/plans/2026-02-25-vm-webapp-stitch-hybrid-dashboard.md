# VM Webapp Stitch Hybrid Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a Stitch-inspired three-column VM Workspace frontend while preserving all current `/api/v2` behavior and existing JS interaction contracts.

**Architecture:** Rebuild `09-tools/web/vm/index.html` in-place into a left/center/right shell and keep the existing DOM IDs consumed by `app.js`. Keep `app.js` as the stateful controller, adding only UI-presentational helpers (timeline styling + non-blocking error banner) without changing backend contracts. Use test-driven updates in `test_vm_webapp_ui_assets.py` and one serving-level shell test to prevent regressions.

**Tech Stack:** FastAPI static serving, vanilla HTML/CSS/JS, Tailwind CDN, Material Icons CDN, pytest, uv.

---

### Task 1: Establish Stitch shell contract and CDN dependencies

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`

**Step 1: Write the failing test**

```python
def test_vm_index_uses_stitch_shell_and_cdn_dependencies() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "https://cdn.tailwindcss.com?plugins=forms,typography" in html
    assert "fonts.googleapis.com/icon?family=Material+Icons+Outlined" in html
    assert 'id="vm-shell-left"' in html
    assert 'id="vm-shell-main"' in html
    assert 'id="vm-shell-right"' in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_uses_stitch_shell_and_cdn_dependencies -v`  
Expected: FAIL because current HTML does not include Stitch shell IDs or CDN entries.

**Step 3: Write minimal implementation**

In `09-tools/web/vm/index.html`, add the Tailwind and Material Icons CDN tags in `<head>` and replace the root layout wrapper with the shell markers:

```html
<body class="...">
  <aside id="vm-shell-left" class="..."></aside>
  <main id="vm-shell-main" class="..."></main>
  <aside id="vm-shell-right" class="..."></aside>
</body>
```

Keep `<title>` containing `VM Web App` to preserve `test_root_serves_ui` expectations.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_uses_stitch_shell_and_cdn_dependencies -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html
git commit -m "test+feat(vm-ui): add stitch shell and cdn contract"
```

### Task 2: Place all existing workflow anchors into the three-column structure

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`

**Step 1: Write the failing test**

```python
def test_vm_index_places_anchor_ids_in_left_center_right_columns() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert re.search(r'id="vm-shell-left".*id="brands-list".*id="projects-list"', html, re.S)
    assert re.search(r'id="vm-shell-main".*id="threads-list".*id="workflow-run-form".*id="timeline-list".*id="workflow-run-detail-list"', html, re.S)
    assert re.search(r'id="vm-shell-right".*id="tasks-list".*id="approvals-list".*id="workflow-artifacts-list".*id="workflow-artifact-preview"', html, re.S)
```

Also add `import re` at the top of the test module.

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_places_anchor_ids_in_left_center_right_columns -v`  
Expected: FAIL until all blocks are moved into the target shell columns.

**Step 3: Write minimal implementation**

Recompose `09-tools/web/vm/index.html` to include:
- Left column: brand/project forms and lists.
- Main column: thread controls, mode help, workflow input/runs/profile preview, timeline, run detail.
- Right column: tasks, approvals, artifacts and preview.

Do not rename any ID currently used in `app.js`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_places_anchor_ids_in_left_center_right_columns -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html
git commit -m "feat(vm-ui): map existing workspace anchors into 3-column stitch layout"
```

### Task 3: Add timeline visual semantics and centralized non-blocking UI error banner

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/app.js`

**Step 1: Write the failing test**

```python
def test_vm_app_js_has_timeline_style_map_and_error_banner_hooks() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "TIMELINE_EVENT_STYLE" in js
    assert "ui-error-banner" in js
    assert "function setUiError" in js
    assert 'id="ui-error-banner"' in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_has_timeline_style_map_and_error_banner_hooks -v`  
Expected: FAIL because hooks and banner do not exist.

**Step 3: Write minimal implementation**

In `09-tools/web/vm/index.html`, add banner container near the top of center content:

```html
<div id="ui-error-banner" class="hidden ..." role="status" aria-live="polite"></div>
```

In `09-tools/web/vm/app.js`, add:

```javascript
const uiErrorBanner = document.getElementById("ui-error-banner");

const TIMELINE_EVENT_STYLE = {
  ApprovalRequested: { icon: "gavel", tone: "amber" },
  ApprovalGranted: { icon: "verified", tone: "green" },
  TaskCreated: { icon: "task_alt", tone: "blue" },
  WorkflowRunFailed: { icon: "error", tone: "red" },
};

function setUiError(message) {
  if (!uiErrorBanner) return;
  uiErrorBanner.textContent = message;
  uiErrorBanner.classList.remove("hidden");
}
```

Then route request failures through `setUiError(...)` (keeping throw behavior) and enhance `renderTimeline(...)` to use `TIMELINE_EVENT_STYLE` for icon/tone classes.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_has_timeline_style_map_and_error_banner_hooks -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html 09-tools/web/vm/app.js
git commit -m "feat(vm-ui): add timeline semantic styling and non-blocking error banner"
```

### Task 4: Guarantee responsive behavior and accessibility markers for shell columns

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`

**Step 1: Write the failing test**

```python
def test_vm_index_shell_has_mobile_stack_and_accessibility_landmarks() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'aria-label="Workspace Navigation"' in html
    assert 'aria-label="Workspace Content"' in html
    assert 'aria-label="Workspace Operations"' in html
    assert "lg:grid" in html or "lg:flex" in html
    assert "overflow-y-auto" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_shell_has_mobile_stack_and_accessibility_landmarks -v`  
Expected: FAIL until landmarks and responsive classes are present.

**Step 3: Write minimal implementation**

Update shell wrappers in `09-tools/web/vm/index.html` to include:
- explicit `aria-label` per column,
- desktop layout classes for 3 columns,
- stacked mobile defaults,
- independent scroll behavior for center/right side panels.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_shell_has_mobile_stack_and_accessibility_landmarks -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html
git commit -m "feat(vm-ui): add responsive and accessibility contracts for 3-column shell"
```

### Task 5: Add serving-level shell regression and run verification gate

**Files:**
- Create: `09-tools/tests/test_vm_webapp_ui_shell.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from vm_webapp.app import create_app


def test_root_serves_stitch_shell_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="vm-shell-left"' in html
    assert 'id="vm-shell-main"' in html
    assert 'id="vm-shell-right"' in html
    assert "cdn.tailwindcss.com" in html
    assert "VM Web App" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_stitch_shell_contract -v`  
Expected: FAIL if shell markers are missing from served root HTML.

**Step 3: Write minimal implementation**

If it fails, align `09-tools/web/vm/index.html` shell IDs/content markers with the test contract until root serving passes.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_stitch_shell_contract -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_shell.py 09-tools/web/vm/index.html
git commit -m "test(vm-ui): add root-served stitch shell regression coverage"
```

### Task 6: Verification-before-completion gate

**Files:**
- No code changes required unless regressions appear.

**Step 1: Run focused regression suite**

Run:
- `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v`
- `uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py -v`
- `uv run pytest 09-tools/tests/test_vm_webapp_api.py::test_root_serves_ui -v`

Expected: PASS for all.

**Step 2: Run broader API smoke for confidence**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -k "thread_lifecycle or workflow_profiles" -v`  
Expected: PASS for selected smoke subset.

**Step 3: Commit verification artifact (only if files changed while fixing regressions)**

```bash
git add <changed-files>
git commit -m "fix(vm-ui): resolve regression found in verification gate"
```

If no fixes were needed, do not create an extra commit.
