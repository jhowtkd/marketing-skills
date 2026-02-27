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

---

## Governança v8: Forecast Preditivo + Priorização Automática

### Overview
Forecast determinístico e explicável para avaliação de risco editorial, combinado com priorização automática de ações baseada em impacto e esforço.

---

### A) Forecast Preditivo (Backend)

#### Módulo `editorial_forecast.py`
Motor de forecast determinístico sem ML externo:

```python
from vm_webapp.editorial_forecast import calculate_forecast, EditorialForecast

forecast = calculate_forecast(insights_data)
# forecast.risk_score: 0-100
# forecast.trend: improving|stable|degrading
# forecast.drivers: list[str]
# forecast.recommended_focus: str
```

#### Heurísticas de Risco
| Fator | Threshold | Score | Driver |
|-------|-----------|-------|--------|
| baseline_none_rate | > 70% | +40 | baseline_none_rate_critical |
| baseline_none_rate | > 50% | +30 | baseline_none_rate_high |
| baseline_none_rate | > 30% | +15 | baseline_none_rate_moderate |
| policy_denials | > 5 | +25 | policy_denials_critical |
| policy_denials | > 0 | +15 | policy_denials_present |
| recency_gap | > 14 dias | +25 | recency_gap_large |
| recency_gap | > 7 dias | +15 | recency_gap_moderate |
| no_golden_marks | any | +40 | no_golden_marks |
| low_global_coverage | < 20% | +15 | low_global_coverage |

#### Endpoint
**GET /api/v2/threads/{thread_id}/editorial-decisions/forecast**

Response:
```json
{
  "thread_id": "thread-xxx",
  "risk_score": 65,
  "trend": "degrading",
  "drivers": ["baseline_none_rate_high", "recency_gap_moderate"],
  "recommended_focus": "Aumentar cobertura de golden",
  "generated_at": "2026-02-27T18:00:00Z"
}
```

#### Trend Detection
- **improving**: marcações recentes (< 3 dias) OU baseline_none_rate < 30%
- **degrading**: sem marcas OU denials > 3
- **stable**: outros casos

#### Test Coverage
- `test_editorial_forecast_endpoint_returns_risk_assessment`: contrato
- `test_editorial_forecast_returns_404_for_unknown_thread`: error handling

---

### B) Priorização Automática de Ações

#### Atributos de Prioridade
Cada recomendação agora inclui:

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `impact_score` | int (1-10) | Impacto da ação no sistema |
| `effort_score` | int (1-10) | Esforço necessário para execução |
| `priority_score` | int | Calculado: impact * 10 - effort * 3 |
| `why_priority` | string | Explicação legível da prioridade |

#### Action Metadata
```python
ACTION_METADATA = {
    "create_objective_golden": {"impact": 9, "effort": 4},
    "create_global_golden": {"impact": 8, "effort": 6},
    "review_brand_policy": {"impact": 7, "effort": 8},
    "run_editorial_review": {"impact": 8, "effort": 5},
}
```

#### Ordenação
Recomendações ordenadas por `priority_score` descendente:
```python
recommendations.sort(key=lambda r: r.priority_score, reverse=True)
```

#### Test Coverage
- `test_editorial_recommendations_include_priority_scores`: campos presentes
- `test_editorial_recommendations_ordered_by_priority_desc`: ordenação

---

### C) UI de Forecast + Priorização (Studio)

#### Tipos Atualizados (`useWorkspace.ts`)
```typescript
type EditorialRecommendation = {
  // ... campos existentes
  impact_score: number;
  effort_score: number;
  priority_score: number;
  why_priority: string;
};

type EditorialForecast = {
  thread_id: string;
  risk_score: number;
  trend: "improving" | "stable" | "degrading";
  drivers: string[];
  recommended_focus: string;
  generated_at: string;
};
```

#### Estado Adicionado
```typescript
const [editorialForecast, setEditorialForecast] = useState<EditorialForecast | null>(null);
const [loadingForecast, setLoadingForecast] = useState(false);
```

#### Forecast Panel
Exibe:
- **Risk Score**: 0-100 com cor (verde/amarelo/vermelho)
- **Trend**: ícone + label localizado (📈 Melhorando, 📉 Degradando, ➡️ Estável)
- **Drivers**: lista de fatores de risco
- **Recommended Focus**: ação sugerida

#### Recommendation Badges
Para cada recomendação:
- **Rank**: #1, #2, #3...
- **Impact Badge**: Alto/Médio/Baixo + valor
- **Effort Badge**: Alto/Médio/Baixo + valor
- **Priority Score**: valor calculado
- **Why Priority**: explicação em tooltip

#### Test Coverage
- `WorkspaceEditorialForecast.test.tsx`: 17 testes
  - Loading, empty, e estados com dados
  - Cores de risco (red/yellow/green)
  - Labels de trend
  - Badges de impacto/esforço

---

### D) Report Noturno com Forecast Delta

#### Script Atualizado (`editorial_ops_report.py`)
Novas opções:
```bash
--forecasts-file FORECASTS_FILE     # Dados de forecast
--previous-report PREVIOUS_REPORT   # Cálculo de delta
```

#### Delta Calculation
| Indicador | Significado |
|-----------|-------------|
| 📈 +N | Risco aumentou significativamente (> 5 pontos) |
| 📉 -N | Risco diminuiu significativamente (< -5 pontos) |
| ➡️ stable | Risco estável (± 5 pontos) |
| 🆕 new | Thread novo (sem histórico) |

#### Top 3 Threads de Maior Risco
Report destaca:
```markdown
## ⚠️ Top 3 Threads by Risk

### 1. thread-xxx
- **Risk Score:** 75/100
- **Trend:** 📉 degrading
- **Recommended Focus:** Criar golden references urgentemente
```

#### Workflow Atualizado
Passos adicionados:
1. Coleta de forecasts para cada thread
2. Download do report anterior (para delta)
3. Cálculo de deltas e ordenação por risco
4. Geração de relatório com seções Forecast e Top Risks

---

## Métricas de Editorial (v8 - Adicionadas)

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `editorial_forecast_requested_total` | Counter | Total de requests de forecast |

---

## Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| Backend API v2 | 42 (+2) | PASS |
| Backend Editorial Forecast | 2 | PASS |
| Backend Editorial Recommendations | 2 | PASS |
| Frontend Workspace | 66 (+17) | PASS |

### Novos Testes v8
- Backend Forecast: +2 (endpoint + error handling)
- Backend Prioritization: +2 (scores + ordenação)
- Frontend Forecast: +17 (panel + badges)

---

## CI Gates (atualizados)

### editorial-ops-nightly
```yaml
- Collect insights AND forecasts
- Download previous report for delta
- Generate report with --forecasts-file and --previous-report
- Highlight top 3 risk threads
```

---

## Commits v8
1. `feat(forecast): add deterministic editorial risk forecast endpoint`
2. `feat(editorial): prioritize recommended actions by impact and effort`
3. `feat(vm-ui): add editorial forecast panel and prioritized recommended actions`
4. `ci(observability): include forecast deltas in nightly editorial ops report`
5. `docs(release): append governance v8 forecast and action prioritization notes`
