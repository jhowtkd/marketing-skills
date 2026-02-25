# VM Webapp Retro Terminal Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir a UI atual do VM Web App por um layout retro terminal com alta fidelidade ao Stitch, mantendo todos os fluxos e contratos DOM/API existentes.

**Architecture:** Reestruturar `09-tools/web/vm/index.html` para uma shell retro em 3 colunas (left/main/right) preservando todos os IDs usados por `app.js`. Aplicar tema retro centralizado em `styles.css` e manter `app.js` como controlador de estado e chamadas `/api/v2/*`, com ajustes apenas de apresentacao. Cobrir regressao com testes de assets e shell servida pela aplicacao.

**Tech Stack:** FastAPI static serving, HTML + Tailwind CDN, CSS custom, JavaScript vanilla, pytest via `uv`.

---

Execution guardrails: `@test-driven-development` + `@verification-before-completion`.

### Task 1: Fixar contrato retro no head e shell root

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`

**Step 1: Write the failing test**

Add this test in `09-tools/tests/test_vm_webapp_ui_assets.py`:

```python
def test_vm_index_contains_retro_terminal_head_and_shell_chrome() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert "Share+Tech+Mono" in html
    assert "JetBrains+Mono" in html
    assert "fonts.googleapis.com/icon?family=Material+Icons" in html
    assert 'class="scanlines"' in html
    assert "SYS.VER.3.0.0 [MONOCHROME]" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_retro_terminal_head_and_shell_chrome -v`  
Expected: FAIL because current HTML does not include all retro markers.

**Step 3: Write minimal implementation**

Update `09-tools/web/vm/index.html` head/body chrome with Stitch-compatible markers:

```html
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@100..800&family=Share+Tech+Mono&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet" />
<div class="scanlines"></div>
<div class="absolute top-0 right-0 p-1 text-[10px] opacity-70">SYS.VER.3.0.0 [MONOCHROME]</div>
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_contains_retro_terminal_head_and_shell_chrome -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html
git commit -m "test+feat(vm-ui): add retro terminal head and shell chrome contract"
```

### Task 2: Migrar coluna esquerda para visual retro sem quebrar IDs

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`

**Step 1: Write the failing test**

Add this test:

```python
def test_vm_index_left_column_uses_retro_panels_with_brand_project_thread_ids() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert re.search(
        r'id="vm-shell-left".*id="brand-create-form".*id="brands-list".*id="project-create-form".*id="projects-list".*id="thread-create-button".*id="threads-list"',
        html,
        re.S,
    )
    assert "Initialize Brand" in html
    assert "Execute Project" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_left_column_uses_retro_panels_with_brand_project_thread_ids -v`  
Expected: FAIL until left-side panel structure is updated.

**Step 3: Write minimal implementation**

In `09-tools/web/vm/index.html`, replace left column blocks with retro cards and keep IDs unchanged:

```html
<aside id="vm-shell-left" class="col-span-12 lg:col-span-3 space-y-6" aria-label="Workspace Navigation">
  <section class="border border-primary bg-black relative">
    <div class="absolute top-0 left-0 ...">Brands</div>
    <form id="brand-create-form" class="p-4 pt-8 space-y-4">...</form>
    <div id="brands-list" class="space-y-2"></div>
  </section>
  <section class="border border-primary bg-black relative">
    <div class="absolute top-0 left-0 ...">Projects</div>
    <form id="project-create-form" class="p-4 pt-8 space-y-2">...</form>
    <div id="projects-list" class="space-y-2"></div>
  </section>
  <section class="border border-primary bg-black relative">
    <div class="absolute top-0 left-0 ...">Threads</div>
    <input id="thread-title-input" ... />
    <button id="thread-create-button" type="button">NEW</button>
    <div id="threads-list" class="space-y-2"></div>
  </section>
</aside>
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_left_column_uses_retro_panels_with_brand_project_thread_ids -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html
git commit -m "feat(vm-ui): retrofit left workspace column to retro terminal panels"
```

### Task 3: Migrar coluna central/direita e manter Studio + Workflow + Ops

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/index.html`

**Step 1: Write the failing test**

Add this test:

```python
def test_vm_index_main_and_right_columns_keep_all_runtime_anchors_in_retro_layout() -> None:
    html = Path("09-tools/web/vm/index.html").read_text(encoding="utf-8")
    assert re.search(
        r'id="vm-shell-main".*id="studio-toolbar".*id="studio-create-plan-button".*id="studio-devmode-toggle".*id="studio-artifact-preview".*id="studio-stage-progress".*id="thread-mode-form".*id="thread-modes-list".*id="timeline-list".*id="workflow-run-form".*id="workflow-run-detail-list"',
        html,
        re.S,
    )
    assert re.search(
        r'id="vm-shell-right".*id="tasks-list".*id="approvals-list".*id="workflow-artifacts-list".*id="workflow-artifact-preview"',
        html,
        re.S,
    )
    assert "Task_Board" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_main_and_right_columns_keep_all_runtime_anchors_in_retro_layout -v`  
Expected: FAIL until main/right structure and labels are fully migrated.

**Step 3: Write minimal implementation**

In `09-tools/web/vm/index.html`, implement retro center/right wrappers and keep IDs:

```html
<main id="vm-shell-main" class="col-span-12 lg:col-span-6 space-y-6" aria-label="Workspace Content">
  <div id="ui-error-banner" class="hidden ..."></div>
  <section id="studio-toolbar" class="border border-primary ...">...</section>
  <section class="border border-primary ..."><pre id="studio-artifact-preview">...</pre></section>
  <section class="border border-primary ..."><div id="studio-stage-progress"></div></section>
  <section class="vm-dev-only border border-primary ...">
    <form id="thread-mode-form">...</form>
    <div id="thread-modes-list"></div>
    <div id="timeline-list"></div>
    <form id="workflow-run-form">...</form>
    <div id="workflow-profile-preview-list"></div>
    <div id="workflow-runs-list"></div>
    <div id="workflow-run-detail-list"></div>
  </section>
