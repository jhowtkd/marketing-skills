# Release: VM Studio Editorial Golden (Event-Sourcing)

**Data:** 2026-02-27  
**Versão:** Editorial Golden Decision (Event-Sourcing)  
**Status:** ✅ Released

---

## Resumo

Implementação completa do sistema de decisão editorial auditável (golden global + golden por objetivo) com baseline oficial `objective > global > previous` no backend e frontend do VM Studio.

---

## Problema Resolvido

Antes desta release, o baseline de comparação no Studio era sempre implícito ("versão anterior"). Faltava:

1. Decisão editorial explícita, auditável e reproduzível
2. Separação entre "melhor versão geral" vs "melhor versão para um objetivo específico"
3. Rastreabilidade de quem marcou o quê, quando e por quê

Agora, editores podem marcar versões como "golden" com justificativa obrigatória, e o sistema automaticamente resolve o baseline correto seguindo a prioridade oficial.

---

## Endpoints Novos

### POST /api/v2/threads/{thread_id}/editorial-decisions/golden

Marca uma versão como golden (global ou por objetivo).

**Request:**
```json
{
  "run_id": "run-abc123",
  "scope": "objective",
  "objective_key": "campanha-lancamento-q1-9f3a2b1c",
  "justification": "Melhor clareza de CTA e estrutura final."
}
```

**Response:**
```json
{
  "event_id": "evt-xyz789",
  "thread_id": "t-123",
  "run_id": "run-abc123",
  "scope": "objective",
  "objective_key": "campanha-lancamento-q1-9f3a2b1c"
}
```

**Validações:**
- `justification` obrigatória (422 se vazia)
- `scope=objective` exige `objective_key` (422 se ausente)
- `run_id` deve pertencer ao `thread_id` (404 se inválido)
- Idempotente via header `Idempotency-Key`

### GET /api/v2/threads/{thread_id}/editorial-decisions

Lista as decisões editoriais atuais do thread.

**Response:**
```json
{
  "global": {
    "run_id": "run-abc123",
    "justification": "best overall",
    "updated_at": "2026-02-27T10:00:00Z"
  },
  "objective": [
    {
      "objective_key": "campanha-lancamento-q1-9f3a2b1c",
      "run_id": "run-def456",
      "justification": "best for this objective",
      "updated_at": "2026-02-27T11:00:00Z"
    }
  ]
}
```

### GET /api/v2/workflow-runs/{run_id}/baseline

Retorna o baseline resolvido para uma run específica.

**Response:**
```json
{
  "run_id": "run-atual",
  "baseline_run_id": "run-referencia",
  "source": "objective_golden",
  "objective_key": "campanha-lancamento-q1-9f3a2b1c"
}
```

**Sources possíveis:**
- `objective_golden` - Versão golden do mesmo objetivo
- `global_golden` - Versão golden global
- `previous` - Versão anterior na lista
- `none` - Sem baseline disponível

---

## Mudanças de UX

### Badges de Golden

Cada card de versão agora exibe badges quando marcado como golden:
- **Golden global** (badge âmbar) - Melhor versão geral do job
- **Golden objetivo** (badge azul) - Melhor versão para este objetivo específico

### Botões de Ação

Na versão ativa, novos botões permitem:
- "Definir como golden global"
- "Definir como golden deste objetivo"

Ambos abrem modal com textarea obrigatória para justificativa.

### Label de Baseline

O painel de comparação agora exibe a fonte real do baseline:
- "Comparando com: Golden deste objetivo"
- "Comparando com: Golden global"
- "Comparando com: Versao anterior"
- "Sem versao anterior para comparar"

### Fallback Local

Se os endpoints de baseline falharem (ex: offline), o sistema automaticamente cai para cálculo local (versão anterior por posição), garantindo que a UX continue funcional.

---

## Arquitetura

### Event-Sourcing

```
Comando (mark_editorial_golden)
    ↓
Evento EditorialGoldenMarked → event_log
    ↓
Projector → editorial_decisions_view (read model)
    ↓
Resolver: objective > global > previous
```

### Models

- `EditorialDecisionView` - Read model materializado
- `derive_objective_key()` - Derivação determinística da chave de objetivo
- `resolve_baseline()` - Algoritmo de prioridade único

### Frontend

- `useWorkspace()` - Carrega editorial decisions e baseline
- `GoldenDecisionModal` - Modal de justificativa
- `isGoldenForRun()` - Helper para badges
- `toBaselineSourceLabel()` - Labels traduzidos

