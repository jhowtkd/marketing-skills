# VM Studio Editorial Golden Decision (Event-Sourcing) Design

## Status
Aprovado para implementacao.

---

## 1. Objetivo

Adicionar decisao editorial auditavel para escolher a melhor referencia de comparacao/regeneracao no Studio, com duas granularidades:

- golden global do job
- golden por objetivo do job

Regra de prioridade ja validada:

1. objective-golden
2. global-golden
3. versao anterior

Regra de governanca ja validada:

- justificativa curta obrigatoria ao marcar golden

---

## 2. Critica Consolidada dos Planos 26/02

Base de comparacao:

- `docs/plans/2026-02-26-vm-studio-2-0-best-solution.md`
- `docs/plans/2026-02-26-vm-studio-2-0-best-solution-implementation.md`

Pontos fortes mantidos:

- foco em contratos reais da API v2
- UX de agencia (`Cliente/Campanha/Job/Versao`)
- pipeline de qualidade + regeneracao guiada

Gap principal que este design fecha:

- baseline de comparacao ainda estava implicita ("versao anterior")
- faltava decisao editorial explicita, auditavel e reproduzivel
- faltava separar "melhor versao geral" vs "melhor versao para um objetivo especifico"

Direcao escolhida:

- manter arquitetura event-driven atual
- nao criar estado paralelo "manual" fora de eventos
- decisao editorial entra no mesmo trilho de `commands_v2 -> event_log -> projectors_v2 -> read models`

---

## 3. Escopo Validado

Dentro do escopo:

- novo evento de dominio para decisao golden
- read-model para estado atual de golden por thread/scope
- endpoint para marcar golden com justificativa obrigatoria
- endpoint para leitura das decisoes atuais
- resolver unico de baseline com prioridade oficial
- UI para marcar golden e visualizar badges
- uso do baseline resolvido em compare/regeneracao

Fora do escopo (neste slice):

- versionamento de rubricas editoriais
- policy de permissao por papel (alem de `workspace-owner` atual)
- merge de multiplas goldens por objetivo

---

## 4. Abordagens Consideradas

### 4.1 Estado so no frontend

Descricao:

- frontend guarda golden em localStorage/API ad-hoc

Pros:

- entrega rapida inicial

Contras:

- sem trilha auditavel
- risco de drift entre usuarios/sessoes
- quebra consistencia com modelo event-sourcing do produto

### 4.2 Tabela mutavel sem evento

Descricao:

- API escreve direto em tabela de "golden atual"

Pros:

- simples de consultar

Contras:

- perde historico de decisao
- dificulta debug de "quem marcou o que, quando e por que"

### 4.3 Event-sourcing first (escolhida)

Descricao:

- comando dedicado gera evento `EditorialGoldenMarked`
- projector atualiza read-model materializado
- baseline resolver usa read-model + fallback deterministico

Pros:

- auditavel
- idempotente
- alinhado com a arquitetura existente
- simples de evoluir para politicas futuras

Contras:

- precisa tocar backend + frontend + testes

---

## 5. Modelo de Dominio

### 5.1 Evento de dominio

Novo event type:

- `EditorialGoldenMarked`

Payload:

- `thread_id: str`
- `run_id: str`
- `scope: "global" | "objective"`
- `objective_key: str | null` (obrigatorio quando scope=`objective`)
- `justification: str` (obrigatorio, texto curto)

Semantica:

- cada novo mark substitui o golden anterior do mesmo escopo/chave
- historico permanece no `event_log`

### 5.2 Read model materializado

Nova view/table projetada:

- `editorial_decisions_view`

Campos:

- `decision_key` (PK, composto logico por `thread_id|scope|objective_key`)
- `thread_id`
- `scope`
- `objective_key` (nullable)
- `run_id`
- `justification`
- `updated_at`
- `event_id`

Semantica:

- guarda o estado atual por slot de decisao
- historico completo continua no `event_log`

### 5.3 Chave de objetivo

Para suportar objective-golden sem UX complexa:

- cada run passa a ter `objective_key` derivada de `request_text`
- derivacao deterministica no backend (normalizacao + slug curto + hash)
- objetivo do mesmo texto/logica gera mesma chave

---

## 6. API v2 (Contrato Proposto)

### 6.1 Marcar golden

`POST /api/v2/threads/{thread_id}/editorial-decisions/golden`

Request:

```json
{
  "run_id": "run-abc123",
  "scope": "objective",
  "objective_key": "campanha-lancamento-q1-9f3a2b1c",
  "justification": "Melhor clareza de CTA e estrutura final."
}
```

