import { useState, useCallback, useEffect } from 'react';

export interface ExperimentVariant {
  variant_id: string;
  name: string;
  config: Record<string, unknown>;
  traffic_allocation: number;
}

export interface Experiment {
  experiment_id: string;
  name: string;
  description: string;
  hypothesis: string;
  primary_metric: string;
  status: 'draft' | 'running' | 'paused' | 'completed' | 'rolled_back';
  risk_level: 'low' | 'medium' | 'high';
  min_sample_size: number;
  min_confidence: number;
  max_lift_threshold: number;
  variants: ExperimentVariant[];
  created_at: string;
  started_at?: string;
  paused_at?: string;
  completed_at?: string;
  rolled_back_at?: string;
}

export interface EvaluationResult {
  experiment_id: string;
  variant_id: string;
  sample_size: number;
  control_conversion_rate: number;
  treatment_conversion_rate: number;
  absolute_lift: number;
  relative_lift: number;
  confidence: number;
  is_significant: boolean;
  reason: string;
}

export interface PromotionDecision {
  experiment_id: string;
  variant_id: string;
  decision: 'auto_apply' | 'approve' | 'continue' | 'block' | 'rollback';
  requires_approval: boolean;
  reason: string;
}

export interface ExperimentStatus {
  brand_id: string;
  version: string;
  metrics: {
    total_experiments: number;
    running_experiments: number;
    assignments_today: number;
    promotions_auto: number;
    promotions_approved: number;
    promotions_blocked: number;
    rollbacks: number;
  };
  active_experiments: Experiment[];
}

interface UseOnboardingExperimentsReturn {
  status: ExperimentStatus | null;
  experiments: Experiment[];
  evaluations: (EvaluationResult & { decision: string; requires_approval: boolean })[];
  loading: boolean;
  error: string | null;
  runEvaluation: () => Promise<void>;
  startExperiment: (experimentId: string) => Promise<void>;
  pauseExperiment: (experimentId: string, reason?: string) => Promise<void>;
  promoteExperiment: (experimentId: string, variantId: string, autoApply?: boolean) => Promise<void>;
  rollbackExperiment: (experimentId: string, reason: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const API_BASE = '/api/v2/brands';

export function useOnboardingExperiments(brandId: string): UseOnboardingExperimentsReturn {
  const [status, setStatus] = useState<ExperimentStatus | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [evaluations, setEvaluations] = useState<(EvaluationResult & { decision: string; requires_approval: boolean })[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-experiments/status`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    }
  }, [brandId]);

  const fetchExperiments = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-experiments`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setExperiments(data.experiments || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch experiments');
    }
  }, [brandId]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.all([fetchStatus(), fetchExperiments()]);
    setLoading(false);
  }, [fetchStatus, fetchExperiments]);

  const runEvaluation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/${brandId}/onboarding-experiments/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metrics_fetcher: 'default' }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setEvaluations(data.evaluations || []);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run evaluation');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const startExperiment = useCallback(async (experimentId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/${brandId}/onboarding-experiments/${experimentId}/start`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ started_by: 'user' }),
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start experiment');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const pauseExperiment = useCallback(async (experimentId: string, reason?: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/${brandId}/onboarding-experiments/${experimentId}/pause`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paused_by: 'user', reason: reason || '' }),
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause experiment');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const promoteExperiment = useCallback(async (experimentId: string, variantId: string, autoApply = false) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/${brandId}/onboarding-experiments/${experimentId}/promote`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            promoted_by: 'user',
            variant_id: variantId,
            auto_apply: autoApply,
          }),
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to promote experiment');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  const rollbackExperiment = useCallback(async (experimentId: string, reason: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/${brandId}/onboarding-experiments/${experimentId}/rollback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rolled_back_by: 'user',
            reason,
          }),
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback experiment');
    } finally {
      setLoading(false);
    }
  }, [brandId, refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    status,
    experiments,
    evaluations,
    loading,
    error,
    runEvaluation,
    startExperiment,
    pauseExperiment,
    promoteExperiment,
    rollbackExperiment,
    refresh,
  };
}
