# v45 Auto-Rollout Policy Contract

> **Versão:** 1.0.0  
> **Sprint:** v45  
> **Status:** Draft  
> **Owner:** Growth Engineering Team

---

## 1. POLICY CONTRACT

### 1.1 Estrutura de Policy por Experimento

Cada experimento ativo no sistema de Auto-Rollout deve ter uma policy documentada com os seguintes campos:

```typescript
interface AutoRolloutPolicy {
  // Identificação
  experiment_id: string;           // UUID único do experimento
  policy_version: string;          // SemVer da policy (ex: "1.0.0")
  created_at: ISO8601Timestamp;
  updated_at: ISO8601Timestamp;
  
  // Estado atual
  active_variant: "control" | "treatment" | string;  // Variante atualmente ativa
  rollout_mode: "manual" | "auto";                   // Modo de operação
  
  // Metadados de decisão
  last_evaluation: ISO8601Timestamp | null;          // Última avaliação automática
  decision_reason: string | null;                    // Razão da última decisão
  decision_trigger: "scheduled" | "threshold" | "manual" | null;
  
  // Configuração de segurança
  rollback_target: "control" | string;               // Variante de fallback
  auto_rollback_enabled: boolean;                    // Rollback automático ativo?
  
  // Thresholds customizados (sobrescrevem defaults)
  custom_gates?: Partial<PromotionGates>;
  
  // Histórico
  decision_history: DecisionLogEntry[];
}

interface DecisionLogEntry {
  timestamp: ISO8601Timestamp;
  from_variant: string;
  to_variant: string;
  reason: string;
  gates_passed?: string[];
  gates_failed?: string[];
  metrics_snapshot: Record<string, number>;
}
```

### 1.2 Formato de Persistência

**Formato primário:** JSON

```json
{
  "experiment_id": "exp_abc123",
  "policy_version": "1.0.0",
  "created_at": "2026-03-04T19:46:15Z",
  "updated_at": "2026-03-04T20:00:00Z",
  "active_variant": "control",
  "rollout_mode": "auto",
  "last_evaluation": "2026-03-04T19:45:00Z",
  "decision_reason": "Aguardando atingir N=30 para avaliação inicial",
  "decision_trigger": "scheduled",
  "rollback_target": "control",
  "auto_rollback_enabled": true,
  "custom_gates": null,
  "decision_history": []
}
```

**Storage:**
- **Runtime:** Redis (key: `rollout:policy:{experiment_id}`)
- **Durabilidade:** PostgreSQL (tabela `experiment_policies`)
- **Backup:** S3 (snapshot diário em formato JSONL)

### 1.3 Versionamento de Policy

| Componente | Padrão | Descrição |
|------------|--------|-----------|
| `policy_version` | SemVer | Versão da estrutura da policy |
| `contract_version` | SemVer | Versão deste contrato (documento) |
| Migrações | Forward-only | Não suportamos downgrade de policy |

**Regras de versionamento:**
- **MAJOR:** Mudanças breaking na estrutura (campos obrigatórios removidos)
- **MINOR:** Novos campos opcionais, novos gates
- **PATCH:** Correções de documentação, clarificações

---

## 2. PROMOTION GATES (Critérios de Segurança)

Todos os gates devem ser satisfeitos para promoção automática ocorrer.

### 2.1 Gate de Ganho Mínimo

| Atributo | Valor |
|----------|-------|
| **ID** | `min_gain` |
| **Threshold** | `score > 1.005` vs control |
| **Métrica** | Score composto do experimento |
| **Racional** | Apenas promover se há ganho real (>0.5% improvement) |

```python
def check_min_gain(control_score: float, treatment_score: float) -> bool:
    """Retorna True se treatment tem ganho mínimo vs control."""
    relative_gain = treatment_score / control_score
    return relative_gain > 1.005
```

### 2.2 Gate de Estabilidade

| Atributo | Valor |
|----------|-------|
| **ID** | `stability` |
| **Amostra mínima** | N ≥ 30 simulações por variante |
| **Confiança estatística** | ≥ 95% (p-value < 0.05) |
| **Métrica** | Teste t de Student ou Mann-Whitney U |

