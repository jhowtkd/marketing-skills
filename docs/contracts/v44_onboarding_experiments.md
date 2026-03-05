# v44 Onboarding Experiments Pack - Experiment Contract

**Status:** Draft  
**Version:** 1.0.0  
**Author:** AGENTE A - Sprint v44  
**Date:** 2026-03-04  
**Scope:** Definição completa do contrato de experimentos A/B para o onboarding flow

---

## 1. EXPERIMENT CONTRACT

### 1.1 Experiment ID

#### Formato
```
<product>_<flow>_<experiment_name>_<version>
```

| Componente | Descrição | Exemplo |
|------------|-----------|---------|
| `product` | Identificador do produto | `app`, `web`, `mobile` |
| `flow` | Nome do fluxo | `onboarding`, `signup`, `setup` |
| `experiment_name` | Nome descritivo snake_case | `cta_wording`, `step_ordering` |
| `version` | Versão do experimento (v{N}) | `v1`, `v2` |

#### Exemplos Válidos
```
app_onboarding_cta_wording_v1
web_signup_resume_timing_v2
mobile_setup_micro_steps_v1
```

#### Unicidade
- **Global:** Cada `experiment_id` deve ser único em todo o sistema
- **Namespace:** O prefixo `<product>_<flow>` garante agrupamento lógico
- **Colisão:** Sistema deve rejeitar criação de experimento com ID duplicado

#### Versionamento
- **Major (v{N}):** Mudanças na estrutura de variantes ou lógica de assignment
- **Minor:** Mudanças em configurações de variantes existentes
- **Patch:** Correções de bugs sem alterar comportamento

> **Regra:** Nova versão major = novo experiment_id. Versões minor/patch mantêm o mesmo ID.

---

### 1.2 Variants Structure

#### Schema
```typescript
interface Variant {
  variant_id: string;           // Identificador único da variante
  name: string;                 // Nome legível para dashboards
  config: Record<string, any>;  // Configuração serializável em JSON
  weight: number;               // Peso na distribuição (0-100)
}

interface Experiment {
  experiment_id: string;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'completed';
  start_date: string;           // ISO 8601
  end_date?: string;            // ISO 8601 (opcional)
  variants: Variant[];
  control_variant_id: string;   // ID da variante de controle
  assignment_strategy: AssignmentStrategy;
  exposure_event: string;       // Nome do evento que dispara exposure
}
```

#### Restrições
- **Mínimo de variantes:** 2 (controle + 1 alternativa)
- **Máximo de variantes:** 10
- **Soma dos weights:** Deve ser exatamente 100
- **Controle obrigatório:** Uma variante deve ser marcada como controle
- **Config serializável:** Todo objeto `config` deve ser JSON.stringify-able

---

### 1.3 Assignment Strategy

#### Tipo
```typescript
type AssignmentStrategy = {
  type: 'deterministic_hash';
  seed_source: 'user_id' | 'session_id' | 'anonymous_id';
  hash_algorithm: 'fnv1a_32' | 'murmur3_32';
};
```

#### Seed Source
| Fonte | Use Case | Persistência |
|-------|----------|--------------|
| `user_id` | Experimentos cross-session para usuários logados | Permanente |
| `session_id` | Experimentos por sessão | Duração da sessão |
| `anonymous_id` | Experimentos para usuários não logados | Cross-session até login |

#### Hash Consistente
- O mesmo usuário + experimento = mesma variante sempre
- Reproduzível em qualquer ambiente
- Independente de ordem de avaliação

---

### 1.4 Exposure Event

#### Definição
Evento que marca o momento em que o usuário foi exposto à variante do experimento.

#### Schema do Evento
```typescript
interface ExperimentExposedEvent {
  event_name: 'experiment_exposed';
  timestamp: string;            // ISO 8601
  user_id?: string;
  session_id: string;
  anonymous_id: string;
  experiment_id: string;
  variant_id: string;
  assignment_metadata: {
    seed: string;
    hash_value: number;
    assignment_timestamp: string;
  };
  context: {
    page_url: string;
    referrer?: string;
    device_type: string;
    // ... outros campos de contexto
  };
}
```

#### Quando Disparar
| Cenário | Ação |
|---------|------|
| Usuário entra em tela com experimento ativo | Disparar `experiment_exposed` |
| Usuário já foi atribuído anteriormente | Não disparar novamente |
| Assignment falha | Disparar `experiment_fallback_triggered` |
| Experimento desativado | Não disparar nada |

