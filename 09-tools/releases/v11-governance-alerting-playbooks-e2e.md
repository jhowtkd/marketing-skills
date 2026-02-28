# Governança Editorial v11 - SLO Alerts Hub, Playbook Chain & Control Center

## Overview
Release focada em alertas operacionais inteligentes, execução segura de cadeias de playbooks e centralização do controle no Studio Control Center. Inclui testes E2E completos para garantir confiabilidade end-to-end.

---

## Release Date
**2026-02-27**

---

## Sumário Executivo

A v11 eleva a governança editorial para um nível proativo e autônomo:

- **SLO Alerts Hub v2**: Agregador determinístico de alertas de múltiplas fontes (SLO violations, drift detection, baseline-none, policy-denied, forecast risk)
- **Playbook Chain**: Execução segura e ordenada de ações com kill-switch, rate-limit, cooldown e idempotência garantida
- **Control Center**: Painel unificado de alertas com execução de playbooks em 1 clique
- **E2E Coverage**: Testes end-to-end completos validando fluxos críticos

---

## A) SLO Alerts Hub v2

### Implementação
- **Módulo**: `vm_webapp/alerts_v2.py`
- **Endpoint**: `GET /api/v2/threads/{thread_id}/alerts`
- **Agregação**: Combina múltiplas fontes de alertas em lista única ordenada por severidade

### Fontes de Alertas

| Tipo | Condição | Severidade |
|------|----------|------------|
| `slo_violation` | baseline_none_rate > 70% | critical |
| `slo_violation` | baseline_none_rate > 50% | warning |
| `baseline_none` | baseline_none_rate > 30% | info |
| `policy_denied` | denied_rate > 25% OU denied > 10 | critical |
| `policy_denied` | denied_rate > 15% OU denied > 5 | warning |
| `policy_denied` | denied > 0 | info |
| `drift_detected` | drift_severity = high | critical |
| `drift_detected` | drift_severity = medium | warning |
| `drift_detected` | drift_severity = low | info |
| `forecast_risk` | risk_score > 70 + trend=degrading | critical |
| `forecast_risk` | risk_score > 50 | warning |
| `forecast_risk` | risk_score > 30 | info |

### Contrato Response
```json
{
  "thread_id": "string",
  "alerts": [
    {
      "alert_id": "alert-baseline_none-critical-20260227120000",
      "alert_type": "slo_violation",
      "severity": "critical",
      "status": "active",
      "title": "Taxa de Baseline None Crítica",
      "description": "75% das resoluções de baseline estão sem referência (3/4).",
      "causa": "baseline_none_rate_exceeded",
      "recomendacao": "Criar golden references urgentemente para estabilizar o baseline.",
      "created_at": "2026-02-27T12:00:00+00:00",
      "updated_at": "2026-02-27T12:00:00+00:00",
      "metadata": {
        "thread_id": "thread-xxx",
        "rate": 0.75,
        "count": 3,
        "total": 4
      }
    }
  ],
  "total_count": 1,
  "by_severity": {
    "critical": 1,
    "warning": 0,
    "info": 0
  },
  "generated_at": "2026-02-27T12:00:00Z"
}
```

### Filtros Suportados
- Query param `?severity=critical` para filtrar por severidade
- Ordenação automática: critical > warning > info

### Test Coverage
- `test_alerts_endpoint_returns_404_for_unknown_thread`: valida 404 para thread inexistente
- `test_alerts_empty_for_thread_with_no_alerts`: estrutura correta mesmo sem dados
- `test_alerts_response_schema_validation`: schema completo de cada alerta
- `test_alerts_multiple_types_combined`: agregação de múltiplas fontes
- `test_alerts_severity_ordering`: ordenação por severidade
- `test_alerts_filter_by_severity`: filtro via query param
- `test_alerts_with_slo_violations`: detecção de violações SLO
- `test_alerts_with_drift_detection`: inclusão de alertas de drift
- `test_alerts_causa_e_recomendacao_presentes`: causa e recomendação em português

---

## B) Playbook Chain

### Implementação
- **Módulo**: `vm_webapp/playbook_chain.py`
- **Endpoint**: `POST /api/v2/threads/{thread_id}/playbooks/execute`
- **Executor**: `PlaybookChainExecutor` com controles de segurança

