# v46 Rollout Dashboard + Approval UX Contract

> **Versão:** 1.0.0  
> **Sprint:** v46  
> **Status:** Draft  
> **Owner:** Growth Engineering Team  
> **Depends on:** v45 Auto-Rollout Policy

---

## 1. Dashboard Data Contract

### 1.1 RolloutPolicy (API Response)

Estrutura de dados retornada pela API para o dashboard. Estende e normaliza campos do v45 `AutoRolloutPolicy` para consumo UI.

```typescript
interface RolloutPolicy {
  // Identificação (consistente com v45)
  experiment_id: string;                    // UUID do experimento
  policy_version: string;                   // SemVer (ex: "1.0.0")
  
  // Estado atual (mapeado de v45.active_variant)
  active_variant: string;                   // "control" | "treatment" | string
  
  // Modo de operação (estendido de v45: manual|auto → AUTO|MANUAL|SUPERVISED)
  rollout_mode: "AUTO" | "MANUAL" | "SUPERVISED";
  
  // Status consolidado (derivado da state machine v45 + necessidades UI)
  status: "promoted" | "blocked" | "rolled_back" | "pending_review" | "evaluating";
  
  // Timestamps (mapeados de v45)
  created_at: string;                       // ISO8601
  updated_at: string;                       // ISO8601
  last_evaluation_at: string | null;        // Mapeado de v45.last_evaluation
  
  // Metadados de decisão (consistente com v45)
  decision_reason: string | null;           // Razão da última decisão
  decision_trigger: "scheduled" | "threshold" | "manual" | "approval" | null;
  
  // Configuração de segurança (consistente com v45)
  rollback_target: string;                  // Sempre "control" no v45
  auto_rollback_enabled: boolean;           // De v45.auto_rollback_enabled
  can_rollback: boolean;                    // Computado: se rollback é permitido agora
  
  // Histórico (mapeado de v45.decision_history → formato UI)
  timeline: TimelineEvent[];
  
  // Métricas consolidadas para UI
  metrics: MetricsSnapshot;
  
  // Gates atuais (referência a v45 gates)
  gates_status?: {
    min_gain: { passed: boolean; threshold: number; actual: number };
    stability: { passed: boolean; confidence: number; sample_size: number };
    risk: { passed: boolean; completion_ok: boolean; abandonment_ok: boolean };
    ttfv_regression: { passed: boolean; increase_ratio: number };
  };
}
```

### 1.2 TimelineEvent

Evento de timeline para o dashboard. Mapeado do `DecisionLogEntry` do v45 com campos adicionais para UI.

```typescript
interface TimelineEvent {
  timestamp: string;                      // ISO8601
  action: "promoted" | "blocked" | "rolled_back" | "approved" | "rejected" | "evaluation_started";
  operator?: string;                      // ID do operador (se ação manual)
  reason?: string;                        // Descrição legível
  variant_id?: string;                    // Variante afetada
  
  // Campos extendidos (de v45 DecisionLogEntry)
  from_variant?: string;                  // Variante anterior
  to_variant?: string;                    // Nova variante
  gates_passed?: string[];                // Gates que passaram
  gates_failed?: string[];                // Gates que falharam
  metrics_snapshot?: Record<string, number>; // Snapshot das métricas
}
```

### 1.3 MetricsSnapshot

Snapshot consolidado de métricas para exibição no dashboard.

```typescript
interface MetricsSnapshot {
  // Amostragem
  total_evaluations: number;              // Total de avaliações realizadas
  sample_size: number;                    // N total de amostras
  sample_size_control: number;            // N do controle
  sample_size_treatment: number;          // N do tratamento
  
  // Performance
  success_rate: number;                   // 0-1 (taxa de sucesso)
  avg_latency_ms: number;                 // Latência média em ms
  error_rate: number;                     // 0-1 (taxa de erro)
  
  // Métricas de negócio (mapeadas de v45)
  control_score?: number;                 // Score do controle
  treatment_score?: number;               // Score do tratamento
  relative_gain?: number;                 // Ganho relativo (treatment/control)
  
  // Métricas de risco (mapeadas de v45 gates)
  completion_rate_control?: number;       // Taxa de completion controle
  completion_rate_treatment?: number;     // Taxa de completion tratamento
  abandonment_rate_control?: number;      // Taxa de abandono controle
  abandonment_rate_treatment?: number;    // Taxa de abandono tratamento
  ttfv_control?: number;                  // TTFV controle (segundos)
  ttfv_treatment?: number;                // TTFV tratamento (segundos)
}
```

---

## 2. Approval Actions Contract

### 2.1 ApprovePromotionRequest

