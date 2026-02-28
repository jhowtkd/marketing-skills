import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { fetchJson, postJson } from "../../../api/client";

export type AlertSeverity = "critical" | "warning" | "info";

export type Alert = {
  alert_id: string;
  severity: AlertSeverity;
  cause: string;
  recommendation: string;
  created_at: string;
  updated_at: string;
  playbook_chain_id?: string;
};

export type PlaybookExecutionResult = {
  status: "success" | "partial" | "failed";
  executed: string[];
  skipped: string[];
  errors?: Array<{ step: string; error: string }>;
  execution_id?: string;
};

export type AlertCounts = {
  total: number;
  critical: number;
  warning: number;
  info: number;
};

export type UseAlertsReturn = {
  alerts: Alert[];
  loading: boolean;
  error: string | null;
  executing: boolean;
  fetchAlerts: () => Promise<void>;
  refreshAlerts: () => Promise<void>;
  executePlaybookChain: (chainId: string, runId?: string) => Promise<PlaybookExecutionResult>;
  criticalAlerts: Alert[];
  hasAlerts: boolean;
  alertCounts: AlertCounts;
};

export function useAlerts(threadId: string | null): UseAlertsReturn {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const hasFetched = useRef(false);

  const fetchAlerts = useCallback(async () => {
    if (!threadId) {
      setAlerts([]);
      setError(null);
      hasFetched.current = false;
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetchJson<{ alerts: Alert[] }>(`/api/v2/threads/${threadId}/alerts`);
      setAlerts(response.alerts || []);
      hasFetched.current = true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch alerts";
      setError(message);
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  const refreshAlerts = useCallback(async () => {
    await fetchAlerts();
  }, [fetchAlerts]);

  const executePlaybookChain = useCallback(
    async (chainId: string, runId?: string): Promise<PlaybookExecutionResult> => {
      if (!threadId) {
        throw new Error("No active thread");
      }

      setExecuting(true);

      try {
        const payload: { chain_id: string; run_id?: string } = { chain_id: chainId };
        if (runId) {
          payload.run_id = runId;
        }

        const result = await postJson<PlaybookExecutionResult>(
          `/api/v2/threads/${threadId}/playbooks/execute`,
          payload,
          "playbook"
        );

        return result;
      } finally {
        setExecuting(false);
      }
    },
    [threadId]
  );

  // Auto-fetch on mount when threadId is provided
  useEffect(() => {
    if (threadId) {
      fetchAlerts();
    } else {
      setAlerts([]);
      setError(null);
      hasFetched.current = false;
    }
  }, [threadId]);

  // Computed values
  const criticalAlerts = useMemo(
    () => alerts.filter((alert) => alert.severity === "critical"),
    [alerts]
  );

  const hasAlerts = useMemo(() => alerts.length > 0, [alerts]);

  const alertCounts = useMemo(
    () => ({
      total: alerts.length,
      critical: alerts.filter((a) => a.severity === "critical").length,
      warning: alerts.filter((a) => a.severity === "warning").length,
      info: alerts.filter((a) => a.severity === "info").length,
    }),
    [alerts]
  );

  return {
    alerts,
    loading,
    error,
    executing,
    fetchAlerts,
    refreshAlerts,
    executePlaybookChain,
    criticalAlerts,
    hasAlerts,
    alertCounts,
  };
}