### Features de Segurança

| Feature | Descrição | Comportamento |
|---------|-----------|---------------|
| **Idempotência** | Mesma chave = mesmo resultado | Cache de execuções por idempotency key |
| **Kill-switch** | Parada emergencial | Bloqueia novas execuções quando ativo (503) |
| **Rate-limit** | Delay entre steps | Configurável em ms entre ações |
| **Cooldown** | Intervalo entre execuções | Prevents execuções duplicadas do mesmo playbook |
| **Stop-on-error** | Falha segura | Para execução quando step falha |
| **Suppression** | Condicional execution | Pula ação quando condição atendida |

### Ações Válidas
- `open_review_task`: Cria tarefa de revisão editorial
- `prepare_guided_regeneration`: Prepara contexto para regeneração guiada
- `suggest_policy_review`: Sugere revisão de policy da brand

### Contrato Request/Response
```json
// Request
POST /api/v2/threads/{thread_id}/playbooks/execute
Headers: Idempotency-Key: <string>

{
  "playbook_id": "recovery-chain",
  "chain_options": {
    "steps": [
      {"action": "open_review_task"},
      {"action": "prepare_guided_regeneration", "suppress_when": {"drift_severity": "none"}},
      {"action": "suggest_policy_review"}
    ],
    "stop_on_error": true,
    "kill_switch": false,
    "rate_limit_delay_ms": 100,
    "cooldown_seconds": 300
  }
}

// Response 200
{
  "execution_id": "exec-a1b2c3d4e5f67890",
  "status": "completed",
  "steps": [
    {
      "action": "open_review_task",
      "executed": true,
      "skipped": false,
      "error": null,
      "motivo": "Ação 'open_review_task' executada com sucesso"
    },
    {
      "action": "prepare_guided_regeneration",
      "executed": false,
      "skipped": true,
      "error": null,
      "motivo": "Suprimido: condição 'drift_severity=none' atendida"
    },
    {
      "action": "suggest_policy_review",
      "executed": true,
      "skipped": false,
      "error": null,
      "motivo": "Ação 'suggest_policy_review' executada com sucesso"
    }
  ]
}

// Response 503 (kill-switch ativo)
{
  "detail": "Kill-switch ativo - execução bloqueada"
}

// Response 429 (cooldown)
{
  "detail": "Cooldown em efeito. Aguarde 245s"
}
```

### Status de Execução
- `completed`: Todos os steps executados com sucesso
- `partial`: Alguns steps falharam mas execução continuou (stop_on_error=false)
- `failed`: Execução parada devido a erro (stop_on_error=true)

### Test Coverage
- `test_playbook_chain_endpoint_returns_404_for_unknown_thread`: valida 404
- `test_playbook_chain_requires_playbook_id`: validação de campos obrigatórios
- `test_playbook_chain_returns_execution_id`: retorno de execution_id
- `test_playbook_chain_returns_steps_array`: array de resultados
- `test_playbook_chain_step_schema`: schema completo de steps
- `test_playbook_chain_executes_steps_in_order`: ordem definida
- `test_playbook_chain_is_idempotent_same_idempotency_key`: idempotência
- `test_playbook_chain_respects_global_kill_switch`: kill-switch (503)
- `test_playbook_chain_respects_rate_limit_between_steps`: rate limiting
- `test_playbook_chain_respects_cooldown`: cooldown entre execuções (429)
- `test_playbook_chain_suppresses_when_condition_met`: suppression condicional

---

## C) Control Center - Alert Panel

### Implementação
- **Componente**: `AlertPanel.tsx` em `web/vm-ui/src/features/workspace/components/`
- **Hook**: `useAlerts.ts` no mesmo diretório
- **Integração**: WorkspacePanel com aba dedicada

### Features do AlertPanel

| Feature | Descrição |
|---------|-----------|
| **Summary Cards** | Contagem por severidade (crítico, warning, info) |
| **Alert Cards** | Cada alerta com severidade visual, causa, recomendação |
| **Execução 1-Clique** | Botão "Executar cadeia recomendada" quando playbook_chain_id presente |
| **Feedback Visual** | Estados de loading, sucesso e erro na execução |
| **Dismiss** | Capacidade de dispensar alertas individuais |
| **Refresh** | Botão de atualização manual |
| **Empty State** | Mensagem positiva quando não há alertas |

