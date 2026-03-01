import { useEffect } from 'react';
import { useQualityOptimizer } from '../hooks/useQualityOptimizer';

interface QualityFirstOptimizerPanelProps {
  runId: string;
}

export function QualityFirstOptimizerPanel({ runId }: QualityFirstOptimizerPanelProps) {
  const {
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
    canApply,
    canReject,
    canFreeze,
    canRollback,
  } = useQualityOptimizer();

  useEffect(() => {
    fetchStatus();
    if (runId) {
      fetchProposals(runId);
    }
  }, [runId, fetchStatus, fetchProposals]);

  const handleApply = async () => {
    if (selectedProposal) {
      await applyProposal(selectedProposal.proposal_id);
    }
  };

  const handleReject = async () => {
    if (selectedProposal) {
      await rejectProposal(selectedProposal.proposal_id);
    }
  };

  const handleFreeze = async () => {
    if (selectedProposal) {
      await freezeProposal(selectedProposal.proposal_id);
    }
  };

  const handleRollback = async () => {
    if (selectedProposal) {
      await rollbackProposal(selectedProposal.proposal_id);
    }
  };

  const handleViewSnapshot = async () => {
    if (selectedProposal && selectedProposal.state === 'applied') {
      await fetchSnapshot(selectedProposal.proposal_id);
    }
  };

  const getStateBadgeColor = (state: string) => {
    switch (state) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'applied':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'frozen':
        return 'bg-blue-100 text-blue-800';
      case 'rolled_back':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getFeasibilityBadgeColor = (feasible: boolean) => {
    return feasible 
      ? 'bg-green-100 text-green-800' 
      : 'bg-red-100 text-red-800';
  };

  if (loading) {
    return (
      <div className="p-4 border rounded-lg bg-white shadow-sm" data-testid="quality-optimizer-loading">
        <h3 className="text-lg font-semibold mb-4">Quality-First Optimizer v25</h3>
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border rounded-lg bg-white shadow-sm" data-testid="quality-optimizer-error">
        <h3 className="text-lg font-semibold mb-4">Quality-First Optimizer v25</h3>
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="p-4 border rounded-lg bg-white shadow-sm" data-testid="quality-optimizer-panel">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Quality-First Optimizer v25</h3>
        {status && (
          <div className="text-sm text-gray-500">
            Total Proposals: {status.total_proposals}
          </div>
        )}
      </div>

      {/* Status Overview */}
      {status && (
        <div className="mb-4 p-3 bg-gray-50 rounded" data-testid="optimizer-status">
          <div className="text-sm text-gray-600 mb-2">Proposals by State:</div>
          <div className="flex gap-2 flex-wrap">
            <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
              Pending: {status.proposals_by_state.pending}
            </span>
            <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
              Applied: {status.proposals_by_state.applied}
            </span>
            <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs">
              Rejected: {status.proposals_by_state.rejected}
            </span>
            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
              Frozen: {status.proposals_by_state.frozen}
            </span>
            <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
              Rolled Back: {status.proposals_by_state.rolled_back}
            </span>
          </div>
        </div>
      )}

      {/* Proposals List */}
      <div className="mb-4">
        <h4 className="text-sm font-medium mb-2">Proposals for Run: {runId}</h4>
        {proposals.length === 0 ? (
          <div className="text-gray-500 text-sm" data-testid="no-proposals">
            No proposals found for this run.
          </div>
        ) : (
          <div className="space-y-2" data-testid="proposals-list">
            {proposals.map((proposal) => (
              <div
                key={proposal.proposal_id}
                onClick={() => selectProposal(proposal)}
                className={`p-3 border rounded cursor-pointer transition-colors ${
                  selectedProposal?.proposal_id === proposal.proposal_id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                data-testid={`proposal-item-${proposal.proposal_id}`}
              >
                <div className="flex justify-between items-start">
                  <div className="text-sm font-medium">
                    {proposal.proposal_id.slice(0, 8)}...
                  </div>
                  <div className="flex gap-1">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${getStateBadgeColor(
                        proposal.state
                      )}`}
                      data-testid={`proposal-state-${proposal.proposal_id}`}
                    >
                      {proposal.state}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${getFeasibilityBadgeColor(
                        proposal.feasibility_check_passed
                      )}`}
                      data-testid={`proposal-feasibility-${proposal.proposal_id}`}
                    >
                      {proposal.feasibility_check_passed ? 'Feasible' : 'Infeasible'}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  V1 Gain: +{proposal.estimated_v1_improvement.toFixed(1)} pts | 
                  Cost: {proposal.estimated_cost_delta_pct > 0 ? '+' : ''}
                  {proposal.estimated_cost_delta_pct.toFixed(1)}% | 
                  MTTC: {proposal.estimated_mttc_delta_pct > 0 ? '+' : ''}
                  {proposal.estimated_mttc_delta_pct.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Proposal Details */}
      {selectedProposal && (
        <div 
          className="mb-4 p-4 border rounded bg-gray-50" 
          data-testid="proposal-details"
        >
          <h4 className="text-sm font-medium mb-3">Proposal Details</h4>
          
          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
              <span className="text-gray-500">Proposal ID:</span>
              <div className="font-mono text-xs">{selectedProposal.proposal_id}</div>
            </div>
            <div>
              <span className="text-gray-500">Run ID:</span>
              <div className="font-mono text-xs">{selectedProposal.run_id}</div>
            </div>
            <div>
              <span className="text-gray-500">State:</span>
              <span className={`ml-2 px-2 py-0.5 rounded text-xs ${getStateBadgeColor(
                selectedProposal.state
              )}`}>
                {selectedProposal.state}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Quality Score:</span>
              <span className="ml-2 font-medium">{selectedProposal.quality_score.toFixed(1)}</span>
            </div>
          </div>

          {/* Impact Metrics */}
          <div className="mb-4 p-3 bg-white rounded border">
            <div className="text-xs font-medium text-gray-600 mb-2">Expected Impact</div>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <div className="text-gray-500 text-xs">V1 Improvement</div>
                <div className="font-medium text-green-600">
                  +{selectedProposal.estimated_v1_improvement.toFixed(1)} pts
                </div>
              </div>
              <div>
                <div className="text-gray-500 text-xs">Cost Impact</div>
                <div className={`font-medium ${
                  selectedProposal.estimated_cost_delta_pct <= 10 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {selectedProposal.estimated_cost_delta_pct > 0 ? '+' : ''}
                  {selectedProposal.estimated_cost_delta_pct.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-gray-500 text-xs">MTTC Impact</div>
                <div className={`font-medium ${
                  selectedProposal.estimated_mttc_delta_pct <= 10 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {selectedProposal.estimated_mttc_delta_pct > 0 ? '+' : ''}
                  {selectedProposal.estimated_mttc_delta_pct.toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Recommended Params */}
          <div className="mb-4">
            <div className="text-xs font-medium text-gray-600 mb-2">Recommended Parameters</div>
            <div className="p-2 bg-white rounded border font-mono text-xs" data-testid="recommended-params">
              {Object.entries(selectedProposal.recommended_params).map(([key, value]) => (
                <div key={key}>
                  {key}: {String(value)}
                </div>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 flex-wrap" data-testid="proposal-actions">
            <button
              onClick={handleApply}
              disabled={processing || !canApply(selectedProposal)}
              className={`px-4 py-2 rounded text-sm font-medium ${
                canApply(selectedProposal)
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              data-testid="apply-button"
            >
              {processing ? 'Processing...' : 'Apply'}
            </button>
            
            <button
              onClick={handleReject}
              disabled={processing || !canReject(selectedProposal)}
              className={`px-4 py-2 rounded text-sm font-medium ${
                canReject(selectedProposal)
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              data-testid="reject-button"
            >
              Reject
            </button>
            
            <button
              onClick={handleFreeze}
              disabled={processing || !canFreeze(selectedProposal)}
              className={`px-4 py-2 rounded text-sm font-medium ${
                canFreeze(selectedProposal)
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              data-testid="freeze-button"
            >
              Freeze
            </button>
            
            <button
              onClick={handleRollback}
              disabled={processing || !canRollback(selectedProposal)}
              className={`px-4 py-2 rounded text-sm font-medium ${
                canRollback(selectedProposal)
                  ? 'bg-orange-600 text-white hover:bg-orange-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              data-testid="rollback-button"
            >
              Rollback
            </button>
            
            {selectedProposal.state === 'applied' && (
              <button
                onClick={handleViewSnapshot}
                className="px-4 py-2 rounded text-sm font-medium bg-gray-200 text-gray-700 hover:bg-gray-300"
                data-testid="view-snapshot-button"
              >
                View Snapshot
              </button>
            )}
          </div>

          {/* Snapshot Display */}
          {snapshot && (
            <div className="mt-4 p-3 bg-white rounded border" data-testid="snapshot-display">
              <div className="text-xs font-medium text-gray-600 mb-2">
                Snapshot (for Rollback)
              </div>
              <div className="text-xs text-gray-500 mb-1">
                Applied at: {new Date(snapshot.applied_at).toLocaleString()}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-xs text-gray-500">Previous Params:</div>
                  <div className="font-mono text-xs bg-gray-100 p-1 rounded">
                    {Object.entries(snapshot.previous_params).map(([k, v]) => (
                      <div key={k}>{k}: {String(v)}</div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Applied Params:</div>
                  <div className="font-mono text-xs bg-gray-100 p-1 rounded">
                    {Object.entries(snapshot.applied_params).map(([k, v]) => (
                      <div key={k}>{k}: {String(v)}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Constraints Info */}
      <div className="mt-4 p-3 bg-blue-50 rounded text-xs text-gray-600">
        <div className="font-medium mb-1">Constraints (v25)</div>
        <div>Max Cost Increase: +10% | Max MTTC Increase: +10% | Max Incident Rate: 5%</div>
      </div>
    </div>
  );
}