Requisição para aprovar promoção manual ou supervisionada.

```typescript
interface ApprovePromotionRequest {
  operator_id: string;                    // Obrigatório: ID do operador
  reason: string;                         // Obrigatório: min 10 caracteres
  variant?: string;                       // Opcional: forçar variante específica
  
  // Validações
  // - operator_id: não vazio, deve existir no sistema
  // - reason: mínimo 10 caracteres, máximo 500
  // - variant: se fornecido, deve ser uma variante válida do experimento
}
```

**Resposta de Sucesso:**
```json
{
  "success": true,
  "new_status": "promoted",
  "previous_status": "pending_review",
  "promoted_variant": "treatment_v2",
  "timestamp": "2026-03-05T10:30:00Z",
  "approved_by": "operator_123",
  "next_evaluation_at": null
}
```

**Resposta de Erro:**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Cannot approve promotion: experiment is not in pending_review state",
    "current_status": "evaluating"
  }
}
```

### 2.2 RejectPromotionRequest

Requisição para rejeitar promoção.

```typescript
interface RejectPromotionRequest {
  operator_id: string;                    // Obrigatório: ID do operador
  reason: string;                         // Obrigatório: min 10 caracteres
  
  // Validações
  // - operator_id: não vazio, deve existir no sistema
  // - reason: mínimo 10 caracteres, máximo 500
}
```

**Resposta de Sucesso:**
```json
{
  "success": true,
  "new_status": "blocked",
  "previous_status": "pending_review",
  "rejected_by": "operator_123",
  "timestamp": "2026-03-05T10:30:00Z",
  "requires_manual_review": true
}
```

### 2.3 ManualRollbackRequest

Requisição para rollback manual de emergência.

```typescript
interface ManualRollbackRequest {
  operator_id: string;                    // Obrigatório: ID do operador
  reason: string;                         // Obrigatório: min 10 caracteres
  force?: boolean;                        // Opcional: ignorar cooldowns (requer permissão admin)
  
  // Validações
  // - operator_id: não vazio, deve existir no sistema
  // - reason: mínimo 10 caracteres, máximo 500
  // - force: requer permissão 'experiment_admin'
}
```

**Resposta de Sucesso:**
```json
{
  "success": true,
  "new_status": "rolled_back",
  "previous_status": "promoted",
  "rolled_back_to": "control",
  "rolled_back_from": "treatment_v2",
  "timestamp": "2026-03-05T10:30:00Z",
  "triggered_by": "operator_123",
  "cooldown_ignored": false
}
```

---

## 3. API Endpoints v2

### 3.1 GET /api/v2/onboarding/rollout-dashboard

Retorna lista de todas as políticas de rollout ativas para o dashboard.

**Query Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `status` | string | Filtrar por status (opcional) |
| `mode` | string | Filtrar por rollout_mode (opcional) |
| `limit` | number | Limite de resultados (default: 50, max: 100) |
| `offset` | number | Offset para paginação (default: 0) |

**Response 200 OK:**
```json
{
  "policies": [
    {
      "experiment_id": "exp_onboarding_v2",
      "policy_version": "1.0.0",
      "active_variant": "treatment",
      "rollout_mode": "SUPERVISED",
      "status": "pending_review",
      "created_at": "2026-03-01T10:00:00Z",
      "updated_at": "2026-03-05T09:00:00Z",
      "last_evaluation_at": "2026-03-05T08:45:00Z",
      "decision_reason": "All gates passed, awaiting approval",
      "decision_trigger": "threshold",
      "rollback_target": "control",
      "auto_rollback_enabled": true,
      "can_rollback": true,
      "timeline": [...],
      "metrics": {...},
      "gates_status": {...}
    }
  ],
  "pagination": {
    "total": 12,
    "limit": 50,
    "offset": 0,
    "has_more": false
  },
  "updated_at": "2026-03-05T10:30:00Z"
}
```

### 3.2 POST /api/v2/onboarding/rollout-policy/{experiment_id}/approve

Aprova promoção de variante.

**Path Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `experiment_id` | string | ID do experimento |

**Request Body:** `ApprovePromotionRequest`

**Response 200 OK:** Ver seção 2.1

**Response 400 Bad Request:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Reason must be at least 10 characters",
    "field": "reason"
  }
}
```

