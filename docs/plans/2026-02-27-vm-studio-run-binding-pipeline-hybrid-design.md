# VM Studio Run Binding Pipeline Hybrid Design

## Status
Proposta aprovada para implementacao.

---

## 1. Objetivo

Garantir que a regressao de `run binding` (thread com runs e `activeRunId` nulo) nunca retorne sem deteccao em CI.

Estrategia escolhida: `hibrido`.

- obrigatorio em PR/push: testes deterministicos e rapidos
- opcional/noturno: browser E2E real para cobertura de UX completa

---

## 2. Problema

O bug recente mostrou que:

- frontend pode perder binding de run ativa mesmo com dados corretos da API
- suite backend sozinha nao captura regressao de apresentacao
- sem guarda de pipeline, o problema passa para smoke manual

---

## 3. Direcao

## 3.1 Guarda obrigatoria (PR)

Adicionar gates deterministicos no workflow de smoke:

1. backend API contract para listagem de runs
2. frontend Vitest focando run binding
3. build frontend

Requisito: rodar em poucos minutos e falhar cedo.

## 3.2 Guarda opcional (nightly / manual)

Adicionar job/browser E2E para fluxo real:

- abrir Studio
- selecionar contexto
- validar auto-selecao de run com `activeRunId` nulo
- validar preview carregado e ausencia do empty state incorreto

Esse job nao bloqueia PR. Ele serve para detectar drift de integracao UI+backend.

---

## 4. Arquitetura de Pipeline

## 4.1 Workflow principal

Arquivo:

- [vm-webapp-smoke.yml](/Users/jhonatan/Repos/marketing-skills/.github/workflows/vm-webapp-smoke.yml)

Mudancas:

- manter bloco Python existente
- adicionar setup Node para `09-tools/web/vm-ui`
- rodar Vitest especifico de run binding
- rodar build frontend

## 4.2 Workflow opcional E2E browser

Novo arquivo:

- `.github/workflows/vm-studio-run-binding-nightly.yml`

Triggers:

- `schedule` (nightly)
- `workflow_dispatch`

Comportamento:

- sobe backend local no job
- sobe UI (ou usa root servido pelo backend)
- roda suite Playwright do fluxo de run binding
- publica artifacts de trace/screenshot

---

## 5. Cobertura de Testes

## 5.1 Deterministica (obrigatoria)

Frontend:

- [WorkspaceRunBinding.test.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/workspace/WorkspaceRunBinding.test.tsx)

Backend:

- teste em `test_vm_webapp_api_v2.py` ou arquivo dedicado garantindo campos da listagem:
  - `request_text`
  - `requested_mode`
  - `effective_mode`

Build:

- `npm run build` em `09-tools/web/vm-ui`

## 5.2 Browser E2E (opcional)

Novo teste Playwright sugerido:

- `09-tools/web/vm-ui/e2e/run-binding.spec.ts`

Asserts:

- nao mostrar "Ainda nao existe uma versao ativa para este job" quando existem runs
- versao ativa renderizada automaticamente
- preview principal visivel

---

## 6. Criterios de Sucesso

- PR falha automaticamente se regressao de run binding reaparecer
- dados de listagem de runs ficam protegidos por teste de contrato
- nightly/browser produz evidencia (screenshot/trace) sem bloquear dev velocity

---

## 7. Riscos e Mitigacoes

Risco: aumento do tempo do workflow principal.

Mitigacao:

- rodar apenas testes frontend focados (run binding + smoke necessario)
- manter browser completo fora do caminho critico de PR

Risco: flakiness de browser E2E.

Mitigacao:

- usar retries curtos + traces
- limitar asserts ao comportamento essencial de binding
