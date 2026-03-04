# CI Final Stabilization Sprint - Design Document

> **Objetivo:** Migrar de ENCERRADO PARCIAL (75% melhor run) para ENCERRADO TOTAL (≥80% consistente)  
> **Data:** 2026-03-04  
> **Status:** Design Aprovado

---

## Contexto

A iniciativa "CI Main Green Hardening" foi encerrada parcialmente com:
- Melhor run: **75%** (18/24 gates)
- Média 5 runs: **62%**
- Meta de encerramento total: **≥80% consistente**
- 6 gates PRE_EXISTING ainda falham

### Gates a Corrigir

| # | Gate | Tipo de Falha | Estratégia |
|---|------|---------------|------------|
| 1 | safety-autotuning-gate-v17 | Arquivo inexistente | Remover referência |
| 2 | agent-dag-gate-v20 | Arquivo inexistente | Remover referência |
| 3 | first-run-quality-gate-v12 | Arquivo inexistente | Remover referência |
| 4 | quality-optimizer-gate-v25 | Teste específico inexistente | Remover referência |
| 5 | rollout-governance-gate-v15 | Requer triagem | Triagem + correção/escalar |
| 6 | onboarding-first-success-gate-v30 | Requer triagem | Triagem + correção/escalar |

---

## Arquitetura da Solução

### Estrutura de 2 Waves

```
Wave 1 (Correção Estrutural - Determinística)
├── safety-autotuning-gate-v17      [arquivo inexistente]
├── agent-dag-gate-v20              [arquivo inexistente]  
└── first-run-quality-gate-v12      [arquivo inexistente]

Wave 2 (Triagem e Correção Seletiva)
├── quality-optimizer-gate-v25      [triagem 5-10 min]
├── rollout-governance-gate-v15     [triagem 5-10 min]
└── onboarding-first-success-gate-v30 [triagem 5-10 min]
```

### Mecanismo de Validação

1. Criar branch `feat/ci-final-stabilization`
2. Aplicar Wave 1 → commit → push
3. Aplicar Wave 2 → commit → push
4. Abrir PR com evidências de cada gate
5. Validar via PR checks (sem merge em main ainda)
6. Merge só se: (a) sem regressão nova, (b) taxa melhora

---

## Design Detalhado por Wave

### Wave 1: Correção Estrutural

#### Gate 1: safety-autotuning-gate-v17

**Problema:** `test_vm_webapp_api_v2_safety_tuning.py` não existe

**Alteração:**
```yaml
# REMOVER:
- run: uv run pytest 09-tools/tests/test_vm_webapp_api_v2_safety_tuning.py -q

# MOTIVO: Arquivo não existe, coverage mantido por:
# - test_vm_webapp_safety_autotuning.py
# - test_vm_webapp_safety_tuning_audit.py
```

#### Gate 2: agent-dag-gate-v20

**Problema:** `test_vm_webapp_api_v2_agent_dag.py` não existe

**Alteração:**
```yaml
# REMOVER:
- run: uv run pytest 09-tools/tests/test_vm_webapp_api_v2_agent_dag.py -q

# MOTIVO: Arquivo não existe, coverage mantido por:
# - test_vm_webapp_agent_dag.py
# - test_vm_webapp_agent_dag_executor.py
# - test_vm_webapp_agent_dag_supervisor.py
```

#### Gate 3: first-run-quality-gate-v12

**Problema:** `test_vm_webapp_first_run_realculation.py` não existe

**Alteração:**
```yaml
# REMOVER:
- run: uv run pytest 09-tools/tests/test_vm_webapp_first_run_realculation.py -q

# MOTIVO: Arquivo não existe, coverage por test_vm_webapp_projectors_v2.py
```

---

### Wave 2: Triagem Seletiva

#### Gate 4: quality-optimizer-gate-v25

**Descoberta da Triagem:**
```
ERROR: not found: test_editorial_ops_report.py::TestNightlyReportGovernanceSection
```

**Alteração:**
```yaml
# REMOVER:
uv run pytest 09-tools/tests/test_editorial_ops_report.py::TestNightlyReportGovernanceSection -q

# MOTIVO: Classe/teste específico não existe no arquivo
```

#### Gate 5: rollout-governance-gate-v15

**Triagem:** Coletar logs do último run (#22668921221)

**Critério de Decisão:**
- Se arquivo inexistente → corrigir (remover/fallback)
- Se teste quebrado real → **escalonar** para Governance Team com RCA
- Se configuração/dependência → corrigir se determinístico

#### Gate 6: onboarding-first-success-gate-v30

**Triagem:** Coletar logs do último run (#22668921221)

**Critério de Decisão:** Idem gate 5

---

## Critérios de Validação

### Por Gate (na feature branch)

| Gate | Validação | Critério de Sucesso |
|------|-----------|---------------------|
| Wave 1 (3 gates) | PR check individual | Gate passa sem erro de arquivo inexistente |
| Wave 2 (3 gates) | PR check + triagem | Gate passa OU falha documentada com RCA |
| Todos | PR check completo | Taxa de verde do run ≥75% (melhoria vs 70% baseline) |

### Rollback e Mitigação

| Cenário | Ação |
|---------|------|
| Regressão em gate que estava passando | Reverter commit específico daquele gate |
| Falha catastrófica em múltiplos gates | Abandonar branch, recriar do zero |
| Taxa de verde piora (<70%) | Não fazer merge, documentar e replanejar |

| Gate | Mitigação se correção falhar |
|------|------------------------------|
| safety-autotuning-gate-v17 | Remover gate temporariamente do workflow |
| agent-dag-gate-v20 | Remover gate temporariamente do workflow |
| first-run-quality-gate-v12 | Remover gate temporariamente do workflow |
| quality-optimizer-gate-v25 | Escalonar para Analytics Team (owner) |
| rollout-governance-gate-v15 | Escalonar para Governance Team (owner) |
| onboarding-first-success-gate-v30 | Escalonar para Onboarding Team (owner) |

---

## Critério Objetivo de "ENCERRADO TOTAL"

**Para declarar ENCERRADO TOTAL após merge:**

| # | Critério | Evidência | Mínimo |
|---|----------|-----------|--------|
| 1 | Taxa de verde consistente | 3 runs consecutivos na main | ≥80% em cada |
| 2 | Nenhuma falha nova | Comparação com baseline | Zero regressões |
| 3 | Gates corrigidos | Runs pós-merge | 6/6 passando ou documentados |
| 4 | Tempo de estabilidade | Janela de observação | 24-48h após merge |

**Se qualquer critério não for atingido:**
- Status: **ENCERRADO PARCIAL** (permanece)
- Ação: Nova sprint de estabilização
- Escopo: Gates remanescentes + novos issues

---

## Princípios Aplicados

1. **YAGNI:** Mudanças mínimas para estabilizar os 6 gates
2. **Sem mascaramento:** Zero workaround que esconda teste quebrado real
3. **Evidência objetiva:** Cada gate termina com status claro
4. **No big-bang:** Feature branch + PR para validação antes de tocar main
5. **Fallback só com equivalência semântica:** Remover onde não houver equivalente

---

## Aprovações

- [x] Arquitetura e estratégia geral
- [x] Wave 1 (Correção Estrutural)
- [x] Wave 2 (Triagem Seletiva)
- [x] Critérios de validação, rollback e mitigação
- [x] Critério objetivo de ENCERRADO TOTAL

**Status:** Design completo e aprovado para implementação.
