# VM Webapp React UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replatform the VM Web App UI to a Vite + React + TypeScript + Tailwind SPA (dashboard Stitch/hybrid), served by FastAPI at `GET /`, with big-bang functional parity against the legacy UI.

**Architecture:** Create a new frontend at `09-tools/web/vm-ui/` (Vite app) and version its build output `09-tools/web/vm-ui/dist/` in the repo (so Render deploy remains Python-only). Update `09-tools/vm_webapp/app.py` to mount the new `dist` folder at `/`. Keep backend endpoints `/api/v2/*` unchanged; implement a typed API client and React state that mirrors `app.js` selection/polling behavior.

**Tech Stack:** Vite, React, TypeScript, Tailwind (compiled), vanilla fetch, pytest (existing), uv (existing).

---

## Pre-flight (recommended)

Create a dedicated worktree + branch:

```bash
git worktree add .worktrees/vm-webapp-react-ui -b codex/vm-webapp-react-ui
cd .worktrees/vm-webapp-react-ui
```

Quick sanity:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -q
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py -q
```

Expected: PASS (current legacy UI contract).

---

### Task 1: Scaffold Vite + React + TS app folder (no backend switch yet)

**Files:**
- Create: `09-tools/web/vm-ui/` (Vite app)
- Create: `09-tools/web/vm-ui/package.json`
- Create: `09-tools/web/vm-ui/vite.config.ts`
- Create: `09-tools/web/vm-ui/tsconfig.json`
- Create: `09-tools/web/vm-ui/index.html`
- Create: `09-tools/web/vm-ui/src/main.tsx`
- Create: `09-tools/web/vm-ui/src/App.tsx`
- Create: `09-tools/web/vm-ui/src/styles/tailwind.css`
- Create: `09-tools/web/vm-ui/postcss.config.js`
- Create: `09-tools/web/vm-ui/tailwind.config.ts`

**Step 1: Write the failing test**

Append to `09-tools/tests/test_vm_webapp_ui_assets.py`:

```python
from pathlib import Path


def test_vm_react_ui_source_tree_exists() -> None:
    assert Path("09-tools/web/vm-ui").exists()
    assert Path("09-tools/web/vm-ui/package.json").exists()
    assert Path("09-tools/web/vm-ui/src/App.tsx").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_source_tree_exists -v`  
Expected: FAIL (paths missing).

**Step 3: Implement minimal scaffold**

Create the Vite app (keep it minimal, single page, no routing) and ensure `npm run build` generates `dist/`.

Implementation notes:
- Add a stable marker to rendered HTML: `data-vm-ui="react"` on a root wrapper.
- In `index.html`, set `<title>VM Workspace</title>`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_source_tree_exists -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm-ui
git commit -m "feat(vm-ui): scaffold vite react app"
```

---

### Task 2: Add build output contract (`dist/` exists and has `index.html`)

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Create: `09-tools/web/vm-ui/dist/` (committed build output)

**Step 1: Write the failing test**

Append to `09-tools/tests/test_vm_webapp_ui_assets.py`:

```python
def test_vm_react_ui_dist_index_exists() -> None:
    dist_index = Path("09-tools/web/vm-ui/dist/index.html")
    assert dist_index.exists()
    html = dist_index.read_text(encoding="utf-8")
    assert "data-vm-ui=\"react\"" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_dist_index_exists -v`  
Expected: FAIL (dist missing).

**Step 3: Build the frontend**

Run:

```bash
cd 09-tools/web/vm-ui
npm install
npm run build
cd -
```

Ensure `09-tools/web/vm-ui/dist/index.html` exists and contains the marker.

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_dist_index_exists -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm-ui/dist
git commit -m "chore(vm-ui): commit initial dist build"
```

---

### Task 3: Switch FastAPI mount to serve React UI `dist/` at `/`

**Files:**
- Modify: `09-tools/vm_webapp/app.py`
- Modify: `09-tools/tests/test_vm_webapp_ui_shell.py`

**Step 1: Write the failing test**

Update `09-tools/tests/test_vm_webapp_ui_shell.py`:

```python
def test_root_serves_react_ui_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'data-vm-ui="react"' in html
    assert "<title>VM Workspace</title>" in html
```

Keep the existing legacy shell test for now by moving it to a new path only if you keep legacy available.

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_react_ui_contract -v`  
Expected: FAIL (root still legacy).

