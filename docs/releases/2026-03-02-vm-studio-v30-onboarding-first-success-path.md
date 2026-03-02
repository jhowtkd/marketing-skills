# VM Studio v30 - Onboarding First Success Path

**Release Date:** 2026-03-02  
**Branch:** `feature/governance-v30-onboarding-first-success-path`  
**Commit:** `2f9ab17b` (api) + `a36a2ae9` (tour) + ...

---

## 🎯 Goal

Entregar onboarding guiado para levar usuário ao primeiro valor com menor fricção.

## 📊 KPIs de Sucesso

| KPI | Target | Status |
|-----|--------|--------|
| `time_to_first_value` | -35% | ✅ Implementado |
| `activation_rate` | +20 p.p. | ✅ Implementado |
| `setup_dropoff` | -30% | ✅ Implementado |

---

## ✨ Novas Funcionalidades

### 1. Onboarding Telemetry & Funnel (Task 1)

**Arquivos:**
- `09-tools/web/vm-ui/src/features/onboarding/telemetry.ts`
- `09-tools/web/vm-ui/src/features/onboarding/funnel.ts`
- `09-tools/web/vm-ui/src/features/onboarding/telemetry.test.ts`

**Funcionalidades:**
- Tracking de eventos: `onboarding_started`, `onboarding_completed`, `onboarding_dropoff`, `time_to_first_value`
- Funnel analytics com persistência de estado
- Métricas de conversão por etapa
- Cálculo automático de TTFV (Time To First Value)

**Commits:**
- `bfa62af5` feat(v30): add onboarding telemetry and funnel tracking

### 2. Guided Setup Wizard (Task 2)

**Arquivos:**
- `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.tsx`
- `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.test.tsx`
- `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx` (integração)

**Funcionalidades:**
- Wizard de 5 passos: Welcome → Workspace Setup → Template Selection → Customization → Completion
- Validação por etapa
- Progress indicator visual
- Integração com WorkspacePanel para primeiro acesso
- Persistência de estado no localStorage

**Commits:**
- `4d23fc41` feat(v30): add guided onboarding wizard with step validation
- `79d31f6d` feat(v30): integrate onboarding wizard into WorkspacePanel

### 3. Template Library + First Success Suggestions (Task 3)

**Arquivos:**
- `09-tools/web/vm-ui/src/features/onboarding/templates.ts`
- `09-tools/web/vm-ui/src/features/onboarding/TemplatePicker.tsx`
- `09-tools/web/vm-ui/src/features/onboarding/TemplatePicker.test.tsx`

**Templates Incluídos:**
- 📝 Blog Post (Recomendado para primeiro valor)
- 🎯 Landing Page
- 📱 Social Media
- ✉️ Email Marketing
- 🔍 Google Ads
- 📢 Meta Ads

**Funcionalidades:**
- Grid de templates com filtros por categoria
- Busca de templates
- Preview de prefill com variáveis
- Badge "1º valor" no template recomendado
- Categorias: content, conversion, social, email, ads

**Commits:**
- `11605a9e` feat(v30): add first-success templates and prefill picker

### 4. Contextual Tour + Resume State (Task 4)

**Arquivos:**
- `09-tools/web/vm-ui/src/features/onboarding/ContextualTour.tsx`
- `09-tools/web/vm-ui/src/features/onboarding/ContextualTour.test.tsx`
- `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.tsx` (integração)

**Funcionalidades:**
- Tour contextual com overlay
- Steps configuráveis por tourId
- Retomada de estado (resume state)
- Persistência de progresso no localStorage
- Navegação: próximo, anterior, pular, finalizar
- Indicador visual de progresso (dots + bar)

**Commits:**
- `a36a2ae9` feat(v30): add contextual tour and onboarding resume state

### 5. Backend Support Endpoints (Task 5)

**Arquivos:**
- `09-tools/vm_webapp/api_onboarding.py`
- `09-tools/tests/test_onboarding_api.py`
- `09-tools/vm_webapp/api.py` (integração)

