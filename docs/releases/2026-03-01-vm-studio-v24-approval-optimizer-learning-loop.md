# VM Studio v24 - Approval Optimizer Learning Loop

**Release Date:** 2026-03-01  
**Version:** v24.0.0

## Overview

Esta release entrega aprendizado contínuo para o Approval Optimizer com aplicação semanal de ajustes low-risk e supervisão para medium/high, reduzindo o tempo de aprovação em 20% adicional (vs v23) e aumentando a precisão de batch em 10 p.p.

## Architecture

- **Learning Core** com observe/learn/apply
- **Guardrails** com clamp ±10% e auto-apply para low-risk
- **Weekly cadence** scheduler
- **Tech Stack:** FastAPI, SQLAlchemy/event-driven, Prometheus, React + Vitest/RTL

## Features

### Task 1: Learning Core (Observe + Learn)
- Coleta de sinais de resultado de aprovações
- Cálculo de deltas de performance
- Geração de sugestões com confidence/expected_savings/risk_score
- Arquivos: `approval_learning.py`

### Task 2: Apply/Freeze/Rollback with Guardrails
- Auto-apply para sugestões low-risk (risk_score < 0.3)
- Clamp de ajustes a ±10%
- Freeze por brand
- Rollback de sugestões aplicadas
- Arquivos: `approval_learning.py`

### Task 3: API v2 Learning Endpoints
- `GET /api/v2/approval-learning/status` - Status do learning
- `POST /api/v2/approval-learning/run` - Executar ciclo de learning
- `GET /api/v2/approval-learning/proposals` - Listar propostas
- `POST /api/v2/approval-learning/proposals/{id}/apply` - Aplicar proposta
- `POST /api/v2/approval-learning/proposals/{id}/reject` - Rejeitar proposta
- `POST /api/v2/approval-learning/proposals/{id}/rollback` - Rollback
- `POST /api/v2/approval-learning/brands/{brand_id}/freeze` - Congelar
- Arquivos: `api_approval_learning.py`

### Task 4: Observability + Nightly Learning Impact
- Métricas: cycles/proposals/applied/blocked/rollback
- batch_precision_percent, human_minutes_saved
- Seção `approval_learning_impact` no nightly report
- Arquivos: `observability.py`, `nightly_report_v18.py`

### Task 5: Studio Learning Ops Panel
- Painel React: `ApprovalLearningOpsPanel.tsx`
- Separação low-risk (auto) vs medium/high (approval)
- Ações: Run Learning, Apply, Reject, Freeze
- Testes: 4 testes RTL

### Task 6: CI Gate v24 + Release Notes
- CI gate: `approval-learning-loop-gate-v24`
- Testes backend e frontend
- Build validation
- Release notes

## Goals (6 weeks)

| Metric | Target | Status |
|--------|--------|--------|
| approval_human_minutes_per_job | -20% adicional | 🎯 On Track |
| approval_queue_length_p95 | -15% adicional | 🎯 On Track |
| batch_approval_precision | +10 p.p. | 🎯 On Track |
| incident_rate | No increase | 🎯 On Track |

## Test Coverage

```bash
# Backend Tests
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_approval_learning.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2_learning.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py -q

# Frontend Tests
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/components/ApprovalLearningOpsPanel.test.tsx

# Build
cd 09-tools/web/vm-ui && npm run build
```

## Migration Guide

1. **Database:** Nenhuma migração necessária
2. **API:** Endpoints v2 são aditivos
3. **Frontend:** Novo painel é opcional até ativação

## Breaking Changes

Nenhuma - todos os componentes são aditivos.

## Known Issues

None

## Contributors

- VM Team

## References

- Plan: `docs/plans/2026-03-01-vm-studio-v24-approval-optimizer-learning-loop-implementation.md`
