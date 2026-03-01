/**
 * Agent DAG Ops Panel (v22)
 * 
 * Panel for managing multi-agent DAG operations including:
 * - Viewing DAG runs and node states
 * - Pause/Resume/Abort runs
 * - Retry failed nodes
 * - Grant/Reject approvals
 */

import { useState, useEffect, useCallback } from 'react';

interface DagNodeState {
  status: string;
  attempts?: number;
  error?: string;
}

interface DagRun {
  run_id: string;
  dag_id: string;
  status: string;
  nodes: number;
  node_states?: Record<string, DagNodeState>;
  pending_approvals?: Array<{
    request_id: string;
    node_id: string;
    risk_level: string;
  }>;
}

interface AgentDagOpsPanelProps {
  brandId?: string;
}

export function AgentDagOpsPanel({ brandId }: AgentDagOpsPanelProps) {
  const [runs, setRuns] = useState<DagRun[]>([]);
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

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchRuns]);

  const handlePause = async (runId: string) => {
    try {
      const response = await fetch(`/api/v2/dag/run/${runId}/pause`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to pause run');
      
      const data = await response.json();
      setRuns(prev => prev.map(r => 
        r.run_id === runId ? { ...r, status: data.status } : r
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause');
    }
  };

  const handleResume = async (runId: string) => {
    try {
      const response = await fetch(`/api/v2/dag/run/${runId}/resume`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to resume run');
      
      const data = await response.json();
      setRuns(prev => prev.map(r => 
        r.run_id === runId ? { ...r, status: data.status } : r
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume');
    }
  };

  const handleAbort = async (runId: string) => {
    try {
      const response = await fetch(`/api/v2/dag/run/${runId}/abort`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to abort run');
      
      const data = await response.json();
      setRuns(prev => prev.map(r => 
        r.run_id === runId ? { ...r, status: data.status } : r
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to abort');
    }
  };

  const handleRetry = async (runId: string, nodeId: string) => {
    try {
      const response = await fetch(`/api/v2/dag/run/${runId}/node/${nodeId}/retry`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to retry node');
      
      const data = await response.json();
      setRuns(prev => prev.map(r => {
        if (r.run_id !== runId || !r.node_states) return r;
        return {
          ...r,
          node_states: {
            ...r.node_states,
            [nodeId]: { ...r.node_states[nodeId], status: data.status },
          },
        };
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry');
    }
  };

  const handleGrant = async (requestId: string) => {
    try {
      const response = await fetch(`/api/v2/dag/approval/${requestId}/grant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ granted_by: 'user' }),
      });
      if (!response.ok) throw new Error('Failed to grant approval');
      
      await fetchRuns(); // Refresh to get updated state
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to grant');
    }
  };

  const handleReject = async (requestId: string) => {
    try {
      const response = await fetch(`/api/v2/dag/approval/${requestId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected_by: 'user', reason: 'Rejected by user' }),
      });
      if (!response.ok) throw new Error('Failed to reject approval');
      
      await fetchRuns(); // Refresh to get updated state
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject');
    }
  };

  if (loading && runs.length === 0) {
    return (
      <div data-testid="dag-ops-loading" className="p-4">
        <h2 className="text-lg font-semibold mb-4">Agent DAG Ops v22</h2>
        <div className="text-gray-500">Loading DAG runs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="dag-ops-error" className="p-4">
        <h2 className="text-lg font-semibold mb-4">Agent DAG Ops v22</h2>
        <div className="text-red-500">{error}</div>
        <button 
          onClick={fetchRuns}
          className="mt-2 px-4 py-2 bg-blue-500 text-white rounded"
        >
          Retry
        </button>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div data-testid="dag-ops-empty" className="p-4">
        <h2 className="text-lg font-semibold mb-4">Agent DAG Ops v22</h2>
        <div className="text-gray-500">No DAG runs found</div>
      </div>
    );
  }

  return (
    <div data-testid="agent-dag-ops-panel" className="p-4">
      <h2 className="text-lg font-semibold mb-4">Agent DAG Ops v22</h2>
      
      <div className="space-y-4">
        {runs.map(run => (
          <div 
            key={run.run_id}
            data-testid={`dag-run-${run.run_id}`}
            className="border rounded-lg p-4 bg-white shadow-sm"
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <h3 className="font-medium">{run.dag_id}</h3>
                <div className="text-sm text-gray-500">
                  Run: {run.run_id} • {run.nodes} nodes
                </div>
              </div>
              <div className="flex gap-2">
                {run.status === 'running' && (
                  <>
                    <button
                      data-testid={`btn-pause-${run.run_id}`}
                      onClick={() => handlePause(run.run_id)}
                      className="px-3 py-1 bg-yellow-500 text-white rounded text-sm"
                    >
                      Pause
                    </button>
                    <button
                      data-testid={`btn-abort-${run.run_id}`}
                      onClick={() => handleAbort(run.run_id)}
                      className="px-3 py-1 bg-red-500 text-white rounded text-sm"
                    >
                      Abort
                    </button>
                  </>
                )}
                {run.status === 'paused' && (
                  <button
                    data-testid={`btn-resume-${run.run_id}`}
                    onClick={() => handleResume(run.run_id)}
                    className="px-3 py-1 bg-green-500 text-white rounded text-sm"
                  >
                    Resume
                  </button>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm font-medium">Status:</span>
              <span className={`text-sm px-2 py-0.5 rounded ${
                run.status === 'completed' ? 'bg-green-100 text-green-800' :
                run.status === 'failed' ? 'bg-red-100 text-red-800' :
                run.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                run.status === 'aborted' ? 'bg-gray-100 text-gray-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {run.status}
              </span>
            </div>

            {/* Node States */}
            {run.node_states && Object.entries(run.node_states).length > 0 && (
              <div className="mb-3">
                <h4 className="text-sm font-medium mb-2">Nodes</h4>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(run.node_states).map(([nodeId, state]) => (
                    <div 
                      key={nodeId}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded"
                    >
                      <div>
                        <span className="text-sm font-medium">{nodeId}</span>
                        <div 
                          data-testid={`node-status-${nodeId}`}
                          className="text-xs text-gray-500"
                        >
                          {state.status}
                          {state.attempts ? ` (attempt ${state.attempts})` : ''}
                        </div>
                      </div>
                      {state.status === 'failed' && (
                        <button
                          data-testid={`btn-retry-${nodeId}`}
                          onClick={() => handleRetry(run.run_id, nodeId)}
                          className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Pending Approvals */}
            {run.pending_approvals && run.pending_approvals.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">Pending Approvals</h4>
                <div className="space-y-2">
                  {run.pending_approvals.map(approval => (
                    <div 
                      key={approval.request_id}
                      className="flex items-center justify-between p-2 bg-yellow-50 border border-yellow-200 rounded"
                    >
                      <div>
                        <span className="text-sm font-medium">{approval.node_id}</span>
                        <div className="text-xs text-gray-500">
                          Risk: {approval.risk_level}
                        </div>
                        <div 
                          data-testid={`approval-status-${approval.request_id}`}
                          className="text-xs text-yellow-600"
                        >
                          pending
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          data-testid={`btn-grant-${approval.request_id}`}
                          onClick={() => handleGrant(approval.request_id)}
                          className="px-2 py-1 bg-green-500 text-white rounded text-xs"
                        >
                          Grant
                        </button>
                        <button
                          data-testid={`btn-reject-${approval.request_id}`}
                          onClick={() => handleReject(approval.request_id)}
                          className="px-2 py-1 bg-red-500 text-white rounded text-xs"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <button
        onClick={fetchRuns}
        className="mt-4 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm"
      >
        Refresh
      </button>
    </div>
  );
}
