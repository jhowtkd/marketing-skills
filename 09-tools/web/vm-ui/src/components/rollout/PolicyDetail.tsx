/**
 * PolicyDetail Component
 * Expanded details for a rollout policy including metrics and timeline
 */

import type { RolloutPolicy } from "../../api/rolloutDashboard";

interface PolicyDetailProps {
  policy: RolloutPolicy;
  isExpanded: boolean;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDateShort(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

function getSuccessRateColor(rate: number): string {
  if (rate >= 0.95) return "text-green-600";
  if (rate >= 0.9) return "text-amber-600";
  return "text-red-600";
}

function getErrorRateColor(rate: number): string {
  if (rate <= 0.01) return "text-green-600";
  if (rate <= 0.05) return "text-amber-600";
  return "text-red-600";
}

export function PolicyDetail({ policy, isExpanded }: PolicyDetailProps) {
  if (!isExpanded) return null;

  // Get first 5 timeline events (most recent first in the array)
  const recentEvents = policy.timeline.slice(0, 5);

  return (
    <div className="border-t border-slate-200 bg-slate-50/50">
      <div 
        className="p-4 lg:p-6"
        role="region"
        aria-label={`Policy details for ${policy.experiment_id}`}
      >
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Policy Configuration */}
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
              Policy Configuration
            </h3>
            <div className="mt-3 space-y-2 rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Experiment ID</span>
                <span className="font-medium text-slate-900">{policy.experiment_id}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Active Variant</span>
                <span className="font-medium text-slate-900">
                  {policy.active_variant || "None"}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Mode</span>
                <span className="font-medium text-slate-900">{policy.mode}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Status</span>
                <span className="font-medium text-slate-900">
                  {formatStatus(policy.status)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Last Evaluation</span>
                <span className="font-medium text-slate-900">
                  {policy.last_evaluation_at ? formatDateShort(policy.last_evaluation_at) : "Never"}
                </span>
              </div>
            </div>

            {/* Promotion Criteria */}
            <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Promotion Criteria
              </h4>
              <div className="mt-3 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600">Min Evaluations</span>
                  <span className="font-medium text-slate-900">
                    {policy.promotion_criteria.min_evaluations}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600">Min Success Rate</span>
                  <span className="font-medium text-slate-900">
                    {(policy.promotion_criteria.min_success_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600">Max Error Rate</span>
                  <span className="font-medium text-slate-900">
                    {(policy.promotion_criteria.max_error_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Rollback Notice */}
            {policy.can_rollback && (
              <div className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
                <span className="font-medium">Rollback Available</span>
              </div>
            )}
          </div>

          {/* Current Metrics */}
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
              Current Metrics
            </h3>
            <div className="mt-3 space-y-2 rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Total Evaluations</span>
                <span className="font-medium text-slate-900">
                  {policy.metrics.total_evaluations.toLocaleString('en-US')}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Success Rate</span>
                <span className={`font-medium ${getSuccessRateColor(policy.metrics.success_rate)}`}>
                  {(policy.metrics.success_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Avg Latency</span>
                <span className="font-medium text-slate-900">
                  {Math.round(policy.metrics.avg_latency_ms)}ms
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Error Rate</span>
                <span className={`font-medium ${getErrorRateColor(policy.metrics.error_rate)}`}>
                  {(policy.metrics.error_rate * 100).toFixed(2)}%
                </span>
              </div>
            </div>
          </div>

          {/* Recent Events */}
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
              Recent Events
            </h3>
            <div className="mt-3 max-h-[250px] overflow-y-auto rounded-xl border border-slate-200 bg-white p-4">
              {recentEvents.length > 0 ? (
                <div className="space-y-3">
                  {recentEvents.map((event, index) => (
                    <div key={`${event.timestamp}-${index}`} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                      <p className="text-sm font-medium text-slate-900">{event.action}</p>
                      <p className="text-xs text-slate-500">{formatDate(event.timestamp)}</p>
                      {event.operator && (
                        <p className="text-xs text-slate-600">by {event.operator}</p>
                      )}
                      {event.reason && (
                        <p className="mt-1 text-xs text-slate-600 italic">&ldquo;{event.reason}&rdquo;</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 italic">No events recorded.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PolicyDetail;
