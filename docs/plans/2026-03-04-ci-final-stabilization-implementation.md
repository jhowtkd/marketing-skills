# CI Final Stabilization Sprint - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir 6 gates PRE_EXISTING para atingir ≥80% taxa de verde consistente (ENCERRADO TOTAL)

**Architecture:** 2 waves em feature branch (Wave 1: correção estrutural de arquivos inexistentes; Wave 2: triagem seletiva e correção), validação via PR checks antes de merge

**Tech Stack:** GitHub Actions, YAML, pytest, npm/vitest

---

## Preparação

### Task 0: Criar feature branch

**Files:**
- Nenhum (apenas git operations)

**Step 1: Criar branch a partir de main atualizada**

```bash
git checkout main
git pull --ff-only
git checkout -b feat/ci-final-stabilization
```

**Step 2: Verificar estado limpo**

Run: `git status --short`
Expected: Vazio ou apenas arquivos não rastreados esperados

**Step 3: Commit inicial (vazio)**

```bash
git commit --allow-empty -m "chore(ci): start final stabilization sprint

Objective: Fix 6 PRE_EXISTING gates to achieve >=80% green rate.
Wave 1: 3 gates with missing test files
Wave 2: 3 gates with triage and selective fix

Refs: docs/plans/2026-03-04-ci-final-stabilization-sprint-design.md"
```

---

## Wave 1: Correção Estrutural (Arquivos Inexistentes)

### Task 1: Fix safety-autotuning-gate-v17

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml:432-434`

**Step 1: Localizar a referência quebrada**

Run: `grep -n "test_vm_webapp_api_v2_safety_tuning.py" .github/workflows/vm-webapp-smoke.yml`
Expected: Linha 433 com comando de pytest

**Step 2: Remover referência ao arquivo inexistente**

```yaml
# Em .github/workflows/vm-webapp-smoke.yml, linha 432-434
# ANTES:
          uv run pytest 09-tools/tests/test_vm_webapp_safety_autotuning.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_api_v2_safety_tuning.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_safety_tuning_audit.py -q

# DEPOIS:
          uv run pytest 09-tools/tests/test_vm_webapp_safety_autotuning.py -q
          # REMOVED: test_vm_webapp_api_v2_safety_tuning.py does not exist
          # Coverage maintained by safety_autotuning.py and safety_tuning_audit.py
          uv run pytest 09-tools/tests/test_vm_webapp_safety_tuning_audit.py -q
```

**Step 3: Validar YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/vm-webapp-smoke.yml'))"`
Expected: Sem erro

**Step 4: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): fix safety-autotuning-gate-v17 - remove missing test file

Remove reference to non-existent test_vm_webapp_api_v2_safety_tuning.py.
Coverage maintained by existing test files.

Refs: Wave 1, gate 1 of 6"
```

---

### Task 2: Fix agent-dag-gate-v20

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml:459-463`

**Step 1: Localizar a referência quebrada**

Run: `grep -n "test_vm_webapp_api_v2_agent_dag.py" .github/workflows/vm-webapp-smoke.yml`
Expected: Linha 462 com comando de pytest

**Step 2: Remover referência ao arquivo inexistente**

```yaml
# Em .github/workflows/vm-webapp-smoke.yml, linha 459-463
# ANTES:
          uv run pytest 09-tools/tests/test_vm_webapp_agent_dag.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_api_v2_agent_dag.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_agent_dag_executor.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_agent_dag_supervisor.py -q

# DEPOIS:
          uv run pytest 09-tools/tests/test_vm_webapp_agent_dag.py -q
          # REMOVED: test_vm_webapp_api_v2_agent_dag.py does not exist
          # Coverage maintained by agent_dag.py, executor.py and supervisor.py
          uv run pytest 09-tools/tests/test_vm_webapp_agent_dag_executor.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_agent_dag_supervisor.py -q
```

**Step 3: Validar YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/vm-webapp-smoke.yml'))"`
Expected: Sem erro

**Step 4: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): fix agent-dag-gate-v20 - remove missing test file

Remove reference to non-existent test_vm_webapp_api_v2_agent_dag.py.
Coverage maintained by existing test files.

Refs: Wave 1, gate 2 of 6"
```

---

### Task 3: Fix first-run-quality-gate-v12

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml:611-615`

**Step 1: Localizar a referência quebrada**

Run: `grep -n "test_vm_webapp_first_run_realculation.py" .github/workflows/vm-webapp-smoke.yml`
Expected: Linha 613 com comando de pytest

**Step 2: Remover referência ao arquivo inexistente**

