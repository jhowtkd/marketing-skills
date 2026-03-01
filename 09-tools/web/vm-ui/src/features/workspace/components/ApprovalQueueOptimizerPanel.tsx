/**
 * Approval Queue Optimizer Panel (v23)
 * 
 * Panel for managing optimized approval queue with batch actions.
 */

import { useState, useEffect, useCallback } from 'react';

interface QueueItem {
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

interface Batch {
  batch_id: string;
  brand_id: string;
  request_count: number;
  total_value: number;
  risk_score: number;
}

interface ApprovalQueueOptimizerPanelProps {
  brandId?: string;
}

export function ApprovalQueueOptimizerPanel({ brandId }: ApprovalQueueOptimizerPanelProps) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch queue
      const queueRes = await fetch('/api/v2/optimizer/queue');
      if (queueRes.ok) {
        setQueue(await queueRes.json());
      }
      
      // Fetch batches
      const batchesRes = await fetch('/api/v2/optimizer/batches');
      if (batchesRes.ok) {
        const data = await batchesRes.json();
        setBatches(data.batches || []);
      }
      
      // Fetch stats
      const statsRes = await fetch('/api/v2/optimizer/stats');
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleCreateBatch = async () => {
    try {
      const res = await fetch(`/api/v2/optimizer/batch/create${brandId ? `?brand_id=${brandId}` : ''}`, {
        method: 'POST',
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      setError('Failed to create batch');
    }
  };

  const handleApproveBatch = async (batchId: string) => {
    try {
      await fetch(`/api/v2/optimizer/batch/${batchId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: 'user' }),
      });
      fetchData();
    } catch (err) {
      setError('Failed to approve batch');
    }
  };

  const handleRejectBatch = async (batchId: string) => {
    try {
      await fetch(`/api/v2/optimizer/batch/${batchId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected_by: 'user', reason: 'Rejected' }),
      });
      fetchData();
    } catch (err) {
      setError('Failed to reject batch');
    }
  };

  const handleExpandBatch = async (batchId: string) => {
    try {
      await fetch(`/api/v2/optimizer/batch/${batchId}/expand`, { method: 'POST' });
      fetchData();
    } catch (err) {
      setError('Failed to expand batch');
    }
  };

  if (loading && queue.length === 0) {
    return (
      <div data-testid="optimizer-loading" className="p-4">
        <h2 className="text-lg font-semibold mb-4">Approval Queue Optimizer v23</h2>
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="optimizer-error" className="p-4">
        <h2 className="text-lg font-semibold mb-4">Approval Queue Optimizer v23</h2>
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div data-testid="approval-optimizer-panel" className="p-4">
      <h2 className="text-lg font-semibold mb-4">Approval Queue Optimizer v23</h2>
      
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-3 rounded">
            <div className="text-sm text-gray-600">Queue Length</div>
            <div className="text-xl font-bold" data-testid="stat-queue-length">
              {stats.queue_length}
            </div>
          </div>
          <div className="bg-green-50 p-3 rounded">
            <div className="text-sm text-gray-600">Avg Priority</div>
            <div className="text-xl font-bold">
              {(stats.avg_priority * 100).toFixed(0)}%
            </div>
          </div>
          <div className="bg-yellow-50 p-3 rounded">
            <div className="text-sm text-gray-600">Critical</div>
            <div className="text-xl font-bold" data-testid="stat-critical">
              {stats.by_priority?.critical || 0}
            </div>
          </div>
          <div className="bg-purple-50 p-3 rounded">
            <div className="text-sm text-gray-600">High Priority</div>
            <div className="text-xl font-bold">
              {stats.by_priority?.high || 0}
            </div>
          </div>
        </div>
      )}
      
      {/* Actions */}
      <div className="mb-4">
        <button
          data-testid="btn-create-batch"
          onClick={handleCreateBatch}
          className="px-4 py-2 bg-blue-500 text-white rounded mr-2"
        >
          Create Batch
        </button>
      </div>
      
      {/* Queue */}
      <div className="mb-6">
        <h3 className="font-medium mb-2">Prioritized Queue</h3>
        {queue.length === 0 ? (
          <div data-testid="empty-queue" className="text-gray-500">Queue is empty</div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {queue.slice(0, 10).map((item) => (
              <div
                key={item.request_id}
                data-testid={`queue-item-${item.request_id}`}
                className="flex justify-between items-center p-3 bg-gray-50 rounded"
              >
                <div>
                  <span className="font-medium">{item.node_id}</span>
                  <span className="text-sm text-gray-500 ml-2">({item.node_type})</span>
                  <div className="text-xs text-gray-400">
                    Priority: {(item.priority_score * 100).toFixed(0)}% | 
                    Risk: {(item.refined_risk_score * 100).toFixed(0)}%
                  </div>
                </div>
                <span className={`px-2 py-1 rounded text-xs ${
                  item.priority_level === 'critical' ? 'bg-red-100 text-red-800' :
                  item.priority_level === 'high' ? 'bg-orange-100 text-orange-800' :
                  item.priority_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {item.priority_level}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Batches */}
      {batches.length > 0 && (
        <div>
          <h3 className="font-medium mb-2">Batches</h3>
          <div className="space-y-2">
            {batches.map((batch) => (
              <div
                key={batch.batch_id}
                data-testid={`batch-${batch.batch_id}`}
                className="p-3 border rounded bg-white"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium">Batch {batch.batch_id[:8]}</div>
                    <div className="text-sm text-gray-500">
                      {batch.request_count} requests | Value: ${batch.total_value}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      data-testid={`btn-approve-${batch.batch_id}`}
                      onClick={() => handleApproveBatch(batch.batch_id)}
                      className="px-2 py-1 bg-green-500 text-white rounded text-sm"
                    >
                      Approve
                    </button>
                    <button
                      data-testid={`btn-reject-${batch.batch_id}`}
                      onClick={() => handleRejectBatch(batch.batch_id)}
                      className="px-2 py-1 bg-red-500 text-white rounded text-sm"
                    >
                      Reject
                    </button>
                    <button
                      data-testid={`btn-expand-${batch.batch_id}`}
                      onClick={() => handleExpandBatch(batch.batch_id)}
                      className="px-2 py-1 bg-gray-500 text-white rounded text-sm"
                    >
                      Expand
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <button
        onClick={fetchData}
        className="mt-4 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm"
      >
        Refresh
      </button>
    </div>
  );
}
