# CI Main Green Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Tornar a branch `main` consistentemente verde em 3-4 semanas, com hardening de workflows, reducao de flake e governanca explicita de gates.

**Architecture:** A execucao sera em ondas semanais por trilhas de falha, com baseline objetivo, mudancas pequenas por workflow e validacao continua em `main`. O plano separa estabilizacao tecnica (workflows e testes) de governanca operacional (owners, SLA, politica de deprecacao) para evitar regressao cronica.

**Tech Stack:** GitHub Actions (`.github/workflows/*.yml`), `gh` CLI, `pytest`, `npm/vitest`, shell scripts em `scripts/`, documentacao em `docs/` e `tasks/`.

---

### Task 1: Construir baseline de estabilidade da main

**Files:**
- Create: `docs/ci/2026-03-main-baseline.md`
- Modify: `tasks/todo.md`

**Step 1: Write the failing test**

Definir criterio de falha: nao existe baseline com classificacao de checks por frequencia e criticidade.

**Step 2: Run test to verify it fails**

Run: `test -f docs/ci/2026-03-main-baseline.md; echo $?`  
Expected: `1` (arquivo nao existe).

**Step 3: Write minimal implementation**

Criar baseline com:
- lista de workflows ativos;
- checks obrigatorios vs legados;
- historico recente de falhas (ultimos 20-50 runs);
- classificacao `PRE_EXISTING`, `NEW_REGRESSION`, `FLAKE`.

**Step 4: Run test to verify it passes**

Run: `test -f docs/ci/2026-03-main-baseline.md; echo $?`  
Expected: `0`.

**Step 5: Commit**

```bash
git add docs/ci/2026-03-main-baseline.md tasks/todo.md
git commit -m "docs(ci): add baseline for main stability hardening"
```

### Task 2: Estabilizar workflow vm-webapp-smoke (onda 1)

**Files:**
- Modify: `.github/workflows/vm-webapp-smoke.yml`
- Modify: `tasks/todo.md`

**Step 1: Write the failing test**

Registrar os subgates com falha cronica no baseline e definir alvo de correcoes.

**Step 2: Run test to verify it fails**

Run: `gh run list --workflow vm-webapp-smoke.yml --branch main --limit 20`  
Expected: presenca de falhas nos mesmos subgates criticos.

**Step 3: Write minimal implementation**

Aplicar mudancas pequenas e isoladas:
- corrigir comandos/paths quebrados;
- remover duplicidade de chamadas redundantes;
- aplicar retry apenas em pontos com flake comprovado.

**Step 4: Run test to verify it passes**

Run:
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/vm-webapp-smoke.yml'))"`
- rerun do workflow no PR de teste e validacao de subgates alvo.

Expected: YAML valido e reducao clara dos subgates falhos.

**Step 5: Commit**

```bash
git add .github/workflows/vm-webapp-smoke.yml tasks/todo.md
git commit -m "ci(smoke): stabilize chronic failing subgates"
```

### Task 3: Alinhar gates v33-v37 (onda 2)

**Files:**
- Modify: `.github/workflows/v33-ci-gate.yml`
- Modify: `.github/workflows/v34-ci-gate.yml`
- Modify: `.github/workflows/v35-ci-gate.yml`
- Modify: `.github/workflows/v36-ci-gate.yml`
- Modify: `.github/workflows/v37-ci-gate.yml`
- Modify: `tasks/todo.md`

**Step 1: Write the failing test**

Definir inconsistencias esperadas: runtime python misto, comandos divergentes e jobs duplicados.

**Step 2: Run test to verify it fails**

Run:
- `rg -n "python-version" .github/workflows/v3{3,4,5,6,7}-ci-gate.yml -S`
- `rg -n "pytest|npm run test|type-check|lint" .github/workflows/v3{3,4,5,6,7}-ci-gate.yml -S`

Expected: divergencia de padrao entre workflows.

**Step 3: Write minimal implementation**

Padronizar contratos minimos:
- mesma versao de runtime onde aplicavel;
- comandos equivalentes entre local e CI;
- nomes de jobs e gates coerentes;
- reduzir duplicidade de validacoes identicas.

