# VM Webapp Studio UI (Guided-first) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a guided “Studio” UX on top of the existing VM event-driven workspace UI so creators can generate and preview plans quickly, while keeping technical surfaces behind an explicit Dev Mode toggle.

**Architecture:** Keep the static SPA served from `09-tools/web/vm/` and keep `09-tools/web/vm/app.js` as the controller/state owner. Add a Studio toolbar + preview + wizard that uses existing `/api/v2/*` endpoints. Hide timeline/modes/workflow IO/run detail behind Dev Mode using CSS + a persisted toggle in `localStorage`. No backend changes in this plan.

**Tech Stack:** vanilla HTML/CSS/JS, Tailwind CDN, Material Icons, pytest, uv.

---

## Pre-flight (recommended)

Create a dedicated worktree + branch for this plan:

```bash
git worktree add .worktrees/vm-webapp-studio-ui -b codex/vm-webapp-studio-ui
cd .worktrees/vm-webapp-studio-ui
```

---

### Task 1: Add Studio + Dev Mode anchors to the HTML shell

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/styles.css`

**Step 1: Write the failing test**

Append to `09-tools/tests/test_vm_webapp_ui_assets.py`:

```python
from pathlib import Path


def test_vm_index_contains_studio_and_devmode_anchors() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="studio-toolbar"' in html
    assert 'id="studio-create-plan-button"' in html
    assert 'id="studio-devmode-toggle"' in html
    assert 'id="studio-artifact-preview"' in html
    assert 'id="studio-wizard"' in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_studio_and_devmode_anchors -v`  
Expected: FAIL (anchors not present).

**Step 3: Write minimal implementation**

In `09-tools/web/vm/index.html` (inside `#vm-shell-main`, near the top of the center column), add:

```html
<section id="studio-toolbar" class="panel bg-white rounded-lg shadow p-4">
  <div class="flex items-center justify-between gap-3">
    <div>
      <h2 class="text-lg font-semibold">Studio</h2>
      <p id="studio-status-text" class="text-sm text-gray-600">Select a plan to begin.</p>
    </div>
    <div class="flex items-center gap-2">
      <button
        id="studio-create-plan-button"
        type="button"
        class="bg-green-600 text-white rounded px-4 py-2"
      >
        Create plan
      </button>
      <label class="inline-flex items-center gap-2 text-sm text-gray-700">
        <input id="studio-devmode-toggle" type="checkbox" class="rounded" />
        Dev mode
      </label>
    </div>
  </div>
</section>

<section class="panel bg-white rounded-lg shadow p-4">
  <h3 class="font-semibold mb-2">Preview</h3>
  <pre
    id="studio-artifact-preview"
    class="item muted p-3 bg-gray-100 rounded text-sm"
  >No preview yet.</pre>
</section>
```

Add wizard modal root near end of `<body>`:

```html
<div
  id="studio-wizard"
  class="vm-modal hidden"
  role="dialog"
  aria-modal="true"
  aria-label="Create plan wizard"
></div>
```

In `09-tools/web/vm/styles.css`, add:

```css
.vm-dev-only { display: none; }

.vm-modal {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.vm-modal__card {
  background: #fff;
  border-radius: 12px;
  max-width: 720px;
  width: 100%;
  padding: 16px;
}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_studio_and_devmode_anchors -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html 09-tools/web/vm/styles.css
git commit -m "feat(vm-ui): add studio toolbar, preview, and wizard anchors"
```

---

### Task 2: Implement Dev Mode toggle (hide technical panels by default)

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/styles.css`
- Modify: `09-tools/web/vm/app.js`

**Step 1: Write the failing test**

Append to `09-tools/tests/test_vm_webapp_ui_assets.py`:

```python
def test_vm_app_js_has_devmode_toggle_wiring() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "studio-devmode-toggle" in js
    assert "localStorage" in js
    assert "vm-dev-only" in js
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_has_devmode_toggle_wiring -v`  
Expected: FAIL.

**Step 3: Hide technical blocks behind `.vm-dev-only`**

In `09-tools/web/vm/index.html`, wrap these blocks with `<div class="vm-dev-only">...</div>`:

- `#thread-mode-form`, `#mode-help`, `#thread-modes-list`
- `#timeline-list`
- `#workflow-io-panel` (input/mode/overrides/profile preview/runs/run detail)

Keep all existing IDs in the DOM (tests and JS depend on them).

**Step 4: Add CSS and JS wiring**

In `09-tools/web/vm/styles.css`:

```css
body[data-dev-mode="1"] .vm-dev-only { display: block; }
```

In `09-tools/web/vm/app.js`, add:

