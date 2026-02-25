# VM Webapp Plataforma Completa Parallel Execution (3 Agents)

> **For Claude:** REQUIRED SUB-SKILL in each parallel session: Use superpowers:executing-plans.

**Goal:** Executar o plano da plataforma completa em 3 agentes paralelos com minimo conflito de arquivos e checkpoints de integracao.

**Base Plan:** `docs/plans/2026-02-25-vm-webapp-plataforma-completa.md`

---

## 1) Estrategia de Paralelizacao

- Paralelizar por dominio tecnico, nao por ordem numerica de tasks.
- Rodar em ondas para respeitar dependencias de contexto e runtime.
- Definir ownership forte de arquivos por agente para evitar conflito.

## 2) Ownership por Agente

### Agent A - Domain + API Contracts

**Ownership principal:**
- `09-tools/vm_webapp/models.py`
- `09-tools/vm_webapp/repo.py`
- `09-tools/vm_webapp/projectors_v2.py`
- `09-tools/vm_webapp/commands_v2.py`
- `09-tools/vm_webapp/api.py`
- testes de dominio/API v2 novos

**Tasks do plano-base:**
- Task 1
- Task 2
- Task 3
- Task 11

### Agent B - Runtime + Resilience + Integration + E2E

**Ownership principal:**
- `09-tools/vm_webapp/workflow_runtime_v2.py`
- `09-tools/vm_webapp/workflow_profiles.py`
- `09-tools/vm_webapp/observability.py`
- `09-tools/tests/test_vm_webapp_platform_e2e.py`
- integracao final no runtime de tool executor e learning ingestion

**Tasks do plano-base:**
- Task 4
- Task 5
- Task 8 (parte de integracao no runtime)
- Task 10 (parte de integracao no runtime)
- Task 12
- Task 13

### Agent C - Tooling + RAG Modules

**Ownership principal:**
- `09-tools/vm_webapp/tooling/*`
- `09-tools/vm_webapp/rag/*`
- `09-tools/vm_webapp/learning.py`
- `09-tools/vm_webapp/memory.py`
- testes de tooling/RAG/learning novos

**Tasks do plano-base:**
- Task 6
- Task 7
- Task 8 (modulos tooling, sem alterar runtime)
- Task 9
- Task 10 (modulo learning, sem alterar runtime)

## 3) Ondas de Execucao

### Wave 1 (rodar em paralelo)

- Agent A: Tasks 1-3
- Agent B: Task 5
- Agent C: Tasks 6-7-9

**Checkpoint 1 (obrigatorio):**
- Reunir PRs/commits de A, B, C
- Integrar primeiro C, depois A, depois B
- Rodar regressao focal:
  - `uv run pytest 09-tools/tests/test_vm_webapp_workflow_profiles.py -q`
  - `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q`
  - `uv run pytest 09-tools/tests/test_vm_webapp_workflow_runtime_v2.py -q`

### Wave 2 (rodar em paralelo apos Checkpoint 1)

- Agent A: Task 11
- Agent B: Tasks 4, 8(runtime), 10(runtime), 12, 13
- Agent C: hardening de Task 8/10 no proprio dominio (tooling/learning), suporte de correcoes sem tocar runtime

**Checkpoint 2 (obrigatorio):**
- Integrar C, depois A, depois B
- Rodar:
  - `uv run pytest 09-tools/tests/test_vm_webapp_*.py -q`
  - `uv run pytest 09-tools/tests/test_vm_webapp_event_driven_e2e.py -q`
  - `uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -q`
  - `uv run pytest 09-tools/tests/test_vm_webapp_platform_e2e.py -q`

### Wave 3 (fechamento)

- Agent A ou Maintainer: Task 14 (README/ARCHITECTURE/release checklist)
- Validacao final e merge gate.

## 4) Setup de Worktrees e Branches

Criar 3 worktrees isolados:

```bash
git worktree add .worktrees/vm-platform-agent-a -b codex/vm-platform-agent-a
git worktree add .worktrees/vm-platform-agent-b -b codex/vm-platform-agent-b
git worktree add .worktrees/vm-platform-agent-c -b codex/vm-platform-agent-c
```

## 5) Prompt inicial de cada sessao paralela

### Sessao Agent A

```text
I'm using the executing-plans skill to implement this plan.
Execute only Agent A scope from docs/plans/2026-02-25-vm-webapp-plataforma-completa-parallel-3-agents.md.
Use docs/plans/2026-02-25-vm-webapp-plataforma-completa.md as base.
Do not touch runtime files owned by Agent B.
Stop at Checkpoint 1 and report "Ready for feedback."
```

### Sessao Agent B

```text
I'm using the executing-plans skill to implement this plan.
Execute only Agent B scope from docs/plans/2026-02-25-vm-webapp-plataforma-completa-parallel-3-agents.md.
Use docs/plans/2026-02-25-vm-webapp-plataforma-completa.md as base.
Do not modify tooling/rag modules owned by Agent C except integration points in runtime.
Stop at Checkpoint 1 and report "Ready for feedback."
```

### Sessao Agent C

```text
I'm using the executing-plans skill to implement this plan.
Execute only Agent C scope from docs/plans/2026-02-25-vm-webapp-plataforma-completa-parallel-3-agents.md.
Use docs/plans/2026-02-25-vm-webapp-plataforma-completa.md as base.
Do not modify api.py, commands_v2.py or workflow_runtime_v2.py.
Stop at Checkpoint 1 and report "Ready for feedback."
```

## 6) Regras de Integracao

- Cada agente faz commits pequenos por task.
- Sem squash durante execucao das ondas.
- Se houver conflito em arquivo fora do ownership, o agente para e reporta.
- Nao avancar para a proxima onda sem checkpoint aprovado.

## 7) Criterio de Sucesso

- 3 agentes executam em paralelo sem conflito estrutural.
- Checkpoint 1 e 2 verdes.
- E2E final cobre Brand -> Campaign -> Task -> Run -> Review -> Learning.

