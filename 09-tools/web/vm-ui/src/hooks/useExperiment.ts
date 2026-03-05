import { useState, useEffect, useCallback } from 'react';
import { trackExperimentExposed } from '../features/onboarding/ttfvTelemetry';

export interface ExperimentVariant {
  id: string;
  config: Record<string, unknown>;
}

export interface RolloutPolicy {
  policy_id: string;
  experiment_id: string;
  active_variant: string;
  mode: 'auto' | 'manual';
  status: 'active' | 'inactive' | 'rolled_back';
}

export interface UseExperimentOptions {
  experimentId: string;
  variants: ExperimentVariant[];
  userId: string;
  /** Para testes: forçar uma variante específica */
  forceVariant?: string;
  /** Carregar policy do servidor */
  loadPolicy?: boolean;
}

export interface UseExperimentReturn {
  /** ID da variante atribuída ou null se controle */
  variantId: string | null;
  /** Config da variante ou vazio se controle */
  config: Record<string, unknown>;
  /** Se está em uma variante de experimento */
  isInExperiment: boolean;
  /** Se a exposição foi registrada */
  isExposed: boolean;
  /** Source da decisão de atribuição */
  decisionSource: 'policy_auto' | 'policy_manual' | 'hash' | 'control_fallback' | null;
  /** Policy ativa (se houver) */
  activePolicy: RolloutPolicy | null;
  /** Se está carregando */
  isLoading: boolean;
}

// Storage key para persistir atribuição entre sessões
const getStorageKey = (experimentId: string, userId: string): string => 
  `exp_${experimentId}_${userId}`;

/**
 * Deterministic hash para atribuir usuário a uma variante
 * Garante que o mesmo usuário sempre veja a mesma variante
 */
function hashUserToVariant(userId: string, experimentId: string, variantCount: number): number {
  const str = `${experimentId}:${userId}`;
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash) % variantCount;
}

/**
 * Fetch active rollout policy from server
 */
async function fetchRolloutPolicy(
  experimentId: string,
  userId: string
): Promise<RolloutPolicy | null> {
  try {
    // Try to fetch policy from API
    const response = await fetch(
      `/api/v2/experiments/${experimentId}/rollout-policy?user_id=${userId}`,
      { method: 'GET', headers: { 'Content-Type': 'application/json' } }
    );
    
    if (!response.ok) {
      // API may not be available or no policy exists
      return null;
    }
    
    const data = await response.json();
    if (data.policy && data.policy.status === 'active') {
      return data.policy as RolloutPolicy;
    }
    return null;
  } catch {
    // Silently fail - policy fetch shouldn't block assignment
    return null;
  }
}

/**
 * Determine variant with policy consideration
 * v45: Integrated policy + hash assignment
 */
function determineVariant(
  userId: string,
  experimentId: string,
  variants: ExperimentVariant[],
  policy: RolloutPolicy | null,
  storedVariant: string | null
): { variantId: string; source: 'policy_auto' | 'policy_manual' | 'hash' | 'control_fallback' } {
  // If we have a stored assignment, use it (sticky assignment)
  if (storedVariant && variants.some(v => v.id === storedVariant)) {
    return { variantId: storedVariant, source: 'hash' };
  }
  
  // Check policy
  if (policy && policy.status === 'active') {
    // Validate variant exists in experiment
    const validVariant = variants.some(v => v.id === policy.active_variant);
    
    if (!validVariant && policy.active_variant !== 'control') {
      // Policy points to invalid variant, fallback to control
      return { variantId: 'control', source: 'control_fallback' };
    }
    
    // Policy auto mode: apply active_variant directly
    if (policy.mode === 'auto' && policy.active_variant !== 'control') {
      return { variantId: policy.active_variant, source: 'policy_auto' };
    }
    
    // Policy manual mode: use hash assignment
    if (policy.mode === 'manual') {
      const assignedIndex = hashUserToVariant(userId, experimentId, variants.length);
      return { variantId: variants[assignedIndex].id, source: 'policy_manual' };
    }
  }
  
  // No active policy or inactive: use v44 hash assignment
  const assignedIndex = hashUserToVariant(userId, experimentId, variants.length);
  return { variantId: variants[assignedIndex].id, source: 'hash' };
}

/**
 * Hook para gerenciar experimentos A/B/n no onboarding
 * 
 * v45: Integrado com sistema de RolloutPolicy
 * 
 * @example
 * ```tsx
 * const { variantId, config, isInExperiment } = useExperiment({
 *   experimentId: 'onboarding_cta_v45',
 *   variants: [
 *     { id: 'control', config: {} },
 *     { id: 'variant_a', config: { buttonText: 'Começar Agora' } },
 *   ],
 *   userId: currentUser.id,
 *   loadPolicy: true,
 * });
 * 
 * // Usar no JSX
 * <button>{config.buttonText || 'Continuar'}</button>
 * ```
 */
