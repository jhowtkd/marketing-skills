/**
 * useOnboardingRecovery Hook (v34)
 * 
 * React hook for interacting with the Onboarding Recovery API.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface RecoveryCase {
  case_id: string;
  user_id: string;
  brand_id: string;
  reason: string;
  status: string;
  priority: string;
  current_step: number;
  total_steps: number;
  progress_percentage: number;
  is_late_stage: boolean;
  dropoff_at: string;
  recovered_at?: string;
  expires_at?: string;
  metadata?: Record<string, unknown>;
}

export interface RecoveryProposal {
  case_id: string;
  user_id: string;
  brand_id: string;
  strategy: {
    strategy: string;
    strategy_type: string;
    reason: string;
    expected_impact: number;
  };
  resume_path: {
    entry_point: string;
    prefill_data: Record<string, unknown>;
    skip_steps: string[];
    highlight_changes: string[];
    estimated_completion_minutes: number;
    friction_score: number;
  };
  requires_approval: boolean;
  priority: string;
  reason: string;
  created_at: string;
}

export interface RecoveryMetrics {
  cases_total: number;
  cases_recoverable: number;
  cases_recovered: number;
  cases_expired: number;
  priority_high: number;
  priority_medium: number;
  priority_low: number;
  proposals_generated: number;
  proposals_auto_applied: number;
  proposals_approved: number;
  proposals_rejected: number;
}

export interface RecoveryStatus {
  brand_id: string;
  state: string;
  version: string;
  frozen: boolean;
  metrics: RecoveryMetrics;
  recoverable_cases: RecoveryCase[];
  pending_approvals: RecoveryProposal[];
}

export interface UseOnboardingRecoveryOptions {
  brandId?: string;
  pollInterval?: number;
  enabled?: boolean;
}

export interface UseOnboardingRecoveryReturn {
  status: RecoveryStatus | null;
  cases: RecoveryCase[];
  pendingApprovals: RecoveryProposal[];
  metrics: RecoveryMetrics | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  runDetection: (sessions: unknown[]) => Promise<{ cases_detected: number; proposals_generated: number }>;
  applyCase: (caseId: string, appliedBy: string, reason?: string) => Promise<boolean>;
  rejectCase: (caseId: string, rejectedBy: string, reason?: string) => Promise<boolean>;
  freeze: (frozenBy: string, reason: string) => Promise<boolean>;
  rollback: (rolledBackBy: string, reason: string) => Promise<boolean>;
}

export function useOnboardingRecovery(options: UseOnboardingRecoveryOptions = {}): UseOnboardingRecoveryReturn {
  const { brandId = 'default', pollInterval = 30000, enabled = true } = options;
  
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
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
          `/api/v2/brands/${brandId}/onboarding-recovery/status`,
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

  const runDetection = useCallback(async (
    sessions: unknown[]
  ): Promise<{ cases_detected: number; proposals_generated: number }> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-recovery/run`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sessions }),
        }
      );
      
      if (res.ok) {
        const data = await res.json();
        await refresh();
        return {
          cases_detected: data.cases_detected || 0,
          proposals_generated: data.proposals_generated || 0,
        };
      }
      return { cases_detected: 0, proposals_generated: 0 };
    } catch (err) {
      return { cases_detected: 0, proposals_generated: 0 };
    }
  }, [brandId, refresh]);

  const applyCase = useCallback(async (
    caseId: string,
    appliedBy: string,
    reason?: string
  ): Promise<boolean> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-recovery/cases/${caseId}/apply`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            applied_by: appliedBy,
            reason: reason || 'Approved for recovery',
          }),
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

  const rejectCase = useCallback(async (
    caseId: string,
    rejectedBy: string,
    reason?: string
  ): Promise<boolean> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-recovery/cases/${caseId}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rejected_by: rejectedBy,
            reason: reason || 'Rejected',
          }),
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

  const freeze = useCallback(async (
    frozenBy: string,
    reason: string
  ): Promise<boolean> => {
    try {
      const res = await fetch(
        `/api/v2/brands/${brandId}/onboarding-recovery/freeze`,
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
        `/api/v2/brands/${brandId}/onboarding-recovery/rollback`,
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
    cases: status?.recoverable_cases || [],
    pendingApprovals: status?.pending_approvals || [],
    metrics: status?.metrics || null,
    loading,
    error,
    refresh,
    runDetection,
    applyCase,
    rejectCase,
    freeze,
    rollback,
  };
}
