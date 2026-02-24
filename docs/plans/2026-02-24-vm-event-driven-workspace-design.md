# VM Event-Driven Workspace Design

## Context

O produto atual prova alguns blocos (chat, runs, approve), mas não resolve o fluxo operacional real de ponta a ponta para time e agentes.
Hoje a experiência ainda é nebulosa em pontos críticos: criação de marca, criação de projeto, criação/gestão de thread e coordenação humana com execução de skills/agentes.

## Goal

Construir um workspace funcional orientado a eventos, com modelo `Marca -> Projeto -> Thread`, colaboração interna no app e timeline unificada de humanos + agentes, com execução semi-automática guiada por aprovações.

## Product Decisions (Approved)

- Criação de Marca e Projeto: **dentro do app** (wizard/CRUD completo).
- Modelo de domínio: **Projeto é container da Marca** (objetivo, canais, prazos) e possui múltiplas threads.
- Colaboração: **híbrida** (pessoas + agentes).
- Comunicação do time no MVP: **somente dentro do app** (comentários, tarefas, aprovações).
- Orquestração de agentes: **semi-automática** (sistema propõe plano, humano inicia/aprova etapas).
- Primeiro fluxo ponta a ponta: **planejamento**.
- Modos de planejamento suportados: **90 dias**, **campanha única**, **editorial** (os 3 obrigatórios).
- Criação de thread: começa **genérica**; modos são escolhidos depois.
- Autenticação MVP: **sem login** (workspace único).
- Direção técnica aprovada: **replataforma com arquitetura orientada a eventos**.

## Information Architecture

Estrutura principal da aplicação:

1. `Brands` (lista + criação + edição)
2. `Projects` por marca (lista + criação + edição)
3. `Threads` por projeto (lista + criação + seleção)
4. `Thread Workspace`:
   - `Timeline` unificada (humanos + agentes + sistema)
   - `Tasks` (humanas)
   - `Approvals` (gates)
   - `Artifacts` (saídas de execução)
   - `Agent Plan` (proposta e execução)

## Domain Model (MVP)

Entidades centrais:

- `Brand`: contexto estratégico de alto nível.
- `Project`: container operacional da marca (`objective`, `channels`, `timeline`, `kpis`).
- `Thread`: unidade de trabalho; inicia genérica; recebe modos depois.
- `ThreadMode`: `plan_90d`, `single_campaign`, `editorial_plan`.
- `Task`: ação humana com responsável e status.
- `Approval`: gate explícito para avanço do fluxo.
- `Comment`: colaboração interna do time.
- `AgentPlan`: proposta de sequência de skills/agentes.
- `AgentExecutionStep`: execução de etapa por agente.

## Architecture (Event-Driven)

Componentes:

- `Command API`: recebe comandos de escrita (`create brand`, `create project`, `create thread`, `approve`, etc.).
- `Event Store` (append-only): fonte de verdade imutável.
- `Orchestrator`: reage a eventos e decide próximos passos humanos/agentes.
- `Agent Runtime`: executa skills/agentes e publica eventos de progresso e resultado.
- `Projectors`: materializam read models para consumo da UI.
- `Read API`: expõe visões prontas para a interface.
- `Unified Timeline`: agregação cronológica de eventos humanos + agentes + sistema.

Princípios operacionais:

- Toda mutação vira evento.
- UI lê apenas read models/projeções.
- Aprovação humana é gate formal de workflow.

## Event Contracts (MVP)

Envelope mínimo por evento:

- `event_id`
- `event_type`
- `aggregate_type`
- `aggregate_id`
- `brand_id`, `project_id`, `thread_id` (quando aplicável)
- `actor_type` (`human` | `agent` | `system`)
- `actor_id`
- `correlation_id`, `causation_id`
- `payload_json`
- `occurred_at`

Eventos iniciais esperados:

