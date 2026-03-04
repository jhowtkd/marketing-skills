# CI Sustainment + Velocity - Design Document

> **Data:** 2026-03-04  
> **Status:** Aprovado para implementação  
> **Baseline:** Commit `f0d46102` (100% green atingido)  
> **Meta:** Manter ≥95% green por 14 dias + reduzir duração em 20%

---

## 1. Contexto

A frente **CI Final Stabilization** foi encerrada com sucesso atingindo **100% green** (28/28 gates) no workflow `vm-webapp-smoke`. A baseline está documentada em `docs/ci/2026-03-main-baseline.md`.

Agora, o objetivo é **sustentar** essa estabilidade enquanto **otimiza** tempo e custo de execução.

---

## 2. Objetivos

| # | Objetivo | Meta | Métrica |
|---|----------|------|---------|
| 1 | Sustentar estabilidade | ≥95% green por 14 dias | Taxa de sucesso do workflow |
| 2 | Reduzir duração média | -20% vs baseline | Tempo médio dos últimos 14 runs |
| 3 | Reduzir duração p95 | -25% vs baseline | Percentil 95 dos últimos 14 runs |
| 4 | Reduzir custo | -40% runner-minutes | Jobs por run × duração média |

---

## 3. Otimizações Propostas

### 3.1 Cache UV (Otimização #1)

**O que:** Cache do diretório `~/.cache/uv` para evitar re-download de dependências Python.

**Onde:** Apenas nos jobs que usam `uv sync` ou `uv run` (não todos os 24 automaticamente).

