# Governanca Editorial v6 - Insights Loop

## Overview
Release focada em fechar o ciclo de feedback operacional do sistema de governanca editorial, expondo KPIs acionaveis via endpoint dedicado e painel de insights no Studio.

---

## A) Reason Code Taxonomy

### Implementacao
- **Enum validado**: `clarity | structure | cta | persuasion | accuracy | tone | other`
- **Armazenamento**: reason_code persistido no payload do evento `EditorialGoldenMarked`
- **Validacao**: Pydantic Literal rejeita valores invalidos com 422

### Contrato
```python
POST /api/v2/threads/{thread_id}/editorial-decisions/golden
{
  "run_id": "string",
  "scope": "global | objective",
  "objective_key": "string | null",
  "justification": "string",
  "reason_code": "clarity | structure | cta | persuasion | accuracy | tone | other"
}
```

### Test Coverage
- `test_editorial_golden_accepts_reason_code`: valida aceitacao de cada reason_code
- `test_editorial_golden_validates_reason_code_enum`: valida 422 para codigo invalido
- `test_editorial_audit_includes_reason_code`: valida retorno no audit

---

## B) Insights Endpoint

### Implementacao
- **Endpoint**: `GET /api/v2/threads/{thread_id}/editorial-decisions/insights`
- **Fonte de dados**: event_log (TimelineItemView) - sem dependencias externas
- **Agregacao**: SQL count/group by comPython post-processing

### Response Contract
```json
{
  "thread_id": "string",
  "totals": {
    "marked_total": 0,
    "by_scope": {
      "global": 0,
      "objective": 0
    },
    "by_reason_code": {
      "clarity": 0,
      "structure": 0,
      "cta": 0,
      "persuasion": 0,
      "accuracy": 0,
      "tone": 0,
      "other": 0
    }
  },
  "policy": {
    "denied_total": 0
  },
  "baseline": {
    "resolved_total": 0,
    "by_source": {
      "objective_golden": 0,
      "global_golden": 0,
      "previous": 0,
      "none": 0
    }
  },
  "recency": {
    "last_marked_at": "2026-02-27T12:00:00Z | null",
    "last_actor_id": "string | null"
  }
}
```

### Test Coverage
- `test_editorial_insights_endpoint_returns_governance_kpis`: valida estrutura completa

---

## C) Painel de Insights no Studio

### Implementacao
- **Localizacao**: WorkspacePanel (abaixo da timeline e auditoria)
- **Hook**: `useWorkspace` integra `fetchEditorialInsights()`
- **Helpers**: `presentation.ts` com formatters para reason_code e datas

### KPIs Expostos
| Card | Metrica | Cor/Destaque |
|------|---------|--------------|
| Total de Marcacoes | `totals.marked_total` | - |
| Global vs Objetivo | `by_scope.global / objective` | Amber/Blue |
| Negados por Policy | `policy.denied_total` | Vermelho se > 0 |
| Sem Baseline | `% de by_source.none` | Alerta operacional |
| Motivo Principal | Top reason_code | Label em pt-BR |
| Ultima Marcacao | `recency.last_marked_at` | Data formatada pt-BR |

### UX Features
- Loading state com spinner
- Error state com retry
- Botao "Atualizar insights" para refresh manual
- Grid responsivo (1 col mobile, 2 col tablet, 4 col desktop)

### Test Coverage
- `WorkspacePanel.test.tsx`: valida renderizacao do painel

---

## D) Impacto Operacional

### Deny Tracking
- Contador de tentativas bloqueadas por policy
- Indicador visual em vermelho quando > 0
- Insight para ajuste fino de regras de policy

### Baseline None Rate
- Percentual de resolucoes sem baseline disponivel
- Indicador de cobertura insuficiente de golden
- Acionavel: time editorial deve marcar mais versoes golden

### Top Reason Code Distribution
- Identifica padroes de qualidade no conteudo
- Exemplo: se "clarity" lidera, time de conteudo deve focar em clareza
- Base para treinamentos direcionados

---

## Metricas de Editorial (atualizadas)

| Metrica | Tipo | Descricao |
|---------|------|-----------|
| `editorial_golden_marked_total` | Counter | Total de marcacoes golden |
| `editorial_golden_marked_scope:global` | Counter | Golden global |
| `editorial_golden_marked_scope:objective` | Counter | Golden por objetivo |
| `editorial_golden_reason:*` | Counter | Distribuicao por reason_code |
| `editorial_baseline_resolved_total` | Counter | Total de resolucoes de baseline |
| `editorial_baseline_source:*` | Counter | Por source (objective_golden, global_golden, previous, none) |
| `editorial_policy_denied_total` | Counter | Tentativas bloqueadas por policy |
| `editorial_insights_requested_total` | Counter | Chamadas ao endpoint insights |

---

## Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| Backend API v2 | 28 | PASS |
| Frontend Workspace | 72 | PASS |

### Novos Testes
- Backend: +1 (insights endpoint)
- Frontend: +4 (reason_code taxonomy x3, insights panel x1)

---

## Migration Notes
- Nenhuma migracao necessaria
- reason_code default: "other" para decisoes existentes
- Insights endpoint funciona com threads sem eventos (retorna zeros)

---

## Commits
1. `feat(reason_code): add taxonomy to golden mark payload with validation`
2. `feat(insights): add editorial insights endpoint with KPI aggregation`
3. `feat(studio): add editorial insights panel to workspace`
4. `ci(vm-webapp): gate editorial insights endpoint and ui coverage`


