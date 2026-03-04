# CI Sustainment + Velocity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 3 otimizações no CI (Cache UV, Merge por Domínio, Paralelização) para reduzir duração em 20% mantendo ≥95% green.

**Architecture:** Adicionar `actions/cache@v4` para UV em jobs específicos, consolidar 24 jobs em 13 por domínio funcional, paralelizar backend/frontend com `&+wait` e validação de exit codes.

**Tech Stack:** GitHub Actions, YAML, UV, npm, bash

**Design Doc:** `docs/plans/2026-03-04-ci-sustainment-velocity-design.md`

---

## Preparação

### Task 0: Criar branch de feature

**Step 1: Criar e switch para branch**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git checkout -b feat/ci-sustainment-velocity
```

Expected: Switched to new branch

---

## Fase 1: Cache UV (Dia 1-2)

### Task 1: Identificar jobs com UV

**Files:**
- Read: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Listar jobs que usam uv**

```bash
cd /Users/jhonatan/Repos/marketing-skills
grep -n "uv run\|uv sync" .github/workflows/vm-webapp-smoke.yml | head -30
```

Expected: Lista de linhas com jobs usando UV

**Step 2: Contar jobs UV**

```bash
grep -c "uv run\|uv sync" .github/workflows/vm-webapp-smoke.yml
```

Expected: ~20 ocorrências (alguns jobs múltiplos)

---

### Task 2: Implementar cache UV em jobs piloto (3 jobs)

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Adicionar cache no job editorial-gate**

Localize o job `editorial-gate` (aprox linha ~100) e adicione APÓS checkout e ANTES de `uv sync`:

```yaml
  editorial-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # CACHE UV - ADICIONAR AQUI
      - name: Cache UV dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-py-3.12-uv-${{ hashFiles('uv.lock') }}-${{ hashFiles('pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-py-3.12-uv-
      
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      # ... resto do job
```

**Step 2: Adicionar cache no job editorial-policy-gate-v5**

Mesmo padrão, adicionar após checkout.

**Step 3: Adicionar cache no job editorial-insights-gate-v6**

Mesmo padrão, adicionar após checkout.

**Step 4: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): add UV cache to pilot jobs (editorial gates)

- Cache ~/.cache/uv with key: OS + Python 3.12 + uv.lock hash
- Applied to 3 editorial gates as pilot"
```

---

### Task 3: Expandir cache UV para todos os jobs UV

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Adicionar cache nos jobs restantes**

Para cada job que usa `uv run` ou `uv sync`, adicione o bloco de cache após `actions/checkout@v4`:

Jobs a modificar:
- editorial-copilot-gate-v13
- segmented-copilot-gate-v14
- decision-automation-gate-v16
- safety-autotuning-gate-v17
- agent-dag-gate-v20
- adaptive-escalation-gate-v21
- approval-cost-optimizer-gate-v23
- approval-learning-loop-gate-v24
- quality-optimizer-gate-v25
- online-control-loop-gate-v26
- predictive-resilience-gate-v27
- recovery-orchestration-gate-v28
- ux-task-first-redesign-gate-v29
- onboarding-first-success-gate-v30
- onboarding-activation-learning-loop-gate-v31
- onboarding-experimentation-gate-v32
- first-run-quality-gate-v12
- rollout-governance-gate-v15
- control-gates (se houver)

**Template para cada job:**
```yaml
      - uses: actions/checkout@v4
      
      - name: Cache UV dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-py-3.12-uv-${{ hashFiles('uv.lock') }}-${{ hashFiles('pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-py-3.12-uv-
```

**Step 2: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): expand UV cache to all UV-dependent jobs

- Applied cache to remaining ~15 jobs
- Consistent cache key across all jobs"
```

---

## Fase 2: Merge por Domínio (Dia 3-4)

### Task 4: Merge grupo editorial (4→1)

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Criar novo job `editorial-gates-combined`**

Substituir os jobs `editorial-gate`, `editorial-policy-gate-v5`, `editorial-insights-gate-v6`, `editorial-copilot-gate-v13` por um único job:

```yaml
  editorial-gates-combined:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Cache UV dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-py-3.12-uv-${{ hashFiles('uv.lock') }}-${{ hashFiles('pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-py-3.12-uv-
      
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      
      # Subgate: editorial
      - name: "[subgate: editorial] Test editorial backend"
        run: uv run pytest 09-tools/tests/test_vm_webapp_editorial.py -q
      
      # Subgate: editorial-policy-v5
      - name: "[subgate: editorial-policy-v5] Test editorial policy"
        run: uv run pytest 09-tools/tests/test_vm_webapp_editorial_policy_v5.py -q
      
      # Subgate: editorial-insights-v6
      - name: "[subgate: editorial-insights-v6] Test editorial insights"
        run: uv run pytest 09-tools/tests/test_vm_webapp_editorial_insights.py -q
      
      # Subgate: editorial-copilot-v13
      - name: "[subgate: editorial-copilot-v13] Test editorial copilot"
        run: |
          uv run pytest 09-tools/tests/test_vm_webapp_editorial_copilot.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_api_v2_copilot.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus_copilot.py -q
      
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: "09-tools/web/vm-ui/package-lock.json"
      
      - name: Install frontend dependencies
        working-directory: ./09-tools/web/vm-ui
        run: npm ci
      
      - name: "[subgate: editorial-copilot-v13] Test editorial copilot UI"
        working-directory: ./09-tools/web/vm-ui
        run: |
          npm run test -- --run src/features/workspace/useWorkspace.copilot.test.tsx
          npm run test -- --run src/features/workspace/components/CopilotPanel.test.tsx
      
      - name: Build frontend
        working-directory: ./09-tools/web/vm-ui
        run: npm run build
```

**Step 2: Remover jobs antigos**

Remover as definições dos 4 jobs antigos do arquivo.

**Step 3: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): merge editorial gates (4→1)

- Combined: editorial-gate + editorial-policy-v5 + editorial-insights-v6 + editorial-copilot-v13
- Each subgate clearly labeled for debuggability
- Shared setup: cache, uv sync, npm ci, build"
```

---

### Task 5: Merge grupo onboarding (3→1)

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Criar novo job `onboarding-gates-combined`**

Substituir os jobs `onboarding-first-success-gate-v30`, `onboarding-activation-learning-loop-gate-v31`, `onboarding-experimentation-gate-v32`:

```yaml
  onboarding-gates-combined:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Cache UV dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-py-3.12-uv-${{ hashFiles('uv.lock') }}-${{ hashFiles('pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-py-3.12-uv-
      
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      
      # Subgate: onboarding-first-success-v30 (backend)
      - name: "[subgate: onboarding-first-success-v30] Test onboarding backend"
        run: |
          uv run pytest 09-tools/tests/test_onboarding_api.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -k "onboarding" -q || echo "No onboarding tests in api_v2"
          uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -k "onboarding" -q || echo "No onboarding tests in prometheus"
      
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: "09-tools/web/vm-ui/package-lock.json"
      
      - name: Install frontend dependencies
        working-directory: ./09-tools/web/vm-ui
        run: npm ci
      
      # Subgate: onboarding-first-success-v30 (frontend)
      - name: "[subgate: onboarding-first-success-v30] Test onboarding UI"
        working-directory: ./09-tools/web/vm-ui
        run: |
          npm run test -- --run src/features/onboarding/telemetry.test.ts
          npm run test -- --run src/features/onboarding/funnel.v31.test.ts
          npm run test -- --run src/features/onboarding/OnboardingWizard.test.tsx
          npm run test -- --run src/features/onboarding/TemplatePicker.test.tsx
          npm run test -- --run src/features/onboarding/ContextualTour.test.tsx
      
      # Subgate: onboarding-activation-learning-loop-v31 (backend)
      - name: "[subgate: onboarding-activation-v31] Test activation backend"
        run: |
          uv run pytest 09-tools/tests/test_vm_webapp_activation_learning.py -q || echo "Activation learning tests"
      
      # Subgate: onboarding-activation-learning-loop-v31 (frontend)
      - name: "[subgate: onboarding-activation-v31] Test activation UI"
        working-directory: ./09-tools/web/vm-ui
        run: npm run test -- --run src/features/onboarding/OneClickFirstRun.test.tsx || echo "OneClickFirstRun test"
      
      # Subgate: onboarding-experimentation-v32 (frontend)
      - name: "[subgate: onboarding-experimentation-v32] Test experimentation"
        working-directory: ./09-tools/web/vm-ui
        run: |
          npm run test -- --run src/features/onboarding/ttfvTelemetry.test.ts || echo "TTFV telemetry test"
```

**Step 2: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): merge onboarding gates (3→1)

- Combined: onboarding-first-success-v30 + onboarding-activation-v31 + onboarding-experimentation-v32
- Clear subgate labels for each test group"
```

---

### Task 6: Merge grupos restantes

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Merge approval gates (2→1)**

Criar `approval-gates-combined` com `approval-cost-optimizer-v23` + `approval-learning-loop-v24`.

**Step 2: Merge safety-resilience gates (4→1)**

Criar `safety-resilience-gates-combined` com `safety-autotuning-v17` + `adaptive-escalation-v21` + `predictive-resilience-v27` + `recovery-orchestration-v28`.

**Step 3: Merge frontend gates (2→1)**

Criar `frontend-gates-combined` com `frontend-gate` + `ux-task-first-redesign-v29`.

**Step 4: Merge quality gates (2→1)**

Criar `quality-gates-combined` com `first-run-quality-v12` + `quality-optimizer-v25`.

**Step 5: Merge control gates (2→1)**

Criar `control-gates-combined` com `online-control-loop-v26` + `rollout-governance-v15`.

**Step 6: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): merge remaining gate groups

- approval-gates-combined (2→1)
- safety-resilience-gates-combined (4→1)
- frontend-gates-combined (2→1)
- quality-gates-combined (2→1)
- control-gates-combined (2→1)

Total: 24 jobs → 13 jobs (-46%)"
```

---

## Fase 3: Paralelização (Dia 5-6)

### Task 7: Implementar paralelização em job combinado (piloto)

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Modificar editorial-gates-combined para paralelização**

Substituir os steps sequenciais por paralelização com `&+wait`:

```yaml
      # Setup comum primeiro
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: "09-tools/web/vm-ui/package-lock.json"
      
      - name: Install frontend dependencies
        working-directory: ./09-tools/web/vm-ui
        run: npm ci
      
      # Paralelização: Backend + Frontend
      - name: "Run tests (parallel)"
        working-directory: ./09-tools/web/vm-ui
        run: |
          echo "::group::[parallel] Starting backend tests in background"
          (
            cd /home/runner/work/marketing-skills/marketing-skills
            uv run pytest 09-tools/tests/test_vm_webapp_editorial.py -q && \
            uv run pytest 09-tools/tests/test_vm_webapp_editorial_policy_v5.py -q && \
            uv run pytest 09-tools/tests/test_vm_webapp_editorial_insights.py -q && \
            uv run pytest 09-tools/tests/test_vm_webapp_editorial_copilot.py -q && \
            uv run pytest 09-tools/tests/test_vm_webapp_api_v2_copilot.py -q && \
            uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus_copilot.py -q
            echo $? > /tmp/backend.exit
          ) &
          BACKEND_PID=$!
          echo "Backend PID: $BACKEND_PID"
          echo "::endgroup::"
          
          echo "::group::[subgate: frontend-copilot] Running frontend tests"
          npm run test -- --run src/features/workspace/useWorkspace.copilot.test.tsx
          FRONTEND_1_EXIT=$?
          npm run test -- --run src/features/workspace/components/CopilotPanel.test.tsx
          FRONTEND_2_EXIT=$?
          echo "::endgroup::"
          
          echo "::group::[parallel] Waiting for backend"
          wait $BACKEND_PID
          BACKEND_EXIT=$(cat /tmp/backend.exit)
          echo "Backend exit code: $BACKEND_EXIT"
          echo "::endgroup::"
          
          echo "::group::[subgate: resumo]"
          echo "Backend: $BACKEND_EXIT"
          echo "Frontend copilot: $FRONTEND_1_EXIT"
          echo "Frontend panel: $FRONTEND_2_EXIT"
          echo "::endgroup::"
          
          # Falha se qualquer um falhou
          if [ $BACKEND_EXIT -ne 0 ] || [ $FRONTEND_1_EXIT -ne 0 ] || [ $FRONTEND_2_EXIT -ne 0 ]; then
            echo "ERROR: One or more test groups failed"
            exit 1
          fi
      
      - name: Build frontend
        working-directory: ./09-tools/web/vm-ui
        run: npm run build
```

**Step 2: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): add parallel execution to editorial-gates-combined

- Backend tests run in background with &
- Frontend tests run in foreground
- Explicit exit code capture for both
- Fail if any subgate fails"
```

---

### Task 8: Expandir paralelização para outros jobs combinados

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Aplicar padrão aos jobs restantes**

Aplicar o mesmo padrão de paralelização em:
- onboarding-gates-combined
- approval-gates-combined
- safety-resilience-gates-combined
- quality-gates-combined
- control-gates-combined

**Jobs que NÃO precisam de paralelização (frontend-only):**
- frontend-gates-combined (já é só frontend)

**Step 2: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): expand parallel execution to all combined gates

- Applied to: onboarding, approval, safety-resilience, quality, control
- Consistent pattern: backend & + frontend foreground + wait
- Exit code validation for all subgates"
```

---

## Fase 4: Finalização e Push (Dia 6)

### Task 9: Validar sintaxe do YAML

**Files:**
- Read: `.github/workflows/vm-webapp-smoke.yml`

**Step 1: Verificar sintaxe**

```bash
cd /Users/jhonatan/Repos/marketing-skills
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/vm-webapp-smoke.yml'))" && echo "YAML valid"
```

Expected: "YAML valid"

**Step 2: Verificar contagem de jobs**

```bash
grep -c "^  [a-z].*:" .github/workflows/vm-webapp-smoke.yml | head -1
```

Expected: ~13 jobs (era 24)

---

### Task 10: Push e Criar PR

**Step 1: Push da branch**

```bash
git push origin feat/ci-sustainment-velocity
```

**Step 2: Criar PR**

```bash
gh pr create \
  --base main \
  --head feat/ci-sustainment-velocity \
  --title "CI Sustainment + Velocity: Cache, Merge, Parallel" \
  --body "## Otimizações Implementadas

### 1. Cache UV (~30% redução em setup)
- Cache de ~/.cache/uv em todos os jobs UV-dependentes
- Chave: OS + Python 3.12 + hash(uv.lock)

### 2. Merge por Domínio (~46% redução em jobs)
- Editorial: 4→1
- Onboarding: 3→1
- Approval: 2→1
- Safety-Resilience: 4→1
- Frontend: 2→1
- Quality: 2→1
- Control: 2→1

Total: 24 jobs → 13 jobs

### 3. Paralelização (~20% redução em duração)
- Backend (pytest) em background com &
- Frontend (npm test) em foreground
- Exit codes validados explicitamente
- Falha se qualquer subgate falhar

## Validação
- [ ] Taxa de green ≥95% por 14 dias
- [ ] Duração média -20% vs baseline
- [ ] Sem falso verde detectado"
```

---

## Métricas de Sucesso

| Métrica | Baseline | Meta | Como Verificar |
|---------|----------|------|----------------|
| Taxa de green | 100% (28/28) | ≥95% | PR checks + main runs |
| Jobs por run | 24 | 13 | Contar em Actions UI |
| Duração | ~? min | -20% | `gh run list --json duration` |
| Cache hit | 0% | >80% | Logs do GitHub Actions |

---

## Rollback (se necessário)

```bash
# Reverter commits específicos
git revert <commit-hash>

# Ou reverter toda a feature branch
git revert --no-commit main..feat/ci-sustainment-velocity
git commit -m "Revert: CI optimizations causing instability"
```

---

**Plan complete and saved to `docs/plans/2026-03-04-ci-sustainment-velocity.md`.**

**Two execution options:**

**1. Subagent-Driven (this session)** - Dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