- `BrandCreated`, `BrandUpdated`
- `ProjectCreated`, `ProjectUpdated`
- `ThreadCreated`, `ThreadModeAdded`
- `AgentPlanProposed`, `AgentPlanStarted`
- `ApprovalRequested`, `ApprovalGranted`, `ApprovalRejected`, `ApprovalExpired`
- `TaskCreated`, `TaskCompleted`, `CommentAdded`
- `AgentStepStarted`, `AgentStepCompleted`, `AgentStepFailedTemporary`, `AgentStepFailedPermanent`

## API Design (v2, Command + Read)

Command endpoints (escrita):

- `POST /api/v2/brands`
- `POST /api/v2/projects`
- `POST /api/v2/threads`
- `POST /api/v2/threads/{thread_id}/modes`
- `POST /api/v2/threads/{thread_id}/agent-plan/propose`
- `POST /api/v2/threads/{thread_id}/agent-plan/start`
- `POST /api/v2/approvals/{approval_id}/grant`
- `POST /api/v2/tasks/{task_id}/comment`
- `POST /api/v2/tasks/{task_id}/complete`

Read endpoints (consulta):

- `GET /api/v2/brands`
- `GET /api/v2/projects?brand_id=...`
- `GET /api/v2/threads?project_id=...`
- `GET /api/v2/threads/{thread_id}/timeline`
- `GET /api/v2/threads/{thread_id}/tasks`
- `GET /api/v2/threads/{thread_id}/approvals`
- `GET /api/v2/threads/{thread_id}/artifacts`

## Primary User Flow (Planning)

1. Criar Marca no app.
2. Criar Projeto na marca (objetivo, canais, prazos, KPIs).
3. Criar Thread genérica no projeto.
4. Selecionar modos de planejamento (um ou mais entre 90 dias, campanha, editorial).
5. Sistema propõe plano de agentes (etapas + dependências + gates).
6. Time comenta, cria/resolve tarefas e aprova etapas no app.
7. Agentes executam após ação humana de início/aprovação.
8. Timeline da thread concentra histórico auditável completo.

## State Rules and Reliability

- Consistência forte no command side por agregado com versionamento otimista.
- Consistência eventual no read side (projeções).
- Comandos mutáveis com `idempotency_key` obrigatória.
- Conflito de versão retorna `409` com instrução de refresh/retry.
- Retries com backoff para falhas transitórias de agente.
- Falha permanente de agente abre tarefa humana automaticamente.
- Eventos não processados vão para `dead_letter_events`.

## Error Handling

- Duplicidade de start/approve bloqueada por idempotência + regra de estado.
- Aprovação fora de contexto retorna `409`.
- Leitura atrasada nunca apaga operação; somente pode atrasar renderização.
- Operações críticas publicam eventos explícitos de falha com motivo.

## Testing Strategy

Backend:

- Unit para validações de comando/transição.
- Integration para event store e ordem por stream.
- Integration para projectors e read models.
- Integration para orchestrator em cenários com gates.
- API E2E cobrindo fluxo `marca -> projeto -> thread -> modos -> proposta -> aprovação -> execução`.

Frontend:

- E2E do fluxo de criação (marca/projeto/thread).
- E2E da colaboração interna (comentários/tarefas/aprovações).
- E2E da timeline unificada e atualização em tempo real.

Regressões obrigatórias:

1. Clique duplo não duplica start/approve.
2. `409` por conflito é recuperável via refresh/retry.
3. Falha permanente de agente cria tarefa humana.
4. Ordem da timeline permanece coerente.
5. Thread genérica aceita modos posteriores sem perder histórico.

## Done Criteria

1. Marca e Projeto podem ser criados/geridos no app.
2. Thread genérica pode ser criada e evoluída com os 3 modos de planejamento.
3. Plano de agentes é proposto automaticamente e executado de forma semi-automática.
4. Colaboração do time ocorre integralmente no app (comentários, tarefas, aprovações).
5. Timeline unificada humanos+agentes auditável por thread.
6. Event store append-only com projeções funcionais.
7. Testes críticos de fluxo e confiabilidade passando.
