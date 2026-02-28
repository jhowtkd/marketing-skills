# VM Studio v14 - Segmented Editorial Copilot

## Overview
Personalização de sugestões do Copiloto Editorial por segmento (`brand + objective_key`) com elegibilidade baseada em volume, ajuste incremental com limites de segurança e fallback automático para ranking v13 global.

## Goals (6 weeks)
- `approval_without_regen_24h`: +5 p.p. sobre baseline v13
- `V1 score médio`: +6 pontos em segmentos elegíveis  
- `regenerações/job`: -15% em segmentos elegíveis

## Architecture

### Segmented Copilot Layer (v14)
Camada de personalização sobre o motor v13:
1. Resolver `segment_key = brand_id + objective_key`
2. Verificar elegibilidade (>=20 runs por segmento)
3. Se elegível: aplicar ajuste incremental no ranking base v13
4. Se inelegível/frozen: fallback para ranking v13 global

### Read-model de Segmento
Agregado por `segment_key`:
- `segment_runs_total`: Total de runs no segmento
- `segment_success_24h_rate`: Taxa de sucesso 24h
- `segment_v1_score_avg`: Score V1 médio
- `segment_regen_rate`: Taxa de regeneração
- `segment_last_updated_at`: Última atualização
- `segment_status`: `eligible | insufficient_volume | frozen | fallback`
- `adjustment_factor`: Fator de ajuste (-0.15 a +0.15)

### Guardrails de Segurança
- **Elegibilidade mínima**: 20 runs por segmento
- **Cap de ajuste**: ±15% no máximo
- **Freeze automático**: Após 7 dias de regressão forte (>10pp sucesso OU >5pts V1)
- **Fallback seguro**: Sempre preserva explainability

## API v2 (v14)

### Endpoints

#### GET /api/v2/threads/{thread_id}/copilot/suggestions
Extensão do endpoint v13 com campos de segmento:

**Response (novos campos):**
```json
{
  "thread_id": "t-xxx",
  "phase": "initial",
  "suggestions": [...],
  "guardrail_applied": false,
  "segment_key": "b1:awareness",
  "segment_status": "eligible",
  "adjustment_factor": 0.08,
  "is_eligible": true
}
```

#### GET /api/v2/threads/{thread_id}/copilot/segment-status
Novo endpoint de inspeção operacional:

**Response:**
```json
{
  "thread_id": "t-xxx",
  "brand_id": "b1",
  "project_id": "p1",
  "segment_key": "b1:awareness",
  "segment_status": "eligible",
  "is_eligible": true,
  "segment_runs_total": 50,
  "segment_success_24h_rate": 0.75,
  "segment_v1_score_avg": 82.0,
  "segment_regen_rate": 0.15,
  "adjustment_factor": 0.08,
  "minimum_runs_threshold": 20,
  "explanation": "Personalização ativa (50 runs). Confiança aumentada em 8%."
}
```

## UX no Studio

### Badges de Personalização
O painel do Copilot agora exibe badges indicando o estado da personalização:

- **"Personalização ativa"** (verde): Segmento elegível com ajuste aplicado
- **"Fallback global"** (cinza): Segmento inelegível ou congelado

### Informações de Volume
- Eligível: Mostra número de runs (ex: "50 runs")
- Inelegível: Mostra progresso (ex: "5/20 runs")

### Dev Mode
Informações técnicas visíveis em modo desenvolvimento:
- `segment_key`: Identificador do segmento
- `segment_status`: Estado atual
- `adjustment_factor`: Fator de ajuste aplicado

## Observabilidade

### Métricas Prometheus
Novas métricas para acompanhamento:

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `copilot_segment_eligible_total` | Counter | Sugestões com segmento elegível |
| `copilot_segment_fallback_total` | Counter | Fallback para v13 global |
| `copilot_segment_freeze_total` | Counter | Segmentos congelados por regressão |
| `copilot_segment_adjustment_bucket:*` | Counter | Distribuição de ajustes |

### KPIs de Acompanhamento
- `segment_personalization_coverage`: Segmentos elegíveis / segmentos ativos
- `segment_lift_success_24h`: Delta de sucesso vs fallback

## Rollout

### Fase 1: Shadow Mode (Semana 1-2)
- Segmentação calculada mas não aplicada
- Logging e métricas coletadas
- Validação de dados

### Fase 2: Piloto (Semana 3-4)
- 2-3 brands com segmentos elegíveis
- Monitoramento intenso
- Ajuste de thresholds

### Fase 3: Expansão (Semana 5-6)
- Todos segmentos elegíveis
- Alertas operacionais ativos

## Riscos e Mitigação

| Risco | Mitigação |
|-------|-----------|
| Overfitting por pouco volume | Gate de 20 runs + fallback automático |
| Oscilação de recomendação | Cap de ajuste ±15% |
| Regressão silenciosa | Freeze automático + alerta operacional |
| Degradação de UX | Fallback limpo preserva explainability |

## Technical Details

### Files Changed
- `09-tools/vm_webapp/copilot_segments.py` (new)
- `09-tools/vm_webapp/editorial_copilot.py` (modified)
- `09-tools/vm_webapp/api.py` (modified)
- `09-tools/vm_webapp/api_copilot.py` (modified)
- `09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts` (modified)
- `09-tools/web/vm-ui/src/features/workspace/components/CopilotPanel.tsx` (modified)
- `.github/workflows/vm-webapp-smoke.yml` (modified)

### Test Coverage
- Backend: 35 new tests (segments, adjustment, API, metrics)
- Frontend: 9 new tests (hook, panel badges)
- Total: 44 new tests passing

### CI Gates
- `segmented-copilot-gate-v14`: Valida backend e frontend
- Build verification incluído

## Related
- v13: Editorial Copilot base (#v13-editorial-copilot)
- v12: First-run ranking (#v12-first-run-ranking)
