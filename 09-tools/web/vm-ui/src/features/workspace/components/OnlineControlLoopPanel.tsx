import React from 'react';
import { useOnlineControlLoop, Proposal, Regression } from '../hooks/useOnlineControlLoop';

interface OnlineControlLoopPanelProps {
  brandId: string;
}

export function OnlineControlLoopPanel({ brandId }: OnlineControlLoopPanelProps) {
  const {
    status,
    proposals,
    regressions,
    loading,
    error,
    processing,
    fetchStatus,
    startCycle,
    applyProposal,
    rejectProposal,
    freezeControlLoop,
    rollbackControlLoop,
    canApply,
    canReject,
    canFreeze,
    canRollback,
  } = useOnlineControlLoop();

  React.useEffect(() => {
    fetchStatus(brandId);
  }, [brandId, fetchStatus]);

  const handleRunCycle = async () => {
    await startCycle(brandId);
  };

  const handleApply = async (proposalId: string) => {
    await applyProposal(brandId, proposalId);
  };

  const handleReject = async (proposalId: string) => {
    await rejectProposal(brandId, proposalId);
  };

  const handleFreeze = async () => {
    await freezeControlLoop(brandId);
  };

  const handleRollback = async (proposalId: string) => {
    await rollbackControlLoop(brandId, proposalId);
  };

  if (loading) {
    return (
      <div data-testid="control-loop-loading" className="p-4 border rounded">
        <div className="flex items-center space-x-2">
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border rounded bg-red-50">
        <p className="text-red-600">{error}</p>
        <button
          onClick={() => fetchStatus(brandId)}
          className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    );
  }

  const getStateDisplay = (state: string) => {
    const stateClasses: Record<string, string> = {
      idle: 'text-gray-600',
      observing: 'text-blue-600',
      detecting: 'text-yellow-600',
      proposing: 'text-purple-600',
      applying: 'text-orange-600',
      verifying: 'text-indigo-600',
      completed: 'text-green-600',
      blocked: 'text-red-600',
      frozen: 'text-cyan-600',
    };
    return stateClasses[state] || 'text-gray-600';
  };

  return (
    <div className="p-4 border rounded bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h2 className="text-lg font-semibold">Online Control Loop v26</h2>
          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
            {status?.version || 'v26'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`text-sm font-medium ${getStateDisplay(status?.state || 'idle')}`}>
            Status: {status?.state ? status.state.charAt(0).toUpperCase() + status.state.slice(1) : 'Idle'}
          </span>
        </div>
      </div>

      {/* Cycle Info */}
      {status?.cycle_id && (
        <div className="mb-4 p-2 bg-gray-50 rounded">
          <p className="text-sm text-gray-600">Cycle: {status.cycle_id}</p>
        </div>
      )}

      {/* State-specific Messages */}
      {status?.state === 'idle' && (
        <div className="mb-4 p-3 bg-gray-50 rounded">
          <p className="text-sm text-gray-600">No active cycle</p>
        </div>
      )}

      {status?.state === 'frozen' && (
        <div className="mb-4 p-3 bg-cyan-50 border border-cyan-200 rounded">
          <p className="text-sm text-cyan-700">Control loop is frozen</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex space-x-2 mb-4">
        {status?.state === 'idle' && (
          <button
            onClick={handleRunCycle}
            disabled={processing}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing ? 'Starting...' : 'Run Control Loop'}
          </button>
        )}
        
        <button
          onClick={handleFreeze}
          disabled={processing || !canFreeze()}
          className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Freeze
        </button>

        <button
          onClick={() => fetchStatus(brandId)}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Refresh
        </button>
      </div>

      {/* Active Regressions */}
      <div className="mb-4">
        <h3 className="text-sm font-medium mb-2">Active Regressions</h3>
        {regressions.length === 0 ? (
          <p className="text-sm text-gray-500">No active regressions</p>
        ) : (
          <div className="space-y-2">
            {regressions.map((regression, idx) => (
              <div key={idx} className="p-2 bg-red-50 border border-red-200 rounded">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{regression.metric}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    regression.severity === 'critical' ? 'bg-red-100 text-red-700' :
                    regression.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                    regression.severity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {regression.severity}
                  </span>
                </div>
                <p className="text-sm text-gray-600">
                  Delta: {regression.delta_pct > 0 ? '+' : ''}{regression.delta_pct.toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Proposals */}
      <div className="mb-4">
        <h3 className="text-sm font-medium mb-2">Proposals ({proposals.length})</h3>
        {proposals.length === 0 ? (
          <p className="text-sm text-gray-500">No active proposals</p>
        ) : (
          <div className="space-y-2">
            {proposals.map((proposal) => (
              <ProposalCard
                key={proposal.proposal_id}
                proposal={proposal}
                onApply={() => handleApply(proposal.proposal_id)}
                onReject={() => handleReject(proposal.proposal_id)}
                onRollback={() => handleRollback(proposal.proposal_id)}
                canApply={canApply(proposal)}
                canReject={canReject(proposal)}
                canRollback={canRollback(proposal)}
                processing={processing}
              />
            ))}
          </div>
        )}
      </div>

      {/* Metrics */}
      <div className="mt-4 pt-4 border-t">
        <h3 className="text-sm font-medium mb-2">Performance</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-500">Time to Detect</p>
            <p className="text-sm font-medium">4 min avg</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Time to Mitigate</p>
            <p className="text-sm font-medium">15 min avg</p>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ProposalCardProps {
  proposal: Proposal;
  onApply: () => void;
  onReject: () => void;
  onRollback: () => void;
  canApply: boolean;
  canReject: boolean;
  canRollback: boolean;
  processing: boolean;
}

function ProposalCard({
  proposal,
  onApply,
  onReject,
  onRollback,
  canApply,
  canReject,
  canRollback,
  processing,
}: ProposalCardProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-700';
      case 'medium': return 'bg-yellow-100 text-yellow-700';
      case 'low': return 'bg-green-100 text-green-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="p-3 border rounded bg-gray-50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="font-medium text-sm">{proposal.adjustment_type}</span>
          <span className={`text-xs px-2 py-0.5 rounded ${getSeverityColor(proposal.severity)}`}>
            {proposal.severity}
          </span>
        </div>
        <span className="text-xs text-gray-500">{proposal.state}</span>
      </div>
      
      <p className="text-sm text-gray-600 mb-1">
        {proposal.target_gate}: {proposal.current_value} → {proposal.proposed_value}
        <span className="text-gray-500"> ({proposal.delta > 0 ? '+' : ''}{proposal.delta})</span>
      </p>
      
      {proposal.requires_approval && proposal.state === 'pending' && (
        <p className="text-xs text-orange-600 mb-2">Requires Approval</p>
      )}

      <div className="flex space-x-2 mt-2">
        {canApply && (
          <button
            onClick={onApply}
            disabled={processing}
            className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            Apply
          </button>
        )}
        
        {canReject && (
          <button
            onClick={onReject}
            disabled={processing}
            className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
          >
            Reject
          </button>
        )}
        
        {canRollback && (
          <button
            onClick={onRollback}
            disabled={processing}
            className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50"
          >
            Rollback
          </button>
        )}
      </div>
    </div>
  );
}
