# VM Studio v31 - Onboarding Activation Learning Loop

**Release Date:** 2026-03-02  
**Branch:** `feature/governance-v31-onboarding-activation-learning-loop`  
**Base:** v30 Onboarding First Success Path  
**Commit:** `aadd0b20` (studio) + `56b976c5` (observability) + ...

---

## 🎯 Goal

Otimizar ativação do onboarding da v30 com aprendizado contínuo, nudges contextuais e experimentação controlada.

## 🏗️ Architecture

Extend da base v30 com um ciclo semanal **observe → propose → apply/review**:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Observe   │ →  │   Propose   │ →  │ Apply/Review│
│  (Metrics)  │    │   (Rules)   │    │  (Actions)  │
└─────────────┘    └─────────────┘    └─────────────┘
       ↑                                    │
       └──────────── Weekly Cycle ←────────┘
```

**Motor de decisão:** Deterministico (rule-based)
- **Auto-apply:** Apenas para ajustes low-risk
- **Aprovação humana:** Para medium/high risk

---

## 📊 6-Week Goals

| KPI | Target | Current Baseline |
|-----|--------|------------------|
| `onboarding_completion_rate` | +15 p.p. | 55% |
| `template_to_first_run_conversion` | +20% | 45% |
| `time_to_first_action` | -20% | 90s |
| `step_1_dropoff_rate` | -25% | 30% |

---

## ✨ Novas Funcionalidades

### 1. Friction Telemetry + Funnel Enrichment (Task 1)

**Arquivos:**
- `09-tools/web/vm-ui/src/features/onboarding/telemetry.ts` (modified)
- `09-tools/web/vm-ui/src/features/onboarding/funnel.v31.test.ts` (new)

**Funcionalidades:**
- Tracking de eventos de fricção:
  - `step_abandoned` - Usuário abandonou um step
  - `step_returned` - Usuário retornou após abandono
  - `step_hesitation` - Hesitação prolongada em um elemento
- Metadados enriquecidos (timeSpentMs, fieldAttempts, element, action)
- Métricas de fricção agregadas (abandons, returns, hesitations)

**Commits:**
- `4396234c` feat(v31): add onboarding friction telemetry and enriched funnel tracking

### 2. Onboarding Activation Engine (Task 2)

**Arquivos:**
- `09-tools/vm_webapp/onboarding_activation.py` (new)
- `09-tools/tests/test_vm_webapp_onboarding_activation.py` (new)

**Funcionalidades:**
- **Rule Engine:** 7 regras pré-configuradas para otimização
- **Risk Classification:**
  - `LOW` - Auto-apply (±10% adjustment)
  - `MEDIUM` - Requires approval
  - `HIGH` - Requires review
- **Max Adjustment:** ±10% por ciclo semanal
- **Proposal Model:** Com current/target values, expected impact
- **Actions:** Run, Apply, Reject, Freeze, Rollback

**Regras Implementadas:**
| Regra | Condição | Risco | Ajuste |
|-------|----------|-------|--------|
| reduce_step_1_complexity | step_1_dropoff > 30% | LOW | -10% |
| add_nudge_to_template_selection | template_conv < 50% | LOW | -8% |
| reduce_time_to_first_action | time_to_action > 90s | LOW | -10% |
| reorder_onboarding_steps | workspace_abandon > template_abandon * 2 | MEDIUM | 0% |
| add_progress_rewards | completion < 50% | MEDIUM | +5% |
| enable_skip_options | too_complex_abandons > 15 | MEDIUM | -5% |
| major_onboarding_redesign | completion < 30% ou abandons > 50 | HIGH | 0% |

**Commits:**
- `47c15380` feat(v31): add onboarding activation rule engine and proposal model

### 3. API v2 Endpoints (Task 3)

**Arquivos:**
- `09-tools/vm_webapp/api_onboarding_activation.py` (new)
- `09-tools/vm_webapp/api.py` (modified)
- `09-tools/tests/test_onboarding_activation_api.py` (new)

**Endpoints:**

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v2/brands/{brand_id}/onboarding-activation/status` | GET | Get activation status e métricas |
| `/api/v2/brands/{brand_id}/onboarding-activation/run` | POST | Run activation engine |
| `/api/v2/brands/{brand_id}/onboarding-activation/proposals` | GET | List proposals (com status filter) |
| `/api/v2/brands/{brand_id}/onboarding-activation/proposals/{id}/apply` | POST | Apply proposal |
| `/api/v2/brands/{brand_id}/onboarding-activation/proposals/{id}/reject` | POST | Reject proposal |
| `/api/v2/brands/{brand_id}/onboarding-activation/freeze` | POST | Freeze proposals |
| `/api/v2/brands/{brand_id}/onboarding-activation/rollback` | POST | Rollback last applied |

**Commits:**
- `719ab3ef` feat(api-v2): add onboarding activation operations endpoints

### 4. Observability + Nightly Report (Task 4)

**Arquivos:**
- `09-tools/vm_webapp/observability.py` (modified)

**Métricas Adicionadas:**
- Cycle counters (cycles, proposals generated/applied/rejected)
- Risk distribution (low/medium/high counts)
- Friction tracking (abandons, returns, hesitations)
- Impact metrics (6-week goals tracking)
- Cadence tracking (adjustments_this_week)

**Commits:**
- `56b976c5` feat(observability): add v31 onboarding activation metrics and nightly section

### 5. Studio Activation Panel (Task 5)