**Response 409 Conflict:**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_STATE",
    "message": "Experiment must be in 'pending_review' or 'evaluating' state",
    "current_state": "promoted"
  }
}
```

### 3.3 POST /api/v2/onboarding/rollout-policy/{experiment_id}/reject

Rejeita promoção de variante.

**Path Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `experiment_id` | string | ID do experimento |

**Request Body:** `RejectPromotionRequest`

**Response 200 OK:** Ver seção 2.2

### 3.4 POST /api/v2/onboarding/rollout-policy/{experiment_id}/rollback

Executa rollback manual.

**Path Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `experiment_id` | string | ID do experimento |

**Request Body:** `ManualRollbackRequest`

**Response 200 OK:** Ver seção 2.3

**Response 403 Forbidden:**
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "Force rollback requires 'experiment_admin' permission"
  }
}
```

### 3.5 GET /api/v2/onboarding/rollout-policy/{experiment_id}/history

Retorna histórico completo de eventos do experimento.

**Path Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `experiment_id` | string | ID do experimento |

**Query Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `limit` | number | Limite de eventos (default: 50) |
| `before` | string | Timestamp ISO8601 para paginação |

**Response 200 OK:**
```json
{
  "experiment_id": "exp_onboarding_v2",
  "history": [
    {
      "timestamp": "2026-03-05T08:45:00Z",
      "action": "evaluation_started",
      "reason": "Scheduled evaluation triggered"
    },
    {
      "timestamp": "2026-03-05T08:45:30Z",
      "action": "blocked",
      "variant_id": "treatment_v2",
      "reason": "Awaiting manual approval in SUPERVISED mode",
      "gates_passed": ["min_gain", "stability", "risk", "ttfv_regression"],
      "metrics_snapshot": {
        "control_score": 0.82,
        "treatment_score": 0.84
      }
    }
  ],
  "pagination": {
    "total": 15,
    "limit": 50,
    "has_more": false
  }
}
```

---

## 4. Telemetry Events

### 4.1 Eventos de Dashboard

#### `rollout_dashboard_viewed`

Emitido quando dashboard é carregado.

```json
{
  "event_type": "rollout_dashboard_viewed",
  "timestamp": "2026-03-05T10:30:00Z",
  "user_id": "operator_123",
  "payload": {
    "filters_applied": {
      "status": null,
      "mode": null
    },
    "results_count": 12,
    "page": "rollout_dashboard"
  },
  "context": {
    "session_id": "sess_abc123",
    "user_role": "experiment_operator"
  }
}
```

#### `rollout_policy_selected`

Emitido quando operador seleciona uma policy para visualizar detalhes.

```json
{
  "event_type": "rollout_policy_selected",
  "timestamp": "2026-03-05T10:31:00Z",
  "user_id": "operator_123",
  "payload": {
    "experiment_id": "exp_onboarding_v2",
    "current_status": "pending_review",
    "rollout_mode": "SUPERVISED"
  }
}
```

### 4.2 Eventos de Aprovação

#### `rollout_approval_submitted`

Emitido quando ação de aprovação/rejeição/rollback é submetida.

```json
{
  "event_type": "rollout_approval_submitted",
  "timestamp": "2026-03-05T10:32:00Z",
  "user_id": "operator_123",
  "payload": {
    "experiment_id": "exp_onboarding_v2",
    "action_type": "approve",         // "approve" | "reject" | "rollback"
    "previous_status": "pending_review",
    "reason_length": 45,
    "forced_variant": null
  }
}
```

#### `rollout_approval_approved`

Emitido quando aprovação é confirmada com sucesso.

```json
{
  "event_type": "rollout_approval_approved",
  "timestamp": "2026-03-05T10:32:05Z",
  "user_id": "operator_123",
  "payload": {
    "experiment_id": "exp_onboarding_v2",
    "approved_variant": "treatment_v2",
    "previous_variant": "control",
    "processing_time_ms": 5230,
    "gates_passed": ["min_gain", "stability", "risk", "ttfv_regression"]
  },
  "context": {
    "triggered_from": "dashboard",
    "approval_reason": "Treatment shows consistent 2.3% improvement"
  }
}
```

#### `rollout_approval_rejected`

Emitido quando rejeição é confirmada.

```json
{
  "event_type": "rollout_approval_rejected",
  "timestamp": "2026-03-05T10:32:05Z",
  "user_id": "operator_123",
  "payload": {
    "experiment_id": "exp_onboarding_v2",
    "rejected_variant": "treatment_v2",
    "new_status": "blocked"
  },
  "context": {
    "triggered_from": "dashboard",
    "rejection_reason": "Insufficient sample size for confidence"
  }
}
```

#### `rollout_manual_rollback_triggered`

Emitido quando rollback manual é executado.