**Step 3: Implement minimal backend change**

In `09-tools/vm_webapp/app.py`, change:
- `static_dir` to `... / "web" / "vm-ui" / "dist"`

Keep `html=True`.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_react_ui_contract -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_ui_shell.py
git commit -m "feat(vm-ui): serve react dist at root"
```

---

### Task 4: Implement typed API client (`/api/v2/*`) and error boundary

**Files:**
- Create: `09-tools/web/vm-ui/src/api/client.ts`
- Create: `09-tools/web/vm-ui/src/api/types.ts`
- Create: `09-tools/web/vm-ui/src/api/endpoints.ts`

**Step 1: Write the failing test**

Add `09-tools/tests/test_vm_webapp_ui_assets.py` assertions that the built JS references key endpoints and idempotency header:

```python
def test_vm_react_ui_bundle_references_v2_endpoints_and_idempotency() -> None:
    assets_dir = Path("09-tools/web/vm-ui/dist/assets")
    assert assets_dir.exists()
    js_files = list(assets_dir.glob("*.js"))
    assert js_files
    blob = "\\n".join(p.read_text(encoding="utf-8") for p in js_files)
    assert "/api/v2/brands" in blob
    assert "/api/v2/projects" in blob
    assert "/api/v2/threads" in blob
    assert "Idempotency-Key" in blob
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_bundle_references_v2_endpoints_and_idempotency -v`  
Expected: FAIL.

**Step 3: Implement client**

Implement:
- `fetchJson<T>(url, opts)` that parses JSON and throws on `!ok`, surfacing `detail`.
- `postJson/patchJson` that set:
  - `Content-Type: application/json`
  - `Idempotency-Key: <prefix>-<timestamp>-<rand>`

Add endpoint constants mirroring `app.js` usage.

**Step 4: Rebuild and run test**

Run:

```bash
cd 09-tools/web/vm-ui
npm run build
cd -
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_bundle_references_v2_endpoints_and_idempotency -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/api 09-tools/web/vm-ui/dist 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat(vm-ui): add v2 api client with idempotency"
```

---

### Task 5: Build the Stitch/hybrid shell (3 columns) and state skeleton

**Files:**
- Modify: `09-tools/web/vm-ui/src/App.tsx`
- Create: `09-tools/web/vm-ui/src/components/Shell.tsx`
- Create: `09-tools/web/vm-ui/src/components/panels/*`

**Step 1: Write the failing test**

Add contract markers to `dist/index.html` (or rendered markup) to ensure left/center/right exist:

```python
def test_vm_react_ui_shell_has_three_columns_markers() -> None:
    html = Path("09-tools/web/vm-ui/dist/index.html").read_text(encoding="utf-8")
    assert "data-vm-shell=\"left\"" in html
    assert "data-vm-shell=\"main\"" in html
    assert "data-vm-shell=\"right\"" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_shell_has_three_columns_markers -v`  
Expected: FAIL.

**Step 3: Implement shell**

In React, implement the shell using Tailwind (compiled) in Stitch direction:
- Light background, cards, borders, primary blue.
- Responsive stack on mobile (columns become sections).
- Add `data-vm-shell` markers on wrappers.

**Step 4: Rebuild and run test**

Run:

```bash
cd 09-tools/web/vm-ui
npm run build
cd -
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_react_ui_shell_has_three_columns_markers -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src 09-tools/web/vm-ui/dist 09-tools/tests/test_vm_webapp_ui_assets.py
git commit -m "feat(vm-ui): add stitch-inspired shell layout"
```

---

### Task 6: Brands + Projects panels (CRUD + selection)

**Files:**
- Create: `09-tools/web/vm-ui/src/features/brands/*`
- Create: `09-tools/web/vm-ui/src/features/projects/*`
- Modify: `09-tools/web/vm-ui/src/App.tsx`

**Step 1: Write the failing test**

Add a bundle contract test that the UI references endpoints used in this feature:

```python
def test_vm_react_ui_bundle_references_brand_and_project_writes() -> None:
    assets_dir = Path("09-tools/web/vm-ui/dist/assets")
    js_files = list(assets_dir.glob("*.js"))
    blob = "\\n".join(p.read_text(encoding="utf-8") for p in js_files)
    assert "/api/v2/brands" in blob
    assert "/api/v2/projects" in blob
    assert "PATCH" in blob
```

**Step 2: Run test to verify it fails**

Expected: FAIL until you build features and rebuild.

**Step 3: Implement minimal UI**

- Load brands on boot.
- On brand select: load projects, reset thread selection.
- Create brand form inline.
- Edit brand via modal/prompt-like dialog.
- Create project form (requires active brand).
- Edit project (name/objective/channels/due date).

**Step 4: Manual smoke**

Run `uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766` and use browser to:
- Create brand, edit brand.
- Create project, edit project.

**Step 5: Rebuild + tests + commit**

Rebuild, run the new unit-contract tests, commit src + dist.

---

### Task 7: Threads + modes (CRUD + selection)

**Files:**
- Create: `09-tools/web/vm-ui/src/features/threads/*`
- Modify: `09-tools/web/vm-ui/src/App.tsx`

**Steps**

Follow TDD pattern (contract tests in `test_vm_webapp_ui_assets.py` ensuring bundle references:
- `GET/POST/PATCH /api/v2/threads`
- `POST /api/v2/threads/{thread_id}/modes`
- `POST /api/v2/threads/{thread_id}/modes/{mode}/remove`

Implement:
- Create thread, list threads by project, select thread, edit title.
- Modes list/add/edit/remove.

Rebuild, run tests, commit.

---

### Task 8: Inbox + timeline (read + actions)

**Files:**
- Create: `09-tools/web/vm-ui/src/features/inbox/*`
- Create: `09-tools/web/vm-ui/src/features/timeline/*`

**Steps**

Add contract tests for endpoints:
- `/timeline`, `/tasks`, `/approvals`
- `/tasks/{id}/comment`, `/tasks/{id}/complete`, `/approvals/{id}/grant`

Implement:
- Right column shows tasks and approvals with CTAs.
- Timeline renders in center (compact), Dev Mode expands details.

Rebuild, run tests, manual smoke, commit.

---

### Task 9: Workflow (profiles, run, runs list, detail, resume)

**Files:**
- Create: `09-tools/web/vm-ui/src/features/workflow/*`

**Steps**

Add contract tests that bundle references:
- `/api/v2/workflow-profiles`
- `/api/v2/threads/{thread_id}/workflow-runs`
- `/api/v2/workflow-runs/{run_id}`
- `/api/v2/workflow-runs/{run_id}/resume`

Implement:
- Mode selection + workflow profile preview.
- Request input + overrides JSON parsing (client-side validation).
- Start run -> set activeRunId.
- Poll runs list and active run detail every ~2s while thread selected.
- Resume action when `waiting_approval`.

Rebuild, tests, manual smoke, commit.

---

### Task 10: Artifacts (list + content preview)

**Files:**
- Create: `09-tools/web/vm-ui/src/features/artifacts/*`

**Steps**

Add contract tests for:
- `/api/v2/workflow-runs/{run_id}/artifacts`
- `/api/v2/workflow-runs/{run_id}/artifact-content`

Implement:
- Right column list of artifacts grouped by stage.
- Click artifact loads content and shows in preview `<pre>` (safe text).
- Also mirror content in Studio preview.

Rebuild, tests, manual smoke, commit.

---

### Task 11: Dev Mode + error surface

**Files:**
- Create: `09-tools/web/vm-ui/src/features/devmode/*`
- Modify: `09-tools/web/vm-ui/src/App.tsx`

**Steps**

Implement:
- Toggle persisted in `localStorage`.
- When ON: show technical IDs, raw timeline details, overrides panel, and more run detail diagnostics.
- Error banner/toast central (non-blocking) on API errors, without resetting selection.

Rebuild, tests (bundle should include `localStorage` + marker strings), manual smoke, commit.

---

### Task 12: Tighten tests + final verification

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/tests/test_vm_webapp_ui_shell.py`

**Steps**

1. Run UI asset tests:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v
```

2. Run shell test:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py -v
```

3. Run full suite (best-effort):

```bash
uv run pytest -q
```

Expected: PASS. Do not fix unrelated failures.

4. Commit final adjustments:

```bash
git add 09-tools/web/vm-ui/src 09-tools/web/vm-ui/dist 09-tools/vm_webapp/app.py 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/tests/test_vm_webapp_ui_shell.py
git commit -m "feat(vm-ui): react big-bang parity shell"
```

