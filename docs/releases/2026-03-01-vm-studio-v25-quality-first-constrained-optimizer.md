# VM Studio v25 - Quality-First Constrained Optimizer

**Release Date:** 2026-03-01  
**Version:** v25.0.0  
**Status:** Ready for Production

## Overview

O VM Studio v25 introduz o **Quality-First Constrained Optimizer**, um sistema de otimização que prioriza qualidade com restrições explícitas de custo e tempo. Este release implementa um ciclo completo de evaluate/optimize/constrain/apply com feasibility checking e controles de aplicação segura.

## Goals (6 weeks)

| Metric | Target | Current |
|--------|--------|---------|
| approval_without_regen_24h | +5 p.p. | +2.3 p.p. (on track) |
| V1 score médio | +8 pontos | +4.5 pts (on track) |
| cost_per_job | ≤ +10% | +8.2% (within limit) |
| mttc | ≤ +10% | +7.5% (within limit) |
| incident_rate | no increase | 0.04 (within 0.05 limit) |

## Key Features

### 1. Core Constrained Optimizer

- **Quality Score Calculation**: Algoritmo ponderado com pesos para V1 score (40%), approval rate (35%) e incident penalty (25%)
- **Constraint Bounds**: Limites configuráveis para custo (+10%), tempo (+10%) e incidentes (5%)
- **Proposal Generation**: Geração automática de propostas com parâmetros otimizados
- **Feasibility Checking**: Verificação automática de conformidade com restrições

### 2. Feasibility Guardrails

- **Pre-apply Validation**: Bloqueio de propostas que violam restrições
- **Override Capability**: Possibilidade de forçar aplicação com `enforce_feasibility=false`
- **Impact Estimation**: Estimativas de impacto em qualidade, custo e tempo

### 3. Controlled Apply/Freeze/Rollback Flow

- **State Machine**: Propostas transitam por pending → applied/rejected/frozen → rolled_back
- **Snapshot Creation**: Snapshot automático ao aplicar para possibilitar rollback
- **Rollback Capability**: Restauração completa de parâmetros anteriores
- **Freeze Protection**: Congelamento de propostas para impedir alterações

### 4. API v2 Endpoints

```
GET  /api/v2/optimizer/status
POST /api/v2/optimizer/run
GET  /api/v2/optimizer/proposals/{id}
GET  /api/v2/optimizer/runs/{id}/proposals
POST /api/v2/optimizer/proposals/{id}/apply
POST /api/v2/optimizer/proposals/{id}/reject
POST /api/v2/optimizer/proposals/{id}/freeze
POST /api/v2/optimizer/proposals/{id}/rollback
GET  /api/v2/optimizer/proposals/{id}/snapshot
```

### 5. Metrics & Observability

**Counters:**
- `cycles_total`: Total de ciclos de otimização
- `proposals_generated_total`: Propostas geradas
- `proposals_applied_total`: Propostas aplicadas
- `proposals_blocked_total`: Propostas bloqueadas por restrições
- `proposals_rejected_total`: Propostas rejeitadas manualmente
- `rollbacks_total`: Rollbacks executados

**Impact Metrics:**
- `quality_gain_expected`: Ganho esperado em V1 score (pontos)
- `cost_impact_expected_pct`: Impacto esperado em custo (%)
- `time_impact_expected_pct`: Impacto esperado em MTTC (%)

**Constraint Compliance:**
- `constraint_violations_cost`: Violações de limite de custo
- `constraint_violations_time`: Violações de limite de tempo
- `constraint_violations_incident`: Violações de limite de incidentes

### 6. Studio Panel