#### Garantias
- **Idempotência:** Mesmo usuário + experimento = no máximo 1 evento `experiment_exposed`
- **Precedência:** Evento deve ser disparado ANTES de qualquer interação
- **Sincronicidade:** Idealmente síncrono; se async, antes de 100ms

---

### 1.5 Fallback Contract

#### Comportamento Padrão
Quando qualquer falha ocorre, o sistema deve sempre retornar a **variante de controle**.

#### Cenários de Fallback

| Cenário | Fallback | Telemetry |
|---------|----------|-----------|
| Assignment falha (erro de hash) | Controle | `experiment_fallback_triggered` |
| Config de variante inválida | Controle | `experiment_fallback_triggered` |
| Experimento desativado | Controle | Silencioso (sem evento) |
| Variante não encontrada | Controle | `experiment_fallback_triggered` |
| Network error ao carregar config | Controle | `experiment_fallback_triggered` |
| Timeout no assignment | Controle | `experiment_fallback_triggered` |

#### Fallback Event Schema
```typescript
interface ExperimentFallbackTriggeredEvent {
  event_name: 'experiment_fallback_triggered';
  timestamp: string;
  user_id?: string;
  session_id: string;
  experiment_id: string;
  fallback_reason: 
    | 'assignment_error'
    | 'invalid_config'
    | 'variant_not_found'
    | 'network_error'
    | 'timeout';
  fallback_variant_id: string;  // Sempre a variante de controle
  error_details?: {
    message: string;
    stack?: string;
  };
}
```

---

## 2. VARIANT STRUCTURE

### 2.1 Exemplos de Variantes

#### Exemplo 1: CTA Copy Variants
```json
{
  "experiment_id": "app_onboarding_cta_wording_v1",
  "name": "CTA Wording Test",
  "variants": [
    {
      "variant_id": "control",
      "name": "Começar (Control)",
      "config": {
        "cta_text": "Começar",
        "cta_subtext": "Inicie sua jornada",
        "button_style": "primary",
        "icon": "arrow-right"
      },
      "weight": 50
    },
    {
      "variant_id": "setup_now",
      "name": "Configurar Agora",
      "config": {
        "cta_text": "Configurar Agora",
        "cta_subtext": "Configure em 2 minutos",
        "button_style": "primary",
        "icon": "settings"
      },
      "weight": 50
    }
  ],
  "control_variant_id": "control"
}
```

#### Exemplo 2: Micro-step Ordering
```json
{
  "experiment_id": "app_onboarding_step_ordering_v1",
  "name": "Micro-step Ordering",
  "variants": [
    {
      "variant_id": "control",
      "name": "Single Step (Control)",
      "config": {
        "flow_type": "single_step",
        "steps": [
          {
            "step_id": "workspace_setup",
            "title": "Configure seu Workspace",
            "fields": ["name", "team_size", "use_case"]
          }
        ]
      },
      "weight": 50
    },
    {
      "variant_id": "two_steps",
      "name": "Two Micro-steps",
      "config": {
        "flow_type": "micro_steps",
        "steps": [
          {
            "step_id": "workspace_basic",
            "title": "Nome do Workspace",
            "fields": ["name"],
            "progress": 50
          },
          {
            "step_id": "workspace_details",
            "title": "Detalhes da Equipe",
            "fields": ["team_size", "use_case"],
            "progress": 100
          }
        ],
        "step_transition_animation": "slide"
      },
      "weight": 50
    }
  ],
  "control_variant_id": "control"
}
```

#### Exemplo 3: Resume Timing
```json
{
  "experiment_id": "app_onboarding_resume_timing_v1",
  "name": "Resume Timing Test",
  "variants": [
    {
      "variant_id": "control",
      "name": "Immediate (Control)",
      "config": {
        "resume_check_timing": "immediate",
        "delay_ms": 0,
        "show_loading_state": false
      },
      "weight": 33.33
    },
    {
      "variant_id": "delay_2s",
      "name": "2 Second Delay",
      "config": {
        "resume_check_timing": "delayed",
        "delay_ms": 2000,
        "show_loading_state": true,
        "loading_message": "Verificando seu progresso..."
      },
      "weight": 33.33
    },
    {
      "variant_id": "delay_5s",
      "name": "5 Second Delay",
      "config": {
        "resume_check_timing": "delayed",
        "delay_ms": 5000,
        "show_loading_state": true,
        "loading_message": "Preparando seu espaço de trabalho...",
        "show_tips_during_delay": true,
        "tips": [
          "Dica: Você pode convidar sua equipe a qualquer momento",
          "Dica: Integre com suas ferramentas favoritas"
        ]
      },
      "weight": 33.34
    }
  ],
  "control_variant_id": "control"
}
```

