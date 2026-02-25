# VM Webapp Studio Guided Design

## Context

O VM Web App (v2) tem uma base técnica forte (event store + commands v2 + projectors + idempotency + workflow runtime por thread/run), mas a UI atual expõe o modelo interno e se comporta como um console de debug:

- O usuário vê `event_type`, IDs (`thread_id`, `run_id`), “modes”, JSON de `skill_overrides`, manifests e logs.
- O “conteúdo” (artefatos) é secundário e opaco (lista + preview cru).
- O caminho para gerar valor tem fricção alta (muitos passos antes de ver resultado).
- Há inconsistência de naming (`Product` no ORM vs “Projects” na UI e read models).
- Feedback é via polling e falta sensação de progresso durante runs.

## Goal

Transformar a UI em um **Studio de Criação** (Guided-first) para markeiros/criadores:

- Entregar um “golden path” (3–5 cliques) até um plano/calendário utilizável.
- Tornar **conteúdo/artefatos** o centro da experiência (preview, ações, iteração).
- Esconder complexidade técnica por padrão e oferecer **Dev Mode** para debug.
- Preservar os contratos atuais do backend `/api/v2/*`, idempotency e engine event-driven.

## Non-Goals (MVP)

- Replataforma para React/Next/Vue.
- Mudanças de schema que exijam migração.
- Autenticação/login multi-tenant.
- “Publicação” nativa (agendamento em redes sociais) no MVP.

## Approved Product/Scope Decisions

1. Estratégia: **Guided-first em cima da UI atual** (`09-tools/web/vm/`), preservando `app.js` como controller.
2. UX: **Studio default + Dev Mode toggle** (console técnico fica opt-in).
3. Golden path: **Brand -> Project -> Create Plan (wizard) -> Preview/Ações**.
4. Playbooks (MVP): **`plan_90d`** e **`content_calendar`** (cards via `/api/v2/workflow-profiles`).
5. Naming: **Renomear `Product` -> `Project` no código**, mantendo `__tablename__ = "products"` (sem migração).
6. Realtime: **Phase 1 mantém polling**; Phase 2 considera SSE para runs v2.

## Domain Model (Produto) e Mapeamento Técnico

O front fala em entidades de produto; o backend mantém implementação atual:

- **Brand**: `BrandView`
- **Project/Campaign**: `ProjectView` (no ORM ainda existe tabela `products`)
- **Plan**: `Thread` (o usuário vê como “Plano”)
- **Version**: `Run` (`workflow run` por thread)
- **Deliverables**: `Artifacts` por stage/run
- **Pendências**: `Approvals` e `Tasks` (ações humanas)

## Information Architecture (UI)

Base: shell 3-colunas do workspace em `09-tools/web/vm/index.html`.

### Left (Navigation)
- Brands + Projects (CRUD básico), como hoje.

### Center (Studio)
Superfície default (sem dados técnicos):

- Header do plano: título, status humano, CTAs (Criar plano, Reexecutar, Exportar).
- Progresso por etapas (stage progress) com labels humanas.
- Tabs:
  - **Visão geral** (MVP: resumo + highlights)
  - **Calendário** (MVP: lista ordenada; evolui para semana/mês)
  - **Documentos** (artefatos em Markdown renderizado/preview)
  - **Histórico** (versões/runs + timeline simplificada)

### Right (Actions / Inbox)
- “Pendências” (approvals + tasks) com CTAs claros.
- Export/Copy/Download (quando aplicável).

### Dev Mode (toggle)
Exibe superfícies técnicas sem poluir o Studio:

- Timeline crua (`event_type`, timestamps)
- IDs completos (`thread_id`, `run_id`)
- JSON `skill_overrides`
- Run detail e manifests (quando necessário)

## Primary User Flows

### 1) Criar um plano (golden path)
1. Selecionar Brand e Project.
2. Clicar “Criar plano”.
3. Wizard:
   - Brief (produto, público, objetivo, canais, tom, período).
   - Escolha do playbook (cards: Plano 90d / Calendário rápido).
   - Confirmar e “Gerar”.
4. App cria Thread e inicia um Run por baixo dos panos.
5. Usuário acompanha progresso e vê preview quando o primeiro artefato estiver disponível.

### 2) Aprovação (quando gate existe)
1. Run entra em `waiting_approval`.
2. Right column mostra “Revisar estratégia” (Approval) com CTA “Aprovar”.
3. Ao aprovar, o workflow retoma e segue até `completed`/`failed`.

### 3) Iteração/versões
1. Usuário ajusta brief/refina.
2. Nova execução gera um novo `run_id` (nova “versão” do plano).
3. Histórico mostra runs anteriores (sem sobrescrever).

## API / Data Needs (Phase 1: sem mudanças)

Usar endpoints existentes:

- Playbooks: `GET /api/v2/workflow-profiles`
- CRUD: `GET/POST/PATCH /api/v2/brands`, `/api/v2/projects`, `/api/v2/threads`
- Modos: `POST /api/v2/threads/{thread_id}/modes`
- Runs: `POST /api/v2/threads/{thread_id}/workflow-runs`, `GET /api/v2/threads/{thread_id}/workflow-runs`
- Run detail: `GET /api/v2/workflow-runs/{run_id}`
- Artifacts: `GET /api/v2/workflow-runs/{run_id}/artifacts`, `GET /api/v2/workflow-runs/{run_id}/artifact-content`
- Timeline/Inbox: `GET /api/v2/threads/{thread_id}/timeline`, `/tasks`, `/approvals`

Optional (Phase 2): endpoint agregado “content plan view” para evitar parsing no front.

## Status/Labels (UX)

Mapeamento de status para labels humanas:

- `queued` -> “Em fila”
- `running` -> “Gerando…”
- `waiting_approval` -> “Aguardando revisão”
- `completed` -> “Pronto”
- `failed` -> “Falhou”

Stages: usar `workflow_profiles.yaml` como fonte de ordem + `approval_required`.

## Error Handling

- Erros de API entram em banner não-bloqueante (sem resetar seleção).
- Writes sempre com `Idempotency-Key` (já existente).
- Dev Mode mantém detalhes do erro (payload/status) quando útil.

## Testing Strategy (MVP)

- Expandir testes de assets UI para:
  - Garantir compatibilidade de IDs legados usados por `app.js`.
  - Garantir presença de containers do Studio e Dev Mode toggle.
- Suite do `vm_webapp` deve ficar verde após renomeação `Product` -> `Project` (sem migração).

## Phasing

### Phase 0: Naming + consistência
- `Product` -> `Project` no código e labels/UI consistentes (“Project/Campaign”).

### Phase 1: Studio MVP (Guided-first)
- Wizard + playbook cards + preview grande de artefatos.
- Dev Mode toggle (timeline/IDs/overrides opt-in).
- Pendências (tasks/approvals) com CTA claro.
- Sem mudanças no backend.

### Phase 2: Realtime + renderização + agregação
- Realtime para runs v2 (SSE) e/ou redução de polling.
- Markdown renderizado com segurança (sanitização).
- Endpoint agregado para “overview/calendar” se necessário.

