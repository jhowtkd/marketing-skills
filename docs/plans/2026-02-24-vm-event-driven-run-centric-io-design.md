# VM Event-Driven Run-Centric IO Design

## Context

A base event-driven do workspace já existe (Brand -> Project -> Thread, timeline, aprovações e comandos v2), porém o fluxo principal de execução ainda não entrega output operacional versionado por etapa.

Hoje há eventos e artefatos simples, mas o produto ainda não opera como workflow explícito de input/output com rastreabilidade completa por execução.

## Goal

Implementar um workflow real no app em que cada pedido na thread dispara uma execução (`run`) que gera artefatos concretos em arquivo (`.md`, `.json`, etc.) com versionamento por etapa e rastreabilidade no timeline.

## Product Decisions (Approved)

- Prioridade: evolução de produto focada em integração real de workflow input/output.
- Fluxo MVP escolhido: `pedido em thread (chat) -> execução de agentes -> output real`.
- Output MVP obrigatório: artefatos em arquivo no workspace com versionamento por etapa.
- Abordagem arquitetural aprovada: **run-centric**.

## Architecture

### Run-Centric Execution Unit

Cada pedido de execução cria um `run_id` único vinculado à thread. O run é decomposto em etapas (`stages`) pelo orquestrador, e cada etapa produz arquivos de saída de forma imutável (sem sobrescrever execuções anteriores).

### Filesystem Contract

Estrutura alvo por run:

- `runtime/vm/runs/<run_id>/run.json`
- `runtime/vm/runs/<run_id>/stages/<ordem>-<stage_key>/manifest.json`
- `runtime/vm/runs/<run_id>/stages/<ordem>-<stage_key>/input.json`
- `runtime/vm/runs/<run_id>/stages/<ordem>-<stage_key>/output.json`
- `runtime/vm/runs/<run_id>/stages/<ordem>-<stage_key>/artifacts/*`

### Artifact Manifest Contract

`manifest.json` por etapa deve registrar:

- `stage_key`, `stage_position`, `attempt`, `status`
- `started_at`, `finished_at`
- `thread_id`, `run_id`, `event_id`
- `artifacts[]` com `path`, `kind`, `sha256`, `size`

### Event + Read-Model Alignment

- Timeline continua como trilha auditável oficial.
- Arquivos no workspace são a fonte de output operacional.
- Eventos de run/etapa e metadados de artefatos alimentam read models para a UI.

## Components and Data Flow

1. Usuário envia pedido de execução na thread.
2. API registra comando/evento de início de run.
3. Orquestrador cria etapas planejadas e inicia execução.
4. Runtime executa etapa e produz `output.json` + arquivos em `artifacts/`.
5. `Artifact Writer` persiste saída de forma atômica e atualiza manifests.
6. Orquestrador emite eventos de sucesso/falha por etapa.
7. Projectors atualizam visões de runs/etapas/artefatos.
8. UI mostra lista de runs, etapas, status e links de artefatos.

## State Model and Reliability

Estados canônicos de run:

- `queued`
- `running`
- `waiting_approval`
- `completed`
- `failed`
- `canceled`

Regras:

- Uma thread não deve iniciar run concorrente sem política explícita de fila.
- Reexecução da mesma thread gera novo `run_id` (nunca sobrescreve run anterior).
- Falha de etapa gera estado `failed` com metadados (`error_code`, `error_message`, `retryable`).
- Retry incrementa `attempt` da etapa sem perda de histórico anterior.

## Validation and Error Handling

### Input Validation

- Thread deve existir e estar `open`.
- Payload de etapa deve cumprir contrato mínimo (`input.json` válido).

### Atomic Persistence

- Escrita em arquivo temporário e `rename` atômico no destino final.
- `manifest.json` só é confirmado após escrita completa dos artefatos.

### Failure Semantics

- Em falha: `StageFailed` + atualização de status de run.
- Etapas concluídas não são invalidadas por falha posterior.
- Outputs existentes não são apagados.

## UI/UX Scope (MVP)

Novo painel no workspace de thread para execução:

- Lista de runs por thread (status + timestamps).
- Lista de etapas por run (status, tentativa, duração).
- Lista de artefatos por etapa com acesso ao conteúdo.

A timeline deve refletir os principais marcos:

- `RunStarted`
- `StageStarted`
- `StageCompleted`/`StageFailed`
- `RunCompleted`/`RunFailed`
- `ArtifactPublished`

## Testing Strategy

### Unit

- Escrita atômica e hashing do `Artifact Writer`.
- Transições de estado de run/etapa e tentativas.

### Integration

- API de start/list para runs, stages e artifacts.
- Projeções consistentes com eventos emitidos.
- Persistência física de arquivos por etapa.

### E2E

- Pedido na thread gera run completo com artefatos em disco.
- Reexecução na mesma thread preserva runs antigos.

### Regression Guard

- Suite existente do `vm_webapp` permanece verde.

## Done Criteria

1. Pedido de execução em thread cria `run_id` e etapas.
2. Cada etapa concluída gera `manifest.json`, `output.json` e artefatos reais.
3. UI mostra runs/etapas/artefatos por thread.
4. Timeline mantém rastreabilidade coerente do workflow.
5. Reexecução não sobrescreve histórico anterior.
6. Testes de unidade, integração e E2E cobrindo fluxo MVP passam.
