# CI Main Stability Baseline

> **Data:** 2026-03-04  
> **Branch:** main  
> **Objetivo:** Documentar estado atual para iniciativa de hardening (3-4 semanas)

---

## Workflows Ativos

| Workflow | Path | Estado | Criticidade |
|----------|------|--------|-------------|
| vm-webapp-smoke | `.github/workflows/vm-webapp-smoke.yml` | Crônico falha | **critical** |
| VM Editorial Governance Monitoring | `.github/workflows/vm-editorial-monitoring.yml` | Crônico falha | important |
| v2.1.3 Residual Risk Gate | `.github/workflows/v2-1-3-residual-risk-gate.yml` | 25% sucesso | important |
| vm-editorial-ops-nightly | `.github/workflows/vm-editorial-ops-nightly.yml` | Crônico falha | legacy |
| vm-studio-run-binding-nightly | `.github/workflows/vm-studio-run-binding-nightly.yml` | 100% sucesso | important |
| v38 Onboarding TTFV Gate | `.github/workflows/v38-onboarding-ttfv-gate.yml` | 100% sucesso | important |
| v23 Approval Optimizer CI Gate | `.github/workflows/v23-ci-gate.yml` | N/A (só PR) | important |
| v33 Onboarding Personalization CI Gate | `.github/workflows/v33-ci-gate.yml` | N/A (só PR) | important |
| v34 Onboarding Recovery Reactivation CI Gate | `.github/workflows/v34-ci-gate.yml` | N/A (só PR) | important |
| v35 Onboarding Continuity CI Gate | `.github/workflows/v35-ci-gate.yml` | N/A (só PR) | important |
| v36 Outcome Attribution & Hybrid ROI CI Gate | `.github/workflows/v36-ci-gate.yml` | N/A (só PR) | important |
| v37 Unified Workspace UI CI Gate | `.github/workflows/v37-ci-gate.yml` | N/A (só PR) | important |
| Lint Scoped | `.github/workflows/lint-scoped.yml` | Ativo | important |
| v2 API Testing Suite | `.github/workflows/testing-suite.yml` | Ativo | important |

---

## Taxa de Verde (últimos 50 runs na main)

| Workflow | Total Runs | Sucessos | Falhas | Taxa Verde |
|----------|-----------|----------|--------|-----------|
| vm-webapp-smoke | 28 | 0 | 28 | **0%** 🔴 |
| VM Editorial Governance Monitoring | 11 | 0 | 11 | **0%** 🔴 |
| vm-editorial-ops-nightly | 3 | 0 | 3 | **0%** 🔴 |
| v2.1.3 Residual Risk Gate | 4 | 1 | 3 | **25%** 🟡 |
| vm-studio-run-binding-nightly | 3 | 3 | 0 | **100%** 🟢 |
| v38 Onboarding TTFV Gate | 1 | 1 | 0 | **100%** 🟢 |

---

## Checks por Workflow (vm-webapp-smoke)

| Subgate | Status na Main | Classificação | Ação |
|---------|---------------|---------------|------|
| editorial-gate | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| editorial-insights-gate-v6 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| agent-dag-gate-v20 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| approval-cost-optimizer-gate-v23 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| first-run-quality-gate-v12 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| onboarding-first-success-gate-v30 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| quality-optimizer-gate-v25 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| rollout-governance-gate-v15 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| safety-autotuning-gate-v17 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| ux-task-first-redesign-gate-v29 | Falha crônica | **PRE_EXISTING** | Corrigir na Onda 1 |
| frontend-gate | ✅ Passando | **VERIFIED_OK** | Manter |
| e2e-tests | ✅ Passando | **VERIFIED_OK** | Manter |
| adaptive-escalation-gate-v21 | ✅ Passando | **VERIFIED_OK** | Manter |

---

## Gates v33-v37 (Status em PRs)

| Gate | unit-tests | lint | type-check | metrics-validation | Classificação |
|------|-----------|------|------------|-------------------|---------------|
| v33 | ❌ FAIL | ❌ FAIL | ✅ PASS | ❌ FAIL | **INCONCLUSIVE** |
| v34 | ❌ FAIL | ❌ FAIL | ✅ PASS | ❌ FAIL | **INCONCLUSIVE** |
| v35 | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **INCONCLUSIVE** |
| v36 | ❌ FAIL | ✅ PASS | ❌ FAIL | ❌ FAIL | **INCONCLUSIVE** |
| v37 | ❌ FAIL | ✅ PASS | ❌ FAIL | ❌ FAIL | **INCONCLUSIVE** |

**Nota:** Estes workflows não rodam na `main`, apenas em PRs e branches de feature.

---

## Classificações Definidas

| Classificação | Definição | Exemplos |
|--------------|-----------|----------|
| **PRE_EXISTING** | Falha também ocorre na main recentemente | vm-webapp-smoke (100% falha) |
| **NEW_REGRESSION** | Main está verde, PR está vermelha | Nenhum identificado |
| **FLAKE** | Falha intermitente, não reproduzível | A investigar |
| **INCONCLUSIVE** | Sem histórico na main para comparar | v33-v37 gates |
| **VERIFIED_OK** | Check passando, validado | frontend-gate, e2e-tests |

---

## Janela de Estabilização

**Meta:** 3-4 semanas para main consistentemente verde (SLO: 80%+ taxa de sucesso)

### Onda 1 (Semana 1-2)
- [ ] Estabilizar vm-webapp-smoke
- [ ] Corrigir subgates crônicos
- [ ] Baseline documentado

### Onda 2 (Semana 2-3)
- [ ] Alinhar v33-v37
- [ ] Padronizar runtimes
- [ ] Reduzir duplicidade

### Onda 3 (Semana 3-4)
- [ ] Governança formalizada
- [ ] Observabilidade semanal
- [ ] Critério de saída atingido

---

## Critério de Saída

1. Taxa de verde da main ≥ 80% (média semanal)
2. vm-webapp-smoke com < 20% de falha
3. Documentação de governança completa
4. Relatório semanal automatizado
5. Lista de riscos residuais documentada

---

## Riscos Residuais Iniciais

1. Workflows v33-v37 podem ter falhas não relacionadas às nossas mudanças
2. vm-editorial-ops-nightly e VM Editorial Governance Monitoring são legados
3. Recursos necessários para correção de subgates individuais