### Hook useAlerts

```typescript
const {
  alerts,           // Alert[] - lista de alertas
  loading,          // boolean - estado de carregamento
  error,            // string | null - erro se houver
  executing,        // boolean - executando playbook
  fetchAlerts,      // () => Promise<void> - buscar alertas
  refreshAlerts,    // () => Promise<void> - recarregar
  executePlaybookChain, // (chainId, runId?) => Promise<PlaybookExecutionResult>
  criticalAlerts,   // Alert[] - apenas críticos
  hasAlerts,        // boolean - há alertas?
  alertCounts,      // { total, critical, warning, info }
} = useAlerts(threadId);
```

### Types
```typescript
type AlertSeverity = "critical" | "warning" | "info";

interface Alert {
  alert_id: string;
  severity: AlertSeverity;
  cause: string;
  recommendation: string;
  created_at: string;
  updated_at: string;
  playbook_chain_id?: string;  // Se presente, permite execução
}

interface PlaybookExecutionResult {
  status: "success" | "partial" | "failed";
  executed: string[];
  skipped: string[];
  errors?: Array<{ step: string; error: string }>;
  execution_id?: string;
}
```

### UI States
- **Loading**: Spinner com mensagem "Carregando alertas..."
- **Error**: Banner vermelho com botão "Tentar novamente"
- **Empty**: Emoji ✅ com mensagem "Nenhum alerta ativo"
- **Alerts List**: Cards com borda colorida por severidade

### Visualização por Severidade
| Severidade | Cor da Borda | Background Badge | Label |
|------------|--------------|------------------|-------|
| critical | red-500 | red-100/text-red-800 | Crítico |
| warning | yellow-500 | yellow-100/text-yellow-800 | Aviso |
| info | blue-500 | blue-100/text-blue-800 | Info |

### Test Coverage (Frontend)
- `AlertPanel.test.tsx`: renderização, estados, interações
- `useAlerts.test.ts`: hook behavior, fetch, execução

---

## D) E2E Evidence

### Test Suite: Event-Driven E2E
- **Arquivo**: `test_vm_webapp_event_driven_e2e.py`
- **Cobertura**: Fluxo completo de event-driven workflow

| Teste | Descrição |
|-------|-----------|
| `test_duplicate_idempotency_key_returns_same_event` | Idempotência de criação |
| `test_stream_conflict_returns_409` | Handlers de conflito |
| `test_approval_gate_blocks_agent_run_until_granted` | Gates de aprovação |
| `test_thread_workflow_request_generates_versioned_artifacts_and_timeline` | Artefatos versionados |
| `test_workflow_queue_is_idempotent_by_idempotency_key` | Idempotência de workflow |
| `test_any_mode_falls_back_to_foundation_and_completes_after_grant` | Fallback e completion |

### Test Suite: Playbook Chain E2E
- **Arquivo**: `test_vm_webapp_playbook_chain.py`
- **Cobertura**: Todos os cenários de execução

| Teste | Cenário |
|-------|---------|
| Endpoint contract tests | 404, 422, schema validation |
| Execution order | Ordem definida dos steps |
| Stop on error | Falha segura |
| Idempotency | Cache de execuções |
| Kill-switch | Parada emergencial (503) |
| Rate-limit | Delay entre steps |
| Cooldown | Intervalo entre execuções (429) |
| Suppressions | Execução condicional |

### Test Suite: Alerts v2 E2E
- **Arquivo**: `test_vm_webapp_alerts_v2.py`
- **Cobertura**: Agregação e schema de alertas

| Teste | Cenário |
|-------|---------|
| 404 para thread inexistente | Error handling |
| Empty state | Thread sem dados |
| Schema validation | Todos os campos obrigatórios |
| Multiple types combined | Agregação de fontes |
| Severity ordering | Ordenação correta |
| Filter by severity | Query params |
| SLO violations | Detecção de thresholds |
| Drift detection | Integração com drift |
| Metadata structure | Consistência de metadados |

---

