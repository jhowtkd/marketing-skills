import React from 'react';
import { useOnboardingExperiments, Experiment, EvaluationResult } from '../hooks/useOnboardingExperiments';

interface OnboardingExperimentPanelProps {
  brandId: string;
}

const StatusBadge: React.FC<{ status: Experiment['status'] }> = ({ status }) => {
  const colors = {
    draft: 'bg-gray-100 text-gray-600 border-gray-200',
    running: 'bg-green-100 text-green-700 border-green-200',
    paused: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    completed: 'bg-blue-100 text-blue-700 border-blue-200',
    rolled_back: 'bg-red-100 text-red-700 border-red-200',
  };

  const labels = {
    draft: 'Draft',
    running: 'Running',
    paused: 'Paused',
    completed: 'Completed',
    rolled_back: 'Rolled Back',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colors[status]}`}>
      {labels[status]}
    </span>
  );
};

const RiskBadge: React.FC<{ level: Experiment['risk_level'] }> = ({ level }) => {
  const colors = {
    low: 'bg-green-100 text-green-800 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    high: 'bg-red-100 text-red-800 border-red-200',
  };

  const labels = {
    low: 'Low Risk',
    medium: 'Medium Risk',
    high: 'High Risk',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colors[level]}`}>
      {labels[level]}
    </span>
  );
};