### 2.2 Configuração por Variante

#### Regras de Configuração
1. **JSON Serializável:** Todo config deve ser parseável por `JSON.stringify/parse`
2. **Schema Validation:** Cada experimento deve ter schema de validação para configs
3. **Merge Strategy:** Configs são merged com defaults; valores undefined não sobrescrevem
4. **Deep Nesting:** Suporta até 5 níveis de profundidade

#### Schema de Validação (Exemplo)
```typescript
const CTAExperimentSchema = z.object({
  cta_text: z.string().min(1).max(50),
  cta_subtext: z.string().max(100).optional(),
  button_style: z.enum(['primary', 'secondary', 'ghost']),
  icon: z.string().optional()
});

const StepOrderingSchema = z.object({
  flow_type: z.enum(['single_step', 'micro_steps']),
  steps: z.array(z.object({
    step_id: z.string(),
    title: z.string(),
    fields: z.array(z.string()),
    progress: z.number().min(0).max(100).optional()
  })).min(1),
  step_transition_animation: z.enum(['slide', 'fade', 'none']).optional()
});
```

---

## 3. TELEMETRY INTEGRATION

### 3.1 Enriquecimento de Eventos

#### Todos os Eventos Carregam
Quando um usuário está em um experimento ativo, TODOS os eventos de telemetry devem incluir:

```typescript
interface ExperimentContext {
  experiment_id: string;
  variant_id: string;
  experiment_version: string;
}

// Exemplo de evento enriquecido
interface AnyTelemetryEvent {
  event_name: string;
  timestamp: string;
  user_id?: string;
  session_id: string;
  // ... campos específicos do evento
  
  // Enriquecimento automático
  experiment_context?: ExperimentContext;  // Presente quando há experimento ativo
}
```

#### Implementação
```typescript
// No telemetry middleware
function enrichWithExperimentContext(event: TelemetryEvent): TelemetryEvent {
  const activeExperiments = getActiveExperimentsForUser(event.user_id);
  
  if (activeExperiments.length > 0) {
    // Prioridade: experimento mais recente ou por ordem de prioridade configurada
    const primaryExperiment = activeExperiments[0];
    
    event.experiment_context = {
      experiment_id: primaryExperiment.experiment_id,
      variant_id: primaryExperiment.variant_id,
      experiment_version: primaryExperiment.version
    };
    
    // Para múltiplos experimentos simultâneos
    event.experiments_context = activeExperiments.map(exp => ({
      experiment_id: exp.experiment_id,
      variant_id: exp.variant_id
    }));
  }
  
  return event;
}
```

### 3.2 Evento experiment_exposed Obrigatório

#### Garantias de Entrega
- **Sync First:** Tentar envio síncrono antes do carregamento da UI
- **Retry:** 3 tentativas com backoff exponencial
- **Persistência:** Queue local se offline
- **Deduplicação:** Hash de user_id + experiment_id para evitar duplicados

#### Exemplo de Fluxo
```
Usuário entra na tela de onboarding
    ↓
Sistema verifica experimentos ativos para este usuário
    ↓
Se há experimento ativo E usuário ainda não foi exposto:
    ↓
Dispara experiment_exposed (síncrono, blocking)
    ↓
Se sucesso: Renderiza UI com variante atribuída
Se falha: Fallback para controle + dispara experiment_fallback_triggered
```

### 3.3 Campos no Payload dos Eventos Existentes

