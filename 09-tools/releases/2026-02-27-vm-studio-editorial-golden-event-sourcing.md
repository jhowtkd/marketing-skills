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