```python
def check_stability(control_samples: list[float], 
                    treatment_samples: list[float]) -> tuple[bool, float]:
    """Retorna (passou, p_value)."""
    from scipy import stats
    
    n_control = len(control_samples)
    n_treatment = len(treatment_samples)
    
    if n_control < 30 or n_treatment < 30:
        return False, 1.0
    
    _, p_value = stats.ttest_ind(control_samples, treatment_samples)
    return p_value < 0.05, p_value
```

### 2.3 Gate de Risco

| Atributo | Valor | Descrição |
|----------|-------|-----------|
| **ID** | `risk` |
| **Completion rate** | ≥ 95% do control | Não degradar conversão |
| **Abandono** | ≤ 110% do control | Não aumentar churn |

```python
def check_risk(control_metrics: dict, treatment_metrics: dict) -> dict:
    """Retorna resultado de cada sub-check."""
    results = {}
    
    # Completion rate check
    control_cr = control_metrics['completion_rate']
    treatment_cr = treatment_metrics['completion_rate']
    cr_ratio = treatment_cr / control_cr if control_cr > 0 else 0
    results['completion_rate_ok'] = cr_ratio >= 0.95
    
    # Abandonment check  
    control_ab = control_metrics['abandonment_rate']
    treatment_ab = treatment_metrics['abandonment_rate']
    ab_ratio = treatment_ab / control_ab if control_ab > 0 else float('inf')
    results['abandonment_ok'] = ab_ratio <= 1.10
    
    return results
```

### 2.4 Gate de Regressão (TTFV)

| Atributo | Valor |
|----------|-------|
| **ID** | `ttfv_regression` |
| **Métrica** | Time To First Value (TTFV) |
| **Threshold** | Aumento máximo de 10% vs control |

```python
def check_ttfv_regression(control_ttfv: float, treatment_ttfv: float) -> bool:
    """TTFV não pode aumentar mais que 10%."""
    if control_ttfv <= 0:
        return treatment_ttfv <= 0  # Ambos devem ser <= 0 ou treatment menor
    
    increase_ratio = treatment_ttfv / control_ttfv
    return increase_ratio <= 1.10
```

### 2.5 Resumo dos Gates

```yaml
promotion_gates:
  min_gain:
    enabled: true
    threshold: 1.005
    comparison: relative_to_control
  
  stability:
    enabled: true
    min_samples: 30
    confidence_level: 0.95
  
  risk:
    enabled: true
    completion_rate_min_ratio: 0.95
    abandonment_max_ratio: 1.10
  
  ttfv_regression:
    enabled: true
    max_increase_ratio: 1.10
```

---

## 3. ROLLBACK POLICY

### 3.1 Condições de Rollback Automático

O sistema dispara rollback automático para `rollback_target` (sempre "control") quando:

| Condição | Threshold | Severidade |
|----------|-----------|------------|
| **Score degradação** | Score < 1.0 vs control | CRITICAL |
| **Completion rate drop** | Queda > 5% vs baseline | HIGH |
| **Abandono spike** | Aumento > 10% vs baseline | HIGH |
| **Erro técnico** | Taxa de erro > 1% | CRITICAL |

```python
class RollbackConditions:
    """Condições que disparam rollback automático."""
    
    SCORE_DEGRADATION = {
        'check': lambda t, c: t < c * 1.0,
        'severity': 'CRITICAL',
        'cooldown_minutes': 5
    }
    
    COMPLETION_RATE_DROP = {
        'check': lambda t, c: t < c * 0.95,
        'severity': 'HIGH',
        'cooldown_minutes': 10
    }
    
    ABANDONMENT_SPIKE = {
        'check': lambda t, c: t > c * 1.10,
        'severity': 'HIGH', 
        'cooldown_minutes': 10
    }
```

### 3.2 Configuração de Rollback