```yaml
# Em .github/workflows/vm-webapp-smoke.yml, linha 611-615
# ANTES:
          uv run pytest 09-tools/tests/test_vm_webapp_first_run_realculation.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_projectors_v2.py -q

# DEPOIS:
          # REMOVED: test_vm_webapp_first_run_realculation.py does not exist
          # Coverage by test_vm_webapp_projectors_v2.py
          uv run pytest 09-tools/tests/test_vm_webapp_projectors_v2.py -q
```

**Step 3: Validar YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/vm-webapp-smoke.yml'))"`
Expected: Sem erro

**Step 4: Commit Wave 1 completa**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): fix first-run-quality-gate-v12 - remove missing test file

Remove reference to non-existent test_vm_webapp_first_run_realculation.py.
Wave 1 complete: 3 gates with missing test files fixed.

Refs: Wave 1 complete, 3 of 6 gates fixed"
```

---

## Wave 2: Triagem e Correção Seletiva

### Task 4: Fix quality-optimizer-gate-v25 (teste específico inexistente)

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml:519-524`

**Step 1: Localizar a referência ao teste específico**

Run: `grep -n "TestNightlyReportGovernanceSection" .github/workflows/vm-webapp-smoke.yml`
Expected: Linha 524 com comando de pytest

**Step 2: Remover referência ao teste específico inexistente**

```yaml
# Em .github/workflows/vm-webapp-smoke.yml, linha 519-524
# ANTES:
          uv run pytest 09-tools/tests/test_vm_webapp_quality_optimizer.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q || echo "API v2 tests completed with warnings"
          uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q
          uv run pytest 09-tools/tests/test_editorial_ops_report.py::TestNightlyReportGovernanceSection -q

# DEPOIS:
          uv run pytest 09-tools/tests/test_vm_webapp_quality_optimizer.py -q
          uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q || echo "API v2 tests completed with warnings"
          uv run pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q
          # REMOVED: TestNightlyReportGovernanceSection does not exist in test_editorial_ops_report.py
```

**Step 3: Validar YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/vm-webapp-smoke.yml'))"`
Expected: Sem erro

**Step 4: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): fix quality-optimizer-gate-v25 - remove missing test class

Remove reference to non-existent TestNightlyReportGovernanceSection.

Refs: Wave 2, gate 4 of 6"
```

---

### Task 5: Triage rollout-governance-gate-v15

**Files:**
- Inspect: Logs do último run
- Modify: `.github/workflows/vm-webapp-smoke.yml` (se necessário)

**Step 1: Coletar logs do último run**

Run: `gh run view 22668921221 --job rollout-governance-gate-v15 --log 2>&1 | tail -50`
Expected: Identificar se é arquivo inexistente, teste quebrado, ou configuração

**Step 2: Analisar e classificar**

**Caso A (arquivo inexistente):**
- Remover referência ao arquivo
- Commit com mensagem explicativa

**Caso B (teste quebrado real):**
- NÃO aplicar workaround
- Documentar em tasks/todo.md com RCA
- Escalonar para Governance Team

**Caso C (configuração/dependência):**
- Corrigir se determinístico
- Validar via PR check

**Step 3: Aplicar correção ou documentar**

Se correção aplicável:
```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): fix rollout-governance-gate-v15 - [descrição da correção]"
```

Se escalonar:
```bash
# Atualizar tasks/todo.md com RCA e próximo passo
git add tasks/todo.md
git commit -m "docs: document rollout-governance-gate-v15 failure and escalation plan

RCA: [descrição]
Escalated to: Governance Team
Next step: [ação]"
```

---

### Task 6: Triage onboarding-first-success-gate-v30

**Files:**
- Inspect: Logs do último run
- Modify: `.github/workflows/vm-webapp-smoke.yml` (se necessário)

**Step 1: Coletar logs do último run**

Run: `gh run view 22668921221 --job onboarding-first-success-gate-v30 --log 2>&1 | tail -50`
Expected: Identificar se é arquivo inexistente, teste quebrado, ou configuração

**Step 2: Analisar e classificar**

Mesmo critério do Task 5:
- Caso A: Corrigir (arquivo inexistente)
- Caso B: Escalonar (teste quebrado real)
- Caso C: Corrigir (configuração determinística)

**Step 3: Aplicar correção ou documentar**

Se correção aplicável:
```bash
git add .github/workflows/vm-webapp-smoke.yml
git commit -m "ci(smoke): fix onboarding-first-success-gate-v30 - [descrição]"
```

Se escalonar:
```bash
git add tasks/todo.md
git commit -m "docs: document onboarding-first-success-gate-v30 failure and escalation plan"
```

---

## Validação e PR

### Task 7: Push e criação de PR

**Files:**
- Nenhum (git operations)

**Step 1: Push da feature branch**

```bash
git push origin feat/ci-final-stabilization
```

**Step 2: Criar PR**

```bash
gh pr create --title "ci(smoke): final stabilization sprint - fix 6 PRE_EXISTING gates" \
  --body "## Objective
