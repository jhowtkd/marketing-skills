import { useState, useEffect, useCallback } from 'react';

interface Proposal {
  suggestion_id: string;
  adjustment_type: string;
  current_value: number;
  proposed_value: number;
  confidence: number;
  expected_savings_percent: number;
  risk_score: number;
  status: string;
}

interface AppliedRecord {
  suggestion_id: string;
  brand_id: string;
  adjustment_type: string;
  previous_value: number;
  applied_value: number;
  mode: string;
  applied_at: string;
}

interface ApprovalLearningOpsPanelProps {
  brandId: string;
}

export function ApprovalLearningOpsPanel({ brandId }: ApprovalLearningOpsPanelProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [history, setHistory] = useState<AppliedRecord[]>([]);
  const [status, setStatus] = useState<{ status: string; version: string } | null>(null);
  const [processing, setProcessing] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/v2/approval-learning/status');
      if (!response.ok) throw new Error('Failed to fetch status');
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, []);

  const fetchProposals = useCallback(async () => {
    try {
      const response = await fetch(`/api/v2/approval-learning/proposals?brand_id=${brandId}`);
      if (!response.ok) throw new Error('Failed to fetch proposals');
      const data = await response.json();
      setProposals(data.proposals || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [brandId]);

  const fetchHistory = useCallback(async () => {
    try {
      const response = await fetch(`/api/v2/approval-learning/history/${brandId}`);
      if (!response.ok) throw new Error('Failed to fetch history');
      const data = await response.json();
      setHistory(data.history || []);
    } catch (err) {
      // History might be empty, that's ok
      setHistory([]);
    }
  }, [brandId]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchStatus(), fetchProposals(), fetchHistory()]);
      setLoading(false);
    };
    loadData();
  }, [fetchStatus, fetchProposals, fetchHistory]);

  const handleApply = async (proposalId: string) => {
    setProcessing(proposalId);
    try {
      const response = await fetch(`/api/v2/approval-learning/proposals/${proposalId}/apply`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to apply proposal');
      await fetchProposals();
      await fetchHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply');
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (proposalId: string) => {
    setProcessing(proposalId);
    try {
      const response = await fetch(`/api/v2/approval-learning/proposals/${proposalId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'manual_reject' }),
      });
      if (!response.ok) throw new Error('Failed to reject proposal');
      await fetchProposals();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject');
    } finally {
      setProcessing(null);
    }
  };

  const handleFreeze = async () => {
    try {
      const response = await fetch(`/api/v2/approval-learning/brands/${brandId}/freeze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'manual_freeze' }),
      });
      if (!response.ok) throw new Error('Failed to freeze');
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to freeze');
    }
  };

  const handleRunLearning = async () => {
    try {
      const response = await fetch('/api/v2/approval-learning/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brand_id: brandId }),
      });
      if (!response.ok) throw new Error('Failed to run learning');
      await fetchProposals();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run learning');
    }
  };

  if (loading) {
    return (
      <div className="p-4 border rounded-lg bg-white shadow-sm">
        <h3 className="text-lg font-semibold mb-4">Approval Learning Ops</h3>
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border rounded-lg bg-white shadow-sm">
        <h3 className="text-lg font-semibold mb-4">Approval Learning Ops</h3>
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  const lowRiskProposals = proposals.filter(p => p.risk_score < 0.3);
  const mediumHighRiskProposals = proposals.filter(p => p.risk_score >= 0.3);

  return (
    <div className="p-4 border rounded-lg bg-white shadow-sm space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Approval Learning Ops</h3>
          <div className="text-sm text-gray-500">
            Status: {status?.status} | Version: {status?.version}
          </div>
        </div>
        <div className="space-x-2">
          <button
            onClick={handleRunLearning}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Run Learning
          </button>
          <button
            onClick={handleFreeze}
            className="px-3 py-1 bg-yellow-500 text-white rounded hover:bg-yellow-600"
          >
            Freeze Learning
          </button>
        </div>
      </div>

      {/* Low Risk Proposals - Auto-apply */}
      {lowRiskProposals.length > 0 && (
        <div className="border rounded p-3 bg-green-50">
          <h4 className="font-medium mb-2 text-green-800">
            Low-Risk Suggestions (Auto-apply)
          </h4>
          <div className="space-y-2">
            {lowRiskProposals.map(proposal => (
              <div key={proposal.suggestion_id} className="flex justify-between items-center p-2 bg-white rounded">
                <div>
                  <div className="font-medium">{proposal.adjustment_type}</div>
                  <div className="text-sm text-gray-500">
                    {proposal.current_value} → {proposal.proposed_value}
                    {' | '}
                    Confidence: {(proposal.confidence * 100).toFixed(0)}%
                    {' | '}
                    Savings: {proposal.expected_savings_percent}%
                  </div>
                </div>
                <button
                  onClick={() => handleApply(proposal.suggestion_id)}
                  disabled={processing === proposal.suggestion_id}
                  className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                >
                  {processing === proposal.suggestion_id ? 'Processing...' : 'Apply'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Medium/High Risk Proposals - Require Approval */}
      {mediumHighRiskProposals.length > 0 && (
        <div className="border rounded p-3 bg-yellow-50">
          <h4 className="font-medium mb-2 text-yellow-800">
            Medium/High-Risk Suggestions (Approval Required)
          </h4>
          <div className="space-y-2">
            {mediumHighRiskProposals.map(proposal => (
              <div key={proposal.suggestion_id} className="flex justify-between items-center p-2 bg-white rounded">
                <div>
                  <div className="font-medium">{proposal.adjustment_type}</div>
                  <div className="text-sm text-gray-500">
                    {proposal.current_value} → {proposal.proposed_value}
                    {' | '}
                    Confidence: {(proposal.confidence * 100).toFixed(0)}%
                    {' | '}
                    Risk: {(proposal.risk_score * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="space-x-2">
                  <button
                    onClick={() => handleApply(proposal.suggestion_id)}
                    disabled={processing === proposal.suggestion_id}
                    className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                  >
                    Apply
                  </button>
                  <button
                    onClick={() => handleReject(proposal.suggestion_id)}
                    disabled={processing === proposal.suggestion_id}
                    className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {proposals.length === 0 && (
        <div className="text-gray-500 text-center py-4">
          No pending suggestions. Click &quot;Run Learning&quot; to generate new proposals.
        </div>
      )}

      {/* Applied History */}
      {history.length > 0 && (
        <div className="border rounded p-3 bg-gray-50">
          <h4 className="font-medium mb-2">Applied History</h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {history.map((record, idx) => (
              <div key={idx} className="text-sm p-2 bg-white rounded">
                <div className="font-medium">{record.adjustment_type}</div>
                <div className="text-gray-500">
                  {record.previous_value} → {record.applied_value}
                  {' | '}
                  Mode: {record.mode}
                  {' | '}
                  {new Date(record.applied_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