#### Eventos de Onboarding (Enriquecidos)
```typescript
// Evento existente - agora com experiment_context
interface OnboardingStartedEvent {
  event_name: 'onboarding_started';
  timestamp: string;
  user_id: string;
  session_id: string;
  entry_point: string;
  referrer?: string;
  
  // NOVO: Contexto de experimento
  experiment_context?: {
    experiment_id: 'app_onboarding_cta_wording_v1';
    variant_id: 'setup_now';
    experiment_version: '1.0.0';
  };
}

interface OnboardingStepCompletedEvent {
  event_name: 'onboarding_step_completed';
  timestamp: string;
  user_id: string;
  step_id: string;
  step_name: string;
  time_spent_ms: number;
  
  // NOVO: Contexto de experimento
  experiment_context?: {
    experiment_id: 'app_onboarding_step_ordering_v1';
    variant_id: 'two_steps';
    experiment_version: '1.0.0';
  };
}

interface OnboardingCompletedEvent {
  event_name: 'onboarding_completed';
  timestamp: string;
  user_id: string;
  total_time_ms: number;
  steps_completed: number;
  
  // NOVO: Contexto de experimento (pode ter múltiplos)
  experiments_context?: Array<{
    experiment_id: string;
    variant_id: string;
  }>;
}
```

#### Eventos de Conversão
```typescript
interface WorkspaceCreatedEvent {
  event_name: 'workspace_created';
  timestamp: string;
  user_id: string;
  workspace_id: string;
  creation_method: 'onboarding' | 'manual';
  
  // NOVO: Experiment context para atribuição de conversão
  experiment_context?: {
    experiment_id: string;
    variant_id: string;
  };
}
```

### 3.4 Eventos de Sistema

```typescript
// Evento de início de experimento
interface ExperimentStartedEvent {
  event_name: 'experiment_started';
  timestamp: string;
  experiment_id: string;
  variant_id: string;
  assignment_method: 'deterministic_hash';
  assignment_seed: string;
}

// Evento de completion de experimento (se aplicável)
interface ExperimentConvertedEvent {
  event_name: 'experiment_converted';
  timestamp: string;
  experiment_id: string;
  variant_id: string;
  conversion_event: string;
  time_to_conversion_ms: number;
}
```

---

## 4. ASSIGNMENT ALGORITHM

### 4.1 Hash de user_id + experiment_id

#### Algoritmo FNV-1a 32-bit (Recomendado)
```typescript
function fnv1a32(input: string): number {
  let hash = 0x811c9dc5;  // FNV offset basis
  
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);  // FNV prime
  }
  
  return hash >>> 0;  // Convert to unsigned 32-bit
}

function generateAssignmentSeed(
  userId: string, 
  experimentId: string
): string {
  return `${userId}:${experimentId}`;
}

function getAssignmentHash(seed: string): number {
  return fnv1a32(seed);
}
```

#### Algoritmo MurmurHash3 32-bit (Alternativa)
```typescript
function murmur3_32(key: string, seed: number = 0): number {
  const remainder = key.length & 3;
  const bytes = key.length - remainder;
  
  let h1 = seed;
  const c1 = 0xcc9e2d51;
  const c2 = 0x1b873593;
  
  // Corpo do algoritmo... (implementação padrão murmur3)
  
  return h1 >>> 0;
}
```

### 4.2 Distribuição Proporcional por Weights

#### Cálculo de Variante
```typescript
interface VariantWithRange {
  variant_id: string;
  weight: number;
  range_start: number;  // Inclusive
  range_end: number;    // Exclusive
}

function calculateVariantRanges(variants: Variant[]): VariantWithRange[] {
  let cumulativeWeight = 0;
  
  return variants.map(variant => {
    const rangeStart = cumulativeWeight;
    cumulativeWeight += variant.weight;
    
    return {
      variant_id: variant.variant_id,
      weight: variant.weight,
      range_start: rangeStart,
      range_end: cumulativeWeight
    };
  });
}

function assignVariant(
  userId: string,
  experimentId: string,
  variants: Variant[]
): string {
  const seed = generateAssignmentSeed(userId, experimentId);
  const hash = getAssignmentHash(seed);
  
  // Normaliza hash para 0-99.999...
  const normalizedValue = (hash / 0xFFFFFFFF) * 100;
  
  const ranges = calculateVariantRanges(variants);
  
  // Encontra a variante correspondente
  const assigned = ranges.find(
    r => normalizedValue >= r.range_start && normalizedValue < r.range_end
  );
  
  if (!assigned) {
    // Fallback: última variante (proteção contra rounding errors)
    return ranges[ranges.length - 1].variant_id;
  }
  
  return assigned.variant_id;
}
```