export function useExperiment({
  experimentId,
  variants,
  userId,
  forceVariant,
  loadPolicy = true,
}: UseExperimentOptions): UseExperimentReturn {
  const [variantId, setVariantId] = useState<string | null>(null);
  const [isExposed, setIsExposed] = useState(false);
  const [decisionSource, setDecisionSource] = useState<UseExperimentReturn['decisionSource']>(null);
  const [activePolicy, setActivePolicy] = useState<RolloutPolicy | null>(null);
  const [isLoading, setIsLoading] = useState(loadPolicy);

  // Determinar variante na montagem
  useEffect(() => {
    // Se não há variantes ou só há controle, não é um experimento
    if (!variants || variants.length === 0) {
      setVariantId(null);
      setIsLoading(false);
      setDecisionSource('control_fallback');
      return;
    }

    // Verificar se há uma variante forçada (para testes)
    if (forceVariant) {
      const forced = variants.find(v => v.id === forceVariant);
      if (forced) {
        setVariantId(forced.id);
        setDecisionSource('policy_manual');
        setIsLoading(false);
        return;
      }
    }

    // Verificar storage para consistência entre sessões
    const storageKey = getStorageKey(experimentId, userId);
    const stored = sessionStorage.getItem(storageKey);
    let storedVariant: string | null = null;
    
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.variantId && variants.some(v => v.id === parsed.variantId)) {
          storedVariant = parsed.variantId;
        }
      } catch {
        // Ignorar erro de parse, continuar com atribuição nova
      }
    }

    // Load policy and determine variant
    const loadAndAssign = async () => {
      let policy: RolloutPolicy | null = null;
      
      if (loadPolicy) {
        policy = await fetchRolloutPolicy(experimentId, userId);
        setActivePolicy(policy);
      }
      
      const result = determineVariant(userId, experimentId, variants, policy, storedVariant);
      
      setVariantId(result.variantId);
      setDecisionSource(result.source);
      
      // Telemetry for policy decisions
      if (result.source === 'policy_auto' && policy) {
        try {
          await fetch('/api/v2/telemetry/policy_decision', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: userId,
              experiment_id: experimentId,
              policy_id: policy.policy_id,
              variant_id: result.variantId,
              decision: 'policy_auto_applied',
              timestamp: new Date().toISOString(),
            }),
          });
        } catch {
          // Silently fail - telemetry shouldn't block UI
        }
      }
      
      // Persistir atribuição
      sessionStorage.setItem(storageKey, JSON.stringify({ 
        variantId: result.variantId, 
        assignedAt: new Date().toISOString(),
        source: result.source,
        policyId: policy?.policy_id,
      }));
      
      setIsLoading(false);
    };

    loadAndAssign();
  }, [experimentId, variants, userId, forceVariant, loadPolicy]);

  // Registrar exposição quando variante é determinada
  useEffect(() => {
    if (variantId && !isExposed && variantId !== 'control') {
      trackExperimentExposed(userId, experimentId, variantId).then(() => {
        setIsExposed(true);
      }).catch(() => {
        // Silently fail - exposure tracking shouldn't block UI
        setIsExposed(true);
      });
    }
  }, [variantId, isExposed, userId, experimentId]);

  // Obter config da variante atual
  const config = variantId 
    ? variants.find(v => v.id === variantId)?.config || {}
    : {};

  const isInExperiment = variantId !== null && variantId !== 'control';

  return {
    variantId,
    config,
    isInExperiment,
    isExposed,
    decisionSource,
    activePolicy,
    isLoading,
  };
}

/**
 * Hook simplificado para casos de uso comuns
 * Retorna apenas o valor da config ou default
 * 
 * @example
 * ```tsx
 * const buttonText = useExperimentValue({
 *   experimentId: 'onboarding_cta_v45',
 *   variants: [
 *     { id: 'control', config: { text: 'Continuar' } },
 *     { id: 'variant_a', config: { text: 'Começar Agora' } },
 *   ],
 *   userId: currentUser.id,
 *   key: 'text',
 *   defaultValue: 'Continuar',
 * });
 * ```
 */
export function useExperimentValue<T>({
  experimentId,
  variants,
  userId,
  key,
  defaultValue,
  forceVariant,
  loadPolicy = true,
}: {
  experimentId: string;
  variants: ExperimentVariant[];
  userId: string;
  key: string;
  defaultValue: T;
  forceVariant?: string;
  loadPolicy?: boolean;
}): T {
  const { config } = useExperiment({
    experimentId,
    variants,
    userId,
    forceVariant,
    loadPolicy,
  });

  return (config[key] as T) ?? defaultValue;
}
