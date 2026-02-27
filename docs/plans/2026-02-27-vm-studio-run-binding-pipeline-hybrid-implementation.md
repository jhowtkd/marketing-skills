# VM Studio Run Binding Pipeline Hybrid Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar um pipeline hibrido que impeça regressao de run binding em PR e adicione cobertura browser E2E opcional/noturna.

**Architecture:** Expandir o workflow existente de smoke com gates deterministicos de frontend/backend e criar workflow separado para browser E2E com Playwright, mantendo PR rapido e cobertura robusta.

**Tech Stack:** GitHub Actions, pytest, Vitest, Vite build, Playwright.

---

### Task 1: Garantir teste backend de contrato da listagem de runs

**Files:**
- Modify: `09-tools/tests/test_vm_webapp_api_v2.py`

**Step 1: Write the failing test**

Adicionar teste assertivo da listagem de runs:

- criar brand/project/thread
- iniciar workflow run
- chamar `GET /api/v2/threads/{thread_id}/workflow-runs`
- validar que o item inclui:
  - `request_text`
  - `requested_mode`
  - `effective_mode`

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/jhonatan/Repos/marketing-skills
PYTHONPATH=09-tools /Users/jhonatan/Repos/marketing-skills/.venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_list_workflow_runs_exposes_requested_and_effective_modes -q
```

Expected: FAIL se contrato regredir.

**Step 3: Write minimal implementation**

Se necessario, ajustar [api.py](/Users/jhonatan/Repos/marketing-skills/09-tools/vm_webapp/api.py) no endpoint `GET /v2/threads/{thread_id}/workflow-runs` para sempre preencher esses campos.

**Step 4: Run test to verify it passes**

Reexecutar comando da Step 2.

**Step 5: Commit**

```bash
git add 09-tools/tests/test_vm_webapp_api_v2.py 09-tools/vm_webapp/api.py
git commit -m "test(api-v2): enforce run list contract for requested/effective mode fields"
```

---

### Task 2: Fortalecer suite frontend de run binding

**Files:**
- Modify: `09-tools/web/vm-ui/src/features/workspace/WorkspaceRunBinding.test.tsx`

**Step 1: Write the failing test**

Adicionar caso cobrindo fallback de payload `items`:

- mock de dados de runs via shape alternativo
- assert de auto-selecao e ausencia do empty state incorreto

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui
npm run test -- --run src/features/workspace/WorkspaceRunBinding.test.tsx
```

Expected: FAIL se regressao for reintroduzida.

**Step 3: Write minimal implementation**

Ajustar mocks/fixtures e, se preciso, pequenos ajustes de robustez no frontend para cobrir ambos formatos (`runs`/`items`).

**Step 4: Run test to verify it passes**

Reexecutar comando da Step 2.

**Step 5: Commit**

```bash
git add 09-tools/web/vm-ui/src/features/workspace/WorkspaceRunBinding.test.tsx 09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts

git commit -m "test(vm-ui): harden run binding coverage for runs/items payload fallback"
```

---

### Task 3: Adicionar gate frontend no workflow principal

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Write the failing expectation**

Sem mudanca de codigo nesta etapa. Definir criterio: workflow precisa rodar frontend binding test e build.

**Step 2: Write minimal implementation**

Atualizar workflow para incluir:

- `actions/setup-node`
- install frontend deps em `09-tools/web/vm-ui`
- rodar:
  - `npm run test -- --run src/features/workspace/WorkspaceRunBinding.test.tsx`
  - `npm run build`

Manter testes Python existentes.

**Step 3: Validate workflow syntax**

Run:

```bash
cd /Users/jhonatan/Repos/marketing-skills
python - <<'PY'
import yaml, pathlib
path = pathlib.Path('.github/workflows/vm-webapp-smoke.yml')
yaml.safe_load(path.read_text())
print('ok')
PY
```

Expected: `ok`.

**Step 4: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(vm-webapp): add frontend run-binding gate to smoke workflow"
```

---

### Task 4: Criar workflow browser E2E opcional/noturno

**Files:**
- Create: `.github/workflows/vm-studio-run-binding-nightly.yml`
- Create: `09-tools/web/vm-ui/e2e/run-binding.spec.ts`
- Create: `09-tools/web/vm-ui/playwright.config.ts`
- Modify: `09-tools/web/vm-ui/package.json`

**Step 1: Write the failing test**

Criar `run-binding.spec.ts` com fluxo minimo:

- abrir Studio
- selecionar contexto seedado
- validar run ativa visivel sem selecao manual
- validar preview carregado

**Step 2: Run test to verify it fails**

Run local (quando ambiente permitir):

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui
npx playwright test e2e/run-binding.spec.ts
```

Expected: FAIL inicialmente.

**Step 3: Write minimal implementation**

- adicionar config Playwright
- adicionar script `test:e2e` no `package.json`
- criar workflow nightly com:
  - `schedule`
  - `workflow_dispatch`
  - artifact upload de traces/screenshots

**Step 4: Run test to verify it passes (ou smoke structure check)**

Se browser local indisponivel, validar:

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui
npx playwright test --list
```

Expected: spec listada sem erro de config.

**Step 5: Commit**

```bash
git add .github/workflows/vm-studio-run-binding-nightly.yml 09-tools/web/vm-ui/e2e/run-binding.spec.ts 09-tools/web/vm-ui/playwright.config.ts 09-tools/web/vm-ui/package.json

git commit -m "ci(vm-studio): add optional nightly playwright run-binding workflow"
```

---

### Task 5: Verificacao final e handoff

**Files:**
- Modify: nenhuma obrigatoria

**Step 1: Run deterministic local checks**

```bash
cd /Users/jhonatan/Repos/marketing-skills
PYTHONPATH=09-tools /Users/jhonatan/Repos/marketing-skills/.venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::test_list_workflow_runs_exposes_requested_and_effective_modes -q

cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui
npm run test -- --run src/features/workspace/WorkspaceRunBinding.test.tsx
npm run build
```

Expected: PASS.

**Step 2: Validate workflows parse**

```bash
cd /Users/jhonatan/Repos/marketing-skills
python - <<'PY'
import yaml
for p in [
  '.github/workflows/vm-webapp-smoke.yml',
  '.github/workflows/vm-studio-run-binding-nightly.yml',
]:
  with open(p, 'r', encoding='utf-8') as f:
    yaml.safe_load(f)
print('workflows ok')
PY
```

Expected: `workflows ok`.

**Step 3: Commit final de verificacao**

```bash
git commit --allow-empty -m "test(ci): verify hybrid run-binding pipeline gates"
```
