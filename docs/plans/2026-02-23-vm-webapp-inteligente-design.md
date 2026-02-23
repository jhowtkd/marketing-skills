# Design: VM Web App Inteligente (Local-First Beta -> SaaS Cloud)

**Data:** 2026-02-23
**Status:** Aprovado em brainstorming

## 1. Objetivo

Transformar este repositorio em um web app (beta local-first) que:

- suporta perfis de **Marca** (alma: `soul.md`) e **Produto** (essencia: `essence.md`);
- roda stacks (Foundation/Conversion/Traffic/Nurture) com execucao por etapas e gates de aprovacao;
- tem memoria persistente **canonico + episodico** e usa **auto-retrieval (RAG)** antes de cada geracao;
- usa **Kimi** como LLM default via endpoint **OpenAI-compatible**;
- nasce com arquitetura que migra para SaaS cloud com o minimo de reescrita (SQLite->Postgres, filesystem->object storage).

## 2. Principios

- **API-first mesmo no local:** o frontend fala com um backend HTTP, mesmo rodando em `localhost`.
- **Separacao de dominio e storage:** dominio (Brand/Product/Thread/Run) nao depende de filesystem/SQLite.
- **Fonte de verdade simples e portavel:** SQLite + filesystem no beta; export/import facil.
- **Memoria controlada:** nenhum "drift" automatico de alma/essencia; promocao para canonico e explicita.
- **Auditoria por run:** cada execucao registra contexto, decisoes e artefatos.

## 3. Escopo (V1 Beta Local-First)

- Web app com:
  - CRUD de Marca e Produto (formulario canonico + editor Markdown para nuance);
  - Chat + execucao de stacks com progresso, logs e gates de aprovacao;
  - Memoria com RAG automatico (zvec) e uma tela de "inspecao do retrieval".
- Providers:
  - LLM: Kimi (OpenAI-compatible), modelo configuravel (default `kimi-for-coding`).
- Persistencia:
  - SQLite como indice relacional;
  - filesystem como blob store local (markdown, artifacts, logs, snapshots).
- Fora de escopo V1:
  - auth/roles multi-tenant real;
  - billing;
  - execucao distribuida em fila;
  - observabilidade SaaS (ex.: tracing externo).

## 4. Entidades e Modelo de Dominio

### 4.1 Entidades Core

- **Brand (Marca)**
  - `brand_id`
  - campos canonicos (ex.: nome, publico, tom, tabus, promessa)
  - `soul.md` (nuance em markdown, livre)

- **Product (Produto)**
  - `product_id`, `brand_id`
  - campos canonicos (ex.: nome, oferta, preco, diferencial, restricoes)
  - `essence.md` (nuance em markdown, livre)

- **Thread (Iniciativa/Campanha)**
  - `thread_id`, `product_id`
  - chat + historico de runs

- **Run (Execucao de stack)**
  - `run_id`, `thread_id`, `stack_name`, `stack_path`
  - status: `running` | `waiting_approval` | `completed` | `failed`
  - stages (sequencia + status/attempts)
  - audit log (eventos) e artifacts

- **Artifact**
  - `artifact_id`, `run_id`, `relative_path`, `content_type`, `created_at`
  - conteudo markdown gerado por etapa (e/ou consolidado)

- **Decision/Feedback**
  - aprovacao/rejeicao por gate (`approval_required`)
  - feedback humano "funcionou / nao funcionou" por run/artefato
  - opcional: sugestao de promocao para canonico

### 4.2 Regras de Memoria

- **Canonico**: Brand (campos + `soul.md`) e Product (campos + `essence.md`) sao sempre injetados.
- **Episodico**: runs, artifacts, decisoes e feedback sao recuperados por RAG conforme necessidade.
- **Promocao para canonico**: somente por acao explicita do usuario (UI).

## 5. Persistencia (SQLite + Filesystem)

### 5.1 SQLite (indice)

Armazena metadados e estado:

- brands, products, threads
- runs, stages, decisions
- feedback
- catalogo de artifacts (path + metadados)

Motivo: consultas rapidas, filtros e migracao direta para Postgres no SaaS.

### 5.2 Filesystem (blob store)

Armazena conteudo e arquivos:

- `soul.md` e `essence.md`
- chat `jsonl`
- artifacts `md`
- snapshots do prompt/context pack por etapa (auditoria)
- eventos `jsonl` por run

### 5.3 Layout Proposto (beta)

Base: `runtime/vm/`

- `runtime/vm/workspace.sqlite3`
- `runtime/vm/brands/<brand_id>/brand.json`
- `runtime/vm/brands/<brand_id>/soul.md`
- `runtime/vm/brands/<brand_id>/products/<product_id>/product.json`
- `runtime/vm/brands/<brand_id>/products/<product_id>/essence.md`
- `runtime/vm/threads/<thread_id>/chat.jsonl`
- `runtime/vm/runs/<run_id>/artifacts/...`
- `runtime/vm/runs/<run_id>/events.jsonl`
- `runtime/vm/runs/<run_id>/prompt-snapshots/...`

## 6. Memoria Semantica (zvec) + RAG Automatico

### 6.1 Papel do zvec

O `zvec` e um indice semantico embutido (in-process) usado para:

- buscar trechos relevantes de `soul/essence`, artifacts e chat;
- reduzir contexto enviado ao LLM mantendo relevancia.

SQLite/filesystem continuam sendo fonte de verdade.

### 6.2 O que entra no indice

