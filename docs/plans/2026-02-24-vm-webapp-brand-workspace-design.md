# VM Web App Brand Workspace Design

## Context

O estado atual do VM Web App funciona para prova de conceito (chat + runs), mas ainda parece mockup para operação diária.  
A necessidade agora é transformar em aplicativo real com navegação por marca, gestão explícita de threads e fluxo consistente para Kimi.

## Goal

Evoluir o app para um **Brand Workspace por aba de marca**, com threads reais por produto, onde chat e run compartilham a mesma thread ativa.

## Product Decisions (MVP)

- Navegação: `Brand Workspace` por aba de marca.
- Gestão de thread: `criar`, `selecionar`, `listar histórico`, `encerrar`.
- Regra de domínio: thread pertence a **1 produto**; UI filtra por produto ativo.
- Criação de thread: apenas botão explícito `Nova Thread`.
- Integração com Kimi: chat e run sempre usam a mesma thread ativa.
- Cadastro de marca/produto no MVP: somente listar/selecionar entidades já existentes.

## Information Architecture

Dentro da aba da marca:

1. Toolbar com seletor de produto + botão `Nova Thread`.
2. Coluna `Threads` (filtro por produto ativo).
3. Painel `Chat` da thread ativa.
4. Painel `Runs` da thread ativa, com timeline e gates em tempo real (SSE).

## Data Model

Adicionar entidade `Thread` persistida:

- `thread_id` (pk)
- `brand_id` (required)
- `product_id` (required)
- `title`
- `status` (`open` | `closed`)
- `created_at`, `updated_at`
- `last_activity_at`

## API Design (MVP)

- `GET /api/v1/threads?brand_id=...&product_id=...`
- `POST /api/v1/threads`
- `POST /api/v1/threads/{thread_id}/close`
- `GET /api/v1/threads/{thread_id}/messages`

Fluxo principal:

- Selecionar marca/produto -> listar threads.
- `Nova Thread` -> criar + selecionar ativa.
- Chat e Run enviam `thread_id` ativo.
- Selecionar thread -> recarregar mensagens + runs.

## UI Strategy (shadcn-like in Vanilla)

Sem migração para React/Tailwind neste estágio.  
Aplicar padrões visuais shadcn-like em HTML/CSS/JS atual:

- Tabs de marca
- Cards
- Buttons (default/secondary/ghost/destructive)
- Inputs/selects com foco consistente
- Badges de status (`open`, `closed`, `running`, `waiting_approval`, `completed`)
- Empty states e feedback local por painel

## State Rules and Error Handling

- Sem produto/thread ativa: desabilitar chat e start run.
- Thread `closed`: bloquear novos envios e novas execuções.
- Erros por painel com retry local.
- Loading por painel com placeholders curtos.
- Approve mantém trava de request em andamento (já existente).

## Test Strategy

Backend:

- API de threads (listar, criar, encerrar, mensagens).
- Filtro por `brand_id + product_id`.
- Bloqueio de chat/run para thread encerrada.

Frontend:

- Estrutura de abas/cards presente.
- Troca de marca/produto recarrega threads.
- `Nova Thread` cria e seleciona ativa.
- Seleção de thread recarrega chat+runs.
- Thread encerrada desabilita input/run.

## Done Criteria

1. Workspace por aba de marca funcional.
2. Threads reais persistidas e filtradas por produto.
3. Chat e run compartilham sempre a thread ativa.
4. Histórico troca corretamente ao mudar thread.
5. Thread encerrada não aceita novas interações.
6. UI consistente no estilo shadcn-like mantendo stack atual.
7. Testes novos e suíte existente passando.
