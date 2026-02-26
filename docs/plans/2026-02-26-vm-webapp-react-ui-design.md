# VM Webapp React UI Replatform Design

## Context

O VM Web App hoje serve uma UI estática em `09-tools/web/vm/` (HTML + CSS + JS vanilla) diretamente no root (`GET /`) via `FastAPI StaticFiles` em `09-tools/vm_webapp/app.py`.

Essa UI consome endpoints existentes em `/api/v2/*` (definidos em `09-tools/vm_webapp/api.py`) e já cobre o fluxo principal de produto:

- Brands -> Projects -> Threads (planos) -> Workflow runs -> Artifacts
- Inbox operacional (Tasks + Approvals)
- “Studio” (wizard guided-first) e “Dev Mode” (toggle persistido)

Existe também um asset de referência visual gerado por Stitch (HTML + PNG) em:

- `08-output/stitch/17545300329362275848/efc2a1c17c924fe7a0f20787bd536adf.html`
- `08-output/stitch/17545300329362275848/efc2a1c17c924fe7a0f20787bd536adf.png`

Este design registra a decisão de replatform (Vite + React + TS + Tailwind) com estilo “dashboard moderno” inspirado nesse Stitch (alta fidelidade com liberdade).

## Goals

- Substituir a UI atual por uma UI em React (SPA estática) com **paridade funcional big-bang**.
- Manter o backend e os contratos `/api/v2/*` **inalterados** (sem migração, sem mudança de payload).
- Manter semântica de atualização atual (polling) e headers de idempotência.
- Padronizar linguagem da UI em **Português (PT-BR)**.
- Aplicar direção visual “Stitch/hybrid dashboard” com liberdade para melhorar UX e manutenção.

## Non-goals (neste estágio)

- Replatform para Next.js/SSR.
- Alterações de schema/DB, migrações, ou novos endpoints obrigatórios.
- Autenticação, multi-tenant, permissões.
- Realtime (SSE/WebSocket) como requisito (polling permanece).
- Renderização “rica” de artefatos (Markdown/HTML) sem um pipeline de sanitização bem definido.

## Decisões Aprovadas

1. **Stack**: Vite + React + TypeScript + Tailwind (compiled).
2. **Estratégia**: Big-bang parity (substituir `GET /` pela nova UI).
3. **Direção visual**: Stitch/hybrid dashboard (alta fidelidade com liberdade).
4. **Idioma**: Português como padrão (labels, botões, mensagens).
5. **Estratégia de entrega**: criar um novo frontend em pasta nova e trocar o mount no FastAPI.
6. **Build/deploy**: versionar o output `dist/` no repo para manter o deploy atual (Render) com build Python-only (`uv sync --frozen`).
7. **Dev Mode**: toggle persistido em `localStorage`, default OFF, revelando superfícies técnicas.

## Abordagem Escolhida

Criar uma nova UI em:

- `09-tools/web/vm-ui/` (fonte: Vite/React)
- `09-tools/web/vm-ui/dist/` (artefatos de build versionados)

E atualizar `09-tools/vm_webapp/app.py` para montar `StaticFiles` apontando para `09-tools/web/vm-ui/dist`.

## UX / Information Architecture

Shell 3-colunas (desktop) com stack em mobile/tablet:

- **Left (Navigation)**: Brands + Projects (criar/listar/selecionar/editar).
- **Center (Workspace)**:
  - Threads (planos): criar/listar/selecionar/editar título.
  - Studio: status humano + CTA “Criar plano” (wizard) + preview grande.
  - Workflow: input + seleção de mode + overrides + preview de workflow profile.
  - Runs: lista e detalhe da execução (status/progresso/approvals pendentes).
  - Timeline: superfície discreta; Dev Mode expande visão técnica.
- **Right (Operations / Inbox)**:
  - Tasks + Approvals com CTAs claras (Comment/Complete/Grant).
  - Artifacts list + preview (conteúdo em texto inicialmente).

## Paridade Funcional (Checklist)

### Brands

- Criar, listar, selecionar, editar nome.

### Projects

- Criar, listar por brand, selecionar, editar (name/objective/channels/due_date).

### Threads (Planos)

- Criar, listar por project, selecionar, editar título.

### Thread Modes

- Listar, adicionar.
- Editar (remove + add).
- Remover.

### Timeline

- Listar itens por thread.

### Tasks

- Listar.
- Comment.
- Complete.

### Approvals

- Listar.
- Grant.

### Workflow

- Carregar workflow profiles e preview por mode.
- Run workflow (request_text + mode + skill_overrides JSON).
- Listar runs por thread.
- Abrir detalhe do run.
- Resume quando `waiting_approval`.
- Listar artifacts por run/stage.
- Abrir artifact content no preview.