```json
{
  "event_type": "rollout_manual_rollback_triggered",
  "timestamp": "2026-03-05T10:32:05Z",
  "user_id": "operator_123",
  "payload": {
    "experiment_id": "exp_onboarding_v2",
    "rolled_back_from": "treatment_v2",
    "rolled_back_to": "control",
    "rollback_type": "manual",
    "force_flag": false,
    "time_in_treatment_minutes": 127
  },
  "context": {
    "triggered_from": "dashboard",
    "rollback_reason": "Detected anomaly in conversion funnel"
  }
}
```

### 4.3 Eventos de Erro

#### `rollout_approval_failed`

Emitido quando ação de aprovação falha.

```json
{
  "event_type": "rollout_approval_failed",
  "timestamp": "2026-03-05T10:32:05Z",
  "user_id": "operator_123",
  "payload": {
    "experiment_id": "exp_onboarding_v2",
    "action_type": "approve",
    "error_code": "INVALID_STATE_TRANSITION",
    "error_message": "Cannot approve: experiment already promoted"
  }
}
```

### 4.4 Schema de Telemetry

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `event_type` | string | Tipo do evento (prefixo: `rollout_`) |
| `timestamp` | ISO8601 | Quando ocorreu |
| `user_id` | string | ID do operador que disparou |
| `payload` | object | Dados específicos do evento |
| `context` | object | Metadados de contexto |

---

## 5. UI States

### 5.1 Estados do Dashboard

| Estado | Descrição | Visual |
|--------|-----------|--------|
| `loading` | Carregando dados iniciais | Skeleton/table loader |
| `error` | Falha ao carregar | Mensagem de erro + botão retry |
| `empty` | Nenhum experimento configurado | Ilustração + CTA para criar |
| `populated` | Dados carregados | Tabela com políticas |
| `refreshing` | Atualizando dados em background | Spinner sutil no header |

```typescript
type DashboardState = 
  | { status: "loading" }
  | { status: "error"; error: Error; retry: () => void }
  | { status: "empty" }
  | { status: "populated"; policies: RolloutPolicy[]; lastUpdated: Date }
  | { status: "refreshing"; policies: RolloutPolicy[] };
```

### 5.2 Estados de Ação (Modal/Form)

| Estado | Descrição | Visual |
|--------|-----------|--------|
| `idle` | Form pronto para input | Campos editáveis |
| `pending` | Aguardando confirmação | Modal de confirmação |
| `validating` | Validando inputs | Inline validation |
| `processing` | Submit em andamento | Spinner + desabilitar |
| `success` | Ação completada | Toast verde + atualização |
| `error` | Falha na ação | Toast vermelho + retry |

```typescript
type ActionState =
  | { status: "idle" }
  | { status: "pending"; action: "approve" | "reject" | "rollback" }
  | { status: "validating"; errors: Record<string, string> }
  | { status: "processing"; action: string }
  | { status: "success"; message: string; newStatus: string }
  | { status: "error"; error: string; canRetry: boolean };
```

### 5.3 Estados de Badge/Chip

Mapeamento de `status` para cores/ícones:

| Status | Cor | Ícone | Descrição UI |
|--------|-----|-------|--------------|
| `promoted` | Verde | ↑ | Promovido |
| `blocked` | Vermelho | ⊘ | Bloqueado |
| `rolled_back` | Laranja | ↩ | Rollback executado |
| `pending_review` | Âmbar | ⏸ | Aguardando aprovação |
| `evaluating` | Azul | ⟳ | Em avaliação |

Mapeamento de `rollout_mode` para badges:

| Modo | Cor | Ícone |
|------|-----|-------|
| `AUTO` | Verde | 🤖 |
| `MANUAL` | Cinza | 👤 |
| `SUPERVISED` | Âmbar | 👤+🤖 |

### 5.4 Estados de Botão de Ação

| Estado | Visual | Comportamento |
|--------|--------|---------------|
| `enabled` | Primário | Clickable |
| `disabled` | Cinza | Não clickable (sem permissão/estado inválido) |
| `loading` | Spinner | Desabilitado durante processamento |
| `success` | Check verde | Feedback temporário |

---

## 6. Integração com v45

### 6.1 Mapeamento de Campos

| v46 (Dashboard) | v45 (Policy) | Notas |
|-----------------|--------------|-------|
| `rollout_mode: "AUTO"` | `rollout_mode: "auto"` | Uppercase para UI |
| `rollout_mode: "MANUAL"` | `rollout_mode: "manual"` | Uppercase para UI |
| `rollout_mode: "SUPERVISED"` | — | **Novo no v46** |
| `status: "promoted"` | State Machine: PROMOTED | Derivado |
| `status: "blocked"` | State Machine: EVALUATING + gates falhos | Derivado |
| `status: "rolled_back"` | State Machine: ROLLED_BACK | Derivado |
| `status: "pending_review"` | — | **Novo no v46** (SUPERVISED mode) |
| `status: "evaluating"` | State Machine: EVALUATING | Derivado |
| `timeline[]` | `decision_history[]` | Formato estendido |
| `can_rollback` | Computado | Baseado em estado + cooldown |