**Arquivos:**
- `09-tools/web/vm-ui/src/features/workspace/hooks/useOnboardingActivation.ts` (new)
- `09-tools/web/vm-ui/src/features/workspace/components/OnboardingActivationPanel.tsx` (new)
- `09-tools/web/vm-ui/src/features/workspace/components/OnboardingActivationPanel.test.tsx` (new)

**Funcionalidades:**
- Hook `useOnboardingActivation` com todas as operações da API
- Painel visual no Studio com:
  - Métricas de ativação (4 KPIs principais)
  - Top friction points
  - Proposals pendentes com ações Apply/Reject
  - Proposals aplicadas (histórico)
  - Botões de ação: Run, Freeze, Rollback
- Badges de risco (Low/Medium/High)
- Badges de status (Pending/Applied/Rejected)
- Estados de loading e erro

**Commits:**
- `aadd0b20` feat(studio): add onboarding activation panel with supervised actions

### 6. CI Gate v31 (Task 6)

**Arquivo:**
- `.github/workflows/vm-webapp-smoke.yml`

**Novo Job:** `onboarding-activation-learning-loop-gate-v31`

**Testes:**
- Backend: `test_onboarding_activation_api.py`, `test_vm_webapp_onboarding_activation.py`
- Frontend: `funnel.v31.test.ts`, `OnboardingActivationPanel.test.tsx`, `workspace/`

**Commits:**
- `ci/docs(v31): add onboarding activation gate and release notes`

---

## 🧪 Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| funnel.v31.test.ts | 9 | ✅ PASS |
| OnboardingActivationEngine | 14 | ✅ PASS |
| OnboardingActivation API | 10 | ✅ PASS |
| OnboardingActivationPanel | 15 | ✅ PASS |
| vm_webapp_api_v2.py | 17 | ✅ PASS |
| vm_webapp_metrics_prometheus.py | 15 | ✅ PASS |

---

## 🔧 Arquivos Modificados

```
09-tools/web/vm-ui/src/features/onboarding/
├── telemetry.ts                    (modified - v31 friction telemetry)
└── funnel.v31.test.ts              (new)

09-tools/vm_webapp/
├── onboarding_activation.py        (new - rule engine)
├── api_onboarding_activation.py    (new - API endpoints)
└── api.py                          (modified - router include)

09-tools/vm_webapp/
└── observability.py                (modified - v31 metrics)

09-tools/web/vm-ui/src/features/workspace/
├── hooks/
│   └── useOnboardingActivation.ts  (new)
└── components/
    ├── OnboardingActivationPanel.tsx      (new)
    └── OnboardingActivationPanel.test.tsx (new)

09-tools/tests/
├── test_onboarding_activation_api.py      (new)
└── test_vm_webapp_onboarding_activation.py (new)

.github/workflows/
└── vm-webapp-smoke.yml             (modified - v31 gate)

docs/releases/
└── 2026-03-02-vm-studio-v31-onboarding-activation-learning-loop.md (new)
```

---

## 🚀 Como Usar

### No Studio (UI)

O painel "Onboarding Activation" está disponível no workspace quando um brand está selecionado.

**Fluxo de Operação:**
1. **Run Activation** - Executa o motor de regras e gera proposals
2. **Review Proposals** - Analise proposals pendentes (Low = auto, Medium/High = aprovação)
3. **Apply/Reject** - Tome decisões nas proposals medium/high
4. **Monitor Metrics** - Acompanhe os 4 KPIs principais
5. **Rollback** - Desfaça última alteração se necessário

### API

```bash
# Ver status e métricas
curl /api/v2/brands/{brand_id}/onboarding-activation/status

# Rodar motor de ativação
curl -X POST /api/v2/brands/{brand_id}/onboarding-activation/run

# Listar proposals
curl /api/v2/brands/{brand_id}/onboarding-activation/proposals

# Aplicar proposal
curl -X POST /api/v2/brands/{brand_id}/onboarding-activation/proposals/{id}/apply

# Rejeitar proposal
curl -X POST /api/v2/brands/{brand_id}/onboarding-activation/proposals/{id}/reject \
  -d '{"reason": "Too aggressive"}'

# Freeze/Rollback
curl -X POST /api/v2/brands/{brand_id}/onboarding-activation/freeze
curl -X POST /api/v2/brands/{brand_id}/onboarding-activation/rollback
```

### Motor de Regras (Python)

```python
from vm_webapp.onboarding_activation import OnboardingActivationEngine

engine = OnboardingActivationEngine()

# Avaliar métricas e gerar proposals
metrics = {
    "completion_rate": 0.45,
    "step_1_dropoff_rate": 0.35,
    "template_to_first_run_conversion": 0.40,
}
proposals = engine.evaluate_rules("brand-123", metrics)

# Aplicar proposal (auto-apply para low risk)
result = engine.apply_proposal("brand-123", proposal_id)

# Identificar top frictions
frictions = engine.identify_top_frictions("brand-123", metrics)
```

---

## ⚠️ Riscos e Mitigações

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Over-adjustment | Média | Alto | Max ±10% per cycle, cadência semanal |
| False positives | Baixa | Médio | Regras deterministicas, explicabilidade |
| User confusion | Baixa | Médio | Nudges contextuais, não obrigatórios |
| Data quality | Média | Alto | Fallback para defaults, validação de inputs |

---

## 📈 Próximos Passos (v32+)

- [ ] Machine learning model para proposal ranking
- [ ] A/B testing framework integrado
- [ ] Personalização por segmento de usuário
- [ ] Alertas proativos para anomalias
- [ ] Integração com email/SaaS para notificações

---

**Release Manager:** @kimi-code-cli  
**Reviewers:** Automated TDD + CI Gates  
**Status:** ✅ Ready for Merge