### Runtime / QoL

- Polling de runs/detalhes (~2s) mantendo sensação de progresso.
- Dev Mode toggle persistido.
- Erros de API em superfície não bloqueante (banner/toast), sem resetar seleção.
- Writes com `Idempotency-Key`.

## Contrato de API (inalterado)

UI continua consumindo os endpoints existentes (exemplos principais):

- `GET/POST/PATCH /api/v2/brands`
- `GET/POST/PATCH /api/v2/projects`
- `GET/POST/PATCH /api/v2/threads`
- `POST /api/v2/threads/{thread_id}/modes`
- `POST /api/v2/threads/{thread_id}/modes/{mode}/remove`
- `GET /api/v2/threads/{thread_id}/timeline`
- `GET /api/v2/threads/{thread_id}/tasks`
- `GET /api/v2/threads/{thread_id}/approvals`
- `GET /api/v2/workflow-profiles`
- `POST /api/v2/threads/{thread_id}/workflow-runs`
- `GET /api/v2/threads/{thread_id}/workflow-runs`
- `GET /api/v2/workflow-runs/{run_id}`
- `POST /api/v2/workflow-runs/{run_id}/resume`
- `GET /api/v2/workflow-runs/{run_id}/artifacts`
- `GET /api/v2/workflow-runs/{run_id}/artifact-content?...`
- `POST /api/v2/tasks/{task_id}/comment`
- `POST /api/v2/tasks/{task_id}/complete`
- `POST /api/v2/approvals/{approval_id}/grant`

## Modelo de Estado (Frontend)

Estado mínimo global (ex.: em `App`/store):

- Seleção ativa: `activeBrandId`, `activeProjectId`, `activeThreadId`, `activeRunId`
- `devMode` (persistido em `localStorage`)
- Caches: brands/projects/threads/profiles/runs/detail/artifacts/timeline/inbox

Regras:

- Troca de brand limpa project/thread/run ativos e recarrega dependências.
- Troca de thread reinicia polling de runs e recarrega timeline/inbox.
- Erros transientes não devem apagar seleção válida.

## Renderização de Artefatos (MVP)

No MVP, artifact content permanece **texto** (ex.: `<pre>`), evitando risco de XSS.

Se for desejado Markdown renderizado no futuro, adicionar sanitização explícita e testes de contrato de segurança antes de habilitar HTML.

## Build / Serve / Deploy

### Desenvolvimento local

- `npm install` em `09-tools/web/vm-ui`
- `npm run dev` para dev server

### Build

- `npm run build` gera `09-tools/web/vm-ui/dist`
- `dist/` é versionado no repo para deploy atual.

### Produção (Render / Managed-first)

O blueprint atual (`deploy/render/vm-webapp-render.yaml`) usa:

- `buildCommand: uv sync --frozen`
- `startCommand: uv run python -m vm_webapp serve ...`

Como não há etapa Node no buildCommand, a estratégia escolhida é servir `dist/` já versionado.

## Testes

Atualizar testes existentes para refletir o novo contrato:

- `09-tools/tests/test_vm_webapp_ui_shell.py`
  - Garantir que `GET /` serve a UI React (ex.: marker `data-vm-ui="react"`).
- `09-tools/tests/test_vm_webapp_ui_assets.py`
  - Garantir que `09-tools/web/vm-ui/dist/index.html` existe.
  - Garantir que os assets referenciados existem (`dist/assets/*`).
  - Garantir que o bundle referencia `/api/v2/*` e usa `Idempotency-Key` em writes.

## Rollout / Rollback

- Rollout: trocar `static_dir` em `09-tools/vm_webapp/app.py` para apontar para `vm-ui/dist` e manter o legado no repo (não servido).
- Rollback: reverter o mount para `09-tools/web/vm` (mudança simples e rápida).

## Riscos e Mitigações

- **`dist/` versionado**: risco de drift (fonte vs build).
  - Mitigação: adicionar um “check” de CI local (ou script) que falha se `dist/` não estiver atualizado após mudanças no frontend.
- **Polling agressivo**: risco de excesso de requests.
  - Mitigação: polling só quando houver thread selecionada; reduzir superfície (ex.: runs/detail), e considerar backoff.
- **Artefatos grandes**: preview pode travar.
  - Mitigação: lazy-load, limitar preview, oferecer download.

## Open Questions

- Dark mode: desejado como fase 2 (o Stitch tem dark). Não é requisito de paridade.
- Introduzir rota de fallback `/legacy`: evitado por enquanto para não manter dois contratos e por causa de paths absolutos do legado (`/app.js`, `/styles.css`).