```javascript
const studioDevModeToggle = document.getElementById("studio-devmode-toggle");
const DEV_MODE_KEY = "vm_dev_mode";

function setDevMode(enabled) {
  document.body.dataset.devMode = enabled ? "1" : "0";
  if (studioDevModeToggle) studioDevModeToggle.checked = !!enabled;
  window.localStorage.setItem(DEV_MODE_KEY, enabled ? "1" : "0");
}

function loadDevMode() {
  const raw = window.localStorage.getItem(DEV_MODE_KEY);
  setDevMode(raw === "1");
}

if (studioDevModeToggle) {
  studioDevModeToggle.addEventListener("change", () => {
    setDevMode(!!studioDevModeToggle.checked);
  });
}
loadDevMode();
```

**Step 5: Run tests**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_has_devmode_toggle_wiring -v
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html 09-tools/web/vm/styles.css 09-tools/web/vm/app.js
git commit -m "feat(vm-ui): add dev mode toggle and hide technical panels by default"
```

---

### Task 3: Implement “Create Plan” wizard (guided run start)

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/app.js`

**Step 1: Write the failing test**

Append to `09-tools/tests/test_vm_webapp_ui_assets.py`:

```python
def test_vm_app_js_includes_studio_wizard_ids() -> None:
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "studio-create-plan-button" in js
    assert "studio-wizard" in js
    assert "/api/v2/threads" in js
    assert "/workflow-runs" in js
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_includes_studio_wizard_ids -v`  
Expected: FAIL.

**Step 3: Add wizard form HTML**

In `09-tools/web/vm/index.html`, set inner content of `#studio-wizard`:

```html
<div class="vm-modal__card">
  <h3 class="text-lg font-semibold mb-3">Create plan</h3>
  <form id="studio-wizard-form" class="space-y-3">
    <input
      id="studio-plan-title-input"
      class="w-full border rounded px-3 py-2"
      placeholder="Title (optional)"
    />
    <textarea
      id="studio-plan-brief-input"
      class="w-full border rounded px-3 py-2 h-28"
      placeholder="Describe product, audience, objective, channels…"
    ></textarea>
    <div id="studio-playbooks" class="grid gap-3 md:grid-cols-2"></div>
    <div class="flex justify-end gap-2">
      <button
        id="studio-wizard-cancel"
        type="button"
        class="bg-gray-200 rounded px-3 py-2"
      >
        Cancel
      </button>
      <button type="submit" class="bg-green-600 text-white rounded px-3 py-2">
        Generate
      </button>
    </div>
  </form>
</div>
```

**Step 4: Implement JS wiring (open/close + playbooks + submit)**

In `09-tools/web/vm/app.js`, add element refs:

```javascript
const studioCreatePlanButton = document.getElementById("studio-create-plan-button");
const studioWizard = document.getElementById("studio-wizard");
const studioWizardForm = document.getElementById("studio-wizard-form");
const studioWizardCancel = document.getElementById("studio-wizard-cancel");
const studioPlanTitleInput = document.getElementById("studio-plan-title-input");
const studioPlanBriefInput = document.getElementById("studio-plan-brief-input");
const studioPlaybooks = document.getElementById("studio-playbooks");
```

Render playbooks from `workflowProfilesState` (allowed: `plan_90d`, `content_calendar`):

```javascript
let studioSelectedMode = "plan_90d";

function renderStudioPlaybooks() {
  if (!studioPlaybooks) return;
  const allowed = new Set(["plan_90d", "content_calendar"]);
  const playbooks = (workflowProfilesState || []).filter((p) => allowed.has(p.mode));
  studioPlaybooks.innerHTML = "";
  for (const p of playbooks) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "border rounded p-3 text-left";
    btn.textContent = `${p.mode}: ${p.description || ""}`;
    btn.addEventListener("click", () => {
      studioSelectedMode = p.mode;
      renderStudioPlaybooks();
    });
    if (p.mode === studioSelectedMode) btn.classList.add("border-blue-500", "bg-blue-50");
    studioPlaybooks.appendChild(btn);
  }
}
```

Wizard open/close:

```javascript
function openStudioWizard() {
  if (!studioWizard) return;
  renderStudioPlaybooks();
  studioWizard.classList.remove("hidden");
}

function closeStudioWizard() {
  if (!studioWizard) return;
  studioWizard.classList.add("hidden");
}
```

Bind:

```javascript
if (studioCreatePlanButton) studioCreatePlanButton.addEventListener("click", openStudioWizard);
if (studioWizardCancel) studioWizardCancel.addEventListener("click", closeStudioWizard);
```