**Implementação:**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-py-${{ env.python-version }}-uv-${{ hashFiles('uv.lock') }}-${{ hashFiles('pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-py-${{ env.python-version }}-uv-
```

**Impacto estimado:** -30% tempo de setup (-15-20s por job)

---

### 3.2 Merge por Domínio (Otimização #2)

**O que:** Consolidar jobs relacionados por domínio funcional.

**Mapeamento:**

| Grupo Merged | Jobs Originais | Jobs Resultante |
|--------------|----------------|-----------------|
| `editorial-gates-combined` | editorial-gate, editorial-policy-v5, editorial-insights-v6, editorial-copilot-v13 | 1 job |
| `onboarding-gates-combined` | onboarding-first-success-v30, onboarding-activation-v31, onboarding-experimentation-v32 | 1 job |
| `approval-gates-combined` | approval-cost-optimizer-v23, approval-learning-loop-v24 | 1 job |
| `safety-resilience-gates-combined` | safety-autotuning-v17, adaptive-escalation-v21, predictive-resilience-v27, recovery-orchestration-v28 | 1 job |
| `frontend-gates-combined` | frontend-gate, ux-task-first-redesign-v29 | 1 job |
| `quality-gates-combined` | first-run-quality-v12, quality-optimizer-v25 | 1 job |
| `control-gates-combined` | online-control-loop-v26, rollout-governance-v15 | 1 job |

**Jobs isolados (permanecem separados):**
- `api-contract-tests` (infra crítica)
- `e2e-tests` (end-to-end, duração diferente)
- `agent-dag-gate-v20` (domínio específico)
- `decision-automation-gate-v16` (critical)
- `segmented-copilot-gate-v14` (já otimizado)

**Total:** 24 jobs → 13 jobs (-46% overhead)

**Debuggabilidade:** Cada subgate terá bloco nomeado:
```yaml
- name: "[subgate: editorial-policy-v5] Run tests"
  run: ...
```

---

### 3.3 Paralelização de Steps (Otimização #3)

**O que:** Rodar backend (pytest) e frontend (npm test) em paralelo dentro do mesmo job.

**Implementação com validação de exit codes:**
```yaml
- name: "Run tests (parallel)"
  run: |
    # Backend em background
    (uv run pytest ...; echo $? > /tmp/backend.exit) &
    BACKEND_PID=$!
    
    # Frontend em foreground
    echo "::group::[subgate: frontend]"
    npm run test ...
    FRONTEND_EXIT=$?
    echo "::endgroup::"
    
    # Espera backend
    wait $BACKEND_PID
    BACKEND_EXIT=$(cat /tmp/backend.exit)
    
    # Resumo
    echo "::group::[subgate: resumo]"
    echo "Backend exit code: $BACKEND_EXIT"
    echo "Frontend exit code: $FRONTEND_EXIT"
    echo "::endgroup::"
    
    # Falha se qualquer um falhou
    if [ $BACKEND_EXIT -ne 0 ] || [ $FRONTEND_EXIT -ne 0 ]; then
      exit 1
    fi
```

**Guardrails obrigatórios:**
1. ✅ Capturar exit code explícito de ambos os lados
2. ✅ Falhar job se qualquer subgate falhar
3. ✅ Logs por subgate com `::group::` + resumo final

---

## 4. Métricas e Monitoramento

### 4.1 KPIs

| Métrica | Baseline (f0d46102) | Meta | Como Medir |
|---------|---------------------|------|------------|
| Taxa de green | 100% (28/28) | ≥95% | GitHub API |
| Duração média | A coletar | -20% | `gh run list --json duration` |
| Duração p95 | A coletar | -25% | Percentil 95 |
| Jobs por run | 24 | 13 | Contagem |
| Setup time | ~30s/job | -50% | Logs GitHub |

### 4.2 Script de Métricas

```bash
./scripts/ci_velocity_metrics.sh \
  --workflow vm-webapp-smoke \
  --baseline-date 2026-03-04 \
  --baseline-commit f0d46102 \
  --alert-channel github-issue
```

**Saída esperada:**
```
Workflow: vm-webapp-smoke
Período: últimos 7 dias
Taxa de sucesso: 100% (14/14 runs)
Duração média: 8m 32s (baseline: 10m 45s) → -20.5% ✅
Duração p95: 12m 15s (baseline: 15m 30s) → -21.0% ✅
Jobs por run: 13 (baseline: 24) → -46% ✅
```

### 4.3 Alertas de Regressão

| Condição | Ação |
|----------|------|
| Taxa de green < 95% em 24h | Criar GitHub issue P0 |
| Duração média aumenta > 10% | Revisar cache hit rate |
| Falha em job merged | Investigar e possível revert |

---

## 5. Risk Mitigation e Rollback

### 5.1 Estratégia de Rollback

| Otimização | Rollback | Tempo |
|------------|----------|-------|
| Cache UV | Remover step `actions/cache` | 5 min |
| Merge jobs | Reverter para jobs individuais | 10 min |
| Paralelização | Mudar `&` para sequencial | 5 min |

### 5.2 Sem Feature Flags (YAGNI)

**Decisão:** Não implementar feature flags permanentes. Rollback via `git revert` + runbook.

**Justificativa:** Feature flags adicionam complexidade permanente para um caso de uso temporário (rollback de emergência).

### 5.3 Runbook de Rollback

#### Cenário 1: Regressão de Estabilidade (Green < 95%)

```bash
# Detectado via health report
gh issue create \
  --title "[URGENT] CI Regression: Green rate dropped to X%" \
  --label "ci,regression,p0"
```

**Passos:**
1. Identificar último commit nas últimas 24h
2. `git revert <commit>`
3. Validar retorno a 100% green
4. Post-mortem em issue

#### Cenário 2: Falso Verde

**Sintomas:** Job passa mas "0 tests ran" ou subprocesso falhou silenciosamente.

**Ação:** Reverter commit de paralelização específico.

#### Cenário 3: Cache Corrompido

**Mitigação (sem código):**
```yaml
# Bump versão da chave de cache
key: ${{ runner.os }}-py-${{ env.python-version }}-uv-...-v2
```

#### Cenário 4: Reverter Tudo (Nuclear)

```bash
# Reverter toda a sprint
git revert --no-commit f0d46102^..HEAD
git commit -m "Revert: CI optimizations causing instability"
git push origin main
```

---

## 6. Implementation Timeline

### Fase 1: Cache UV (Dia 1-2)

| Dia | Atividade | Validação |
|-----|-----------|-----------|
| 1 | Implementar cache em 3-5 jobs piloto | Hit rate >80%? |
| 1 | Monitorar runs por 4h | Cache funcionando? |
| 2 | Expandir para todos os jobs UV | Todos com cache? |
| 2 | Coletar baseline de setup time | Redução mensurável? |

### Fase 2: Merge por Domínio (Dia 3-4)

| Dia | Atividade | Validação |
|-----|-----------|-----------|
| 3 | Merge `editorial` (4→1) | 100% green? |
| 3 | Merge `onboarding` (3→1) | 100% green? |
| 4 | Merge grupos restantes | 100% green? |
| 4 | Coletar métricas | Duração reduziu? |

### Fase 3: Paralelização (Dia 5-6)

| Dia | Atividade | Validação |
|-----|-----------|-----------|
| 5 | Implementar `&+wait` em jobs combinados | Exit codes corretos? |
| 5 | Validar logs por subgate | Debug OK? |
| 6 | Full rollout | 100% green? |

### Fase 4: Monitoramento (Dia 7-14)

| Dia | Atividade | Validação |
|-----|-----------|-----------|
| 7 | Coletar métricas pós-otimização | Meta -20% atingida? |
| 7-14 | Health report diário | Taxa green ≥95%? |
| 14 | **Decisão final** | Consolidar ou reverter |

### Checkpoints de Go/No-Go

| Checkpoint | Critério | Ação se Falhar |
|------------|----------|----------------|
| D1 | Cache hit rate >80% | Revisar chave de cache |
| D3 | Editorial+onboarding 100% green | Reverter merges |
| D5 | Paralelização sem falso verde | Voltar para sequencial |
| D7 | Meta -20% tempo atingida | **Ajustar táticas** (não rollback) |
| D14 | Taxa green ≥95% sustentada | **ENCERRAR** ou reverter |

**Nota:** D7 (meta de performance) **não aciona rollback automático**. Rollback só por **regressão de estabilidade** (green <95%).

---

## 7. Decisões Aprovadas

| Decisão | Status | Racional |
|---------|--------|----------|
| Estratégia agressiva (aceitar 2-3 dias instabilidade) | ✅ Aprovado | Baseline sólido permite movimento rápido |
| Ordem: Cache → Merge → Paralelização | ✅ Aprovado | Quick win primeiro, maior impacto depois |
| Merge por domínio funcional | ✅ Aprovado | Isolamento lógico, debug fácil |
| Cache UV com chave precisa (uv.lock + pyproject.toml) | ✅ Aprovado | Invalidação precisa, baixo risco |
| Paralelização com `& + wait` | ✅ Aprovado | Economia de runners e tempo |
| Sem feature flags (YAGNI) | ✅ Aprovado | Rollback via git revert é suficiente |
| D7 não aciona rollback | ✅ Aprovado | Rollback só por estabilidade, não performance |

---

## 8. Próximos Passos

1. Transicionar para `writing-plans` skill
2. Criar plano de implementação detalhado
3. Executar Fase 1 (Cache UV)

---

**Design aprovado em:** 2026-03-04  
**Próximo review:** Pós-Fase 1 (Dia 2)