Indexar por `brand_id`, `product_id`, `thread_id` e `run_id`:

- `soul.md` e campos canonicos da marca
- `essence.md` e campos canonicos do produto
- artifacts markdown (por etapa)
- decisoes de gate + feedback "funcionou/nao funcionou"
- mensagens do chat (opcional por politica de privacidade local)

### 6.3 Chunking

Dividir markdown em chunks por:

- headings (H2/H3) e paragrafos
- tamanho maximo de caracteres (limite configuravel)

Cada chunk vira um documento com metadados e texto.

### 6.4 Auto-retrieval (antes de cada geracao)

Passos:

1. Construir query de retrieval:
   - pedido do usuario + `stage_id` + nomes de marca/produto
2. Buscar top-k no zvec:
   - com filtros por `brand_id`, `product_id` e opcionalmente `thread_id`
3. Montar **Context Pack** e chamar o Kimi:
   - sempre inclui canonico (alma/essencia)
   - inclui apenas snippets recuperados (episodico)

### 6.5 Context Pack (formato logico)

- **System/Guardrails**
- **Brand Canonical**
  - campos canonicos + `soul.md`
- **Product Canonical**
  - campos canonicos + `essence.md`
- **Retrieved Memory (top-k)**
  - lista de snippets com origem (artifact/run/chat), timestamp e score
- **Stage Contract**
  - instrucoes de saida (arquivo esperado, formato markdown, criterios)
- **User Request**

## 7. LLM Provider (Kimi OpenAI-Compatible)

### 7.1 Default

- Base URL: `https://api.kimi.com/coding/v1`
- Model: configuravel (default `kimi-for-coding`)

### 7.2 Contrato do Provider

Criar interface `LLMProvider` com:

- `generate(messages, *, model, temperature, max_tokens, stream)` -> resposta/stream
- politicas de retry e backoff (configuravel)
- redacao de segredos em logs

Motivo: manter swap facil no futuro (OpenAI/Anthropic/etc.) sem mexer no dominio/UI.

## 8. Execucao de Stacks (Run Engine)

### 8.1 Fonte dos stacks

Usar `06-stacks/*/stack.yaml` como definicao de:

- `sequence` de stages
- `approval_required`
- outputs esperados

### 8.2 Comportamento

- Iniciar run: cria `Run` + `Stages` no SQLite e cria diretorio `runs/<run_id>/`.
- Rodar stages em background:
  - antes de cada stage: RAG + Context Pack
  - gerar artifact(s)
  - salvar artifact no filesystem e registrar no SQLite
  - logar evento em `events.jsonl`
- Gates:
  - se `approval_required=true`, pausar com status `waiting_approval`
  - UI exibe botao `Approve` / `Skip` / `Retry`

### 8.3 Auditoria

Por stage, salvar snapshot de:

- parametros do stage
- Context Pack usado
- resposta bruta do LLM (ou referencia)
- artifacts gerados

## 9. Backend Web (FastAPI ASGI)

### 9.1 Motivacao

- ASGI facilita streaming (SSE) e jobs longos.
- Mantem o padrao API-first, migrando para SaaS sem trocar contratos.

### 9.2 Streaming

- Endpoint SSE para eventos de execucao e status do run:
  - start/end de stage
  - logs
  - gates aguardando aprovacao

## 10. UI V1 (Static + Fetch)

### 10.1 Layout

- **Contexto ativo:** Marca/Produto/Thread selecionados
- **Chat:** entrada + historico
- **Runs/Stages:** lista de runs com progresso e botoes de aprovacao
- **Memoria:** tela de debug do retrieval (query, top-k, origens)

### 10.2 CRUD hibrido (canonico + markdown)

- Formulario para campos canonicos
- Editor markdown para `soul.md` e `essence.md`
- Botao "Promover para canonico" para transformar feedback em atualizacao canonica (via confirmacao)

## 11. API V1 (proposta)

- `POST /api/v1/brands`, `GET /api/v1/brands`, `PATCH /api/v1/brands/{id}`
- `POST /api/v1/products`, `GET /api/v1/brands/{id}/products`, `PATCH /api/v1/products/{id}`
- `POST /api/v1/threads`, `GET /api/v1/threads/{id}`
- `POST /api/v1/chat`
- `POST /api/v1/runs`, `GET /api/v1/runs/{id}`
- `POST /api/v1/runs/{id}/approve`, `POST /api/v1/runs/{id}/retry`
- `GET /api/v1/events` (SSE)
- `POST /api/v1/memory/search` (debug do RAG)

## 12. Config e Ambiente

- Padronizar runtime do app em **Python 3.12** (necessario para zvec no beta).
- Gerenciar ambiente com `uv`.
- Config via `.env` (segredos) e `settings.yaml` (nao-segredos).

## 13. Caminho para SaaS Cloud (futuro)

1. Trocar SQLite por Postgres (mesmo modelo relacional).
2. Trocar filesystem por object storage (S3/R2).
3. Adicionar auth (org/user/roles) e isolamento multi-tenant real.
4. Execucao assinc: fila de jobs + retries + timeouts.
5. Observabilidade: tracing, metrica por run/stage, latencia e custo.

## 14. Riscos e Mitigacoes

- **Contexto grande:** limitar top-k e tamanho de chunks; contracts por stage.
- **Drift de marca:** promocao para canonico so com confirmacao explicita.
- **Lock-in de provider:** interface `LLMProvider` e testes de contrato.
- **Reprodutibilidade:** snapshots por run/stage e export/import do workspace.

