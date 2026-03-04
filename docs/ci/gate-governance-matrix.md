# Gate Governance Matrix

> **Versão:** 1.0  
> **Data:** 2026-03-04  
> **Status:** Ativo

---

## Matriz de Ownership e SLA

| Gate/Workflow | Owner Técnico | Criticidade | SLA Resposta | Política de Deprecação |
|--------------|---------------|-------------|--------------|------------------------|
| vm-webapp-smoke | Platform Team | **critical** | 4h | Não deprecar - core gate |
| VM Editorial Governance Monitoring | Editorial Team | important | 8h | Revisar em 90 dias |
| v2.1.3 Residual Risk Gate | Governance Team | important | 8h | Integrar em v2.2 |
| vm-studio-run-binding-nightly | Studio Team | important | 24h | Manter - estável |
| v38 Onboarding TTFV Gate | Onboarding Team | important | 8h | Evoluir para v39 |
| v23 Approval Optimizer CI Gate | Governance Team | important | 8h | Merge em vm-webapp-smoke |
| v33 Onboarding Personalization CI Gate | Onboarding Team | important | 8h | Merge em v38 |
| v34 Onboarding Recovery Reactivation CI Gate | Onboarding Team | important | 8h | Merge em v38 |
| v35 Onboarding Continuity CI Gate | Onboarding Team | important | 8h | Merge em v38 |
| v36 Outcome Attribution & Hybrid ROI CI Gate | Analytics Team | important | 8h | Revisar após Q2 |
| v37 Unified Workspace UI CI Gate | Workspace Team | important | 8h | Evoluir para v40 |
| vm-editorial-ops-nightly | Editorial Team | legacy | 48h | **Deprecar em 60 dias** |
| Lint Scoped | Platform Team | important | 24h | Manter |
| v2 API Testing Suite | Platform Team | **critical** | 4h | Não deprecar - core suite |

---

## Legenda de Criticidade

| Nível | Definição | Ação em Falha |
|-------|-----------|---------------|
| **critical** | Bloqueia release, impacto em produção | PagerDuty + rollback automático |
| **important** | Impacta qualidade, não bloqueia release | Notificação Slack + card prioritário |
| **legacy** | Manutenção mínima, será deprecado | Notificação semanal |

---

## SLA de Resposta

| Prioridade | Tempo | Escalonamento |
|------------|-------|---------------|
| 4h | P0 - Critical | Equipe + Manager |
| 8h | P1 - Important | Equipe |
| 24h | P2 - Normal | Equipe (melhor esforço) |
| 48h | P3 - Legacy | Community/文档 |

---

## Política de Deprecação

### Critérios para Deprecação
1. **Duplicação:** Funcionalidade coberta por outro gate
2. **Inatividade:** Sem falhas relevantes por 90+ dias
3. **Legado:** Feature descontinuada
4. **Custos:** Custo de manutenção > valor agregado

### Processo de Deprecação
1. Criar issue de deprecação com justificativa
2. Notificar stakeholders (7 dias)
3. Adicionar warning no workflow (30 dias)
4. Mover para modo "dry-run" (30 dias)
5. Remover completamente

### Gates Marcados para Deprecação

| Gate | Motivo | Timeline | Ação Alternativa |
|------|--------|----------|------------------|
| vm-editorial-ops-nightly | Legado, duplicado | 60 dias | Usar VM Editorial Governance |
| v33-v35 (onboarding) | Duplicação | 90 dias | Merge em v38/v39 unificado |
| v23 | Overlap com smoke | 60 dias | Mover para vm-webapp-smoke |

---

## Responsabilidades

### Platform Team
- vm-webapp-smoke
- v2 API Testing Suite
- Lint Scoped
- Infraestrutura de CI

### Editorial Team
- VM Editorial Governance Monitoring
- vm-editorial-ops-nightly (legado)

### Governance Team
- v2.1.3 Residual Risk Gate
- v23 Approval Optimizer CI Gate
- Políticas de compliance

### Onboarding Team
- v38 Onboarding TTFV Gate
- v33-v35 Onboarding Gates

### Workspace Team
- v37 Unified Workspace UI CI Gate

### Analytics Team
- v36 Outcome Attribution & Hybrid ROI CI Gate

### Studio Team
- vm-studio-run-binding-nightly

---

## Checklist de Manutenção Mensal

- [ ] Revisar gates com taxa de verde < 50%
- [ ] Atualizar owners (rotatividade de equipe)
- [ ] Verificar gates marcados para deprecação
- [ ] Revisar SLAs (adequados à criticidade?)
- [ ] Documentar novos gates adicionados

---

## Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-03-04 | 1.0 | Criação inicial | CI Hardening Initiative |