Achieve >=80% green rate by fixing 6 PRE_EXISTING failing gates.

## Changes
- Wave 1: Fix 3 gates with missing test files (safety-autotuning, agent-dag, first-run-quality)
- Wave 2: Fix/triage 3 gates (quality-optimizer, rollout-governance, onboarding-first-success)

## Validation
- [ ] PR checks pass
- [ ] No new regressions
- [ ] Green rate improves

## Evidence
[To be filled with run results]

Refs: docs/plans/2026-03-04-ci-final-stabilization-sprint-design.md"
```

---

### Task 8: Monitorar PR checks

**Files:**
- Nenhum (monitoring)

**Step 1: Aguardar PR checks**

Run: `gh pr checks --watch`
Expected: Verificar status de cada gate corrigido

**Step 2: Coletar evidências**

```bash
# Identificar run ID do PR check
gh run list --branch feat/ci-final-stabilization --limit 1

# Analisar resultado
gh run view <run_id> --json jobs --jq '[.jobs[] | {name: .name, conclusion: .conclusion}]'
```

**Step 3: Calcular taxa de verde**

```bash
gh run view <run_id> --json jobs --jq '{
  total: (.jobs | length),
  success: ([.jobs[] | select(.conclusion == "success")] | length),
  rate: (([.jobs[] | select(.conclusion == "success")] | length) / (.jobs | length) * 100 | floor)
}'
```

**Critério de merge:**
- Taxa de verde ≥75% (melhoria vs 70% baseline)
- Sem regressões em gates que estavam passando

---

### Task 9: Merge (se critérios atendidos)

**Step 1: Merge do PR**

```bash
gh pr merge --squash --delete-branch
```

**Step 2: Aguardar runs na main**

```bash
# Monitorar 3 runs consecutivos
gh run list --workflow vm-webapp-smoke.yml --branch main --limit 3
```

**Step 3: Validar critério de ENCERRADO TOTAL**

| # | Critério | Evidência |
|---|----------|-----------|
| 1 | Taxa ≥80% em 3 runs | Coletar de cada run |
| 2 | Sem regressões | Comparar com baseline |
| 3 | 6 gates corrigidos | Verificar status |
| 4 | 24-48h estável | Aguardar janela |

---

## Documentação Final

### Task 10: Atualizar baseline

**Files:**
- Modify: `docs/ci/2026-03-main-baseline.md`
- Modify: `tasks/todo.md`

**Step 1: Atualizar com resultados**

Documentar:
- Taxa de verde final
- Gates corrigidos vs escalonados
- Decisão: ENCERRADO TOTAL ou PARCIAL

**Step 2: Commit final**

```bash
git add docs/ci/2026-03-main-baseline.md tasks/todo.md
git commit -m "docs: update CI stabilization results and final status

Results: [taxa]% green rate, [X]/6 gates fixed
Decision: [ENCERRADO TOTAL/PARCIAL]

Refs: feat/ci-final-stabilization"
```

---

## Rollback Procedures

### Se regressão for detectada:

```bash
# Reverter commit específico
git revert <commit-hash>
git push origin feat/ci-final-stabilization
```

### Se taxa piorar (<70%):

```bash
# Abandonar branch e replanejar
git checkout main
git branch -D feat/ci-final-stabilization
git push origin --delete feat/ci-final-stabilization
# Documentar em tasks/todo.md e replanejar
```

---

## Summary

| Task | Gate | Tipo | Ação |
|------|------|------|------|
| 1 | safety-autotuning-v17 | Arquivo inexistente | Remover referência |
| 2 | agent-dag-v20 | Arquivo inexistente | Remover referência |
| 3 | first-run-quality-v12 | Arquivo inexistente | Remover referência |
| 4 | quality-optimizer-v25 | Teste específico inexistente | Remover referência |
| 5 | rollout-governance-v15 | Triagem | Corrigir ou escalar |
| 6 | onboarding-first-success-v30 | Triagem | Corrigir ou escalar |
| 7-10 | Validação | PR + Merge + Docs | Evidência objetiva |

**Critério de sucesso:** ≥80% green rate em 3 runs consecutivos na main.