#### Exemplo de Distribuição
```
Variantes:
- control: weight=50 (range: 0-50)
- variant_a: weight=30 (range: 50-80)
- variant_b: weight=20 (range: 80-100)

Hash resulta em normalizedValue = 42.5
→ Atribuído a: control (0 ≤ 42.5 < 50)

Hash resulta em normalizedValue = 65.2
→ Atribuído a: variant_a (50 ≤ 65.2 < 80)

Hash resulta em normalizedValue = 91.8
→ Atribuído a: variant_b (80 ≤ 91.8 < 100)
```

### 4.3 Determinístico e Reproduzível

#### Garantias
1. **Same Input = Same Output:** Mesmo userId + experimentId = mesma variante
2. **Cross-platform:** Mesmo algoritmo em todas as plataformas
3. **Time-independent:** Assignment não muda com o tempo
4. **Environment-independent:** Mesmo resultado em dev/staging/prod

#### Teste de Reprodutibilidade
```typescript
// Teste unitário obrigatório
describe('Assignment Algorithm', () => {
  it('should be deterministic', () => {
    const userId = 'user_123';
    const experimentId = 'app_onboarding_test_v1';
    const variants = [
      { variant_id: 'control', weight: 50 },
      { variant_id: 'variant_a', weight: 50 }
    ];
    
    const run1 = assignVariant(userId, experimentId, variants);
    const run2 = assignVariant(userId, experimentId, variants);
    const run3 = assignVariant(userId, experimentId, variants);
    
    expect(run1).toBe(run2);
    expect(run2).toBe(run3);
  });
  
  it('should distribute according to weights', () => {
    const variants = [
      { variant_id: 'control', weight: 50 },
      { variant_id: 'variant_a', weight: 50 }
    ];
    
    const assignments = generateAssignments(10000, variants);
    
    // Tolerância de 5% para variação estatística
    expect(assignments.control).toBeGreaterThan(4500);
    expect(assignments.control).toBeLessThan(5500);
    expect(assignments.variant_a).toBeGreaterThan(4500);
    expect(assignments.variant_a).toBeLessThan(5500);
  });
});
```

#### Cache de Assignment
```typescript
interface AssignmentCache {
  [experimentId: string]: {
    variant_id: string;
    assigned_at: string;
    expires_at: string;
  };
}

// TTL do cache: 24 horas
const ASSIGNMENT_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

function getCachedOrAssign(
  userId: string,
  experiment: Experiment
): string {
  const cache: AssignmentCache = loadAssignmentCache(userId);
  const cached = cache[experiment.experiment_id];
  
  if (cached && new Date(cached.expires_at) > new Date()) {
    return cached.variant_id;
  }
  
  const variantId = assignVariant(userId, experiment.experiment_id, experiment.variants);
  
  cache[experiment.experiment_id] = {
    variant_id: variantId,
    assigned_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + ASSIGNMENT_CACHE_TTL_MS).toISOString()
  };
  
  saveAssignmentCache(userId, cache);
  
  return variantId;
}
```

---

## 5. FALLBACK CONTRACT

### 5.1 Se Assignment Falha → Controle

#### Cenários de Falha de Assignment
```typescript
enum AssignmentFailureReason {
  HASH_ERROR = 'hash_error',
  INVALID_SEED = 'invalid_seed',
  VARIANT_MISMATCH = 'variant_mismatch',
  CALCULATION_ERROR = 'calculation_error'
}

function safeAssignVariant(
  userId: string,
  experiment: Experiment
): { variant_id: string; from_fallback: boolean; reason?: string } {
  try {
    // Validações pré-assignment
    if (!userId || typeof userId !== 'string') {
      throw new Error('Invalid user_id');
    }
    
    if (!experiment.variants || experiment.variants.length < 2) {
      throw new Error('Invalid variants configuration');
    }
    
    // Tenta assignment
    const variantId = assignVariant(userId, experiment.experiment_id, experiment.variants);
    
    // Valida se variante existe
    const variantExists = experiment.variants.some(v => v.variant_id === variantId);
    if (!variantExists) {
      throw new Error(`Assigned variant ${variantId} not found in experiment`);
    }
    
    return { variant_id: variantId, from_fallback: false };
    
  } catch (error) {
    // Fallback para controle
    const controlVariant = experiment.variants.find(
      v => v.variant_id === experiment.control_variant_id
    );
    
    if (!controlVariant) {
      // Último recurso: primeira variante
      return { 
        variant_id: experiment.variants[0]?.variant_id || 'control',
        from_fallback: true,
        reason: error instanceof Error ? error.message : 'unknown_error'
      };
    }
    
    return { 
      variant_id: controlVariant.variant_id,
      from_fallback: true,
      reason: error instanceof Error ? error.message : 'unknown_error'
    };
  }
}
```

