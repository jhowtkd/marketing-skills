# Governança Editorial v5

## Overview
Release focada em governança editorial multi-tenant com policy configurável por brand e painel de auditoria no Studio.

---

## Governança v5: Multitenant Policy + Studio Audit UI

### A) Policy Multi-tenant por Brand

#### Modelo de Dados
Tabela `editorial_policies`:
```sql
brand_id (PK)                    -- Identificador da brand
editor_can_mark_objective (bool) -- Default: true
editor_can_mark_global (bool)    -- Default: false
updated_at (timestamp)           -- Última atualização
```

#### Endpoints

**GET /api/v2/brands/{brand_id}/editorial-policy**
- Retorna a policy da brand (ou defaults se não configurada)
- Response:
```json
{
  "brand_id": "brand-xxx",
  "editor_can_mark_objective": true,
  "editor_can_mark_global": false,
  "updated_at": "2026-02-27T10:30:00Z"
}
```

**PUT /api/v2/brands/{brand_id}/editorial-policy**
- Requer: header `Authorization: Bearer <actor>:admin` (apenas admin)
- Requer: header `Idempotency-Key` (idempotência obrigatória)
- Request:
```json
{
  "editor_can_mark_objective": true,
  "editor_can_mark_global": false
}
```

#### Lógica de Autorização
- **Admin**: sempre pode marcar golden (global e objective)
- **Editor**: depende das flags da policy da brand
  - `editor_can_mark_objective: true` -> pode marcar objective
  - `editor_can_mark_global: true` -> pode marcar global
- **Viewer**: nunca pode marcar golden

#### Test Coverage
- `test_get_editorial_policy_endpoint_returns_defaults`: defaults seguros
- `test_put_editorial_policy_requires_admin_role`: RBAC no gerenciamento
- `test_put_editorial_policy_requires_idempotency_key`: idempotência
- `test_put_editorial_policy_persists_changes`: persistência
- `test_editorial_policy_is_idempotent`: comportamento idempotente
- `test_mark_golden_uses_brand_policy`: integração com mark golden

---

### B) Evaluador de Policy Isolado

#### Módulo `editorial_policy.py`
Extrai a lógica de autorização para módulo dedicado e testável:

```python
from vm_webapp.editorial_policy import PolicyEvaluator, Role, Scope, BrandPolicy

evaluator = PolicyEvaluator()
result = evaluator.evaluate(role=Role.EDITOR, scope=Scope.OBJECTIVE)
# result.allowed: bool
# result.reason: str
```

#### Características
- **Determinístico**: mesma entrada sempre produz mesma saída
- **Type-safe**: enums para Role e Scope
- **Extensível**: Protocol `PolicyStore` permite diferentes backends
- **Safe fallback**: retorna defaults quando policy não existe

#### Factory Function
```python
from vm_webapp.editorial_policy import create_evaluator_from_session

evaluator = create_evaluator_from_session(session, brand_id="brand-xxx")
result = evaluator.evaluate(role="editor", scope="global", brand_id="brand-xxx")
```

#### Test Coverage (Matrix Completa)
| Role   | Scope     | Policy Flags              | Expected |
|--------|-----------|---------------------------|----------|
| admin  | global    | any                       | allow    |
| admin  | objective | any                       | allow    |
| viewer | global    | any                       | deny     |
| viewer | objective | any                       | deny     |
| editor | objective | editor_can_mark_objective=true  | allow    |
| editor | objective | editor_can_mark_objective=false | deny     |
| editor | global    | editor_can_mark_global=true     | allow    |
| editor | global    | editor_can_mark_global=false    | deny     |

- `test_policy_evaluator_admin_can_global`: admin permissões
- `test_policy_evaluator_viewer_cannot_any_scope`: viewer restrições
- `test_policy_evaluator_editor_can_objective_with_default_policy`: defaults
- `test_policy_evaluator_editor_cannot_global_with_default_policy`: defaults
- `test_policy_evaluator_editor_can_global_when_policy_allows`: policy override
- `test_policy_evaluator_editor_cannot_objective_when_policy_denies`: policy deny
- `test_policy_evaluator_fallback_to_default_when_store_none`: fallback seguro
- `test_policy_evaluator_fallback_to_default_when_brand_id_none`: fallback seguro
- `test_policy_evaluator_fallback_to_default_when_policy_not_found`: fallback seguro
- `test_policy_matrix_all_combinations`: matrix completa documentada

---

### C) UI de Auditoria no Studio

#### Endpoint Consumido
`GET /api/v2/threads/{thread_id}/editorial-decisions/audit`

