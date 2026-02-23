# VM Web App Realtime UI Design

## Context

O backend do VM Web App já tem:
- `POST /api/v1/chat`
- engine de runs com gate (`waiting_approval`)
- gravação de eventos por run em `events.jsonl`

A UI atual (`09-tools/web/vm`) é estática.

## Goal

Entregar uma UI funcional com:
- chat integrado ao backend
- histórico de mensagens em sessão
- início de run foundation por botão e por comando `/run foundation`
- painel de runs com atualização em tempo real via SSE
- ação de `Approve` quando run parar em gate

## Decisions (approved)

- Escopo: **completo** (chat + histórico + runs/gates em realtime)
- Acionamento de run: **híbrido** (botão + comando `/run foundation`)
- Aprovação: **approve only**
- Stack do estágio: **apenas foundation**
- Estratégia de realtime: **SSE lendo `events.jsonl`** (fonte persistente)

## Architecture

### Frontend

- `09-tools/web/vm/index.html`
  - área de chat com input e lista de mensagens
  - botão `Start Foundation Run`
  - painel de runs com timeline e botão `Approve`
- `09-tools/web/vm/app.js`
  - carrega brands/products da API
  - mantém `thread_id` em `localStorage`
  - fluxo de chat normal via `POST /api/v1/chat`
  - intercepta `/run foundation` e inicia run
  - abre conexão SSE do run ativo e atualiza timeline
- `09-tools/web/vm/styles.css`
  - estilos de estado (`running`, `waiting_approval`, `completed`)
  - feedback de erro e loading

### Backend

- `09-tools/vm_webapp/api.py`
  - listar produtos por brand
  - iniciar run foundation
  - listar runs e stages por thread
  - aprovar run em gate
  - SSE de eventos por run
- `09-tools/vm_webapp/repo.py`
  - queries para produtos/runs por filtros
  - helper para localizar stage em `waiting_approval`
- `09-tools/vm_webapp/run_engine.py`
  - método para continuar execução após `Approve`
  - manter emissão de eventos no mesmo `events.jsonl`

## Data Flow

1. UI inicializa:
   - `GET /api/v1/brands`
   - `GET /api/v1/products?brand_id=<id>`
2. Usuário envia chat:
   - mensagem comum -> `POST /api/v1/chat`
   - comando `/run foundation` -> `POST /api/v1/runs/foundation`
3. Ao iniciar run:
   - UI define `run_id` ativo
   - abre `GET /api/v1/runs/{run_id}/events` (SSE)
4. Eventos SSE atualizam painel:
   - `run_started`, `stage_completed`, `approval_required`, `run_completed`
5. Em `approval_required`:
   - botão `Approve` -> `POST /api/v1/runs/{run_id}/approve`
   - backend continua execução até próximo gate/completion

## API Contract (V1)

- `GET /api/v1/products?brand_id=b1`
- `GET /api/v1/runs?thread_id=t1`
- `POST /api/v1/runs/foundation`
- `POST /api/v1/runs/{run_id}/approve`
- `GET /api/v1/runs/{run_id}/events` (`text/event-stream`)

## Error Handling

- Frontend:
  - mensagem inline em falhas de chat/run
  - reconexão SSE com backoff
  - feedback para comandos inválidos (`/run x`)
- Backend:
  - 404 para run inexistente
  - 409 quando `approve` for chamado sem stage aguardando aprovação
  - 400 para payload inválido

## Test Strategy

- Backend (pytest + TestClient):
  - lista de produtos por brand
  - start run foundation
  - approve transiciona `waiting_approval` -> `running/completed`
  - SSE retorna stream com eventos esperados
  - chat mantém comportamento atual com comando tratado no frontend
- Frontend:
  - smoke funcional manual no browser para:
    - envio de chat
    - start por botão
    - start por `/run foundation`
    - aprovação de gate
    - atualização em tempo real do painel

## Out of Scope (this stage)

- múltiplas stacks no UI
- edição/retry de stage
- autenticação/autorização
- paginação de histórico e filtros avançados
