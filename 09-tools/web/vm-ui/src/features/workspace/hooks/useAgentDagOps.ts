/**
 * Hook for Agent DAG Operations (v22)
 * 
 * Provides state management and API interactions for DAG operations.
 */

import { useState, useEffect, useCallback } from 'react';

export interface DagNodeState {
  status: 'pending' | 'waiting_approval' | 'running' | 'completed' | 'failed' | 'timeout' | 'handoff_failed';
  attempts: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface DagApproval {
  request_id: string;
  node_id: string;
  risk_level: 'low' | 'medium' | 'high';
  status: 'pending' | 'granted' | 'rejected' | 'escalated';
  requested_at: string;
}

export interface DagRun {
  run_id: string;
  dag_id: string;
  brand_id: string;
  project_id: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'aborted';
  node_states: Record<string, DagNodeState>;
  pending_approvals: DagApproval[];
  started_at: string;
  completed_at?: string;
}

export interface DagMetrics {
  runs_total: number;
  runs_completed: number;
  runs_failed: number;
  nodes_executed: number;
  nodes_failed: number;
  retries_total: number;
  handoff_failures: number;
  approvals_pending: number;
  avg_approval_wait_sec: number;
}

export interface UseAgentDagOpsResult {
  runs: DagRun[];
  metrics: DagMetrics | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  pauseRun: (runId: string) => Promise<void>;
  resumeRun: (runId: string) => Promise<void>;
  abortRun: (runId: string) => Promise<void>;
  retryNode: (runId: string, nodeId: string) => Promise<void>;
  grantApproval: (requestId: string, grantedBy: string) => Promise<void>;
  rejectApproval: (requestId: string, rejectedBy: string, reason: string) => Promise<void>;
}

export function useAgentDagOps(brandId?: string): UseAgentDagOpsResult {
  const [runs, setRuns] = useState<DagRun[]>([]);
  const [metrics, setMetrics] = useState<DagMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const url = brandId
        ? `/api/v2/dag/runs?brand_id=${brandId}`
        : '/api/v2/dag/runs';

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch DAG runs');
      }

      const data = await response.json();
      setRuns(data.runs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch('/api/v2/dag/metrics');
      if (!response.ok) {
        throw new Error('Failed to fetch DAG metrics');
      }

      const data = await response.json();
      setMetrics(data);
    } catch (err) {
      // Don't set error for metrics - they're supplementary
      console.error('Failed to fetch metrics:', err);
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([fetchRuns(), fetchMetrics()]);
  }, [fetchRuns, fetchMetrics]);

  const pauseRun = useCallback(async (runId: string) => {
    const response = await fetch(`/api/v2/dag/run/${runId}/pause`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to pause run');
    
    const data = await response.json();
    setRuns(prev => prev.map(r =>
      r.run_id === runId ? { ...r, status: data.status } : r
    ));
  }, []);

  const resumeRun = useCallback(async (runId: string) => {
    const response = await fetch(`/api/v2/dag/run/${runId}/resume`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to resume run');
    
    const data = await response.json();
    setRuns(prev => prev.map(r =>
      r.run_id === runId ? { ...r, status: data.status } : r
    ));
  }, []);

  const abortRun = useCallback(async (runId: string) => {
    const response = await fetch(`/api/v2/dag/run/${runId}/abort`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to abort run');
    
    const data = await response.json();
    setRuns(prev => prev.map(r =>
      r.run_id === runId ? { ...r, status: data.status } : r
    ));
  }, []);

  const retryNode = useCallback(async (runId: string, nodeId: string) => {
    const response = await fetch(`/api/v2/dag/run/${runId}/node/${nodeId}/retry`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to retry node');
    
    const data = await response.json();
    setRuns(prev => prev.map(r => {
      if (r.run_id !== runId) return r;
      return {
        ...r,
        node_states: {
          ...r.node_states,
          [nodeId]: { ...r.node_states[nodeId], status: 'pending', attempts: 0 },
        },
      };
    }));
  }, []);

  const grantApproval = useCallback(async (requestId: string, grantedBy: string) => {
    const response = await fetch(`/api/v2/dag/approval/${requestId}/grant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ granted_by: grantedBy }),
    });
    if (!response.ok) throw new Error('Failed to grant approval');
    
    await refresh();
  }, [refresh]);

  const rejectApproval = useCallback(async (requestId: string, rejectedBy: string, reason: string) => {
    const response = await fetch(`/api/v2/dag/approval/${requestId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rejected_by: rejectedBy, reason }),
    });
    if (!response.ok) throw new Error('Failed to reject approval');
    
    await refresh();
  }, [refresh]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [refresh]);

  return {
    runs,
    metrics,
    loading,
    error,
    refresh,
    pauseRun,
    resumeRun,
    abortRun,
    retryNode,
    grantApproval,
    rejectApproval,
  };
}