Query params:
- `scope`: filtro por escopo (`all` | `global` | `objective`)
- `limit`: paginação (default: 50)
- `offset`: paginação (default: 0)

Response:
```json
{
  "thread_id": "thread-xxx",
  "events": [
    {
      "event_id": "evt-xxx",
      "event_type": "EditorialGoldenMarked",
      "actor_id": "user-xxx",
      "actor_role": "admin",
      "scope": "global",
      "objective_key": null,
      "run_id": "run-xxx",
      "justification": "Melhor versao ate agora",
      "occurred_at": "2026-02-27T10:30:00Z"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

#### Componente EditorialAuditSection
Localizado em `WorkspacePanel.tsx`, exibe:

**Filtros por Scope**
- Botões: "Todos" | "Global" | "Objetivo"
- Atualiza query params e reseta offset

**Lista de Eventos**
Para cada evento exibe:
- Tipo (Golden Global / Golden Objetivo) com cor diferenciada
- Run ID (truncado)
- Actor ID + Role localizada
- Objective Key (se scope=objective)
- Justificativa em itálico
- Timestamp formatado (pt-BR)

**Paginação**
- Botões "Anterior" / "Próximo"
- Info: "1-20 de 42"
- Controles disabled nos limites

#### State Management
Hook `useWorkspace` exporta:
```typescript
{
  editorialAudit: EditorialAuditResponse | null;
  auditScopeFilter: "all" | "global" | "objective";
  setAuditScopeFilter: (scope) => void;
  auditPagination: { limit: number; offset: number };
  setAuditPagination: (pagination) => void;
  refreshEditorialAudit: (params?) => Promise<void>;
}
```

#### Helpers de Presentation
- `formatAuditEvent`: formata evento API para display
- `toHumanActorRole`: localiza roles (admin→Administrador)
- `AUDIT_SCOPE_FILTER_LABELS`: labels dos filtros

#### Test Coverage
- `formatAuditEvent formats global scope event correctly`: formatação
- `formatAuditEvent formats objective scope event with objective_key`: formatação
- `toHumanActorRole translates known roles`: localização
- `renders events with correct formatting`: renderização
- `calls onScopeChange when filter button clicked`: interação
- `handles pagination correctly`: paginação

---

## Métricas de Editorial (atualizadas)

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `editorial_golden_marked_total` | Counter | Total de marcações golden |
| `editorial_golden_marked_scope:global` | Counter | Golden global |
| `editorial_golden_marked_scope:objective` | Counter | Golden por objetivo |
| `editorial_golden_policy_denied_total` | Counter | Tentativas negadas por policy |
| `editorial_golden_policy_denied_role:{role}` | Counter | Denial por role |
| `editorial_golden_policy_denied_scope:{scope}` | Counter | Denial por scope |
| `editorial_baseline_resolved_total` | Counter | Total de resoluções de baseline |
| `editorial_baseline_source:objective_golden` | Counter | Baseline de golden objetivo |
| `editorial_baseline_source:global_golden` | Counter | Baseline de golden global |
| `editorial_baseline_source:previous` | Counter | Baseline de versão anterior |
| `editorial_baseline_source:none` | Counter | Sem baseline disponível |
| `editorial_decisions_list_total` | Counter | Listagens de decisões |

---

## Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| Backend API v2 | 40 | PASS |
| Backend Editorial Policy | 22 | PASS |
| Frontend Workspace | 49 | PASS |

### Novos Testes v5
- Backend Policy: +15 (matrix completa + integração)
- Backend API: +0 (reutiliza testes existentes)
- Frontend Audit UI: +9 (novo componente)

---

## CI Gates

### editorial-policy-gate-v5
```yaml
- uv run pytest 09-tools/tests/test_vm_webapp_editorial_policy.py -q
- uv run pytest 09-tools/tests/test_vm_webapp_api_v2.py -k "editorial" -q
```

### frontend-gate (atualizado)
```yaml
- npm run test -- --run ... EditorialAuditPanel.test.tsx
```

---

## Migration Notes
- **Nova tabela**: `editorial_policies` criada automaticamente via SQLAlchemy
- **Defaults seguros**: sem migration, brands sem policy usam defaults
- **Backward compatible**: endpoints de mark golden continuam funcionando
- **Frontend**: novo painel aparece automaticamente no Studio

---

## Commits
1. `feat(policy): add brand-scoped editorial policy with admin-managed endpoints`
2. `test(policy): add deterministic policy matrix coverage for editorial decisions`
3. `feat(vm-ui): add editorial audit panel with scope filter and pagination`
4. `ci(vm-webapp): gate multi-tenant editorial policy and audit coverage`
5. `docs(release): append governance v5 multitenant policy and studio audit ui`
