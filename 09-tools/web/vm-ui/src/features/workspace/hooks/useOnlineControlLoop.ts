import { useState, useCallback, useEffect } from 'react';

export interface ControlLoopStatus {
  version: string;
  state: 'idle' | 'observing' | 'detecting' | 'proposing' | 'applying' | 'verifying' | 'completed' | 'blocked' | 'frozen';
  cycle_id: string | null;
  brand_id: string;
  active_proposals: Proposal[];
  active_regressions: Regression[];
}

export interface Proposal {
  proposal_id: string;
  adjustment_type: string;
  target_gate: string;
  current_value: number;
  proposed_value: number;
  delta: number;
  severity: 'low' | 'medium' | 'high';
  requires_approval: boolean;
  estimated_impact: Record<string, number>;
  state: 'pending' | 'applied' | 'rejected' | 'rolled_back';
  applied_at?: string;
  rolled_back_at?: string;
}

export interface Regression {
  metric: string;
  severity: string;
  delta_pct: number;
  detected_at?: string;
}

export interface ControlLoopMetrics {
  cycles_total: number;
  regressions_detected_total: number;
  mitigations_applied_total: number;
  mitigations_blocked_total: number;
  rollbacks_total: number;
  time_to_detect_avg_seconds: number;
  time_to_mitigate_avg_seconds: number;
  active_cycles: number;
  frozen_brands: number;
}

interface UseOnlineControlLoopReturn {
  status: ControlLoopStatus | null;
  proposals: Proposal[];
  regressions: Regression[];
  metrics: ControlLoopMetrics | null;
  selectedProposal: Proposal | null;
  loading: boolean;
  error: string | null;
  processing: boolean;
  fetchStatus: (brandId: string) => Promise<void>;
  startCycle: (brandId: string) => Promise<boolean>;
  applyProposal: (brandId: string, proposalId: string) => Promise<boolean>;
  rejectProposal: (brandId: string, proposalId: string) => Promise<boolean>;
  freezeControlLoop: (brandId: string) => Promise<boolean>;
  rollbackControlLoop: (brandId: string, proposalId?: string) => Promise<boolean>;
  selectProposal: (proposal: Proposal | null) => void;
  canApply: (proposal: Proposal) => boolean;
  canReject: (proposal: Proposal) => boolean;
  canFreeze: () => boolean;
  canRollback: (proposal: Proposal) => boolean;
}

const API_BASE = '/api/v2';

export function useOnlineControlLoop(): UseOnlineControlLoopReturn {
  const [status, setStatus] = useState<ControlLoopStatus | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [regressions, setRegressions] = useState<Regression[]>([]);
  const [metrics, setMetrics] = useState<ControlLoopMetrics | null>(null);
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const fetchStatus = useCallback(async (brandId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/brands/${brandId}/control-loop/status`);
      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }
      const data = await response.json();
      setStatus(data);
      setProposals(data.active_proposals || []);
      setRegressions(data.active_regressions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const startCycle = useCallback(async (brandId: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/brands/${brandId}/control-loop/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`Failed to start cycle: ${response.statusText}`);
      }
      const data = await response.json();
      // Refresh status after starting
      await fetchStatus(brandId);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const applyProposal = useCallback(async (brandId: string, proposalId: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/brands/${brandId}/control-loop/proposals/${proposalId}/apply`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved: true }),
        }
      );
      if (!response.ok) {
        throw new Error(`Failed to apply proposal: ${response.statusText}`);
      }
      await fetchStatus(brandId);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const rejectProposal = useCallback(async (brandId: string, proposalId: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/brands/${brandId}/control-loop/proposals/${proposalId}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'User rejected' }),
        }
      );
      if (!response.ok) {
        throw new Error(`Failed to reject proposal: ${response.statusText}`);
      }
      await fetchStatus(brandId);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const freezeControlLoop = useCallback(async (brandId: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/brands/${brandId}/control-loop/freeze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'User frozen' }),
      });
      if (!response.ok) {
        throw new Error(`Failed to freeze: ${response.statusText}`);
      }
      await fetchStatus(brandId);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const rollbackControlLoop = useCallback(async (brandId: string, proposalId?: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const body = proposalId ? JSON.stringify({ proposal_id: proposalId }) : JSON.stringify({});
      const response = await fetch(`${API_BASE}/brands/${brandId}/control-loop/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      if (!response.ok) {
        throw new Error(`Failed to rollback: ${response.statusText}`);
      }
      await fetchStatus(brandId);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const selectProposal = useCallback((proposal: Proposal | null) => {
    setSelectedProposal(proposal);
  }, []);

  const canApply = useCallback((proposal: Proposal): boolean => {
    return proposal.state === 'pending' && proposal.severity === 'low' && !proposal.requires_approval;
  }, []);

  const canReject = useCallback((proposal: Proposal): boolean => {
    return proposal.state === 'pending';
  }, []);

  const canFreeze = useCallback((): boolean => {
    return status?.state !== 'frozen';
  }, [status]);

  const canRollback = useCallback((proposal: Proposal): boolean => {
    return proposal.state === 'applied';
  }, []);

  return {
    status,
    proposals,
    regressions,
    metrics,
    selectedProposal,
    loading,
    error,
    processing,
    fetchStatus,
    startCycle,
    applyProposal,
    rejectProposal,
    freezeControlLoop,
    rollbackControlLoop,
    selectProposal,
    canApply,
    canReject,
    canFreeze,
    canRollback,
  };
}
