import React from 'react';
import { useOnboardingActivation, Proposal } from '../hooks/useOnboardingActivation';

interface OnboardingActivationPanelProps {
  brandId: string;
}

const RiskBadge: React.FC<{ level: Proposal['risk_level'] }> = ({ level }) => {
  const colors = {
    low: 'bg-green-100 text-green-800 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    high: 'bg-red-100 text-red-800 border-red-200',
  };

  const labels = {
    low: 'Low Risk (Auto)',
    medium: 'Medium Risk',
    high: 'High Risk',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colors[level]}`}>
      {labels[level]}
    </span>
  );
};

const StatusBadge: React.FC<{ status: Proposal['status'] }> = ({ status }) => {
  const colors = {
    pending: 'bg-gray-100 text-gray-600',
    applied: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
  };

  const labels = {
    pending: 'Pending',
    applied: 'Applied',
    rejected: 'Rejected',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>
      {labels[status]}
    </span>
  );
};

export const OnboardingActivationPanel: React.FC<OnboardingActivationPanelProps> = ({ brandId }) => {
  const {
    status,
    proposals,
    loading,
    error,
    runActivation,
    applyProposal,
    rejectProposal,
    freezeProposals,
    rollbackLast,
    refresh,
  } = useOnboardingActivation(brandId);

  if (loading && !status) {
    return (
      <section className="rounded-[1.5rem] border border-slate-200 bg-white/90 p-4 shadow-sm">
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
          <span className="ml-3 text-sm text-slate-600">Loading activation data...</span>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-[1.5rem] border border-red-200 bg-red-50/50 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-red-800">Error Loading Activation Data</h3>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
          <button
            onClick={refresh}
            className="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
          >
            Retry
          </button>
        </div>
      </section>
    );
  }

  const pendingProposals = proposals.filter((p) => p.status === 'pending');
  const appliedProposals = proposals.filter((p) => p.status === 'applied');

  return (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-end justify-between gap-3 mb-4">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Governança v31
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Onboarding Activation</h3>
        </div>
        <div className="flex items-center gap-2">
          {status?.frozen && (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              🥶 Frozen
            </span>
          )}
          <button
            onClick={refresh}
            disabled={loading}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Metrics Summary */}
      {status && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Completion Rate
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {(status.metrics.completion_rate * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-slate-500">Target: +15pp</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Template Conv.
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {(status.metrics.template_to_first_run_conversion * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-slate-500">Target: +20%</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Time to Action
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {Math.round(status.metrics.average_time_to_first_action_ms / 1000)}s
            </p>
            <p className="text-xs text-slate-500">Target: -20%</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Step 1 Dropoff
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {(status.metrics.step_1_dropoff_rate * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-slate-500">Target: -25%</p>
          </div>
        </div>
      )}

      {/* Top Frictions */}
      {status && status.top_frictions.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-slate-800 mb-2">Top Friction Points</h4>
          <div className="flex flex-wrap gap-2">
            {status.top_frictions.map((friction, idx) => (
              <div
                key={idx}
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs border ${
                  friction.severity === 'high'
                    ? 'bg-red-50 border-red-200 text-red-700'
                    : friction.severity === 'medium'
                    ? 'bg-yellow-50 border-yellow-200 text-yellow-700'
                    : 'bg-blue-50 border-blue-200 text-blue-700'
                }`}
              >
                <span className="font-medium">
                  {friction.step || friction.reason}
                </span>
                <span className="opacity-60">({friction.count})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={runActivation}
          disabled={loading || status?.frozen}
          className="rounded-lg bg-[var(--vm-primary)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:opacity-90"
        >
          {loading ? 'Running...' : 'Run Activation'}
        </button>
        <button
          onClick={freezeProposals}
          disabled={loading || status?.frozen}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
        >
          Freeze
        </button>
        <button
          onClick={rollbackLast}
          disabled={loading || appliedProposals.length === 0}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
        >
          Rollback
        </button>
      </div>

      {/* Pending Proposals */}
      {pendingProposals.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-slate-800 mb-2">
            Pending Proposals ({pendingProposals.length})
          </h4>
          <div className="space-y-2">
            {pendingProposals.map((proposal) => (
              <div
                key={proposal.id}
                className="rounded-xl border border-slate-200 bg-slate-50/50 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <RiskBadge level={proposal.risk_level} />
                      <StatusBadge status={proposal.status} />
                    </div>
                    <p className="text-sm font-medium text-slate-800">{proposal.description}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {proposal.rule_name} • {proposal.adjustment_percent > 0 ? '+' : ''}
                      {proposal.adjustment_percent}% adjustment
                    </p>
                    <p className="text-xs text-slate-600 mt-1 italic">
                      Expected: {proposal.expected_impact}
                    </p>
                  </div>
                  <div className="flex flex-col gap-1">
                    {proposal.risk_level === 'low' ? (
                      <span className="text-xs text-green-600 font-medium">Auto-applied</span>
                    ) : (
                      <>
                        <button
                          onClick={() => applyProposal(proposal.id)}
                          disabled={loading}
                          className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white disabled:opacity-50 hover:bg-green-700"
                        >
                          Apply
                        </button>
                        <button
                          onClick={() => rejectProposal(proposal.id, 'Not suitable')}
                          disabled={loading}
                          className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white disabled:opacity-50 hover:bg-red-700"
                        >
                          Reject
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Applied Proposals */}
      {appliedProposals.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-800 mb-2">
            Applied Proposals ({appliedProposals.length})
          </h4>
          <div className="space-y-2">
            {appliedProposals.slice(0, 3).map((proposal) => (
              <div
                key={proposal.id}
                className="rounded-xl border border-slate-200 bg-slate-50/30 p-3 opacity-70"
              >
                <div className="flex items-center gap-2">
                  <RiskBadge level={proposal.risk_level} />
                  <StatusBadge status={proposal.status} />
                  <span className="text-xs text-slate-500">{proposal.description}</span>
                </div>
              </div>
            ))}
            {appliedProposals.length > 3 && (
              <p className="text-xs text-slate-400 text-center">
                +{appliedProposals.length - 3} more applied
              </p>
            )}
          </div>
        </div>
      )}

      {proposals.length === 0 && !loading && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-4 text-center">
          <p className="text-sm text-slate-600">No proposals yet.</p>
          <p className="text-xs text-slate-400 mt-1">
            Click &quot;Run Activation&quot; to generate optimization proposals.
          </p>
        </div>
      )}
    </section>
  );
};

export default OnboardingActivationPanel;
