/**
 * useOutcomeRoi Hook (v36)
 * 
 * React hook for interacting with the Outcome Attribution and Hybrid ROI API.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface Proposal {
  proposal_id: string;
  brand_id: string;
  touchpoint_type: string;
  action: string;
  expected_impact: Record<string, unknown>;
  hybrid_index: number;
  risk_level: 'low' | 'medium' | 'high';
  status: 'pending' | 'applied' | 'rejected' | 'rolled_back';
  score_explanation: string;
  created_at: string;
}

export interface AttributionSummary {
  total_outcomes: number;
  total_touchpoints: number;
  by_outcome_type: Record<string, number>;
  window_days: number;
}

export interface ROISummary {
  total_proposals: number;
  avg_hybrid_index: number;
  by_risk_level: Record<string, number>;
}

export interface ROIMetrics {
  outcomes_attributed: number;
  proposals_generated: number;
  proposals_auto_applied: number;
  proposals_pending_approval: number;
  proposals_approved: number;
  proposals_rejected: number;
  proposals_blocked: number;
  hybrid_roi_index_avg: number;
  payback_time_avg_days: number;
  guardrail_violations: number;
}

export interface ROIStatus {
  brand_id: string;
  state: string;
  version: string;
  frozen: boolean;
  metrics: ROIMetrics;
  attribution_summary: AttributionSummary;
  roi_summary: ROISummary;
}

export interface UseOutcomeRoiOptions {
  brandId?: string;
  pollInterval?: number;
  enabled?: boolean;
}

export interface UseOutcomeRoiReturn {
  status: ROIStatus | null;
  proposals: Proposal[];
  metrics: ROIMetrics | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  runAttribution: (options?: {
    outcome_type?: string;
    auto_apply_low_risk?: boolean;
  }) => Promise<void>;
  applyProposal: (proposalId: string, note?: string) => Promise<boolean>;
  rejectProposal: (proposalId: string, reason: string) => Promise<boolean>;
  freeze: (reason: string) => Promise<boolean>;
  rollback: (reason: string, proposalIds?: string[]) => Promise<boolean>;
}

const API_BASE = '/api/v2/brands';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`HTTP ${response.status}: ${error}`);
  }
  
  return response.json();
}

export function useOutcomeRoi(options: UseOutcomeRoiOptions = {}): UseOutcomeRoiReturn {
  const { brandId, pollInterval = 30000, enabled = true } = options;
  
  const [status, setStatus] = useState<ROIStatus | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [metrics, setMetrics] = useState<ROIMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!brandId) return;
    
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchJSON<ROIStatus>(
        `${API_BASE}/${brandId}/outcome-roi/status`,
        { signal: abortControllerRef.current.signal }
      );
      
      setStatus(data);
      setMetrics(data.metrics);
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  const fetchProposals = useCallback(async () => {
    if (!brandId) return;
    
    try {
      const data = await fetchJSON<{ proposals: Proposal[] }>(
        `${API_BASE}/${brandId}/outcome-roi/proposals`
      );
      setProposals(data.proposals);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  }, [brandId]);

  const refresh = useCallback(async () => {
    await fetchStatus();
    await fetchProposals();
  }, [fetchStatus, fetchProposals]);

  const runAttribution = useCallback(async (runOptions?: {
    outcome_type?: string;
    auto_apply_low_risk?: boolean;
  }) => {
    if (!brandId) return;
    
    try {
      setLoading(true);
      await fetchJSON(`${API_BASE}/${brandId}/outcome-roi/run`, {
        method: 'POST',
        body: JSON.stringify({
          outcome_type: runOptions?.outcome_type ?? 'activation',
          auto_apply_low_risk: runOptions?.auto_apply_low_risk ?? true,
        }),
      });
      await refresh();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const applyProposal = useCallback(async (proposalId: string, note?: string): Promise<boolean> => {
    if (!brandId) return false;
    
    try {
      setLoading(true);
      await fetchJSON(`${API_BASE}/${brandId}/outcome-roi/proposals/${proposalId}/apply`, {
        method: 'POST',
        body: JSON.stringify({ applied_by: 'user', note }),
      });
      await refresh();
      return true;
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const rejectProposal = useCallback(async (proposalId: string, reason: string): Promise<boolean> => {
    if (!brandId) return false;
    
    try {
      setLoading(true);
      await fetchJSON(`${API_BASE}/${brandId}/outcome-roi/proposals/${proposalId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ rejected_by: 'user', reason }),
      });
      await refresh();
      return true;
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const freeze = useCallback(async (reason: string): Promise<boolean> => {
    if (!brandId) return false;
    
    try {
      setLoading(true);
      await fetchJSON(`${API_BASE}/${brandId}/outcome-roi/freeze`, {
        method: 'POST',
        body: JSON.stringify({ frozen_by: 'user', reason }),
      });
      await refresh();
      return true;
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const rollback = useCallback(async (reason: string, proposalIds?: string[]): Promise<boolean> => {
    if (!brandId) return false;
    
    try {
      setLoading(true);
      await fetchJSON(`${API_BASE}/${brandId}/outcome-roi/rollback`, {
        method: 'POST',
        body: JSON.stringify({ rolled_back_by: 'user', reason, proposal_ids: proposalIds }),
      });
      await refresh();
      return true;
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  useEffect(() => {
    if (!enabled || !brandId) return;
    
    refresh();
    
    if (pollInterval > 0) {
      const interval = setInterval(refresh, pollInterval);
      return () => clearInterval(interval);
    }
  }, [brandId, enabled, pollInterval, refresh]);

  return {
    status,
    proposals,
    metrics,
    loading,
    error,
    refresh,
    runAttribution,
    applyProposal,
    rejectProposal,
    freeze,
    rollback,
  };
}
