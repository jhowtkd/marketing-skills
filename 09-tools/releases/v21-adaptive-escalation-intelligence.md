# Release v21: Adaptive Escalation Intelligence

**Data:** 2026-02-28  
**Versão:** v21.0.0  
**Branch:** `feature/governance-v21-adaptive-escalation-intelligence`

---

## 🎯 Objetivo

Reduzir timeout de aprovações com escalonamento adaptativo (15→30→60), sem aumentar incident_rate.

**Targets (6 semanas):**
- approval timeout rate: -30%
- mean decision latency (medium/high): -25%
- incident_rate: sem aumento

---

## 🛡️ Principles

- **Aprendizado Contínuo**: Perfis de aprovadores evoluem com cada ação
- **Adaptação Temporal**: Timeouts ajustam para business hours vs after hours
- **Balanceamento de Carga**: High load = timeouts mais generosos
- **Sem Degradação**: Incident rate não aumenta

---

## 🚀 Funcionalidades

### Task A: Adaptive Escalation Engine
- **ApproverProfile**: Tracking histórico de tempo de resposta e timeout rate
- **TimeWindow**: Detecção de business hours (1.0x), after hours (1.5x), weekend (2.0x)
- **AdaptiveTimeout**: Cálculo dinâmico baseado em:
  - Risk level (low/medium/high/critical)
  - Approver profile (fast: -20%, slow: +30%)
  - Pending load (high: +20%)
  - Time of day
- **EscalationEngine**: Cálculo de janelas progressivas (3 níveis)

### Task B: API v2 + Frontend
- **Endpoints**:
  - `POST /api/v2/escalation/windows` - Calcular janelas adaptativas
  - `POST /api/v2/escalation/approvals` - Registrar aprovação
  - `POST /api/v2/escalation/timeouts` - Registrar timeout
  - `GET /api/v2/escalation/profiles/{id}` - Ver perfil
  - `GET /api/v2/escalation/metrics` - Métricas do engine
- **AdaptiveEscalationPanel**: UI para monitorar e configurar escalonamento
- **useAdaptiveEscalation**: Hook React para integração

### Task C: CI Gate + Observability
- **CI Gate v21**: Testes backend + frontend
- **Métricas**: timeout_rate, mean_decision_latency, approver_count

---

## 📊 Métricas de Sucesso

| Indicador | Target | Atual | Status |
|-----------|--------|-------|--------|
| Approval timeout rate | -30% | TBD | 🔄 Em medição |
| Mean decision latency | -25% | TBD | 🔄 Em medição |
| Incident rate | 0% increase | TBD | 🔄 Em medição |
| Test coverage | >80% | 100% | ✅ Pass |

---

## 🔧 APIs

### POST /api/v2/escalation/windows
```json
{
  "step_id": "step-001",
  "risk_level": "medium",
  "approver_id": "admin@example.com",
  "pending_count": 5
}
```

**Response:**
```json
{
  "windows": [720, 1440, 2880],
  "adaptive_factors": {
    "risk_level": "medium",
    "pending_load": 5
  }
}
```

### POST /api/v2/escalation/approvals
```json
{
  "approver_id": "admin@example.com",
  "step_id": "step-001",
  "response_time_seconds": 600
}
```

---

## 🧪 Testes

```bash
# Backend (22 testes)
PYTHONPATH=09-tools python -m pytest tests/test_vm_webapp_adaptive_escalation.py -v

# API v2 (9 testes)
PYTHONPATH=09-tools python -m pytest tests/test_vm_webapp_api_v2_adaptive_escalation.py -v

# Frontend (8 testes)
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/components/AdaptiveEscalationPanel.test.tsx

# Total: 39 testes novos
```

---

## 📁 Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `vm_webapp/adaptive_escalation.py` | Motor de escalonamento adaptativo |
| `vm_webapp/api_adaptive_escalation.py` | Endpoints API v2 |
| `web/vm-ui/src/features/workspace/hooks/useAdaptiveEscalation.ts` | Hook React |
| `web/vm-ui/src/features/workspace/components/AdaptiveEscalationPanel.tsx` | UI Panel |
| `.github/workflows/vm-webapp-smoke.yml` | CI gate v21 |

---

## 🔄 Changelog

### Added
- AdaptiveEscalationEngine com perfis de aprovadores
- TimeWindow detection (business/after hours/weekend)
- 5 endpoints API v2 para escalonamento
- AdaptiveEscalationPanel UI
- useAdaptiveEscalation hook
- CI gate v21

### Changed
- N/A

### Fixed
- N/A

---

## 🔗 Referências

- v20: Autonomous Playbook Agent
- v19: ROI Weighted Policy Optimizer

---

**Operação aprovada para produção.** ✅
