import { useState, useEffect, useCallback } from 'react';
import { trackExperimentExposed } from '../features/onboarding/ttfvTelemetry';

export interface ExperimentVariant {
  id: string;
  config: Record<string, unknown>;
}

export interface UseExperimentOptions {
  experimentId: string;
  variants: ExperimentVariant[];
  userId: string;
  /** Para testes: forçar uma variante específica */
  forceVariant?: string;
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
 * Hook para gerenciar experimentos A/B/n no onboarding
 * 
 * @example
 * ```tsx
 * const { variantId, config, isInExperiment } = useExperiment({
 *   experimentId: 'onboarding_cta_v44',
 *   variants: [
 *     { id: 'control', config: {} },
 *     { id: 'variant_a', config: { buttonText: 'Começar Agora' } },
 *   ],
 *   userId: currentUser.id,
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
}: UseExperimentOptions): UseExperimentReturn {
  const [variantId, setVariantId] = useState<string | null>(null);
  const [isExposed, setIsExposed] = useState(false);

  // Determinar variante na montagem
  useEffect(() => {
    // Se não há variantes ou só há controle, não é um experimento
    if (!variants || variants.length === 0) {
      setVariantId(null);
      return;
    }

    // Verificar se há uma variante forçada (para testes)
    if (forceVariant) {
      const forced = variants.find(v => v.id === forceVariant);
      if (forced) {
        setVariantId(forced.id);
        return;
      }
    }

    // Verificar storage para consistência entre sessões
    const storageKey = getStorageKey(experimentId, userId);
    const stored = sessionStorage.getItem(storageKey);
    
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.variantId && variants.some(v => v.id === parsed.variantId)) {
          setVariantId(parsed.variantId);
          return;
        }
      } catch {
        // Ignorar erro de parse, continuar com atribuição nova
      }
    }

    // Atribuir baseado em hash determinístico
    // Control group (índice 0) é o fallback padrão
    const assignedIndex = hashUserToVariant(userId, experimentId, variants.length);
    const assigned = variants[assignedIndex];
    
    setVariantId(assigned.id);

    // Persistir atribuição
    sessionStorage.setItem(storageKey, JSON.stringify({ 
      variantId: assigned.id, 
      assignedAt: new Date().toISOString() 
    }));
  }, [experimentId, variants, userId, forceVariant]);

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
  };
}

/**
 * Hook simplificado para casos de uso comuns
 * Retorna apenas o valor da config ou default
 * 
 * @example
 * ```tsx
 * const buttonText = useExperimentValue({
 *   experimentId: 'onboarding_cta_v44',
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
}: {
  experimentId: string;
  variants: ExperimentVariant[];
  userId: string;
  key: string;
  defaultValue: T;
  forceVariant?: string;
}): T {
  const { config } = useExperiment({
    experimentId,
    variants,
    userId,
    forceVariant,
  });

  return (config[key] as T) ?? defaultValue;
}
