/**
 * useApprovalOptimizer Hook (v23)
 * 
 * React hook for interacting with the Approval Optimizer API.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface QueueItem {
  request_id: string;
  run_id: string;
  node_id: string;
  node_type: string;
  risk_level: string;
  priority_score: number;
  priority_level: string;
  refined_risk_score: number;
  wait_time_seconds: number;
}

export interface Batch {
  batch_id: string;
  brand_id: string;
  request_count: number;
  total_value: number;
  risk_score: number;
  status: string;
  expires_at?: string;
}

export interface OptimizerStats {
  queue_length: number;
  avg_priority: number;
  avg_risk: number;
  by_priority: Record<string, number>;
  by_risk: Record<string, number>;
  batches_pending: number;
}

export interface UseApprovalOptimizerOptions {
  brandId?: string;
  pollInterval?: number;
  enabled?: boolean;
}

export interface UseApprovalOptimizerReturn {
  queue: QueueItem[];
  batches: Batch[];
  stats: OptimizerStats | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  createBatch: () => Promise<boolean>;
  approveBatch: (batchId: string, approvedBy: string) => Promise<boolean>;
  rejectBatch: (batchId: string, rejectedBy: string, reason?: string) => Promise<boolean>;
  expandBatch: (batchId: string) => Promise<boolean>;
}

export function useApprovalOptimizer(options: UseApprovalOptimizerOptions = {}): UseApprovalOptimizerReturn {
  const { brandId, pollInterval = 30000, enabled = true } = options;
  
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [stats, setStats] = useState<OptimizerStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const refreshPromiseRef = useRef<Promise<void> | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    // Deduplicate concurrent refresh calls
    if (refreshPromiseRef.current) {
      return refreshPromiseRef.current;
    }
    
    const promise = (async () => {
      try {
        setLoading(true);
        setError(null);
        
        const signal = abortControllerRef.current!.signal;
        
        // Fetch queue
        const queueRes = await fetch('/api/v2/optimizer/queue', { signal });
        if (queueRes.ok) {
          setQueue(await queueRes.json());
        }
        
        // Fetch batches
        const batchesRes = await fetch('/api/v2/optimizer/batches', { signal });
        if (batchesRes.ok) {
          const data = await batchesRes.json();
          setBatches(data.batches || []);
        }
        
        // Fetch stats
        const statsRes = await fetch('/api/v2/optimizer/stats', { signal });
        if (statsRes.ok) {
          setStats(await statsRes.json());
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
  }, []);

  const createBatch = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(
        `/api/v2/optimizer/batch/create${brandId ? `?brand_id=${brandId}` : ''}`,
        { method: 'POST' }
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

  const approveBatch = useCallback(async (batchId: string, approvedBy: string): Promise<boolean> => {
    try {
      const res = await fetch(`/api/v2/optimizer/batch/${batchId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: approvedBy }),
      });
      if (res.ok) {
        await refresh();
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  }, [refresh]);

  const rejectBatch = useCallback(async (
    batchId: string,
    rejectedBy: string,
    reason?: string
  ): Promise<boolean> => {
    try {
      const res = await fetch(`/api/v2/optimizer/batch/${batchId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected_by: rejectedBy, reason: reason || 'Rejected' }),
      });
      if (res.ok) {
        await refresh();
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  }, [refresh]);

  const expandBatch = useCallback(async (batchId: string): Promise<boolean> => {
    try {
      const res = await fetch(`/api/v2/optimizer/batch/${batchId}/expand`, {
        method: 'POST',
      });
      if (res.ok) {
        await refresh();
        return true;
      }
      return false;
    } catch (err) {
      return false;
    }
  }, [refresh]);

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
    queue,
    batches,
    stats,
    loading,
    error,
    refresh,
    createBatch,
    approveBatch,
    rejectBatch,
    expandBatch,
  };
}