Submit flow (create thread -> add mode -> start run -> select thread/run):

```javascript
async function startStudioPlan() {
  if (!activeBrandId || !activeProjectId) {
    setUiError("Select a brand and project first.");
    return;
  }
  const title = (studioPlanTitleInput?.value || "").trim() || "New plan";
  const request_text = (studioPlanBriefInput?.value || "").trim();
  if (!request_text) return;

  const created = await postV2(
    ENDPOINT_THREADS,
    { project_id: activeProjectId, brand_id: activeBrandId, title },
    "studio-thread-create"
  );
  const thread_id = created.thread_id;
  await postV2(
    `/api/v2/threads/${encodeURIComponent(thread_id)}/modes`,
    { mode: studioSelectedMode },
    "studio-mode"
  );
  const started = await postV2(
    `/api/v2/threads/${encodeURIComponent(thread_id)}/workflow-runs`,
    { request_text, mode: studioSelectedMode, skill_overrides: {} },
    "studio-workflow-run"
  );

  activeThreadId = thread_id;
  activeWorkflowRunId = started.run_id || null;
  closeStudioWizard();
  await loadThreads(activeProjectId);
}

if (studioWizardForm) {
  studioWizardForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await startStudioPlan();
  });
}
```

**Step 5: Run tests**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_app_js_includes_studio_wizard_ids -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html 09-tools/web/vm/app.js
git commit -m "feat(vm-ui): add create plan wizard (guided workflow start)"
```

---

### Task 4: Studio status + stage progress + preview mirroring

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`
- Modify: `09-tools/web/vm/app.js`

**Step 1: Write the failing test**

Append to `09-tools/tests/test_vm_webapp_ui_assets.py`:

```python
def test_vm_index_contains_studio_progress_anchors() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert 'id="studio-stage-progress"' in html
    assert 'id="studio-status-text"' in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_studio_progress_anchors -v`  
Expected: FAIL.

**Step 3: Add progress container**

In `09-tools/web/vm/index.html`:

```html
<section class="panel bg-white rounded-lg shadow p-4">
  <h3 class="font-semibold mb-2">Progress</h3>
  <div id="studio-stage-progress" class="list space-y-2"></div>
</section>
```

**Step 4: Implement status/progress rendering + mirror artifact preview**

In `09-tools/web/vm/app.js`:

```javascript
const studioStatusText = document.getElementById("studio-status-text");
const studioStageProgress = document.getElementById("studio-stage-progress");
const studioArtifactPreview = document.getElementById("studio-artifact-preview");

const STATUS_LABEL = {
  queued: "Em fila",
  running: "Gerando…",
  waiting_approval: "Aguardando revisão",
  completed: "Pronto",
  failed: "Falhou",
};

function humanizeStageKey(key) {
  return String(key || "").replaceAll("_", " ");
}

function renderStudioRun(detail) {
  if (!detail) return;
  if (studioStatusText) {
    const label = STATUS_LABEL[detail.status] || detail.status;
    studioStatusText.textContent = `${label} · ${detail.effective_mode || detail.mode || ""}`.trim();
  }
  if (studioStageProgress) {
    const rows = Array.isArray(detail.stages)
      ? detail.stages.slice().sort((a, b) => a.position - b.position)
      : [];
    clearAndRender(studioStageProgress, rows, (stage) => {
      const node = document.createElement("div");
      node.className = "item";
      node.textContent = `${humanizeStageKey(stage.stage_id)} — ${stage.status}`;
      return node;
    });
  }
}
```

Call from `loadWorkflowRunDetail(runId)`:

```javascript
const detail = await fetchJson(`/api/v2/workflow-runs/${encodeURIComponent(runId)}`);
renderWorkflowRunDetail(detail);
renderStudioRun(detail);
```

Mirror in `loadWorkflowArtifactContent`:

```javascript
workflowArtifactPreview.textContent = body.content || "";
if (studioArtifactPreview) studioArtifactPreview.textContent = body.content || "";
```

**Step 5: Run tests**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_studio_progress_anchors -v
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html 09-tools/web/vm/app.js
git commit -m "feat(vm-ui): add studio status, stage progress, and preview mirroring"
```

---

### Task 5: Verification gate

**Step 1: Run focused tests**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py -v
uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q
```

Expected: PASS.

**Step 2: Optional manual smoke**

1. Start server: `uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766`
2. In browser:
   - Select brand + project
   - Click “Create plan”, fill brief, select playbook, Generate
   - Watch Studio status/progress update
   - Preview mirrors artifact content
   - Toggle Dev mode to access timeline/modes/workflow panels