---

## Governança v7 (Automação Operacional)

### Overview
Release focada em automatizar ações operacionais baseadas em degradação de KPIs, permitindo recuperação com 1 clique e relatórios consolidados noturnos.

---

## A) Motor de Recomendações Automáticas

### Implementação
- **Módulo**: `vm_webapp/editorial_recommendations.py`
- **Endpoint**: `GET /api/v2/threads/{thread_id}/editorial-decisions/recommendations`
- **Análises implementadas**:
  - `baseline_none_rate` alto → recomenda "criar golden de objetivo"
  - `policy_denied_total` crescente → recomenda "revisar policy da brand"
  - Ausência de marcações recentes → recomenda "rodar revisão editorial"
  - Baixa cobertura global → recomenda "criar golden global"

### Contrato Response
```json
{
  "thread_id": "string",
  "recommendations": [
    {
      "severity": "info | warning | critical",
      "reason": "baseline_none_rate_high",
      "action_id": "create_objective_golden",
      "title": "Criar Golden de Objetivo",
      "description": "50% das resoluções estão sem referência..."
    }
  ],
  "generated_at": "2026-02-27T15:00:00Z"
}
```

### Severidades
| Severidade | Condição | Cor UI |
|------------|----------|--------|
| `critical` | baseline_none > 80% OU policy_denied > 10 | Vermelho |
| `warning` | baseline_none > 50% OU policy_denied > 3 | Âmbar |
| `info` | Outras recomendações | Cinza |

---

## B) Playbook de Recuperação (1 Clique)

### Implementação
- **Endpoint**: `POST /api/v2/threads/{thread_id}/editorial-decisions/playbook/execute`
- **Idempotency**: Obrigatório via header `Idempotency-Key`
- **Ações disponíveis**:
  - `open_review_task`: Cria tarefa de revisão editorial
  - `prepare_guided_regeneration`: Prepara contexto para regeneração guiada
  - `suggest_policy_review`: Sugere revisão de policy da brand

### Request/Response
```json
// Request
{
  "action_id": "open_review_task",
  "run_id": "run-xxx",
  "note": "Revisar estrutura do conteúdo"
}

// Response
{
  "status": "success",
  "executed_action": "open_review_task",
  "created_entities": [
    {"entity_type": "review_task", "entity_id": "r-123"}
  ],
  "event_id": "evt-xxx"
}
```

### Auditoria
- Evento `EditorialPlaybookExecuted` emitido na timeline
- Payload inclui `action_id`, `run_id`, `note`, `actor_role`

---

## C) Painel de Ações Recomendadas no Studio

### Implementação
- **Localização**: WorkspacePanel (após insights editoriais)
- **Hook**: `useWorkspace` expõe `recommendations`, `refreshRecommendations`, `executePlaybookAction`

### UI Features
| Feature | Descrição |
|---------|-----------|
| Loading state | Spinner durante carregamento |
| Empty state | Mensagem quando não há recomendações |
| Error state | Retry button em caso de falha |
| Severidade badges | Chips coloridos (critical=vermelho, warning=âmbar, info=cinza) |
| Botão Executar | 1 clique para executar ação do playbook |
| Refresh manual | Botão "Recarregar ações" |

### Estados
- `!hasActiveThread`: Mensagem "Escolha um job..."
- `loadingRecommendations`: Spinner
- `!recommendations`: Mensagem de erro com retry
- `recommendations.length === 0`: Mensagem informativa
- Lista de cards com severidade, título, descrição, motivo e botão executar

---

## D) Workflow Noturno de Relatório Consolidado

### Implementação
- **Arquivo**: `.github/workflows/vm-editorial-ops-nightly.yml`
- **Trigger**: Schedule (6 AM UTC) + workflow_dispatch
- **Script**: `scripts/editorial_ops_report.py`

### Funcionalidades
- Coleta insights por thread (via API interna)
- Agrega métricas: total marked, denied, baseline sources
- Calcula baseline_none_rate
- Gera relatório markdown com alertas automáticos
- Publica resumo no `GITHUB_STEP_SUMMARY`
- Upload de artifacts (markdown + JSON raw)

### Alertas Automáticos
| Condição | Alerta |
|----------|--------|
| baseline_none_rate > 30% | "⚠️ High baseline-none rate" |
| total_denied > 5 | "⚠️ Policy denials detected" |
| total_marked == 0 | "⚠️ No golden marks" |

### Formats de Saída
- `--format markdown`: Relatório human-readable (padrão)
- `--format json`: Estrutura para consumo programático

---

## Test Summary (v7)

| Suite | Tests | Status |
|-------|-------|--------|
| Backend API v2 | 48 | PASS |
| Frontend Workspace | 52 | PASS |

### Novos Testes
- Backend: +4 (recommendations endpoint, playbook execute, validation)
- Frontend: +3 (recommendations hook, panel, execute action)

---

## Migration Notes
- Nenhuma migração necessária
- Playbook actions são idempotentes via Idempotency-Key
- Relatório noturno inicia com dados vazios até threads serem configurados

---

## Commits v7
1. `feat(editorial): add automated governance recommendations endpoint`
2. `feat(editorial): add one-click recovery playbook execution endpoint`
3. `feat(vm-ui): add recommended actions panel with one-click recovery playbook`
4. `ci(observability): add nightly editorial ops consolidated report workflow`
5. `docs(release): append governance v7 automated actions and nightly ops reporting`
