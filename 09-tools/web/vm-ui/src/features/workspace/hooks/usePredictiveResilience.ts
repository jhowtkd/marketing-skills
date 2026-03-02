import { useState, useCallback, useEffect } from 'react';

export interface ResilienceScore {
  incident_component: number;
  handoff_component: number;
  approval_component: number;
  composite_score: number;
  risk_class: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
}

export interface PredictiveSignal {
  signal_id: string;
  metric_name: string;
  current_value: number;
  predicted_value: number;
  delta: number;
  delta_pct: number;
  confidence: number;
  forecast_horizon_hours: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
}

export interface MitigationProposal {
  proposal_id: string;
  signal_id: string;
  mitigation_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  can_auto_apply: boolean;
  requires_escalation: boolean;
  estimated_impact: Record<string, number>;
  state: 'pending' | 'applied' | 'rejected' | 'rolled_back';
  created_at: string;
  applied_at?: string;
  rolled_back_at?: string;
  rejection_reason?: string;
}

export interface PredictiveStatus {
  brand_id: string;
  state: 'idle' | 'observing' | 'detecting' | 'proposing' | 'mitigating' | 'completed' | 'frozen';
  version: string;
  cycle_id: string | null;
  last_run_at: string | null;
  resilience_score: ResilienceScore | null;
  active_proposals: MitigationProposal[];
  active_signals: PredictiveSignal[];
  cycles_total: number;
  proposals_total: number;
  proposals_applied: number;
  proposals_rejected: number;
  proposals_rolled_back: number;
  false_positives_total: number;
  frozen_brands: number;
}

export interface RunResult {
  cycle_id: string;
  brand_id: string;
  enabled: boolean;
  score: ResilienceScore;
  signals_detected: number;
  proposals_generated: number;
  proposals_applied: number;
  proposals_pending: number;
  freeze_triggered: boolean;
  proposals: MitigationProposal[];
  signals: PredictiveSignal[];
  applied_ids: string[];
  pending_ids: string[];
}

interface UsePredictiveResilienceReturn {
  status: PredictiveStatus | null;
  proposals: MitigationProposal[];
  signals: PredictiveSignal[];
  selectedProposal: MitigationProposal | null;
  loading: boolean;
  error: string | null;
  processing: boolean;
  fetchStatus: (brandId: string) => Promise<void>;
  runCycle: (brandId: string, autoApply?: boolean) => Promise<RunResult | null>;
  applyProposal: (brandId: string, proposalId: string) => Promise<boolean>;
  rejectProposal: (brandId: string, proposalId: string, reason?: string) => Promise<boolean>;
  freezeBrand: (brandId: string) => Promise<boolean>;
  unfreezeBrand: (brandId: string) => Promise<boolean>;
  rollbackProposal: (brandId: string, proposalId?: string) => Promise<boolean>;
  selectProposal: (proposal: MitigationProposal | null) => void;
  canApply: (proposal: MitigationProposal) => boolean;
  canReject: (proposal: MitigationProposal) => boolean;
  canFreeze: () => boolean;
  canUnfreeze: () => boolean;
  canRollback: (proposal: MitigationProposal) => boolean;
  getRiskClassColor: (riskClass: string) => string;
  getSeverityColor: (severity: string) => string;
}

const API_BASE = '/api/v2';

export function usePredictiveResilience(): UsePredictiveResilienceReturn {
  const [status, setStatus] = useState<PredictiveStatus | null>(null);
  const [proposals, setProposals] = useState<MitigationProposal[]>([]);
  const [signals, setSignals] = useState<PredictiveSignal[]>([]);
  const [selectedProposal, setSelectedProposal] = useState<MitigationProposal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const fetchStatus = useCallback(async (brandId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/brands/${brandId}/predictive-resilience/status`);
      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }
      const data = await response.json();
      setStatus(data);
      setProposals(data.active_proposals || []);
      setSignals(data.active_signals || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const runCycle = useCallback(async (brandId: string, autoApply: boolean = true): Promise<RunResult | null> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/brands/${brandId}/predictive-resilience/run?auto_apply_low_risk=${autoApply}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      );
      if (!response.ok) {
        throw new Error(`Failed to run cycle: ${response.statusText}`);
      }
      const data: RunResult = await response.json();
      // Refresh status after running
      await fetchStatus(brandId);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const applyProposal = useCallback(async (brandId: string, proposalId: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/brands/${brandId}/predictive-resilience/proposals/${proposalId}/apply`,
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

  const rejectProposal = useCallback(async (brandId: string, proposalId: string, reason?: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/brands/${brandId}/predictive-resilience/proposals/${proposalId}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: reason || 'User rejected' }),
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

  const freezeBrand = useCallback(async (brandId: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/brands/${brandId}/predictive-resilience/freeze`, {
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

  const unfreezeBrand = useCallback(async (brandId: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/brands/${brandId}/predictive-resilience/unfreeze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`Failed to unfreeze: ${response.statusText}`);
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

  const rollbackProposal = useCallback(async (brandId: string, proposalId?: string): Promise<boolean> => {
    setProcessing(true);
    setError(null);
    try {
      const body = proposalId ? JSON.stringify({ proposal_id: proposalId }) : JSON.stringify({});
      const response = await fetch(`${API_BASE}/brands/${brandId}/predictive-resilience/rollback`, {
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

  const selectProposal = useCallback((proposal: MitigationProposal | null) => {
    setSelectedProposal(proposal);
  }, []);

  const canApply = useCallback((proposal: MitigationProposal): boolean => {
    return proposal.state === 'pending' && proposal.severity === 'low' && proposal.can_auto_apply;
  }, []);

  const canReject = useCallback((proposal: MitigationProposal): boolean => {
    return proposal.state === 'pending';
  }, []);

  const canFreeze = useCallback((): boolean => {
    return status?.state !== 'frozen';
  }, [status]);

  const canUnfreeze = useCallback((): boolean => {
    return status?.state === 'frozen';
  }, [status]);

  const canRollback = useCallback((proposal: MitigationProposal): boolean => {
    return proposal.state === 'applied';
  }, []);

  const getRiskClassColor = useCallback((riskClass: string): string => {
    const colors: Record<string, string> = {
      low: 'text-green-600 bg-green-50',
      medium: 'text-yellow-600 bg-yellow-50',
      high: 'text-orange-600 bg-orange-50',
      critical: 'text-red-600 bg-red-50',
    };
    return colors[riskClass] || 'text-gray-600 bg-gray-50';
  }, []);

  const getSeverityColor = useCallback((severity: string): string => {
    const colors: Record<string, string> = {
      low: 'text-green-600',
      medium: 'text-yellow-600',
      high: 'text-orange-600',
      critical: 'text-red-600',
    };
    return colors[severity] || 'text-gray-600';
  }, []);

  return {
    status,
    proposals,
    signals,
    selectedProposal,
    loading,
    error,
    processing,
    fetchStatus,
    runCycle,
    applyProposal,
    rejectProposal,
    freezeBrand,
    unfreezeBrand,
    rollbackProposal,
    selectProposal,
    canApply,
    canReject,
    canFreeze,
    canUnfreeze,
    canRollback,
    getRiskClassColor,
    getSeverityColor,
  };
}