## API Endpoints Novos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v2/threads/{thread_id}/alerts` | Lista alertas agregados |
| POST | `/api/v2/threads/{thread_id}/playbooks/execute` | Executa cadeia de playbook |

### Query Parameters
- `GET /alerts?severity=critical` - Filtra por severidade

### Headers Obrigatórios
- `Idempotency-Key` para POST /playbooks/execute

---

## Breaking Changes

**Nenhum breaking change.** Esta release é backward compatible:
- Novos endpoints adicionados, nenhum modificado
- Novos campos opcionais em responses existentes
- Frontend com graceful degradation

---

## Test Coverage Report

### Backend
| Suite | Tests | Status |
|-------|-------|--------|
| Alerts v2 | 12 | ✅ PASS |
| Playbook Chain | 16 | ✅ PASS |
| Event-Driven E2E | 6 | ✅ PASS |

### Frontend
| Suite | Tests | Status |
|-------|-------|--------|
| AlertPanel | 8 | ✅ PASS |
| useAlerts hook | 6 | ✅ PASS |
| Control Center Integration | 4 | ✅ PASS |

### Cobertura Total
- **Backend**: 34 novos testes
- **Frontend**: 18 novos testes
- **Total**: 52 testes adicionados

---

## Métricas de Operação

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `alerts_hub_requested_total` | Counter | Requisições ao hub de alertas |
| `alerts_hub_count:{n}` | Counter | Distribuição por quantidade |
| `playbook_chain_executed_total` | Counter | Execuções de chain |
| `playbook_chain_step_executed_total` | Counter | Steps executados |
| `playbook_chain_killswitch_active` | Gauge | Kill-switch ativo |
| `playbook_chain_cooldown_blocked_total` | Counter | Bloqueios por cooldown |

---

## Como Operar

### Visualizar Alertas
```bash
curl "http://localhost:8000/api/v2/threads/{thread_id}/alerts"
```

### Filtrar Alertas Críticos
```bash
curl "http://localhost:8000/api/v2/threads/{thread_id}/alerts?severity=critical"
```

### Executar Playbook Chain
```bash
curl -X POST \
  "http://localhost:8000/api/v2/threads/{thread_id}/playbooks/execute" \
  -H "Idempotency-Key: unique-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_id": "recovery-chain",
    "chain_options": {
      "steps": [
        {"action": "open_review_task"},
        {"action": "prepare_guided_regeneration"}
      ],
      "stop_on_error": true,
      "cooldown_seconds": 300
    }
  }'
```

### Verificar Status via UI
1. Acesse o Studio Control Center
2. Navegue até a aba "Alerts"
3. Visualize alertas ativos e suas severidades
4. Clique "Executar cadeia recomendada" para ações automáticas

---

## Limitações Conhecidas

1. **Ações de Playbook**: Apenas 3 ações implementadas (open_review_task, prepare_guided_regeneration, suggest_policy_review)
2. **Rate-limit**: Delay fixo entre steps, não adaptativo
3. **Cooldown Global**: Por playbook/thread, não por usuário
4. **Alert Dismissal**: Não persiste (recarrega ao refresh)
5. **Playbook Chain UI**: Requer refresh manual após execução

---

## Links para Documentação

- [Arquitetura do Sistema](../../ARCHITECTURE.md)
- [Quickstart](../../QUICKSTART.md)
- [Skill Principal](../../SKILL.md)
- [API v2 Documentation](../../docs/api/v2/)
- [Frontend Workspace](../../09-tools/web/vm-ui/src/features/workspace/)

---

## Commits

1. `feat(alerts): implement SLO Alerts Hub v2 (Task A)`
2. `feat(playbook-chain): implement Task B - Playbook Chain backend`
3. `feat(studio): add Alert Panel and useAlerts hook to Control Center (Task C)`
4. `test(e2e): add event-driven and playbook chain E2E tests`
5. `ci(vm-webapp): add v11 alerting and playbook gates to smoke workflow`

---

## Próximos Passos (v12)

- [ ] WebSocket para alertas em tempo real
- [ ] Playbook actions customizáveis via config
- [ ] Alert routing e notificações (email/Slack)
- [ ] Dashboard de métricas de alertas
- [ ] Machine learning para forecast de alertas