```yaml
rollback_policy:
  enabled: true
  target_variant: "control"  # Sempre control
  auto_rollback_triggers:
    - score_degradation
    - completion_rate_drop
    - abandonment_spike
    - technical_error
  cooldown_period_minutes: 5   # Evitar flip-flop
  max_rollbacks_per_hour: 3    # Circuit breaker
  require_manual_after: 2      # Após 2 rollbacks, requer aprovação
```

### 3.3 Rollback Manual

Operadores podem trigger rollback manual via:
- Dashboard: Botão "Emergency Rollback"
- API: `POST /api/v1/experiments/{id}/rollback`
- CLI: `kimi rollout rollback --experiment-id={id}`

Rollback manual ignora cooldowns mas requer justificativa.

---

## 4. DECISION ALGORITHM

### 4.1 Passo a Passo da Avaliação

```
┌─────────────────────────────────────────────────────────────┐
│  DECISION ALGORITHM - Auto-Rollout v1.0                     │
└─────────────────────────────────────────────────────────────┘

INICIALIZAÇÃO
  ├── Carregar policy do experimento
  ├── Verificar rollout_mode == "auto"
  └── Se manual → LOG(skip) → FIM

CHECAGEM DE PRECONDIÇÕES
  ├── Verificar se há dados suficientes (N >= 30)
  ├── Verificar se variantes estão healthy (no errors)
  └── Se falha → AGUARDAR → FIM

AVALIAÇÃO DE ROLLBACK (primeiro - segurança)
  ├── Checar condições de rollback
  │   ├── Score < 1.0?
  │   ├── Completion rate drop > 5%?
  │   ├── Abandono spike > 10%?
  │   └── Erro técnico?
  └── Se qualquer condição → ROLLBACK → FIM

AVALIAÇÃO DE PROMOTION GATES
  ├── Gate 1: Ganho mínimo (score > 1.005)
  │   └── Se falha → LOG(blocked) → FIM
  ├── Gate 2: Estabilidade (N>=30, confiança>=95%)
  │   └── Se falha → LOG(blocked) → FIM
  ├── Gate 3: Risco (completion≥95%, abandono≤110%)
  │   └── Se falha → LOG(blocked) → FIM
  ├── Gate 4: Regressão TTFV (≤10% increase)
  │   └── Se falha → LOG(blocked) → FIM
  └── Todos passaram → PROMOTE → FIM

FIM
  ├── Registrar decisão no history
  ├── Emitir telemetry event
  └── Atualizar timestamps
```

### 4.2 Ordem de Checagem

**Prioridade 1 (Segurança):** Rollback conditions → Proteger usuários
**Prioridade 2 (Validação):** Promotion gates → Garantir qualidade
**Prioridade 3 (Ação):** Promote ou Manter

### 4.3 Default Seguro

Em qualquer situação de dúvida ou erro:
- **Default:** Manter em `control`
- **Ação:** Logar warning + alertar operador
- **Nunca:** Promover com dados inconclusivos

```python
class SafeDefaultDecision:
    """Quando em dúvida, manter controle."""
    
    def decide(self, uncertainty_reason: str) -> Decision:
        return Decision(
            action='maintain',
            target_variant='control',
            reason=f"Safe default: {uncertainty_reason}",
            requires_attention=True
        )
```

---

## 5. TELEMETRY DE GOVERNANÇA

### 5.1 Eventos de Governance

#### `experiment_promoted`

Emitido quando uma variante é promovida para 100% do tráfego.

```json
{
  "event_type": "experiment_promoted",
  "timestamp": "2026-03-04T20:15:30Z",
  "experiment_id": "exp_abc123",
  "payload": {
    "variant_id": "treatment_v2",
    "previous_variant": "control",
    "score": 1.023,
    "score_vs_control": 1.023,
    "gates_passed": ["min_gain", "stability", "risk", "ttfv_regression"],
    "sample_size_control": 150,
    "sample_size_treatment": 152,
    "confidence_level": 0.97,
    "decision_duration_seconds": 45
  },
  "context": {
    "policy_version": "1.0.0",
    "triggered_by": "scheduled_evaluation",
    "evaluated_at": "2026-03-04T20:15:00Z"
  }
}
```