**Step 4: Run test to verify it passes**

Run:
- `python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/v3*-ci-gate.yml')]"`
- execucao dos gates alterados em PR de validacao.

Expected: YAML valido e melhoria da taxa de verde nesses workflows.

**Step 5: Commit**

```bash
git add .github/workflows/v33-ci-gate.yml .github/workflows/v34-ci-gate.yml .github/workflows/v35-ci-gate.yml .github/workflows/v36-ci-gate.yml .github/workflows/v37-ci-gate.yml tasks/todo.md
git commit -m "ci(v33-v37): align runtime and gate contracts"
```

### Task 4: Formalizar governanca de gates

**Files:**
- Create: `docs/ci/gate-governance-matrix.md`
- Modify: `docs/runbooks/ci-hardening-v2.1.2.md`
- Modify: `tasks/todo.md`

**Step 1: Write the failing test**

Criterio de falha: nao existe matriz unica de ownership/SLA por gate.

**Step 2: Run test to verify it fails**

Run: `test -f docs/ci/gate-governance-matrix.md; echo $?`  
Expected: `1`.

**Step 3: Write minimal implementation**

Criar matriz com:
- gate/workflow;
- owner tecnico;
- criticidade (`critical`, `important`, `legacy`);
- SLA de resposta;
- politica de deprecacao.

**Step 4: Run test to verify it passes**

Run:
- `test -f docs/ci/gate-governance-matrix.md; echo $?`
- `rg -n "critical|important|legacy|SLA|owner" docs/ci/gate-governance-matrix.md -S`

Expected: `0` e campos obrigatorios presentes.

**Step 5: Commit**

```bash
git add docs/ci/gate-governance-matrix.md docs/runbooks/ci-hardening-v2.1.2.md tasks/todo.md
git commit -m "docs(ci): add gate governance matrix and SLA policy"
```

### Task 5: Criar observabilidade semanal de estabilidade

**Files:**
- Create: `scripts/ci_weekly_health_report.sh`
- Create: `docs/ci/weekly-health/README.md`
- Modify: `tasks/todo.md`

**Step 1: Write the failing test**

Criterio de falha: nao existe comando unico para relatorio semanal de saude da main.

**Step 2: Run test to verify it fails**

Run: `test -f scripts/ci_weekly_health_report.sh; echo $?`  
Expected: `1`.

**Step 3: Write minimal implementation**

Criar script que consolida:
- taxa de verde dos ultimos runs de `main`;
- top checks falhos;
- tempo medio de execucao;
- saida em markdown.

**Step 4: Run test to verify it passes**

Run:
- `bash scripts/ci_weekly_health_report.sh --help`
- `bash scripts/ci_weekly_health_report.sh --branch main --limit 30`

Expected: script executa e gera relatorio legivel.

**Step 5: Commit**

```bash
git add scripts/ci_weekly_health_report.sh docs/ci/weekly-health/README.md tasks/todo.md
git commit -m "chore(ci): add weekly health report script for main"
```

### Task 6: Validacao final e criterio de saida

**Files:**
- Modify: `tasks/todo.md`
- Modify: `docs/ci/2026-03-main-baseline.md`

**Step 1: Write the failing test**

Definir criterio formal de saida sem evidencias consolidadas.

**Step 2: Run test to verify it fails**

Run: `rg -n "janela continua|SLO|criterio de saida|main verde" docs/ci/2026-03-main-baseline.md -S`  
Expected: incompleto antes da consolidacao.

**Step 3: Write minimal implementation**

Consolidar evidencias finais:
- comparativo antes/depois por workflow;
- taxa de verde por semana;
- lista de riscos residuais e backlog de legado.

**Step 4: Run test to verify it passes**

Run:
- `gh run list --branch main --limit 30`
- revisao manual do baseline atualizado e checklist final no `tasks/todo.md`.

Expected: criterio de saida atendido e proposta objetiva de encerramento da iniciativa.

**Step 5: Commit**

```bash
git add docs/ci/2026-03-main-baseline.md tasks/todo.md
git commit -m "chore(ci): finalize main green hardening evidence and exit criteria"
```

