import React from 'react';
import { usePredictiveResilience, MitigationProposal, PredictiveSignal } from '../hooks/usePredictiveResilience';

interface PredictiveResiliencePanelProps {
  brandId: string;
}

export function PredictiveResiliencePanel({ brandId }: PredictiveResiliencePanelProps) {
  const {
    status,
    proposals,
    signals,
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
    canApply,
    canReject,
    canFreeze,
    canUnfreeze,
    canRollback,
    getRiskClassColor,
    getSeverityColor,
  } = usePredictiveResilience();

  React.useEffect(() => {
    fetchStatus(brandId);
  }, [brandId, fetchStatus]);

  const handleRunCycle = async () => {
    await runCycle(brandId);
  };

  const handleApply = async (proposalId: string) => {
    await applyProposal(brandId, proposalId);
  };

  const handleReject = async (proposalId: string) => {
    await rejectProposal(brandId, proposalId);
  };

  const handleFreeze = async () => {
    await freezeBrand(brandId);
  };

  const handleUnfreeze = async () => {
    await unfreezeBrand(brandId);
  };

  const handleRollback = async (proposalId: string) => {
    await rollbackProposal(brandId, proposalId);
  };

  if (loading) {
    return (
      <div data-testid="predictive-resilience-loading" className="p-4 border rounded">
        <div className="flex items-center space-x-2">
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
          <span>Loading Predictive Resilience...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="predictive-resilience-error" className="p-4 border rounded bg-red-50">
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

  const score = status?.resilience_score;

  return (
    <div data-testid="predictive-resilience-panel" className="p-4 border rounded bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h2 className="text-lg font-semibold">Predictive Resilience v27</h2>
          <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">
            {status?.version || 'v27'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span
            data-testid="resilience-state"
            className={`px-2 py-0.5 text-xs rounded ${
              status?.state === 'frozen'
                ? 'bg-red-100 text-red-700'
                : 'bg-green-100 text-green-700'
            }`}
          >
            {status?.state || 'idle'}
          </span>
          {processing && (
            <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
          )}
        </div>
      </div>

      {/* Resilience Score */}
      {score && (
        <div data-testid="resilience-score" className="mb-4 p-3 bg-gray-50 rounded">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Composite Score</span>
            <span
              data-testid="risk-class-badge"
              className={`px-2 py-0.5 text-xs rounded font-medium ${getRiskClassColor(score.risk_class)}`}
            >
              {score.risk_class.toUpperCase()}
            </span>
          </div>
          <div data-testid="composite-score" className="text-2xl font-bold mb-2">
            {(score.composite_score * 100).toFixed(1)}%
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div data-testid="incident-component" className="text-center p-1 bg-white rounded">
              <div className="text-gray-500">Incident</div>
              <div className="font-medium">{(score.incident_component * 100).toFixed(0)}%</div>
            </div>
            <div data-testid="handoff-component" className="text-center p-1 bg-white rounded">
              <div className="text-gray-500">Handoff</div>
              <div className="font-medium">{(score.handoff_component * 100).toFixed(0)}%</div>
            </div>
            <div data-testid="approval-component" className="text-center p-1 bg-white rounded">
              <div className="text-gray-500">Approval</div>
              <div className="font-medium">{(score.approval_component * 100).toFixed(0)}%</div>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        <div data-testid="stat-cycles" className="text-center p-2 bg-gray-50 rounded">
          <div className="text-lg font-semibold">{status?.cycles_total || 0}</div>
          <div className="text-xs text-gray-500">Cycles</div>
        </div>
        <div data-testid="stat-proposals" className="text-center p-2 bg-gray-50 rounded">
          <div className="text-lg font-semibold">{status?.proposals_total || 0}</div>
          <div className="text-xs text-gray-500">Proposals</div>
        </div>
        <div data-testid="stat-applied" className="text-center p-2 bg-green-50 rounded">
          <div className="text-lg font-semibold text-green-600">{status?.proposals_applied || 0}</div>
          <div className="text-xs text-gray-500">Applied</div>
        </div>
        <div data-testid="stat-false-positives" className="text-center p-2 bg-yellow-50 rounded">
          <div className="text-lg font-semibold text-yellow-600">{status?.false_positives_total || 0}</div>
          <div className="text-xs text-gray-500">False Pos</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex space-x-2 mb-4">
        <button
          data-testid="run-cycle-button"
          onClick={handleRunCycle}
          disabled={processing || status?.state === 'frozen'}
          className="flex-1 px-3 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
        >
          Run Cycle
        </button>
        {canFreeze() && (
          <button
            data-testid="freeze-button"
            onClick={handleFreeze}
            disabled={processing}
            className="px-3 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-300"
          >
            Freeze
          </button>
        )}
        {canUnfreeze() && (
          <button
            data-testid="unfreeze-button"
            onClick={handleUnfreeze}
            disabled={processing}
            className="px-3 py-2 text-sm bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300"
          >
            Unfreeze
          </button>
        )}
      </div>

      {/* Active Signals */}
      {signals.length > 0 && (
        <div data-testid="signals-section" className="mb-4">
          <h3 className="text-sm font-medium mb-2">Active Signals ({signals.length})</h3>
          <div className="space-y-2">
            {signals.map((signal) => (
              <SignalCard key={signal.signal_id} signal={signal} getSeverityColor={getSeverityColor} />
            ))}
          </div>
        </div>
      )}

      {/* Proposals */}
      {proposals.length > 0 && (
        <div data-testid="proposals-section">
          <h3 className="text-sm font-medium mb-2">
            Pending Proposals ({proposals.filter(p => p.state === 'pending').length})
          </h3>
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
                getSeverityColor={getSeverityColor}
              />
            ))}
          </div>
        </div>
      )}

      {proposals.length === 0 && signals.length === 0 && (
        <div data-testid="empty-state" className="text-center py-8 text-gray-500">
          No active signals or proposals
        </div>
      )}
    </div>
  );
}

interface SignalCardProps {
  signal: PredictiveSignal;
  getSeverityColor: (severity: string) => string;
}

function SignalCard({ signal, getSeverityColor }: SignalCardProps) {
  return (
    <div data-testid={`signal-card-${signal.signal_id}`} className="p-2 bg-yellow-50 rounded border border-yellow-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span data-testid="signal-metric" className="text-sm font-medium">{signal.metric_name}</span>
          <span
            data-testid="signal-severity"
            className={`text-xs px-1.5 py-0.5 rounded ${getSeverityColor(signal.severity)} bg-white`}
          >
            {signal.severity}
          </span>
        </div>
        <div data-testid="signal-confidence" className="text-xs text-gray-500">
          {(signal.confidence * 100).toFixed(0)}% confidence
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-600">
        Current: {signal.current_value.toFixed(3)} → Predicted: {signal.predicted_value.toFixed(3)}
        <span data-testid="signal-delta" className="ml-2 text-red-600">
          (+{(signal.delta_pct * 100).toFixed(1)}%)
        </span>
      </div>
    </div>
  );
}

interface ProposalCardProps {
  proposal: MitigationProposal;
  onApply: () => void;
  onReject: () => void;
  onRollback: () => void;
  canApply: boolean;
  canReject: boolean;
  canRollback: boolean;
  getSeverityColor: (severity: string) => string;
}

function ProposalCard({
  proposal,
  onApply,
  onReject,
  onRollback,
  canApply,
  canReject,
  canRollback,
  getSeverityColor,
}: ProposalCardProps) {
  const stateColors: Record<string, string> = {
    pending: 'bg-yellow-50 border-yellow-200',
    applied: 'bg-green-50 border-green-200',
    rejected: 'bg-gray-50 border-gray-200',
    rolled_back: 'bg-red-50 border-red-200',
  };

  return (
    <div
      data-testid={`proposal-card-${proposal.proposal_id}`}
      className={`p-3 rounded border ${stateColors[proposal.state] || 'bg-white border-gray-200'}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span data-testid="proposal-type" className="text-sm font-medium">
            {proposal.mitigation_type}
          </span>
          <span
            data-testid="proposal-severity"
            className={`text-xs px-1.5 py-0.5 rounded ${getSeverityColor(proposal.severity)} bg-white`}
          >
            {proposal.severity}
          </span>
          {proposal.can_auto_apply && (
            <span data-testid="proposal-auto-apply" className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
              Auto
            </span>
          )}
        </div>
        <span
          data-testid="proposal-state"
          className={`text-xs px-1.5 py-0.5 rounded ${
            proposal.state === 'applied'
              ? 'bg-green-100 text-green-700'
              : proposal.state === 'pending'
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          {proposal.state}
        </span>
      </div>

      <p data-testid="proposal-description" className="text-xs text-gray-600 mb-2">
        {proposal.description}
      </p>

      {proposal.estimated_impact && Object.keys(proposal.estimated_impact).length > 0 && (
        <div data-testid="proposal-impact" className="text-xs text-gray-500 mb-2">
          Impact:{' '}
          {Object.entries(proposal.estimated_impact)
            .map(([key, value]) => `${key}: ${value > 0 ? '+' : ''}${(value * 100).toFixed(1)}%`)
            .join(', ')}
        </div>
      )}

      {proposal.state === 'pending' && (
        <div className="flex space-x-2 mt-2">
          {canApply && (
            <button
              data-testid="apply-button"
              onClick={onApply}
              className="flex-1 px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600"
            >
              Apply
            </button>
          )}
          {canReject && (
            <button
              data-testid="reject-button"
              onClick={onReject}
              className="flex-1 px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
            >
              Reject
            </button>
          )}
          {!canApply && proposal.severity !== 'low' && (
            <span data-testid="requires-approval" className="text-xs text-orange-600 italic">
              Requires approval
            </span>
          )}
        </div>
      )}

      {proposal.state === 'applied' && canRollback && (
        <button
          data-testid="rollback-button"
          onClick={onRollback}
          className="mt-2 px-2 py-1 text-xs bg-orange-500 text-white rounded hover:bg-orange-600"
        >
          Rollback
        </button>
      )}

      {proposal.rejection_reason && (
        <p data-testid="rejection-reason" className="mt-2 text-xs text-red-600">
          Reason: {proposal.rejection_reason}
        </p>
      )}
    </div>
  );
}