#### `experiment_promotion_blocked`

Emitido quando promotion é bloqueada por gates não atingidos.

```json
{
  "event_type": "experiment_promotion_blocked",
  "timestamp": "2026-03-04T20:15:30Z",
  "experiment_id": "exp_abc123",
  "payload": {
    "variant_id": "treatment_v2",
    "gates_failed": ["min_gain", "stability"],
    "gates_passed": ["risk"],
    "failure_reasons": {
      "min_gain": "Score 1.002 below threshold 1.005",
      "stability": "Insufficient samples: N=15 (required: 30)"
    },
    "metrics_snapshot": {
      "control_score": 0.85,
      "treatment_score": 0.852,
      "control_completion": 0.92,
      "treatment_completion": 0.91
    }
  },
  "context": {
    "policy_version": "1.0.0",
    "next_evaluation_scheduled": "2026-03-04T21:15:00Z"
  }
}
```

#### `experiment_rolled_back`

Emitido quando ocorre rollback (automático ou manual).

```json
{
  "event_type": "experiment_rolled_back",
  "timestamp": "2026-03-04T20:15:30Z",
  "experiment_id": "exp_abc123",
  "payload": {
    "from_variant": "treatment_v2",
    "to_variant": "control",
    "rollback_type": "automatic",
    "trigger_reason": "score_degradation",
    "reason_details": "Treatment score 0.89 dropped below control 0.91",
    "time_in_treatment_minutes": 127,
    "affected_users": 342,
    "metrics_at_rollback": {
      "control_score": 0.91,
      "treatment_score": 0.89,
      "control_completion": 0.92,
      "treatment_completion": 0.87
    }
  },
  "context": {
    "policy_version": "1.0.0",
    "triggered_by": "monitoring_alert",
    "manual_approval": null
  }
}
```

### 5.2 Schema de Telemetry

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `event_type` | string | Tipo do evento |
| `timestamp` | ISO8601 | Quando ocorreu |
| `experiment_id` | string | ID do experimento |
| `payload` | object | Dados específicos do evento |
| `context` | object | Metadados de contexto |

### 5.3 Destinos de Telemetry

```yaml
telemetry_destinations:
  primary:
    - datadog_events
    - kafka_topic: "experiment.governance"
  
  secondary:
    - s3_bucket: "s3://telemetry/experiments/"
    - bigquery_table: "analytics.experiment_events"
  
  alerting:
    - pagerduty: CRITICAL events
    - slack: HIGH events
    - email_digest: daily summary
```

---

## 6. STATE MACHINE

### 6.1 Diagrama de Estados

```
                              ┌─────────────────────────────────────┐
                              │                                     │
                              ▼                                     │
┌─────────┐    start     ┌─────────┐    evaluate    ┌─────────────┐ │
│  DRAFT  │─────────────►│ CONTROL │───────────────►│  EVALUATING │─┘
└─────────┘              └────┬────┘                └──────┬──────┘
                              │                            │
                              │ manual rollback            │ all gates pass
                              │◄───────────────────────────┤
                              │                            │
                              │                            ▼
                              │                     ┌─────────────┐
                              │                     │  PROMOTED   │
                              │                     └──────┬──────┘
                              │                            │
                              │ rollback triggered         │ degradation detected
                              │◄───────────────────────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ROLLED_BACK  │
                       └──────┬──────┘
                              │
                              │ manual review
                              ▼
                       ┌─────────────┐
                       │   CLOSED    │
                       └─────────────┘
```

### 6.2 Estados e Definições

| Estado | Descrição | Permissões |
|--------|-----------|------------|
| `DRAFT` | Experimento configurado, não iniciado | Editar config, Start |
| `CONTROL` | 100% tráfego no controle, aguardando dados | Pause, Stop, Manual promote |
| `EVALUATING` | Coletando dados, checando gates periodicamente | Pause, Emergency rollback |
| `PROMOTED` | Treatment ativo como nova baseline | Monitor, Rollback |
| `ROLLED_BACK` | Retornado para control após problema | Review, Close, Restart |
| `CLOSED` | Experimento arquivado | Read-only |