</main>
<aside id="vm-shell-right" class="col-span-12 lg:col-span-3 space-y-6" aria-label="Workspace Operations">
  <section class="border border-primary ..."><div id="tasks-list"></div></section>
  <section class="border border-primary ..."><div id="approvals-list"></div></section>
  <section class="border border-primary ...">
    <div id="workflow-artifacts-list"></div>
    <pre id="workflow-artifact-preview"></pre>
  </section>
</aside>
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_index_main_and_right_columns_keep_all_runtime_anchors_in_retro_layout -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/index.html
git commit -m "feat(vm-ui): move studio workflow and operations anchors into retro layout"
```

### Task 4: Consolidar tokens retro em CSS e alinhar classes de acao no app.js

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_assets.py`
- Modify: `09-tools/web/vm/styles.css`
- Modify: `09-tools/web/vm/app.js`

**Step 1: Write the failing test**

Add this test:

```python
def test_vm_retro_theme_tokens_and_action_button_hooks_exist() -> None:
    css = Path("09-tools/web/vm/styles.css").read_text(encoding="utf-8")
    js = Path("09-tools/web/vm/app.js").read_text(encoding="utf-8")
    assert "--terminal-bg" in css
    assert ".scanlines" in css
    assert ".vm-terminal-btn" in css
    assert "createActionButton(label, onClick, variant" in js
    assert "vm-terminal-btn" in js
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_retro_theme_tokens_and_action_button_hooks_exist -v`  
Expected: FAIL before CSS token migration and JS button variant support.

**Step 3: Write minimal implementation**

In `09-tools/web/vm/styles.css`, add retro primitives:

```css
:root {
  --terminal-bg: #000;
  --terminal-ink: #fff;
  --terminal-dim: #1a1a1a;
  --terminal-line: #ffffff66;
}
.scanlines { /* fixed overlay */ }
.vm-terminal-btn {
  border: 1px solid var(--terminal-ink);
  background: transparent;
  color: var(--terminal-ink);
  text-transform: uppercase;
}
.vm-terminal-btn:hover {
  background: var(--terminal-ink);
  color: var(--terminal-bg);
}
```

In `09-tools/web/vm/app.js`, extend button helper:

```javascript
function createActionButton(label, onClick, variant = "default") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `vm-terminal-btn ${variant === "danger" ? "vm-terminal-btn--danger" : ""}`.trim();
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py::test_vm_retro_theme_tokens_and_action_button_hooks_exist -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/web/vm/styles.css 09-tools/web/vm/app.js
git commit -m "feat(vm-ui): add retro theme tokens and terminal action button hooks"
```

### Task 5: Blindar shell servida e executar verificacao final

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_ui_shell.py`

**Step 1: Write the failing test**

Expand `test_root_serves_stitch_shell_contract`:

```python
def test_root_serves_stitch_shell_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="vm-shell-left"' in html
    assert 'id="vm-shell-main"' in html
    assert 'id="vm-shell-right"' in html
    assert "Share+Tech+Mono" in html
    assert "class=\"scanlines\"" in html
    assert "VM Web App Event-Driven Workspace" in html
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_stitch_shell_contract -v`  
Expected: FAIL until served HTML includes retro markers.

**Step 3: Write minimal implementation**

If needed, adjust `09-tools/web/vm/index.html` imports/labels so the served root page contains all asserted markers without changing server routing.

**Step 4: Run tests to verify pass**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py -v
```

Expected: PASS in both files.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_ui_shell.py 09-tools/web/vm/index.html
git commit -m "test(vm-ui): protect served retro shell and run ui regression checks"
```

### Task 6: Verificacao completa antes de merge

**Files:**
- No file changes required unless regressions are found

**Step 1: Run workspace UI/backend smoke tests**

Run:

```bash
uv run pytest 09-tools/tests/test_vm_webapp_ui_assets.py -v
uv run pytest 09-tools/tests/test_vm_webapp_ui_shell.py -v
uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -v
```

Expected: PASS.

**Step 2: Manual functional sweep**

Run app and validate flow:
1. Brand create/select
2. Project create/select
3. Thread create/select
4. Mode add/edit/remove
5. Workflow run/detail/artifacts
6. Task comment/complete
7. Approval grant/resume
8. Studio wizard generate flow

Expected: No functional regressions.

**Step 3: Fix any failing checks minimally**

If any assertion fails, apply smallest possible change and rerun only affected tests first, then rerun full commands from Step 1.

**Step 4: Re-run full verification**

Run all commands from Step 1 again and confirm green.

**Step 5: Commit**

```bash
git add 09-tools/web/vm/index.html 09-tools/web/vm/styles.css 09-tools/web/vm/app.js 09-tools/tests/test_vm_webapp_ui_assets.py 09-tools/tests/test_vm_webapp_ui_shell.py
git commit -m "chore(vm-ui): finalize retro terminal dashboard verification"
```