### 6.2 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│                    v45 Auto-Rollout Policy                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Policy Store │  │ State Machine│  │ Decision Engine      │   │
│  │ (Redis/PG)   │  │              │  │ (Gates/Evaluation)   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                     │               │
│         └─────────────────┼─────────────────────┘               │
│                           │                                     │
│                           ▼                                     │
│                  ┌─────────────────┐                            │
│                  │  Policy Service │                            │
│                  │  (Internal API) │                            │
│                  └────────┬────────┘                            │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            │ Transform/Mapear
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    v46 Rollout Dashboard API                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ /rollout-dashboard│  │ /approve        │  │ /rollback       │  │
│  │ (List Policies) │  │ (Approval)      │  │ (Emergency)     │  │
│  └────────┬────────┘  └─────────────────┘  └─────────────────┘  │
│           │                                                      │
│           │                                                      │
│  ┌────────┴────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ RolloutPolicy   │  │ ApprovalRequest │  │ Telemetry       │  │
│  │ (Response DTO)  │  │ (Validation)    │  │ (Events)        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ REST API v2
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (RolloutDashboard.tsx)               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Policy Table    │  │ Approval Modal  │  │ Timeline View   │  │
│  │ (List View)     │  │ (Actions)       │  │ (History)       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Compatibilidade

- **v45 continua funcionando:** O v46 é uma camada de UI/API em cima do v45
- **Migration path:** Políticas v45 são automaticamente compatíveis
- **Nova funcionalidade:** Modo SUPERVISED e approvals são adições ao v45

---

## Appendix A: Exemplo Completo de Resposta API

```json
{
  "policies": [
    {
      "experiment_id": "exp_onboarding_v2",
      "policy_version": "1.0.0",
      "active_variant": "treatment",
      "rollout_mode": "SUPERVISED",
      "status": "pending_review",
      "created_at": "2026-03-01T10:00:00Z",
      "updated_at": "2026-03-05T09:00:00Z",
      "last_evaluation_at": "2026-03-05T08:45:00Z",
      "decision_reason": "All gates passed, awaiting manual approval",
      "decision_trigger": "threshold",
      "rollback_target": "control",
      "auto_rollback_enabled": true,
      "can_rollback": true,
      "timeline": [
        {
          "timestamp": "2026-03-01T10:00:00Z",
          "action": "evaluation_started",
          "reason": "Experiment started in SUPERVISED mode"
        },
        {
          "timestamp": "2026-03-05T08:45:00Z",
          "action": "blocked",
          "variant_id": "treatment_v2",
          "reason": "All gates passed - awaiting approval",
          "gates_passed": ["min_gain", "stability", "risk", "ttfv_regression"],
          "metrics_snapshot": {
            "control_score": 0.82,
            "treatment_score": 0.84,
            "confidence": 0.96
          }
        }
      ],
      "metrics": {
        "total_evaluations": 45,
        "sample_size": 302,
        "sample_size_control": 150,
        "sample_size_treatment": 152,
        "success_rate": 0.847,
        "avg_latency_ms": 245,
        "error_rate": 0.003,
        "control_score": 0.82,
        "treatment_score": 0.84,
        "relative_gain": 1.024
      },
      "gates_status": {
        "min_gain": {
          "passed": true,
          "threshold": 1.005,
          "actual": 1.024
        },
        "stability": {
          "passed": true,
          "confidence": 0.96,
          "sample_size": 302
        },
        "risk": {
          "passed": true,
          "completion_ok": true,
          "abandonment_ok": true
        },
        "ttfv_regression": {
          "passed": true,
          "increase_ratio": 1.02
        }
      }
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 50,
    "offset": 0,
    "has_more": false
  },
  "updated_at": "2026-03-05T10:30:00Z"
}
```

---

## Appendix B: Changelog

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-03-05 | Growth Eng | Versão inicial do contrato v46 |

---

## Appendix C: Referências

- [v45 Auto-Rollout Policy Contract](./v45_auto_rollout_policy.md)
- [RFC-43: Onboarding Guardrails](./v43_onboarding_guardrails.md)
- [RFC-44: Onboarding Experiments](./v44_onboarding_experiments.md)
- Frontend: `09-tools/web/vm-ui/src/pages/RolloutDashboard.tsx`