const DecisionBadge: React.FC<{ decision: string; requiresApproval: boolean }> = ({ 
  decision, 
  requiresApproval 
}) => {
  const colors: Record<string, string> = {
    auto_apply: 'bg-green-100 text-green-800 border-green-200',
    approve: 'bg-blue-100 text-blue-800 border-blue-200',
    continue: 'bg-gray-100 text-gray-600 border-gray-200',
    block: 'bg-red-100 text-red-800 border-red-200',
    rollback: 'bg-orange-100 text-orange-800 border-orange-200',
  };

  const labels: Record<string, string> = {
    auto_apply: 'Auto-Apply',
    approve: 'Needs Approval',
    continue: 'Continue',
    block: 'Blocked',
    rollback: 'Rollback',
  };

  return (
    <div className="flex items-center gap-1">
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colors[decision] || colors.continue}`}>
        {labels[decision] || decision}
      </span>
      {requiresApproval && (
        <span className="text-xs text-amber-600" title="Requires human approval">👤</span>
      )}
    </div>
  );
};

export const OnboardingExperimentPanel: React.FC<OnboardingExperimentPanelProps> = ({ brandId }) => {
  const {
    status,
    experiments,
    evaluations,
    loading,
    error,
    runEvaluation,
    startExperiment,
    pauseExperiment,
    promoteExperiment,
    rollbackExperiment,
    refresh,
  } = useOnboardingExperiments(brandId);

  if (loading && !status) {
    return (
      <section className="rounded-[1.5rem] border border-slate-200 bg-white/90 p-4 shadow-sm">
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
          <span className="ml-3 text-sm text-slate-600">Loading experiments...</span>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-[1.5rem] border border-red-200 bg-red-50/50 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-red-800">Error Loading Experiments</h3>
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

  const runningExperiments = experiments.filter((e) => e.status === 'running');
  const draftExperiments = experiments.filter((e) => e.status === 'draft');
  const completedExperiments = experiments.filter((e) => e.status === 'completed');

  return (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-end justify-between gap-3 mb-4">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Governança v32
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Onboarding Experiments</h3>
        </div>
        <div className="flex items-center gap-2">
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
              Total Experiments
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {status.metrics.total_experiments}
            </p>
            <p className="text-xs text-slate-500">{status.metrics.running_experiments} running</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Assignments Today
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {status.metrics.assignments_today}
            </p>
            <p className="text-xs text-slate-500">User allocations</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Auto-Applied
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {status.metrics.promotions_auto}
            </p>
            <p className="text-xs text-slate-500">Low risk promotions</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Blocked/Rollbacks
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {status.metrics.promotions_blocked + status.metrics.rollbacks}
            </p>
            <p className="text-xs text-slate-500">Guardrail actions</p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={runEvaluation}
          disabled={loading}
          className="rounded-lg bg-[var(--vm-primary)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:opacity-90"
        >
          {loading ? 'Running...' : 'Run Weekly Evaluation'}
        </button>
      </div>

      {/* Evaluations */}
      {evaluations.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-slate-800 mb-2">
            Latest Evaluations
          </h4>
          <div className="space-y-2">
            {evaluations.slice(0, 3).map((evalItem, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-slate-200 bg-slate-50/50 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <DecisionBadge 
                        decision={evalItem.decision} 
                        requiresApproval={evalItem.requires_approval} 
                      />
                      {evalItem.is_significant ? (
                        <span className="text-xs text-green-600 font-medium">✓ Significant</span>
                      ) : (
                        <span className="text-xs text-gray-500">Not significant</span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-slate-800">
                      {evalItem.experiment_id}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Sample: {evalItem.sample_size} • 
                      Lift: {(evalItem.relative_lift * 100).toFixed(1)}% • 
                      Confidence: {(evalItem.confidence * 100).toFixed(0)}%
                    </p>
                    {evalItem.reason && (
                      <p className="text-xs text-slate-600 mt-1 italic">
                        {evalItem.reason}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Running Experiments */}
      {runningExperiments.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-slate-800 mb-2">
            Running Experiments ({runningExperiments.length})
          </h4>
          <div className="space-y-2">
            {runningExperiments.map((experiment) => (
              <div
                key={experiment.experiment_id}
                className="rounded-xl border border-slate-200 bg-slate-50/50 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={experiment.status} />
                      <RiskBadge level={experiment.risk_level} />
                    </div>
                    <p className="text-sm font-medium text-slate-800">{experiment.name}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {experiment.experiment_id} • {experiment.primary_metric}
                    </p>
                    <p className="text-xs text-slate-600 mt-1 italic">
                      {experiment.hypothesis}
                    </p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {experiment.variants.map((variant) => (
                        <span
                          key={variant.variant_id}
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-600"
                        >
                          {variant.name} ({variant.traffic_allocation}%)
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => pauseExperiment(experiment.experiment_id, 'Manual pause')}
                      disabled={loading}
                      className="rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
                    >
                      Pause
                    </button>
                    {experiment.risk_level === 'low' && (
                      <button
                        onClick={() => promoteExperiment(experiment.experiment_id, experiment.variants[1]?.variant_id || 'treatment', true)}
                        disabled={loading}
                        className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white disabled:opacity-50 hover:bg-green-700"
                      >
                        Auto-Promote
                      </button>
                    )}
                    {experiment.risk_level !== 'low' && (
                      <button
                        onClick={() => promoteExperiment(experiment.experiment_id, experiment.variants[1]?.variant_id || 'treatment', false)}
                        disabled={loading}
                        className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white disabled:opacity-50 hover:bg-blue-700"
                      >
                        Request Approval
                      </button>
                    )}
                    <button
                      onClick={() => rollbackExperiment(experiment.experiment_id, 'Manual rollback')}
                      disabled={loading}
                      className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white disabled:opacity-50 hover:bg-red-700"
                    >
                      Rollback
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Draft Experiments */}
      {draftExperiments.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-slate-800 mb-2">
            Draft Experiments ({draftExperiments.length})
          </h4>
          <div className="space-y-2">
            {draftExperiments.map((experiment) => (
              <div
                key={experiment.experiment_id}
                className="rounded-xl border border-slate-200 bg-slate-50/30 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={experiment.status} />
                      <RiskBadge level={experiment.risk_level} />
                    </div>
                    <p className="text-sm font-medium text-slate-800">{experiment.name}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Min sample: {experiment.min_sample_size} • 
                      Confidence: {(experiment.min_confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <button
                    onClick={() => startExperiment(experiment.experiment_id)}
                    disabled={loading}
                    className="rounded bg-[var(--vm-primary)] px-3 py-1 text-xs font-medium text-white disabled:opacity-50 hover:opacity-90"
                  >
                    Start
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Completed Experiments */}
      {completedExperiments.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-800 mb-2">
            Completed ({completedExperiments.length})
          </h4>
          <div className="space-y-2">
            {completedExperiments.slice(0, 3).map((experiment) => (
              <div
                key={experiment.experiment_id}
                className="rounded-xl border border-slate-200 bg-slate-50/30 p-3 opacity-70"
              >
                <div className="flex items-center gap-2">
                  <StatusBadge status={experiment.status} />
                  <span className="text-xs text-slate-500">{experiment.name}</span>
                </div>
              </div>
            ))}
            {completedExperiments.length > 3 && (
              <p className="text-xs text-slate-400 text-center">
                +{completedExperiments.length - 3} more completed
              </p>
            )}
          </div>
        </div>
      )}

      {experiments.length === 0 && !loading && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-4 text-center">
          <p className="text-sm text-slate-600">No experiments yet.</p>
          <p className="text-xs text-slate-400 mt-1">
            Create experiments to start A/B testing onboarding variations.
          </p>
        </div>
      )}
    </section>
  );
};

export default OnboardingExperimentPanel;
