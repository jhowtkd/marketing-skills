# VM Studio v22 - Multi-Agent DAG Orchestrator

**Release Date:** 2026-03-01  
**Version:** v22.0.0

## Overview

Esta release entrega orquestração multi-agente por DAG com retries/timeouts robustos, supervisão humana por risco e operação completa no Studio.

## Architecture

- **Planner/Executor/Reviewer pattern** com orquestrador DAG
- **Fila de aprovações por nó** com risk-based routing
- **Auditoria completa** e painel Agent DAG Ops
- **Tech Stack:** FastAPI, SQLAlchemy/event-driven, Prometheus, React + Vitest/RTL

## Features

### Task 1: DAG Planner + Schema de Execução
- Criação de DAGs válidas com ordenação topológica
- Detecção automática de ciclos
- Modelos de dados: `DagNode`, `DagEdge`, `AgentDag`, `DagRun`
- Arquivos: `agent_dag.py`, `agent_dag_models.py`

### Task 2: Executor com Timeout/Retry/Handoff Resiliente
- Timeout de 15 minutos por nó
- 3 retries com backoff exponencial
- Idempotência por node/task_id
- Handoff failed após exaustão
- Arquivos: `agent_dag_executor.py`

### Task 3: Supervisão de Risco + Approvals por Nó
- Low-risk: auto-execute
- Medium/High-risk: waiting_approval
- Grant/Reject por nó específico
- Escalonamento por timeout (60 min)
- Arquivos: `agent_dag_supervisor.py`

### Task 4: API v2 DAG Ops Endpoints
- `POST /api/v2/dag/run` - Criar run
- `GET /api/v2/dag/run/{run_id}` - Consultar run
- `POST /api/v2/dag/run/{run_id}/pause` - Pausar
- `POST /api/v2/dag/run/{run_id}/resume` - Retomar
- `POST /api/v2/dag/run/{run_id}/abort` - Abortar
- `POST /api/v2/dag/run/{run_id}/node/{node_id}/retry` - Retry de nó
- `POST /api/v2/dag/approval/{request_id}/grant` - Aprovar
- `POST /api/v2/dag/approval/{request_id}/reject` - Rejeitar
- Arquivos: `api_agent_dag.py`, atualização `api.py`

### Task 5: Audit Trail + Metrics + Nightly DAG Section
- Métricas Prometheus: run/node/retry/timeout/approval_wait
- Audit trail completo de eventos
- Seção DAG no nightly report com gargalos
- Arquivos: `agent_dag_audit.py`, atualização `observability.py`, `nightly_report_v18.py`

### Task 6: Studio Agent DAG Ops Panel + CI/Docs
- Painel React: `AgentDagOpsPanel.tsx`
- Hook: `useAgentDagOps.ts`
- Testes: 11 testes RTL
- CI gate: `dag-orchestrator-gate-v22`

## Goals (6 weeks)

| Metric | Target | Status |
|--------|--------|--------|
| Throughput (jobs/day) | +30% | 🎯 On Track |
| Mean time to completion | -25% | 🎯 On Track |
| Handoff timeout failures | -40% | 🎯 On Track |
| Incident rate | No increase | 🎯 On Track |

## Test Coverage

```bash
# Backend Tests
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_agent_dag.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_agent_dag_executor.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_agent_dag_supervisor.py -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_api_v2.py::TestDagOpsEndpoints -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_vm_webapp_metrics_prometheus.py::TestDagMetrics -q
PYTHONPATH=09-tools .venv/bin/python -m pytest 09-tools/tests/test_editorial_ops_report.py::TestNightlyReportDagSection -q

# Frontend Tests
cd 09-tools/web/vm-ui && npm run test -- --run src/features/workspace/components/AgentDagOpsPanel.test.tsx

# Build
cd 09-tools/web/vm-ui && npm run build
```

## Migration Guide

1. **Database:** Nenhuma migração necessária (in-memory store para testes)
2. **API:** Endpoints v2 são aditivos, não quebram compatibilidade
3. **Frontend:** Novo painel é opcional até ativação completa

## Breaking Changes

Nenhuma - todos os componentes são aditivos.

## Known Issues

None

## Contributors

- VM Team

## References

- Plan: `docs/plans/2026-03-01-vm-studio-v22-multi-agent-dag-orchestrator-implementation.md`
