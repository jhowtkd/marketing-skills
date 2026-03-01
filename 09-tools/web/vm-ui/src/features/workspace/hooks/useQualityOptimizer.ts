import { useState, useEffect, useCallback } from 'react';

export type ProposalState = 'pending' | 'applied' | 'rejected' | 'frozen' | 'rolled_back';

export interface QualityProposal {
  proposal_id: string;
  run_id: string;
  state: ProposalState;
  recommended_params: Record<string, unknown>;
  estimated_v1_improvement: number;
  estimated_cost_delta_pct: number;
  estimated_mttc_delta_pct: number;
  estimated_incident_rate: number;
  feasibility_check_passed: boolean;
  quality_score: number;
  created_at: string;
  applied_at?: string;
  rolled_back_at?: string;
}

export interface OptimizerStatus {
  version: string;
  total_proposals: number;
  proposals_by_state: {
    pending: number;
    applied: number;
    rejected: number;
    frozen: number;
    rolled_back: number;
  };
}

export interface ProposalSnapshot {
  proposal_id: string;
  previous_params: Record<string, unknown>;
  applied_params: Record<string, unknown>;
  applied_at: string;
}

export interface UseQualityOptimizerReturn {
  // State
  status: OptimizerStatus | null;
  proposals: QualityProposal[];
  selectedProposal: QualityProposal | null;
  snapshot: ProposalSnapshot | null;
  loading: boolean;
  error: string | null;
  processing: boolean;
  
  // Actions
  fetchStatus: () => Promise<void>;
  fetchProposals: (runId: string) => Promise<void>;
  selectProposal: (proposal: QualityProposal | null) => void;
  fetchSnapshot: (proposalId: string) => Promise<void>;
  applyProposal: (proposalId: string, enforceFeasibility?: boolean) => Promise<boolean>;
  rejectProposal: (proposalId: string) => Promise<boolean>;
  freezeProposal: (proposalId: string) => Promise<boolean>;
  rollbackProposal: (proposalId: string) => Promise<boolean>;
  runOptimizer: (runData: unknown) => Promise<QualityProposal | null>;
  
  // Helpers
  canApply: (proposal: QualityProposal) => boolean;
  canReject: (proposal: QualityProposal) => boolean;
  canFreeze: (proposal: QualityProposal) => boolean;
  canRollback: (proposal: QualityProposal) => boolean;
}

