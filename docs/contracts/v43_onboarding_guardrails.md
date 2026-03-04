# v43 Onboarding Frontend Contract Tests

**Data:** 2026-03-04  
**Sprint:** v43  
**Agente:** AGENTE B

---

## Resumo

Este documento define os contratos de teste implementados no frontend do onboarding para garantir a estabilidade e previsibilidade do fluxo de onboarding.

---

## 1. Contrato de Ordem de Steps v42 (Template First)

**Arquivo:** `09-tools/web/vm-ui/src/features/onboarding/OnboardingWizard.test.tsx`

### Regra
A ordem oficial dos steps no onboarding é **v42 Variant A: Template First**:

```
welcome → template_selection → workspace_setup → customization → completion
   1           2                   3                4              5
```

### Testes Implementados

| Teste | Descrição |
|-------|-----------|
| `deve seguir ordem oficial de steps v42` | Valida a ordem exata dos 5 steps |
| `deve permitir navegação back respeitando a ordem v42` | Valida navegação reversa |
| `deve permitir skip em qualquer step` | Valida funcionalidade de skip |

### Impacto de Mudanças
- **Se STEP_ORDER for alterado:** Os testes de contrato falharão
- **Ação necessária:** Atualizar explicitamente o teste e este documento
- **Motivo:** Prevenir mudanças acidentais na ordem que impactam TTFV (Time To First Value)

---

## 2. Contrato de Eventos de Telemetry

**Arquivo:** `09-tools/web/vm-ui/src/features/onboarding/ttfvTelemetry.test.ts`

### Eventos Essenciais

| Evento | Campos Obrigatórios | Descrição |
|--------|---------------------|-----------|
| `onboarding_started` | `event`, `userId`, `sessionId`, `timestamp` | Início do onboarding |
| `onboarding_progress_saved` | `event`, `userId`, `sessionId`, `timestamp`, `step`, `metadata.savedStep`, `metadata.source` | Salvamento de progresso |
| `fast_lane_presented` | `userId`, `sessionId`, `timestamp`, `step`, `metadata.confidence`, `metadata.recommendedPath`, `metadata.timeSavedMinutes`, `metadata.skippedSteps`, `metadata.reasons` | Oferta de fast lane |
| `fast_lane_accepted` | `userId`, `sessionId`, `timestamp`, `step`, `metadata.confidence`, `metadata.timeSavedMinutes`, `metadata.skippedSteps` | Aceite de fast lane |
| `fast_lane_rejected` | `userId`, `sessionId`, `timestamp`, `step`, `reason`, `metadata.confidence`, `metadata.reasons` | Rejeição de fast lane |
| `first_value_reached` | `event`, `userId`, `sessionId`, `timestamp`, `ttfvMs`, `ttfvMinutes`, `templateId` | Primeiro valor alcançado |

### Validações de Shape

```typescript
// CONTRATO: confidence deve estar entre 0 e 1
expect(body.metadata.confidence).toBeGreaterThanOrEqual(0);
expect(body.metadata.confidence).toBeLessThanOrEqual(1);

// CONTRATO: recommendedPath deve ser fast_lane ou standard
expect(['fast_lane', 'standard']).toContain(body.metadata.recommendedPath);

// CONTRATO: source deve ser manual, auto_save ou resume
expect(['manual', 'auto_save', 'resume']).toContain(body.metadata.source);

// CONTRATO: timestamp deve estar em formato ISO
expect(body.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
```

---

## 3. Testes de Fallback (Resiliência)

### OnboardingWizard.test.tsx

| Teste | Cenário | Comportamento Esperado |
|-------|---------|------------------------|
| `deve continuar funcionando quando API de progresso retorna 500` | API progress falha | Wizard continua funcionando normalmente |
| `deve continuar funcionando quando API de progresso retorna timeout` | Timeout na API | Wizard inicia sem prompt de resume |
| `deve continuar funcionando quando auto-save falha silenciosamente` | Falha no auto-save | Usuário continua navegando normalmente |

### ttfvTelemetry.test.ts

| Teste | Cenário | Comportamento Esperado |
|-------|---------|------------------------|
| `deve logar erro silenciosamente quando telemetry falha` | Network error | Erro logado, exceção não lançada |
| `deve logar erro quando API retorna status 500` | HTTP 500 | Erro logado silenciosamente |
| `deve logar erro quando API retorna 429` | Rate limit | Erro logado silenciosamente |
| `deve continuar funcionando mesmo quando todas as chamadas de telemetry falham` | Falha total | Nenhuma exceção lançada |

---

## Comandos de Validação

```bash
# Testes de contrato do OnboardingWizard
npm run test -- --run OnboardingWizard.test.tsx

# Testes de contrato de telemetry
npm run test -- --run ttfvTelemetry.test.ts

# Build de produção
npm run build

# Todos os testes
npm run test -- --run
```

---

## Estatísticas de Implementação

| Métrica | Valor |
|---------|-------|
| Testes adicionados no OnboardingWizard.test.tsx | 6 novos testes |
| Testes adicionados no ttfvTelemetry.test.ts | 11 novos testes |
| Total de testes no arquivo OnboardingWizard | 36 testes |
| Total de testes no arquivo ttfvTelemetry | 30 testes |
| Total de testes no projeto | 770 testes |
| Build | ✅ Sucesso |

---

## Notas de Implementação

1. **Priorização de contratos:** Os testes foram escritos para falhar explicitamente se contratos forem violados, garantindo que mudanças na ordem de steps ou no shape de eventos sejam intencionais.

2. **Fallback graceful:** Todos os testes de fallback garantem que o wizard continua funcionando mesmo quando APIs falham, priorizando a experiência do usuário sobre a telemetria.

3. **Sem mudanças de comportamento:** Apenas testes foram adicionados. Nenhum código de produção foi alterado, mantendo a estabilidade do sistema.

---

## Referências

- v38: TTFV Telemetry tracking
- v39: Fast lane CTA
- v40: Save/Resume functionality
- v42: Template First step order
- v43: Contract tests (esta implementação)
