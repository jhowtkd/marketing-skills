/**
 * Hook for ROI Optimizer operations (v19).
 */

import { useState, useCallback, useEffect } from 'react';

export interface RoiWeights {
  business: number;
  quality: number;
  efficiency: number;
}

export interface RoiCurrentScore {
  total: number;
  business: number;
  quality: number;
  efficiency: number;
}

export interface RoiProposal {
  id: string;
  description: string;
  expected_roi_delta: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected' | 'blocked' | 'applied';
  adjustments: Record<string, number>;
  autoapply_eligible: boolean;
  block_reason?: string;
  created_at: string;
  applied_at?: string;
}

export interface RoiOptimizerStatus {
  mode: string;
  cadence: string;
  weights: RoiWeights;
  current_score: RoiCurrentScore | null;
  last_run_at: string | null;
}

export interface RunOptimizationResult {
  proposals: RoiProposal[];
  score_before: number;
  score_after: number;
}

interface UseRoiOptimizerReturn {
  // State
  status: RoiOptimizerStatus | null;
  proposals: RoiProposal[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchStatus: () => Promise<void>;
  fetchProposals: () => Promise<void>;
  runOptimization: (params: {
    approval_without_regen_24h: number;
    revenue_attribution_usd: number;
    regen_per_job: number;
    quality_score_avg: number;
    avg_latency_ms: number;
    cost_per_job_usd: number;
    incident_rate?: number;
    projected_incident_rate?: number;
    target_improvement?: number;
  }) => Promise<RunOptimizationResult | null>;
  applyProposal: (proposalId: string) => Promise<boolean>;
  rejectProposal: (proposalId: string, reason?: string) => Promise<boolean>;
  rollback: () => Promise<boolean>;
  
  // Helpers
  hasPendingProposals: boolean;
  hasAutoapplyEligibleProposals: boolean;
  getProposalsByStatus: (status: RoiProposal['status']) => RoiProposal[];
}

const API_BASE = '/api/v2/roi';

export function useRoiOptimizer(): UseRoiOptimizerReturn {
  const [status, setStatus] = useState<RoiOptimizerStatus | null>(null);
  const [proposals, setProposals] = useState<RoiProposal[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/status`);
      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchProposals = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/proposals`);
      if (!response.ok) {
        throw new Error(`Failed to fetch proposals: ${response.statusText}`);
      }
      const data = await response.json();
      setProposals(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const runOptimization = useCallback(async (params): Promise<RunOptimizationResult | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!response.ok) {
        throw new Error(`Failed to run optimization: ${response.statusText}`);
      }
      const data = await response.json();
      setProposals(data.proposals);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const applyProposal = useCallback(async (proposalId: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/proposals/${proposalId}/apply`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Failed to apply proposal: ${response.statusText}`);
      }
      // Refresh proposals after apply
      await fetchProposals();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [fetchProposals]);

  const rejectProposal = useCallback(async (proposalId: string, reason?: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/proposals/${proposalId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason || 'Rejected by user' }),
      });
      if (!response.ok) {
        throw new Error(`Failed to reject proposal: ${response.statusText}`);
      }
      // Refresh proposals after reject
      await fetchProposals();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [fetchProposals]);

  const rollback = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/rollback`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Failed to rollback: ${response.statusText}`);
      }
      // Refresh after rollback
      await fetchProposals();
      await fetchStatus();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [fetchProposals, fetchStatus]);

  // Derived state
  const hasPendingProposals = Array.isArray(proposals) && proposals.some(p => p.status === 'pending');
  const hasAutoapplyEligibleProposals = Array.isArray(proposals) && proposals.some(p => p.autoapply_eligible && p.status === 'pending');
  
  const getProposalsByStatus = useCallback(
    (statusFilter: RoiProposal['status']) => Array.isArray(proposals) ? proposals.filter(p => p.status === statusFilter) : [],
    [proposals]
  );

  // Auto-fetch on mount
  useEffect(() => {
    fetchStatus();
    fetchProposals();
  }, [fetchStatus, fetchProposals]);

  return {
    status,
    proposals,
    isLoading,
    error,
    fetchStatus,
    fetchProposals,
    runOptimization,
    applyProposal,
    rejectProposal,
    rollback,
    hasPendingProposals,
    hasAutoapplyEligibleProposals,
    getProposalsByStatus,
  };
}
