import { useEffect, useState, useCallback } from "react";
import { WorkflowApi } from "../../api/typed-client";
import type { WorkflowRun } from "../../types/api";

type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "paused";

interface WorkflowStatusProps {
  runId: string;
  threadId?: string;
  onStatusChange?: (status: RunStatus) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

interface StatusInfo {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
  animate: boolean;
}

const STATUS_CONFIG: Record<RunStatus, StatusInfo> = {
  pending: {
    label: "Pending",
    color: "text-yellow-700",
    bgColor: "bg-yellow-100",
    icon: "⏳",
    animate: true,
  },
  running: {
    label: "Running",
    color: "text-blue-700",
    bgColor: "bg-blue-100",
    icon: "⚡",
    animate: true,
  },
  completed: {
    label: "Completed",
    color: "text-green-700",
    bgColor: "bg-green-100",
    icon: "✓",
    animate: false,
  },
  failed: {
    label: "Failed",
    color: "text-red-700",
    bgColor: "bg-red-100",
    icon: "✕",
    animate: false,
  },
  cancelled: {
    label: "Cancelled",
    color: "text-gray-700",
    bgColor: "bg-gray-100",
    icon: "⊘",
    animate: false,
  },
  paused: {
    label: "Paused",
    color: "text-orange-700",
    bgColor: "bg-orange-100",
    icon: "⏸",
    animate: false,
  },
};

const POLL_INTERVAL = 5000; // 5 seconds

export default function WorkflowStatus({
  runId,
  threadId,
  onStatusChange,
  onComplete,
  onError,
}: WorkflowStatusProps): JSX.Element {
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [status, setStatus] = useState<RunStatus>("pending");
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [isPolling, setIsPolling] = useState(true);

  const fetchStatus = useCallback(async () => {
    if (!runId) return;

    try {
      setError(null);
      const runData = await WorkflowApi.getRun(runId);

      if (runData && typeof runData === "object") {
        const workflowRun = runData as WorkflowRun;
        setRun(workflowRun);

        const newStatus = (workflowRun.status as RunStatus) || "pending";

        // Only update if status changed
        if (newStatus !== status) {
          setStatus(newStatus);
          onStatusChange?.(newStatus);

          // Trigger callbacks based on status
          if (newStatus === "completed") {
            onComplete?.();
          } else if (newStatus === "failed") {
            onError?.("Workflow run failed");
          }
        }
      }

      setLastUpdated(new Date());
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch status";
      setError(errorMessage);
      onError?.(errorMessage);
    }
  }, [runId, status, onStatusChange, onComplete, onError]);

  // Polling effect
  useEffect(() => {
    // Fetch immediately
    fetchStatus();

    if (!isPolling) return;

    // Check if status is terminal
    const isTerminal = ["completed", "failed", "cancelled"].includes(status);
    if (isTerminal) return;

    const interval = setInterval(fetchStatus, POLL_INTERVAL);

    return () => {
      clearInterval(interval);
    };
  }, [runId, isPolling, status, fetchStatus]);

  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;

  const handlePauseResume = () => {
    setIsPolling(!isPolling);
  };

  const handleRefresh = () => {
    fetchStatus();
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Status Icon with animation */}
          <span
            className={`flex h-10 w-10 items-center justify-center rounded-full text-lg ${config.bgColor} ${config.color} ${
              config.animate ? "animate-pulse" : ""
            }`}
          >
            {config.icon}
          </span>

          <div>
            <p className="font-medium text-slate-900">
              {config.label}
              {config.animate && (
                <span className="ml-2 inline-block h-2 w-2 animate-pulse rounded-full bg-current"></span>
              )}
            </p>
            <p className="text-sm text-slate-600">
              Run ID: <code className="text-xs">{runId.slice(0, 8)}...</code>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Last updated timestamp */}
          <span className="text-xs text-slate-500">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>

          {/* Refresh button */}
          <button
            onClick={handleRefresh}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            title="Refresh now"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>

          {/* Pause/Resume button */}
          <button
            onClick={handlePauseResume}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            title={isPolling ? "Pause updates" : "Resume updates"}
          >
            {isPolling ? (
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            ) : (
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Run details */}
      {run && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {run.requested_mode && (
              <div>
                <p className="text-xs font-medium text-slate-500">Mode</p>
                <p className="text-sm text-slate-900">{run.requested_mode}</p>
              </div>
            )}
            {run.request_text && (
              <div className="sm:col-span-2">
                <p className="text-xs font-medium text-slate-500">Request</p>
                <p className="line-clamp-2 text-sm text-slate-900">
                  {run.request_text}
                </p>
              </div>
            )}
            {run.created_at && (
              <div>
                <p className="text-xs font-medium text-slate-500">Started</p>
                <p className="text-sm text-slate-900">
                  {new Date(run.created_at).toLocaleString()}
                </p>
              </div>
            )}
            {run.objective_key && (
              <div>
                <p className="text-xs font-medium text-slate-500">Objective</p>
                <p className="text-sm text-slate-900">{run.objective_key}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mt-4 rounded bg-red-50 p-3">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Progress indicator */}
      {config.animate && (
        <div className="mt-4">
          <div className="h-1 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full ${config.bgColor.replace("bg-", "bg-")} animate-[loading_2s_ease-in-out_infinite]`}
              style={{
                width: "30%",
                backgroundColor: "currentColor",
              }}
            />
          </div>
          <style>{`
            @keyframes loading {
              0% { transform: translateX(-100%); }
              50% { transform: translateX(200%); }
              100% { transform: translateX(-100%); }
            }
          `}</style>
        </div>
      )}
    </div>
  );
}

// Hook for using workflow status
export function useWorkflowStatus(runId: string | null) {
  const [status, setStatus] = useState<RunStatus>("pending");
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!runId) return;

    let cancelled = false;
    let interval: ReturnType<typeof setInterval>;

    async function fetchStatus() {
      if (cancelled) return;
      setIsLoading(true);

      try {
        const runData = await WorkflowApi.getRun(runId);
        if (cancelled) return;

        if (runData && typeof runData === "object") {
          const workflowRun = runData as WorkflowRun;
          setRun(workflowRun);
          setStatus((workflowRun.status as RunStatus) || "pending");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to fetch status");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchStatus();

    // Only poll if not in terminal state
    const isTerminal = ["completed", "failed", "cancelled"].includes(status);
    if (!isTerminal) {
      interval = setInterval(fetchStatus, POLL_INTERVAL);
    }

    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [runId, status]);

  return { status, run, error, isLoading };
}
