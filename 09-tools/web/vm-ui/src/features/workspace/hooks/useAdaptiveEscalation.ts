/**
 * Hook for Adaptive Escalation (v21)
 * 
 * Provides:
 * - Escalation window calculations
 * - Approver profile management
 * - Metrics monitoring
 */

import { useState, useCallback, useEffect } from 'react';

export interface EscalationWindows {
  windows: number[];  // Timeout values in seconds
  adaptiveFactors: {
    riskLevel: string;
    pendingLoad: number;
    approverProfile?: ApproverProfile;
  };
}

export interface ApproverProfile {
  approverId: string;
  avgResponseTimeMinutes: number;
  approvalsCount: number;
  timeoutsCount: number;
  timeoutRate: number;
}

export interface EscalationMetrics {
  approverCount: number;
  totalApprovals: number;
  totalTimeouts: number;
  timeoutRate: number;
}

interface UseAdaptiveEscalationReturn {
  // State
  windows: EscalationWindows | null;
  profile: ApproverProfile | null;
  metrics: EscalationMetrics | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  calculateWindows: (params: {
    stepId: string;
    riskLevel: string;
    approverId?: string;
    pendingCount: number;
  }) => Promise<void>;
  
  recordApproval: (params: {
    approverId: string;
    stepId: string;
    responseTimeSeconds: number;
  }) => Promise<void>;
  
  recordTimeout: (params: {
    approverId: string;
    stepId: string;
  }) => Promise<void>;
  
  loadProfile: (approverId: string) => Promise<void>;
  loadMetrics: () => Promise<void>;
}

const API_BASE = '/api/v2/escalation';

export function useAdaptiveEscalation(): UseAdaptiveEscalationReturn {
  const [windows, setWindows] = useState<EscalationWindows | null>(null);
  const [profile, setProfile] = useState<ApproverProfile | null>(null);
  const [metrics, setMetrics] = useState<EscalationMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateWindows = useCallback(async (params: {
    stepId: string;
    riskLevel: string;
    approverId?: string;
    pendingCount: number;
  }) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/windows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step_id: params.stepId,
          risk_level: params.riskLevel,
          approver_id: params.approverId,
          pending_count: params.pendingCount,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to calculate windows: ${response.statusText}`);
      }
      
      const data = await response.json();
      setWindows({
        windows: data.windows,
        adaptiveFactors: {
          riskLevel: data.adaptive_factors?.risk_level,
          pendingLoad: data.adaptive_factors?.pending_load,
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const recordApproval = useCallback(async (params: {
    approverId: string;
    stepId: string;
    responseTimeSeconds: number;
  }) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/approvals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approver_id: params.approverId,
          step_id: params.stepId,
          response_time_seconds: params.responseTimeSeconds,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to record approval: ${response.statusText}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const recordTimeout = useCallback(async (params: {
    approverId: string;
    stepId: string;
  }) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/timeouts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approver_id: params.approverId,
          step_id: params.stepId,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to record timeout: ${response.statusText}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadProfile = useCallback(async (approverId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/profiles/${approverId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to load profile: ${response.statusText}`);
      }
      
      const data = await response.json();
      setProfile({
        approverId: data.approver_id,
        avgResponseTimeMinutes: data.avg_response_time_minutes,
        approvalsCount: data.approvals_count,
        timeoutsCount: data.timeouts_count,
        timeoutRate: data.timeout_rate,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/metrics`);
      
      if (!response.ok) {
        throw new Error(`Failed to load metrics: ${response.statusText}`);
      }
      
      const data = await response.json();
      setMetrics({
        approverCount: data.approver_count,
        totalApprovals: data.total_approvals,
        totalTimeouts: data.total_timeouts,
        timeoutRate: data.timeout_rate,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    windows,
    profile,
    metrics,
    isLoading,
    error,
    calculateWindows,
    recordApproval,
    recordTimeout,
    loadProfile,
    loadMetrics,
  };
}