**Endpoints:**

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v2/onboarding/state` | GET | Get onboarding state for user |
| `/api/v2/onboarding/state` | POST | Update onboarding state |
| `/api/v2/onboarding/templates` | GET | List templates (filter by category) |
| `/api/v2/onboarding/templates/{id}` | GET | Get template by ID |
| `/api/v2/onboarding/templates/recommended` | GET | Get recommended template |
| `/api/v2/onboarding/events` | POST | Track onboarding event |
| `/api/v2/onboarding/metrics` | GET | Get funnel metrics |

**Commits:**
- `2f9ab17b` feat(api-v2): add onboarding state and templates endpoints

### 6. CI Gate v30 (Task 6)

**Arquivo:**
- `.github/workflows/vm-webapp-smoke.yml`

**Novo Job:** `onboarding-first-success-gate-v30`

**Testes:**
- Backend: `test_onboarding_api.py`, `test_vm_webapp_api_v2.py`, `test_vm_webapp_metrics_prometheus.py`
- Frontend: telemetry, funnel, wizard, template picker, contextual tour, workspace

**Commits:**
- `ci(v30): add onboarding first-success gate and release notes`

---

## 🧪 Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| telemetry.ts | 7 | ✅ PASS |
| OnboardingWizard | 10 | ✅ PASS |
| TemplatePicker | 13 | ✅ PASS |
| ContextualTour | 12 | ✅ PASS |
| api_onboarding.py | 15 | ✅ PASS |
| WorkspacePanel | 413 | ✅ PASS |

---

## 🔧 Arquivos Modificados

```
09-tools/web/vm-ui/src/features/onboarding/
├── telemetry.ts (new)
├── telemetry.test.ts (new)
├── funnel.ts (new)
├── OnboardingWizard.tsx (new)
├── OnboardingWizard.test.tsx (new)
├── templates.ts (new)
├── TemplatePicker.tsx (new)
├── TemplatePicker.test.tsx (new)
├── ContextualTour.tsx (new)
├── ContextualTour.test.tsx (new)

09-tools/vm_webapp/
├── api_onboarding.py (new)
├── api.py (modified)

09-tools/tests/
├── test_onboarding_api.py (new)

09-tools/web/vm-ui/src/features/workspace/
├── WorkspacePanel.tsx (modified)

.github/workflows/
├── vm-webapp-smoke.yml (modified)

docs/releases/
└── 2026-03-02-vm-studio-v30-onboarding-first-success-path.md (new)
```

---

## 🚀 Como Usar

### Ativação do Onboarding

O onboarding é ativado automaticamente para novos usuários (quando `vm_onboarding_completed` não está no localStorage).

### Componentes React

```tsx
// Onboarding Wizard
import { OnboardingWizard } from './features/onboarding/OnboardingWizard';

<OnboardingWizard
  userId="user-123"
  onComplete={() => console.log('Complete!')}
  onSkip={() => console.log('Skipped')}
/>

// Template Picker
import { TemplatePicker } from './features/onboarding/TemplatePicker';
import { FIRST_SUCCESS_TEMPLATES } from './features/onboarding/templates';

<TemplatePicker
  templates={FIRST_SUCCESS_TEMPLATES}
  onSelect={(id, template) => console.log(id, template)}
  onCancel={() => console.log('Cancelled')}
  recommendedTemplateId="blog-post"
/>

// Contextual Tour
import { ContextualTour } from './features/onboarding/ContextualTour';

<ContextualTour
  steps={tourSteps}
  isOpen={showTour}
  onComplete={() => setShowTour(false)}
  onSkip={() => setShowTour(false)}
  tourId="onboarding-v30"
  resumeStepId="workspace" // optional: resume from step
/>
```

### API Endpoints

```bash
# Get onboarding state
curl /api/v2/onboarding/state?user_id=user-123

# Update onboarding state
curl -X POST /api/v2/onboarding/state \
  -d '{"user_id": "user-123", "current_step": "workspace_setup", "has_started": true}'

# Get templates
curl /api/v2/onboarding/templates?category=content

# Track event
curl -X POST /api/v2/onboarding/events \
  -d '{"event": "onboarding_started", "user_id": "user-123", "timestamp": "2026-03-02T12:00:00Z"}'

# Get metrics
curl /api/v2/onboarding/metrics
```

---

## 📈 Métricas Implementadas

- **Total Started**: Número de usuários que iniciaram onboarding
- **Total Completed**: Número de usuários que completaram
- **Completion Rate**: Taxa de conversão (%)
- **Average TTFV**: Tempo médio até primeiro valor (ms)
- **Dropoff by Step**: Abandono por etapa do funnel

---

## 🔮 Próximos Passos

- [ ] Analytics dashboard para visualização de métricas
- [ ] A/B testing de templates
- [ ] Onboarding personalizado por segmento
- [ ] Integração com email de boas-vindas
- [ ] Tour interativo com hotspots

---

**Release Manager:** @kimi-code-cli  
**Reviewers:** Automated TDD + CI Gates  
**Status:** ✅ Ready for Merge
