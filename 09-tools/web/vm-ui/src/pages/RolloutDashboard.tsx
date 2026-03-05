/**
 * Rollout Dashboard Page
 * Main dashboard for managing experiment rollout policies
 */

import React, { useEffect, useState, useCallback } from "react";
import {
  fetchRolloutDashboard,
  approvePromotion,
  rejectPromotion,
  manualRollback,
  trackRolloutDashboardViewed,
  trackApprovalAction,
  type RolloutPolicy,
  type RolloutStatus,
} from "../api/rolloutDashboard";
import { StatusBadge } from "../components/rollout/StatusBadge";
import { ApprovalActions } from "../components/rollout/ApprovalActions";
import { ApprovalModal, type ApprovalAction } from "../components/rollout/ApprovalModal";
import { PolicyDetail } from "../components/rollout/PolicyDetail";

type ToastType = "success" | "error";

interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((type: ToastType, message: string) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, message }]);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, showToast, dismissToast };
}

const AUTO_REFRESH_INTERVAL = 30000; // 30 seconds

export function RolloutDashboard() {
  const [policies, setPolicies] = useState<RolloutPolicy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    action: ApprovalAction;
    policy: RolloutPolicy | null;
  }>({ isOpen: false, action: "approve", policy: null });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toasts, showToast, dismissToast } = useToast();

  // Fetch data
  const fetchData = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setIsRefreshing(true);
    
    try {
      const data = await fetchRolloutDashboard();
      setPolicies(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load rollout policies"
      );
    } finally {
      setIsLoading(false);
      if (showRefreshing) setIsRefreshing(false);
    }
  }, []);

  // Initial load and telemetry
  useEffect(() => {
    fetchData();
    trackRolloutDashboardViewed().catch(console.error);
  }, [fetchData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData(false);
    }, AUTO_REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRefresh = () => {
    fetchData(true);
  };

  const toggleRow = (experimentId: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(experimentId)) {
        next.delete(experimentId);
      } else {
        next.add(experimentId);
      }
      return next;
    });
  };

  const handleActionClick = (policy: RolloutPolicy, action: ApprovalAction) => {
    setModalState({ isOpen: true, action, policy });
  };

  const handleModalClose = () => {
    if (isSubmitting) return;
    setModalState({ isOpen: false, action: "approve", policy: null });
  };

  const handleModalSubmit = async (data: {
    operatorId: string;
    reason: string;
  }) => {
    if (!modalState.policy) return;

    setIsSubmitting(true);
    const { policy, action } = modalState;

    try {
      switch (action) {
        case "approve":
          await approvePromotion(
            policy.experiment_id,
            data.operatorId,
            data.reason,
            policy.active_variant || undefined
          );
          await trackApprovalAction("approved", policy.experiment_id, data.operatorId);
          showToast("success", `Promotion approved for ${policy.experiment_id}`);
          break;
        case "reject":
          await rejectPromotion(policy.experiment_id, data.operatorId, data.reason);
          await trackApprovalAction("rejected", policy.experiment_id, data.operatorId);
          showToast("success", `Promotion rejected for ${policy.experiment_id}`);
          break;
        case "rollback":
          await manualRollback(policy.experiment_id, data.operatorId, data.reason);
          await trackApprovalAction("rollback", policy.experiment_id, data.operatorId);
          showToast("success", `Rollback initiated for ${policy.experiment_id}`);
          break;
      }

      handleModalClose();
      // Refresh data after action
      fetchData();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Action failed";
      showToast("error", errorMessage);
      throw err; // Re-throw to show error in modal
    } finally {
      setIsSubmitting(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--vm-bg)] p-4 lg:p-6">
        <div className="mx-auto max-w-[1600px]">
          <div className="flex h-96 items-center justify-center">
            <div className="text-center">
              <div className="inline-flex items-center">
                <svg
                  className="h-8 w-8 animate-spin text-[var(--vm-primary)]"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              </div>
              <p className="mt-4 text-sm text-slate-500">Loading rollout policies...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-[var(--vm-bg)] p-4 lg:p-6">
        <div className="mx-auto max-w-[1600px]">
          <div className="rounded-2xl border border-red-200 bg-red-50 p-8">
            <h2 className="text-lg font-semibold text-red-800">
              Failed to Load Dashboard
            </h2>
            <p className="mt-2 text-sm text-red-700">{error}</p>
            <button
              onClick={handleRefresh}
              className="mt-4 rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--vm-bg)] p-4 lg:p-6">
      <div className="mx-auto max-w-[1600px]">
        {/* Header */}
        <header className="mb-6 rounded-2xl border border-[color:var(--vm-line)] bg-[color:var(--vm-surface)] p-4 shadow-[0_18px_45px_rgba(22,32,51,0.08)] lg:p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-[var(--vm-primary)]">
                Experiment Management
              </p>
              <h1 className="mt-2 font-serif text-3xl text-[var(--vm-ink)]">
                Rollout Dashboard
              </h1>
              <p className="mt-2 max-w-xl text-sm text-[var(--vm-muted)]">
                Monitor and manage experiment rollout policies. Review pending approvals,
                track metrics, and control promotion decisions.
              </p>
            </div>
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Refresh dashboard data"
            >
              <svg
                className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </header>

        {/* Empty state */}
        {policies.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 p-12 text-center">
            <svg
              className="mx-auto h-12 w-12 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h2 className="mt-4 text-lg font-semibold text-slate-900">
              No Experiments Found
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              There are no experiments with rollout policies configured yet.
            </p>
          </div>
        ) : (
          /* Table */
          <div className="overflow-hidden rounded-2xl border border-[color:var(--vm-line)] bg-[color:var(--vm-surface)] shadow-[0_18px_45px_rgba(22,32,51,0.08)]">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50/80">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 lg:px-6">
                      Experiment ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 lg:px-6">
                      Active Variant
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 lg:px-6">
                      Mode
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 lg:px-6">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 lg:px-6">
                      Last Evaluation
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 lg:px-6">
                      Actions
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 lg:px-6">
                      Details
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {policies.map((policy) => (
                    <React.Fragment key={policy.experiment_id}>
                      <tr className="hover:bg-slate-50/50">
                        <td className="px-4 py-4 lg:px-6">
                          <code className="rounded bg-slate-100 px-2 py-1 text-xs font-mono text-slate-700">
                            {policy.experiment_id}
                          </code>
                        </td>
                        <td className="px-4 py-4 lg:px-6">
                          {policy.active_variant ? (
                            <code className="rounded bg-slate-100 px-2 py-1 text-xs font-mono text-slate-700">
                              {policy.active_variant}
                            </code>
                          ) : (
                            <span className="text-sm text-slate-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-4 lg:px-6">
                          <span className="text-sm font-medium text-slate-700">
                            {policy.mode}
                          </span>
                        </td>
                        <td className="px-4 py-4 lg:px-6">
                          <StatusBadge status={policy.status} />
                        </td>
                        <td className="px-4 py-4 lg:px-6">
                          <span className="text-sm text-slate-600">
                            {policy.last_evaluation_at
                              ? new Date(
                                  policy.last_evaluation_at
                                ).toLocaleString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })
                              : "Never"}
                          </span>
                        </td>
                        <td className="px-4 py-4 lg:px-6">
                          <ApprovalActions
                            mode={policy.mode}
                            status={policy.status}
                            canRollback={policy.can_rollback}
                            onApprove={() =>
                              handleActionClick(policy, "approve")
                            }
                            onReject={() =>
                              handleActionClick(policy, "reject")
                            }
                            onRollback={() =>
                              handleActionClick(policy, "rollback")
                            }
                            disabled={isSubmitting}
                          />
                        </td>
                        <td className="px-4 py-4 text-center lg:px-6">
                          <button
                            onClick={() => toggleRow(policy.experiment_id)}
                            className="inline-flex items-center justify-center rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
                            aria-label={
                              expandedRows.has(policy.experiment_id)
                                ? "Hide details"
                                : "Show details"
                            }
                            aria-expanded={expandedRows.has(
                              policy.experiment_id
                            )}
                          >
                            <svg
                              className={`h-5 w-5 transition-transform ${
                                expandedRows.has(policy.experiment_id)
                                  ? "rotate-180"
                                  : ""
                              }`}
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M19 9l-7 7-7-7"
                              />
                            </svg>
                          </button>
                        </td>
                      </tr>
                      <tr>
                        <td colSpan={7} className="p-0">
                          <PolicyDetail
                            policy={policy}
                            isExpanded={expandedRows.has(policy.experiment_id)}
                          />
                        </td>
                      </tr>
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Approval Modal */}
      <ApprovalModal
        isOpen={modalState.isOpen}
        action={modalState.action}
        experimentId={modalState.policy?.experiment_id || ""}
        onClose={handleModalClose}
        onSubmit={handleModalSubmit}
        isSubmitting={isSubmitting}
      />

      {/* Toast Notifications */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-center gap-3 rounded-xl px-4 py-3 shadow-lg transition-all ${
              toast.type === "success"
                ? "bg-green-600 text-white"
                : "bg-red-600 text-white"
            }`}
            role="alert"
            aria-live="polite"
          >
            {toast.type === "success" ? (
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            )}
            <span className="text-sm font-medium">{toast.message}</span>
            <button
              onClick={() => dismissToast(toast.id)}
              className="ml-2 rounded p-1 hover:bg-white/20"
              aria-label="Dismiss notification"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RolloutDashboard;