export function useQualityOptimizer(): UseQualityOptimizerReturn {
  const [status, setStatus] = useState<OptimizerStatus | null>(null);
  const [proposals, setProposals] = useState<QualityProposal[]>([]);
  const [selectedProposal, setSelectedProposal] = useState<QualityProposal | null>(null);
  const [snapshot, setSnapshot] = useState<ProposalSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/v2/optimizer/status');
      if (!response.ok) throw new Error('Failed to fetch status');
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, []);

  const fetchProposals = useCallback(async (runId: string) => {
    try {
      const response = await fetch(`/api/v2/optimizer/runs/${runId}/proposals`);
      if (!response.ok) throw new Error('Failed to fetch proposals');
      const data = await response.json();
      const fetchedProposals: QualityProposal[] = data.proposals || [];
      setProposals(fetchedProposals);
      
      // If we have proposals, select the first pending one by default
      const pendingProposal = fetchedProposals.find(p => p.state === 'pending');
      if (pendingProposal && !selectedProposal) {
        setSelectedProposal(pendingProposal);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [selectedProposal]);

  const selectProposal = useCallback((proposal: QualityProposal | null) => {
    setSelectedProposal(proposal);
    setSnapshot(null); // Clear snapshot when selecting a different proposal
  }, []);

  const fetchSnapshot = useCallback(async (proposalId: string) => {
    try {
      const response = await fetch(`/api/v2/optimizer/proposals/${proposalId}/snapshot`);
      if (!response.ok) {
        if (response.status === 404) {
          setSnapshot(null);
          return;
        }
        throw new Error('Failed to fetch snapshot');
      }
      const data = await response.json();
      setSnapshot(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, []);

  const applyProposal = useCallback(async (proposalId: string, enforceFeasibility = true): Promise<boolean> => {
    setProcessing(true);
    try {
      const response = await fetch(`/api/v2/optimizer/proposals/${proposalId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enforce_feasibility: enforceFeasibility }),
      });
      
      if (!response.ok) {
        if (response.status === 409) {
          throw new Error('Proposal cannot be applied: not feasible or invalid state');
        }
        throw new Error('Failed to apply proposal');
      }
      
      // Refresh proposals
      if (selectedProposal) {
        await fetchProposals(selectedProposal.run_id);
      }
      await fetchStatus();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchProposals, fetchStatus, selectedProposal]);

  const rejectProposal = useCallback(async (proposalId: string): Promise<boolean> => {
    setProcessing(true);
    try {
      const response = await fetch(`/api/v2/optimizer/proposals/${proposalId}/reject`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        if (response.status === 409) {
          throw new Error('Proposal cannot be rejected: invalid state');
        }
        throw new Error('Failed to reject proposal');
      }
      
      if (selectedProposal) {
        await fetchProposals(selectedProposal.run_id);
      }
      await fetchStatus();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchProposals, fetchStatus, selectedProposal]);

  const freezeProposal = useCallback(async (proposalId: string): Promise<boolean> => {
    setProcessing(true);
    try {
      const response = await fetch(`/api/v2/optimizer/proposals/${proposalId}/freeze`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        if (response.status === 409) {
          throw new Error('Proposal cannot be frozen: invalid state');
        }
        throw new Error('Failed to freeze proposal');
      }
      
      if (selectedProposal) {
        await fetchProposals(selectedProposal.run_id);
      }
      await fetchStatus();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to freeze');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchProposals, fetchStatus, selectedProposal]);

  const rollbackProposal = useCallback(async (proposalId: string): Promise<boolean> => {
    setProcessing(true);
    try {
      const response = await fetch(`/api/v2/optimizer/proposals/${proposalId}/rollback`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        if (response.status === 409) {
          throw new Error('Proposal cannot be rolled back: not applied');
        }
        throw new Error('Failed to rollback proposal');
      }
      
      // Fetch snapshot after rollback
      await fetchSnapshot(proposalId);
      
      if (selectedProposal) {
        await fetchProposals(selectedProposal.run_id);
      }
      await fetchStatus();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback');
      return false;
    } finally {
      setProcessing(false);
    }
  }, [fetchProposals, fetchStatus, fetchSnapshot, selectedProposal]);

  const runOptimizer = useCallback(async (runData: unknown): Promise<QualityProposal | null> => {
    setProcessing(true);
    try {
      const response = await fetch('/api/v2/optimizer/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(runData),
      });
      
      if (!response.ok) throw new Error('Failed to run optimizer');
      
      const data = await response.json();
      const newProposal: QualityProposal = data;
      
      await fetchStatus();
      return newProposal;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run optimizer');
      return null;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  // State transition helpers
  const canApply = useCallback((proposal: QualityProposal): boolean => {
    return proposal.state === 'pending' && proposal.feasibility_check_passed;
  }, []);

  const canReject = useCallback((proposal: QualityProposal): boolean => {
    return proposal.state === 'pending';
  }, []);

  const canFreeze = useCallback((proposal: QualityProposal): boolean => {
    return proposal.state === 'pending';
  }, []);

  const canRollback = useCallback((proposal: QualityProposal): boolean => {
    return proposal.state === 'applied';
  }, []);

  return {
    status,
    proposals,
    selectedProposal,
    snapshot,
    loading,
    error,
    processing,
    fetchStatus,
    fetchProposals,
    selectProposal,
    fetchSnapshot,
    applyProposal,
    rejectProposal,
    freezeProposal,
    rollbackProposal,
    runOptimizer,
    canApply,
    canReject,
    canFreeze,
    canRollback,
  };
}
