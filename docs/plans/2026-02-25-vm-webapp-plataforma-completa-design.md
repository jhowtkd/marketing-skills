# Design: VM Webapp Plataforma Completa

**Date:** 2026-02-25  
**Topic:** Evolucao do `09-tools/vm_webapp` para plataforma completa de Agencia Virtual com agentes de IA.

## 1. Escopo e Decisoes de Direcao

- Escopo aprovado: plataforma completa (dominio, orquestracao, RAG, Tool Layer, observabilidade e deploy).
- Prazo: sem prazo fixo, priorizando robustez e operabilidade.
- Estrategia de construcao: evoluir o `09-tools/vm_webapp` atual (sem reescrita total).
- Infra de producao: managed-first (servicos gerenciados).
- Estrategia de entrega: fatias verticais ponta-a-ponta.

## 2. Arquitetura-alvo (Alto Nivel)

A plataforma sera evoluida de forma modular dentro do repositorio atual, preservando compatibilidade retroativa enquanto novos modulos entram em producao.

### 2.1 Blocos principais

- **Application/API:** FastAPI atual como porta de entrada para UI e APIs v2/v3.
- **Domain Core:** entidades `Brand`, `Campaign`, `Task`, politicas de heranca e versionamento.
- **Orchestration Engine:** state machine com planejamento, execucao paralela, review e consolidacao.
- **Tool Layer:** registry, plugins, executor e adapters (MCP, Function Calling, LangChain).
- **Knowledge Layer (RAG):** indexacao de artefatos/aprendizados e retrieval hierarquico.
- **Execution Layer:** filas e workers assincronos para estagios de workflow.
- **Platform Ops:** observabilidade, auditoria, metricas de custo/qualidade e operacao.

### 2.2 Infra managed-first (producao)

- Postgres para dados transacionais, views e auditoria.
- Redis para filas, locks, cache e rate limiting.
- Object storage para artifacts.
- Vector store para RAG.
- Web service + worker services em plataforma gerenciada.

## 3. Modelo de Dominio e Contratos

### 3.1 Agregados centrais

- `Brand`: identidade visual imutavel, voz, posicionamento, regras globais.
- `Campaign`: objetivos, canais, budget, timeline, segmentacao, overrides controlados.
- `Task`: tipo de entrega, especificacoes tecnicas, criterios de qualidade, dependencias.
- `WorkflowRun`: execucao ponta-a-ponta com estado, custo, latencia e resultado.
- `StageRun`: status por etapa, tentativas, gates, fallback e artefatos.
- `Artifact`: saidas versionadas (texto, json, midia, metadados).
- `Learning`: aprendizado implicito/explicito indexado para RAG.
- `Tool`, `ToolPermission`, `ToolCredentialRef`: catalogo, autorizacao e referencia de segredo.
- `AuditEvent`: trilha de governanca e rastreabilidade.

### 3.2 Regras de contrato

- Heranca contextual obrigatoria: `Brand -> Campaign -> Task`.
- Sobrescritas somente em campos permitidos por politica.
- Versionamento append-only de regras e contexto.
- Cada `WorkflowRun` referencia snapshots imutaveis para reproducao fiel.

## 4. Fluxo de Execucao e Orquestracao

1. API recebe demanda e resolve contexto com snapshot versionado.
2. `WorkflowRun` e criado com `requested_mode`, `effective_mode` e politicas de execucao.
3. Planner monta DAG de `StageRun` (sequencial/paralelo/condicional).
4. Workers executam estagios via Tool Layer.
5. Reviewer aplica quality gates (compliance de marca, qualidade e politicas).
6. Falhas acionam retry/backoff/fallback; excedendo politica, run falha com diagnostico.
7. Consolidator empacota outputs e publica artifacts.
8. Pipeline de learning indexa conteudo aprovado no RAG.
9. Timeline, auditoria e estado ficam disponiveis no Studio e na API.

### 4.1 Estados minimos de run

- Fluxo principal: `queued -> running -> waiting_approval -> running -> completed`
- Fluxos alternativos: `running -> failed`, `waiting_approval -> cancelled`

### 4.2 Garantias operacionais

- Idempotencia por comando/evento.
- Resume seguro para runs pausados.
- Snapshot imutavel por execucao.

## 5. Tool Layer, RAG e Seguranca

### 5.1 Tool Layer

- Registry central com schema versionado de entrada/saida.
- Plugin loader para extensao por ferramentas.
- Executor com timeout, retry policy, circuit breaker e metrica de custo.
- Adaptadores: MCP, OpenAI Function Calling, LangChain.
- Governanca: permissoes por tenant/projeto/agente, rate limits por ferramenta/acao.
- Credenciais: apenas referencias (`ToolCredentialRef`) para provider de segredo.

### 5.2 RAG

- Fontes: artifacts aprovados, regras de marca, feedback humano, historico de campanhas.
- Chunking com metadados hierarquicos (`brand_id`, `campaign_id`, `task_type`, `stage`, `quality_score`).
- Retrieval com filtro por brand, boost por similaridade de campanha/task e reranking.
- Escrita condicionada a qualidade minima para evitar aprendizado de baixa qualidade.

### 5.3 Seguranca e compliance

- Autenticacao/autorizacao por tenant.
- Auditoria completa de invocacao de tools e mudancas de politicas.
- Sanitizacao de inputs e validacao forte de payload.
- Regras de retencao e isolamento de dados por tenant.

## 6. Estrategia de Migracao e Validacao

### 6.1 Fases de entrega (fatias verticais)

1. Fundamentos de dominio: contratos, snapshots/versionamento e migracoes de banco.
2. Orquestracao robusta: DAG, gates, retry/fallback/circuit breaker e auditoria.
3. Tool Layer produtiva: registry/plugins/executor + permissoes + credenciais + adapters.
4. RAG completo: indexacao de artifacts/learnings e retrieval hierarquico.
5. Hardening de plataforma: observabilidade, custos, SLOs e rollout progressivo.

### 6.2 Verificacao obrigatoria por fase

- Testes unitarios de dominio e heranca contextual.
- Testes de integracao (API + runtime assincrono + tools).
- Testes E2E com aprovacao/rework.
- Testes de resiliencia (timeout, falha de provider, fallback).
- Validacao de seguranca e isolamento multi-tenant.

### 6.3 Definicao de "funcionando"

A plataforma completa sera considerada funcional quando:

- Entregar run ponta-a-ponta com artifacts reais, review e aprendizado.
- Operar com resiliencia sob falhas de provider/tool.
- Aplicar governanca ativa (permissoes, auditoria, limites).
- Expor observabilidade suficiente para operacao em producao managed-first.