---

## Evidências de Testes

### Backend

```bash
PYTHONPATH=09-tools .venv/bin/python -m pytest \
  09-tools/tests/test_vm_webapp_editorial_decisions.py \
  09-tools/tests/test_vm_webapp_projectors_v2.py \
  09-tools/tests/test_vm_webapp_commands_v2.py \
  09-tools/tests/test_vm_webapp_api_v2.py -v
```

**Resultado: 26 passed**

Cobertura:
- Derivação de objective_key estável
- Resolução de baseline com prioridade
- Projeção de eventos para read model
- Idempotência do comando
- Validações de API (422, 404)
- Contrato aditivo (objective_key em runs)

### Frontend

```bash
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/
```

**Resultado: 31 passed (10 test files)**

Cobertura:
- Carregamento de editorial decisions
- Fallback local quando API falha
- Modal bloqueia submit sem justificativa
- Badges renderizam corretamente
- Label de baseline reflete source real

### Build

```bash
cd 09-tools/web/vm-ui && npm run build
```

**Resultado: ✓ built in 617ms**

---

## Arquivos Alterados

### Backend

```
09-tools/vm_webapp/editorial_decisions.py                    (novo)
09-tools/tests/test_vm_webapp_editorial_decisions.py         (novo)
09-tools/vm_webapp/models.py                                 (+ EditorialDecisionView)
09-tools/vm_webapp/projectors_v2.py                          (+ handler EditorialGoldenMarked)
09-tools/vm_webapp/repo.py                                   (+ list_editorial_decisions_view)
09-tools/tests/test_vm_webapp_projectors_v2.py               (+ teste de projeção)
09-tools/vm_webapp/commands_v2.py                            (+ mark_editorial_golden_command)
09-tools/tests/test_vm_webapp_commands_v2.py                 (+ teste de idempotência)
09-tools/vm_webapp/api.py                                    (+ endpoints editorial decisions, baseline)
09-tools/vm_webapp/workflow_runtime_v2.py                    (+ objective_key no plan.json)
09-tools/tests/test_vm_webapp_api_v2.py                      (+ testes Task 4 e Task 5)
```

### Frontend

```
09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts                    (+ editorial decisions, baseline, markGoldenDecision)
09-tools/web/vm-ui/src/features/workspace/presentation.ts                    (+ helpers baseline, isGoldenForRun)
09-tools/web/vm-ui/src/features/workspace/GoldenDecisionModal.tsx            (novo)
09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx                 (+ badges, botões golden, baseline label)
09-tools/web/vm-ui/src/features/workspace/useWorkspace.editorialDecision.test.tsx (novo)
09-tools/web/vm-ui/src/features/workspace/WorkspaceGoldenDecisionFlow.test.tsx    (novo)
```

---

## Riscos Residuais

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Objective key collision | Baixa | Médio | Hash SHA-1 na derivação |
| Performance em threads com muitas runs | Baixa | Baixo | Indexação no banco |
| Concorrência no mesmo stream | Baixa | Médio | Versionamento do event log |

---

## Rollback

Esta release é **backwards compatible**:
- Clientes antigos ignoram campos novos
- Endpoints novos são aditivos
- Não há migração de dados necessária

Para rollback: remover código dos 3 arquivos principais do backend (api.py, commands_v2.py, projectors_v2.py) e do frontend (useWorkspace.ts, WorkspacePanel.tsx).

---

## Próximos Passos Sugeridos

1. **Política de permissões** - Restringir marcação golden a roles específicos
2. **Timeline de golden** - Mostrar histórico de mudanças de golden no frontend
3. **Métricas** - Track usage de golden decisions para analytics

---

## Commits

```
2cc1e7c feat(vm-runtime): add editorial baseline resolver and objective-key derivation
6388d8d feat(api-v2): project editorial golden decisions into read model
13e8911 feat(api-v2): add idempotent command for editorial golden marking
d9d8116 feat(api-v2): add editorial decisions endpoints for golden marks
7fc0afd feat(vm-runtime): expose objective_key and resolved baseline for workflow runs
972627e feat(vm-ui): load editorial decisions and resolved baseline in workspace hook
81a2d8d feat(vm-ui): add golden decision modal, badges, and baseline source labels
```

---

**Aprovado para release.** ✅