### 5.2 Se Config de Variante Inválida → Controle

#### Validação de Config
```typescript
function validateVariantConfig(
  variant: Variant,
  schema: z.ZodSchema
): { valid: boolean; errors?: string[] } {
  try {
    schema.parse(variant.config);
    return { valid: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        valid: false,
        errors: error.errors.map(e => `${e.path.join('.')}: ${e.message}`)
      };
    }
    return { valid: false, errors: ['Unknown validation error'] };
  }
}

function getValidVariantConfig(
  experiment: Experiment,
  variantId: string,
  schema: z.ZodSchema
): { variant_id: string; config: any; valid: boolean } {
  const variant = experiment.variants.find(v => v.variant_id === variantId);
  
  if (!variant) {
    // Fallback para controle
    const control = experiment.variants.find(
      v => v.variant_id === experiment.control_variant_id
    );
    return {
      variant_id: control!.variant_id,
      config: control!.config,
      valid: false
    };
  }
  
  const validation = validateVariantConfig(variant, schema);
  
  if (!validation.valid) {
    // Dispara telemetry de fallback
    track('experiment_fallback_triggered', {
      experiment_id: experiment.experiment_id,
      fallback_reason: 'invalid_config',
      attempted_variant: variantId,
      validation_errors: validation.errors
    });
    
    // Retorna controle
    const control = experiment.variants.find(
      v => v.variant_id === experiment.control_variant_id
    );
    return {
      variant_id: control!.variant_id,
      config: control!.config,
      valid: false
    };
  }
  
  return { variant_id: variant.variant_id, config: variant.config, valid: true };
}
```

### 5.3 Se Experimento Desativado → Controle

#### Estados de Experimento
```typescript
type ExperimentStatus = 'draft' | 'active' | 'paused' | 'completed';

const EXPERIMENT_STATUS_FLOW: Record<ExperimentStatus, { 
  assignable: boolean;
  behavior: 'normal' | 'control_only' | 'no_experiment' 
}> = {
  draft: { assignable: false, behavior: 'no_experiment' },
  active: { assignable: true, behavior: 'normal' },
  paused: { assignable: false, behavior: 'control_only' },
  completed: { assignable: false, behavior: 'control_only' }
};

function shouldAssignExperiment(
  experiment: Experiment
): { shouldAssign: boolean; fallbackToControl: boolean } {
  const statusConfig = EXPERIMENT_STATUS_FLOW[experiment.status];
  
  return {
    shouldAssign: statusConfig.assignable,
    fallbackToControl: statusConfig.behavior === 'control_only'
  };
}

function resolveExperimentForUser(
  userId: string,
  experiment: Experiment
): { variant_id: string; config: any; is_fallback: boolean; reason?: string } {
  const statusCheck = shouldAssignExperiment(experiment);
  
  // Experimento em draft - não participa
  if (!statusCheck.shouldAssign && !statusCheck.fallbackToControl) {
    return {
      variant_id: 'none',
      config: {},
      is_fallback: true,
      reason: 'experiment_not_active'
    };
  }
  
  // Experimento pausado/completed - sempre controle
  if (statusCheck.fallbackToControl) {
    const control = experiment.variants.find(
      v => v.variant_id === experiment.control_variant_id
    );
    
    return {
      variant_id: control!.variant_id,
      config: control!.config,
      is_fallback: true,
      reason: `experiment_${experiment.status}`
    };
  }
  
  // Assignment normal
  const assignment = safeAssignVariant(userId, experiment);
  
  return {
    variant_id: assignment.variant_id,
    config: experiment.variants.find(v => v.variant_id === assignment.variant_id)!.config,
    is_fallback: assignment.from_fallback,
    reason: assignment.reason
  };
}
```

### 5.4 Telemetry de Fallback

