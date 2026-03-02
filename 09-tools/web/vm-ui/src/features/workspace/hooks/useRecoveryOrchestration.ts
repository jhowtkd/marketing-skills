import { useState, useCallback } from 'react';

export interface RecoveryRun {
  run_id: string;
  brand_id: string;
  incident_id: string;
  incident_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'frozen' | 'rolled_back';
  auto_executed: boolean;
  approval_request_id?: string;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  steps_completed: number;
  steps_total: number;
}

export interface ApprovalRequest {
  request_id: string;
  run_id: string;
  brand_id: string;
  incident_type: string;
  severity: string;
  requested_at: string;
  status: 'pending' | 'approved' | 'rejected';
  approved_by?: string;
  rejected_by?: string;
  reason?: string;
}

export interface RecoveryStatus {
  brand_id: string;
  state: string;
  version: string;
  metrics: {
    total_runs: number;
    successful_runs: number;
    failed_runs: number;
    auto_runs: number;
    manual_runs: number;
    pending_approvals: number;
  };
  active_incidents: Array<{
    incident_id: string;
    type: string;
    severity: string;
    description: string;
    timestamp: string;
  }>;
  pending_approvals: ApprovalRequest[];
}

export interface RecoveryEvent {
  event_id: string;
  brand_id: string;
  event_type: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export function useRecoveryOrchestration() {
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [runs, setRuns] = useState<RecoveryRun[]>([]);
  const [events, setEvents] = useState<RecoveryEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const fetchStatus = useCallback(async (brandId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/status`);
      if (!response.ok) throw new Error('Failed to fetch recovery status');
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRuns = useCallback(async (brandId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/events`);
      if (!response.ok) throw new Error('Failed to fetch recovery runs');
      const data = await response.json();
      setEvents(data.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const startRecovery = useCallback(async (
    brandId: string,
    incidentType: string,
    severity: string,
    description?: string
  ) => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_type: incidentType,
          severity,
          description,
        }),
      });
      if (!response.ok) throw new Error('Failed to start recovery');
      const data = await response.json();
      await fetchStatus(brandId);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const approveRecovery = useCallback(async (brandId: string, requestId: string, approvedBy: string, reason?: string) => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/approve/${requestId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: approvedBy, reason }),
      });
      if (!response.ok) throw new Error('Failed to approve recovery');
      const data = await response.json();
      await fetchStatus(brandId);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const rejectRecovery = useCallback(async (brandId: string, requestId: string, rejectedBy: string, reason?: string) => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/reject/${requestId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected_by: rejectedBy, reason }),
      });
      if (!response.ok) throw new Error('Failed to reject recovery');
      const data = await response.json();
      await fetchStatus(brandId);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const freezeRecovery = useCallback(async (brandId: string, incidentId: string, reason?: string) => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/freeze/${incidentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) throw new Error('Failed to freeze recovery');
      const data = await response.json();
      await fetchStatus(brandId);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const rollbackRecovery = useCallback(async (brandId: string, runId: string, reason?: string) => {
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/rollback/${runId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) throw new Error('Failed to rollback recovery');
      const data = await response.json();
      await fetchStatus(brandId);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const retryRecovery = useCallback(async (brandId: string, runId: string) => {
    setProcessing(true);
    setError(null);
    try {
      // Retry is implemented as a new run with the same parameters
      const response = await fetch(`/api/v2/brands/${brandId}/recovery/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_type: 'retry',
          severity: 'medium',
          context: { original_run_id: runId },
        }),
      });
      if (!response.ok) throw new Error('Failed to retry recovery');
      const data = await response.json();
      await fetchStatus(brandId);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus]);

  const getSeverityColor = useCallback((severity: string): string => {
    const colors: Record<string, string> = {
      low: 'bg-blue-100 text-blue-700',
      medium: 'bg-yellow-100 text-yellow-700',
      high: 'bg-orange-100 text-orange-700',
      critical: 'bg-red-100 text-red-700',
    };
    return colors[severity] || 'bg-gray-100 text-gray-700';
  }, []);

  const getStatusColor = useCallback((status: string): string => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-700',
      running: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
      frozen: 'bg-purple-100 text-purple-700',
      rolled_back: 'bg-orange-100 text-orange-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  }, []);

  const canApprove = useCallback((request: ApprovalRequest): boolean => {
    return request.status === 'pending';
  }, []);

  const canReject = useCallback((request: ApprovalRequest): boolean => {
    return request.status === 'pending';
  }, []);

  const canFreeze = useCallback((run: RecoveryRun): boolean => {
    return ['pending', 'running'].includes(run.status);
  }, []);

  const canRollback = useCallback((run: RecoveryRun): boolean => {
    return ['completed', 'failed'].includes(run.status);
  }, []);

  const canRetry = useCallback((run: RecoveryRun): boolean => {
    return ['failed', 'rolled_back'].includes(run.status);
  }, []);

  return {
    status,
    runs,
    events,
    loading,
    error,
    processing,
    fetchStatus,
    fetchRuns,
    startRecovery,
    approveRecovery,
    rejectRecovery,
    freezeRecovery,
    rollbackRecovery,
    retryRecovery,
    getSeverityColor,
    getStatusColor,
    canApprove,
    canReject,
    canFreeze,
    canRollback,
    canRetry,
  };
}