### 6.3 Transições e Condições

```yaml
state_transitions:
  DRAFT_to_CONTROL:
    trigger: manual_start
    permissions: [experiment_admin]
    
  CONTROL_to_EVALUATING:
    trigger: traffic_split_started
    condition: treatment_receiving_traffic
    
  EVALUATING_to_CONTROL:
    trigger: gates_not_met
    condition: evaluation_completed AND not_all_gates_passed
    
  EVALUATING_to_PROMOTED:
    trigger: auto_promotion
    condition: |
      all_gates_passed AND 
      no_rollback_conditions AND
      cooldown_period_elapsed
    
  EVALUATING_to_ROLLED_BACK:
    trigger: auto_rollback
    condition: |
      rollback_condition_triggered AND
      auto_rollback_enabled
    
  PROMOTED_to_ROLLED_BACK:
    trigger: degradation_detected
    condition: |
      score_degradation OR
      completion_drop OR
      abandonment_spike
    
  ROLLED_BACK_to_CONTROL:
    trigger: manual_confirm
    permissions: [experiment_admin]
    requires: incident_review_completed
    
  ROLLED_BACK_to_EVALUATING:
    trigger: manual_restart
    permissions: [experiment_admin]
    requires: fix_deployed AND hypothesis_updated
    
  ANY_to_CLOSED:
    trigger: manual_archive
    permissions: [experiment_admin]
    condition: experiment_completed OR experiment_cancelled
```

### 6.4 Guardiões de Transição

```python
class StateTransitionGuard:
    """Valida se uma transição de estado é permitida."""
    
    def can_transition(
        self,
        from_state: ExperimentState,
        to_state: ExperimentState,
        context: TransitionContext
    ) -> tuple[bool, str]:
        """Retorna (permitido, razão)."""
        
        guards = {
            (State.EVALUATING, State.PROMOTED): [
                self._all_gates_passed,
                self._no_active_rollback_conditions,
                self._cooldown_elapsed
            ],
            (State.PROMOTED, State.ROLLED_BACK): [
                self._rollback_condition_met
            ],
            (State.ROLLED_BACK, State.EVALUATING): [
                self._fix_deployed,
                self._incident_reviewed,
                self._admin_approved
            ]
        }
        
        for guard in guards.get((from_state, to_state), []):
            passed, reason = guard(context)
            if not passed:
                return False, reason
        
        return True, "OK"
```

---

## Appendix A: Exemplo Completo de Policy

```json
{
  "experiment_id": "exp_onboarding_v2",
  "policy_version": "1.0.0",
  "created_at": "2026-03-01T10:00:00Z",
  "updated_at": "2026-03-04T19:46:15Z",
  "active_variant": "treatment",
  "rollout_mode": "auto",
  "last_evaluation": "2026-03-04T19:45:00Z",
  "decision_reason": "All gates passed, auto-promoted treatment_v2",
  "decision_trigger": "scheduled",
  "rollback_target": "control",
  "auto_rollback_enabled": true,
  "custom_gates": {
    "min_gain": {
      "threshold": 1.01
    }
  },
  "decision_history": [
    {
      "timestamp": "2026-03-04T19:45:00Z",
      "from_variant": "control",
      "to_variant": "treatment",
      "reason": "Auto-promotion: all gates passed",
      "gates_passed": ["min_gain", "stability", "risk", "ttfv_regression"],
      "metrics_snapshot": {
        "control_score": 0.82,
        "treatment_score": 0.84,
        "confidence": 0.96,
        "n_control": 150,
        "n_treatment": 148
      }
    }
  ]
}
```

---

## Appendix B: Changelog

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-03-04 | Growth Eng | Versão inicial da policy v45 |

---

## Appendix C: Referências

- [RFC-42: Auto-Rollout Architecture](../rfc/rfc42_auto_rollout.md)
- [Experiment Framework API](../api/experiment_framework.md)
- [Runbook: Emergency Rollback](../runbooks/emergency_rollback.md)
