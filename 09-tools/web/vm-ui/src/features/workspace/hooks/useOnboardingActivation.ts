import { useState, useCallback, useEffect } from 'react';

export interface Proposal {
  id: string;
  rule_name: string;
  description: string;
  risk_level: 'low' | 'medium' | 'high';
  current_value: number;
  target_value: number;
  adjustment_percent: number;
  expected_impact: string;
  status: 'pending' | 'applied' | 'rejected';
  created_at: string;
}

export interface ActivationStatus {
  brand_id: string;
  metrics: {
    completion_rate: number;
    step_1_dropoff_rate: number;
    template_to_first_run_conversion: number;
    average_time_to_first_action_ms: number;
  };
  top_frictions: Array<{
    type: string;
    step?: string;
    reason?: string;
    count: number;
    severity: string;
  }>;
  active_proposals_count: number;
  frozen: boolean;
}

interface UseOnboardingActivationReturn {
  status: ActivationStatus | null;
  proposals: Proposal[];
  loading: boolean;
  error: string | null;
  runActivation: () => Promise<void>;
  applyProposal: (proposalId: string) => Promise<void>;
  rejectProposal: (proposalId: string, reason?: string) => Promise<void>;
  freezeProposals: () => Promise<void>;
  rollbackLast: () => Promise<void>;
  refresh: () => Promise<void>;
}

const API_BASE = '/api/v2/brands';

export function useOnboardingActivation(brandId: string): UseOnboardingActivationReturn {
  const [status, setStatus] = useState<ActivationStatus | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-activation/status`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    }
  }, [brandId]);

  const fetchProposals = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-activation/proposals`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setProposals(data.proposals || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch proposals');
    }
  }, [brandId]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.all([fetchStatus(), fetchProposals()]);
    setLoading(false);
  }, [fetchStatus, fetchProposals]);

  const runActivation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-activation/run`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run activation');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const applyProposal = useCallback(async (proposalId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/${brandId}/onboarding-activation/proposals/${proposalId}/apply`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply proposal');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const rejectProposal = useCallback(async (proposalId: string, reason?: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/${brandId}/onboarding-activation/proposals/${proposalId}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: reason || '' }),
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject proposal');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const freezeProposals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-activation/freeze`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to freeze proposals');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const rollbackLast = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-activation/rollback`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    status,
    proposals,
    loading,
    error,
    runActivation,
    applyProposal,
    rejectProposal,
    freezeProposals,
    rollbackLast,
    refresh,
  };
}
