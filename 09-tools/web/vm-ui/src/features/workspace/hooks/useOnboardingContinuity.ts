/**
 * useOnboardingContinuity Hook (v35)
 * 
 * React hook for interacting with the Onboarding Continuity API.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface Checkpoint {
  checkpoint_id: string;
  user_id: string;
  brand_id: string;
  step_id: string;
  step_data: Record<string, unknown>;
  form_data: Record<string, unknown>;
  version: number;
  status: string;
  created_at: string;
}

export interface HandoffBundle {
  bundle_id: string;
  user_id: string;
  brand_id: string;
  source_session: string;
  target_session?: string;
  checkpoint_ids: string[];
  context_payload: {
    current_step?: string;
    current_step_number?: number;
    completed_steps?: string[];
    form_data?: Record<string, unknown>;
    version?: number;
  };
  source_priority: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  failure_reason?: string;
}

export interface ContinuityMetrics {
  checkpoints_created: number;
  checkpoints_committed: number;
  checkpoints_rolled_back: number;
  bundles_created: number;
  bundles_pending: number;
  bundles_completed: number;
  bundles_failed: number;
  resumes_auto_applied: number;
  resumes_needing_approval: number;
  context_loss_events: number;
  conflicts_detected: number;
}

export interface ContinuityStatus {
  brand_id: string;
  state: string;
  version: string;
  frozen: boolean;
  metrics: ContinuityMetrics;
  recent_handoffs: HandoffBundle[];
}

export interface UseOnboardingContinuityOptions {
  brandId?: string;
  pollInterval?: number;
  enabled?: boolean;
}

export interface UseOnboardingContinuityReturn {
  status: ContinuityStatus | null;
  handoffs: HandoffBundle[];
  metrics: ContinuityMetrics | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  createCheckpoint: (
    userId: string,
    stepId: string,
    stepData?: Record<string, unknown>,
    formData?: Record<string, unknown>
  ) => Promise<{ checkpoint_id: string; bundle_id?: string } | null>;
  resumeHandoff: (
    bundleId: string,
    targetSession: string,
    resumedBy: string,
    force?: boolean
  ) => Promise<{ success: boolean; context?: Record<string, unknown>; needsApproval?: boolean } | null>;
  freeze: (frozenBy: string, reason: string) => Promise<boolean>;
  rollback: (rolledBackBy: string, reason: string) => Promise<boolean>;
}

export function useOnboardingContinuity(options: UseOnboardingContinuityOptions = {}): UseOnboardingContinuityReturn {
  const { brandId = 'default', pollInterval = 30000, enabled = true } = options;
  
  const [status, setStatus] = useState<ContinuityStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const refreshPromiseRef = useRef<Promise<void> | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    if (refreshPromiseRef.current) {
      return refreshPromiseRef.current;
    }
    
    const promise = (async () => {
      try {
        setLoading(true);
        setError(null);
        
        const signal = abortControllerRef.current!.signal;
        
        const res = await fetch(
          `/api/v2/brands/${brandId}/onboarding-continuity/status`,
          { signal }
        );
        
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
        }
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    })();
    
    refreshPromiseRef.current = promise;
    await promise;
    refreshPromiseRef.current = null;
  }, [brandId]);

  const createCheckpoint = useCallback(async (
    userId: string,
    stepId: string,
    stepData: Record<string, unknown> = {},
    formData: Record<string, unknown> = {}
  ): Promise<{ checkpoint_id: string; bundle_id?: string } | null> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-continuity/run`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            source_session: `session-${Date.now()}`,
            step_id: stepId,
            step_data: stepData,
            form_data: formData,
          }),
        }
      );
      
      if (res.ok) {
        const data = await res.json();
        await refresh();
        return {
          checkpoint_id: data.checkpoint_id,
          bundle_id: data.bundle_id,
        };
      }
      return null;
    } catch (err) {
      return null;
    }
  }, [brandId, refresh]);

  const resumeHandoff = useCallback(async (
    bundleId: string,
    targetSession: string,
    resumedBy: string,
    force: boolean = false
  ): Promise<{ success: boolean; context?: Record<string, unknown>; needsApproval?: boolean } | null> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-continuity/resume`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            bundle_id: bundleId,
            target_session: targetSession,
            resumed_by: resumedBy,
            force,
          }),
        }
      );
      
      if (res.ok) {
        const data = await res.json();
        await refresh();
        return {
          success: data.success,
          context: data.context,
          needsApproval: data.needs_approval,
        };
      }
      return null;
    } catch (err) {
      return null;
    }
  }, [brandId, refresh]);

  const freeze = useCallback(async (
    frozenBy: string,
    reason: string
  ): Promise<boolean> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-continuity/freeze`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ frozen_by: frozenBy, reason }),
        }
      );
      
      if (res.ok) {
        await refresh();
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  }, [brandId, refresh]);

  const rollback = useCallback(async (
    rolledBackBy: string,
    reason: string
  ): Promise<boolean> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-continuity/rollback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rolled_back_by: rolledBackBy, reason }),
        }
      );
      
      if (res.ok) {
        await refresh();
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  }, [brandId, refresh]);

  // Polling effect
  useEffect(() => {
    if (!enabled) return;
    
    refresh();
    const interval = setInterval(refresh, pollInterval);
    return () => {
      clearInterval(interval);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [enabled, pollInterval, refresh]);

  return {
    status,
    handoffs: status?.recent_handoffs || [],
    metrics: status?.metrics || null,
    loading,
    error,
    refresh,
    createCheckpoint,
    resumeHandoff,
    freeze,
    rollback,
  };
}