#### Schema Completo de Fallback
```typescript
interface FallbackTelemetry {
  event_name: 'experiment_fallback_triggered';
  timestamp: string;            // ISO 8601
  
  // Identificação
  user_id?: string;
  session_id: string;
  anonymous_id: string;
  
  // Contexto do experimento
  experiment_id: string;
  attempted_variant_id?: string;
  fallback_variant_id: string;
  
  // Razão do fallback
  fallback_reason: 
    | 'assignment_error'
    | 'invalid_config'
    | 'variant_not_found'
    | 'network_error'
    | 'timeout'
    | 'experiment_paused'
    | 'experiment_completed'
    | 'experiment_draft'
    | 'experiment_not_found';
  
  // Detalhes do erro
  error_details?: {
    message: string;
    code?: string;
    stack?: string;
  };
  
  // Contexto adicional
  context: {
    assignment_seed?: string;
    assignment_hash?: number;
    validation_errors?: string[];
    retry_count?: number;
  };
}
```

#### Implementação do Tracker
```typescript
class FallbackTelemetryTracker {
  track(fallbackEvent: Omit<FallbackTelemetry, 'event_name' | 'timestamp'>): void {
    const event: FallbackTelemetry = {
      event_name: 'experiment_fallback_triggered',
      timestamp: new Date().toISOString(),
      ...fallbackEvent
    };
    
    // Log estruturado para monitoring
    console.error('[Experiment Fallback]', {
      experiment_id: event.experiment_id,
      reason: event.fallback_reason,
      user_id: event.user_id,
      timestamp: event.timestamp
    });
    
    // Envia para telemetry pipeline
    telemetry.track(event);
    
    // Alerta se taxa de fallback > threshold
    this.checkFallbackRate(event.experiment_id);
  }
  
  private checkFallbackRate(experimentId: string): void {
    const rate = getFallbackRateForExperiment(experimentId);
    if (rate > 0.05) {  // 5% threshold
      alerting.trigger({
        severity: 'warning',
        message: `High fallback rate for experiment ${experimentId}: ${(rate * 100).toFixed(2)}%`,
        experiment_id: experimentId
      });
    }
  }
}

// Uso
const fallbackTracker = new FallbackTelemetryTracker();

// Exemplo de uso no código
function assignUserToExperiment(userId: string, experiment: Experiment): AssignmentResult {
  try {
    // ... lógica de assignment
  } catch (error) {
    fallbackTracker.track({
      session_id: getSessionId(),
      anonymous_id: getAnonymousId(),
      user_id: userId,
      experiment_id: experiment.experiment_id,
      fallback_variant_id: experiment.control_variant_id,
      fallback_reason: 'assignment_error',
      error_details: {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      },
      context: {}
    });
    
    return fallbackToControl(experiment);
  }
}
```

---

## 6. IMPLEMENTATION CHECKLIST

### 6.1 Backend/Server
- [ ] Implementar `fnv1a32` hash function
- [ ] Criar `ExperimentService` com assignment logic
- [ ] Implementar cache de assignments (Redis/session)
- [ ] Criar endpoints para config de experimentos
- [ ] Implementar validação de schemas
- [ ] Setup de fallback tracking

### 6.2 Frontend/Client
- [ ] Criar `ExperimentProvider` (React/Vue/etc)
- [ ] Implementar hook `useExperiment(experimentId)`
- [ ] Integrar com telemetry pipeline
- [ ] Implementar localStorage cache de assignments
- [ ] Criar componente `ExperimentExposureTracker`

### 6.3 Telemetry
- [ ] Adicionar `experiment_context` em todos os eventos
- [ ] Implementar `experiment_exposed` event
- [ ] Implementar `experiment_fallback_triggered` event
- [ ] Criar dashboards de monitoramento
- [ ] Setup de alertas para fallback rate

### 6.4 QA/Testing
- [ ] Testes unitários do assignment algorithm
- [ ] Testes de determinismo (mesmo input = mesmo output)
- [ ] Testes de distribuição estatística
- [ ] Testes de fallback scenarios
- [ ] Testes de performance do hash

---

## 7. APPENDIX

### 7.1 Referências
- [FNV Hash](http://www.isthe.com/chongo/tech/comp/fnv/)
- [MurmurHash](https://github.com/aappleby/smhasher)
- [A/B Testing Statistics](https://www.evanmiller.org/ab-testing/)

### 7.2 Changelog
| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-04 | Initial contract definition |

---

**END OF CONTRACT**