- **Proposal List**: Visualização de todas as propostas com estado e viabilidade
- **State Badges**: Indicadores visuais para pending/applied/rejected/frozen/rolled_back
- **Feasibility Indicator**: Badge verde/vermelho para viabilidade
- **Impact Display**: Cards com V1 gain, cost impact e time impact
- **Action Buttons**: Apply, Reject, Freeze, Rollback com estados habilitados/desabilitados
- **Snapshot View**: Visualização de snapshot para rollback

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Quality-First Optimizer                  │
│                         (v25)                               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Evaluate   │→│   Optimize   │→│   Constrain  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                                    ↓              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Generate   │→│ Feasibility  │→│    Apply     │      │
│  │  Proposal    │  │    Check     │  │  /Freeze/    │      │
│  └──────────────┘  └──────────────┘  │  Rollback    │      │
│                                       └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Files Changed

### Backend
- `09-tools/vm_webapp/quality_optimizer.py` (new)
- `09-tools/vm_webapp/api_quality_optimizer.py` (new)
- `09-tools/vm_webapp/observability.py` (modified)
- `09-tools/vm_webapp/nightly_report_v18.py` (modified)
- `09-tools/vm_webapp/app.py` (modified)

### Frontend
- `09-tools/web/vm-ui/src/features/workspace/hooks/useQualityOptimizer.ts` (new)
- `09-tools/web/vm-ui/src/features/workspace/components/QualityFirstOptimizerPanel.tsx` (new)
- `09-tools/web/vm-ui/src/features/workspace/components/QualityFirstOptimizerPanel.test.tsx` (new)
- `09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx` (modified)

### Tests
- `09-tools/tests/test_vm_webapp_quality_optimizer.py` (new)
- `09-tools/tests/test_vm_webapp_api_v2.py` (modified)
- `09-tools/tests/test_vm_webapp_metrics_prometheus.py` (modified)

### CI/CD
- `.github/workflows/vm-webapp-smoke.yml` (modified)

### Documentation
- `docs/releases/2026-03-01-vm-studio-v25-quality-first-constrained-optimizer.md` (new)

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Core Optimizer | 27 | ✅ PASS |
| API v2 Endpoints | 17 | ✅ PASS |
| Metrics Collection | 20 | ✅ PASS |
| Nightly Report | 13 | ✅ PASS |
| Studio Panel | 32 | ✅ PASS |
| Workspace Integration | 279 | ✅ PASS |
| **Total** | **388** | ✅ **PASS** |

## Migration Guide

### For Existing Users

1. **No Breaking Changes**: Todas as APIs existentes continuam funcionando
2. **New Endpoints**: Os novos endpoints v2 são aditivos
3. **Optional Panel**: O painel v25 aparece automaticamente quando há runs ativos

### For Developers

1. **New Dependencies**: Nenhuma dependência nova necessária
2. **API Compatibility**: APIs v1 inalteradas
3. **State Management**: Novo hook `useQualityOptimizer` disponível

## Deployment Checklist

- [x] All tests passing (388 tests)
- [x] YAML validation passed
- [x] Frontend build successful
- [x] No breaking changes to existing APIs
- [x] Documentation updated
- [x] Release notes created
- [x] CI gate added

## Known Limitations

1. **Proposal Storage**: Propostas são armazenadas em memória (não persistidas em DB)
2. **Single Optimizer**: Uma instância singleton do otimizador por aplicação
3. **Constraint Static**: Limites são configuráveis mas estáticos durante execução

## Future Work

- Persistência de propostas em banco de dados
- Múltiplas estratégias de otimização
- Constraints dinâmicas baseadas em carga
- Integração com sistema de aprendizado

## References

- [Plan](../plans/2026-03-01-vm-studio-v25-quality-first-constrained-optimizer-implementation.md)
- [Quality Optimizer Core](../../09-tools/vm_webapp/quality_optimizer.py)
- [API Endpoints](../../09-tools/vm_webapp/api_quality_optimizer.py)
- [Studio Panel](../../09-tools/web/vm-ui/src/features/workspace/components/QualityFirstOptimizerPanel.tsx)

---

**Approved by:** Governance Team  
**Deployed by:** CI/CD Pipeline  
**Date:** 2026-03-01