Regras:

- `Idempotency-Key` obrigatorio
- `justification` obrigatoria (ex: 8..280 chars apos trim)
- `scope=objective` exige `objective_key`
- run deve pertencer ao `thread_id`

Response:

```json
{
  "event_id": "evt-...",
  "thread_id": "t-...",
  "run_id": "run-...",
  "scope": "objective",
  "objective_key": "..."
}
```

### 6.2 Ler decisoes atuais do thread

`GET /api/v2/threads/{thread_id}/editorial-decisions`

Response:

```json
{
  "global": {
    "run_id": "run-...",
    "justification": "...",
    "updated_at": "..."
  },
  "objective": [
    {
      "objective_key": "campanha-lancamento-q1-9f3a2b1c",
      "run_id": "run-...",
      "justification": "...",
      "updated_at": "..."
    }
  ]
}
```

### 6.3 Baseline resolvido para uma run

`GET /api/v2/workflow-runs/{run_id}/baseline`

Response:

```json
{
  "run_id": "run-atual",
  "baseline_run_id": "run-referencia-ou-null",
  "source": "objective_golden|global_golden|previous|none",
  "objective_key": "campanha-lancamento-q1-9f3a2b1c"
}
```

### 6.4 Extensoes em endpoints existentes

`GET /api/v2/threads/{thread_id}/workflow-runs`:

- incluir `objective_key`

`GET /api/v2/workflow-runs/{run_id}`:

- incluir `objective_key`

---

## 7. Resolver de Baseline (Fonte Unica)

Algoritmo para run ativa `R`:

1. if existe golden objective para `R.objective_key` e run diferente de `R`: usar este
2. else if existe golden global e run diferente de `R`: usar este
3. else usar versao anterior por ordem de criacao
4. else sem baseline

Detalhes:

- nunca retornar a propria run ativa como baseline
- se golden aponta para run inexistente/deletada, ignorar e seguir fallback
- resultado sempre inclui `source` para debug e UX

---

## 8. UX no VM Studio

### 8.1 Acoes novas por versao

Em cada card de versao:

- `Definir como golden global`
- `Definir como golden deste objetivo`

Ambas abrem modal de justificativa curta (obrigatoria).

### 8.2 Sinalizacao visual

Badges na versao:

- `Golden global`
- `Golden objetivo`

No bloco de comparacao:

- label explicita do baseline, por exemplo:
  - `Comparando com: Golden deste objetivo`
  - `Comparando com: Golden global`
  - `Comparando com: Versao anterior`

### 8.3 Fluxo de regeneracao guiada

Ao abrir `Regenerar guiado`:

- exibir baseline selecionado pela regra oficial
- reaproveitar `objective_key` da run ativa

---

## 9. Regras de Erro e Confiabilidade

Cenarios e respostas:

- `run_id` nao pertence ao thread -> `404`
- `scope=objective` sem `objective_key` -> `422`
- `justification` vazia/curta -> `422`
- conflito de stream version -> `409`
- idempotencia repetida -> mesmo resultado anterior

Observabilidade minima:

- contador `editorial_golden_marked_total`
- contador por scope
- tempo ate primeira decisao golden por thread (metrica futura opcional)

---

## 10. Estrategia de Testes

Backend:

- command idempotente para mark golden
- projector atualiza `editorial_decisions_view`
- endpoint valida contratos/erros
- resolver respeita prioridade objective > global > previous

Frontend:

- baseline selector usa endpoint/resolver corretamente
- badges aparecem no run card certo
- modal exige justificativa para submit
- regressao: quando nao ha golden, fallback continua versao anterior

E2E/smoke:

- criar 3 runs
- marcar golden global e objective
- validar baseline da run ativa
- executar regeneracao guiada com baseline correto

---

## 11. Rollout Seguro

Fase 1 (backend):

- eventos + projector + endpoints + testes de contrato

Fase 2 (frontend):

- badges + modal + consumo do baseline resolvido

Fase 3 (operacao):

- smoke local
- atualizar release note

Sem breaking change:

- clientes antigos continuam operando
- novos campos sao aditivos

---

## 12. Criterios de Sucesso

- decisao golden fica auditavel via event_log/timeline
- baseline de comparacao segue prioridade oficial sempre
- usuario consegue marcar golden com 1 acao + justificativa curta
- scorecard/diff/regeneracao passam a usar baseline editorial (nao so versao anterior)

---

## 13. Handoff

Proximo passo: executar plano TDD detalhado em `docs/plans/2026-02-27-vm-studio-editorial-golden-event-sourcing-implementation.md` via `executing-plans`.
