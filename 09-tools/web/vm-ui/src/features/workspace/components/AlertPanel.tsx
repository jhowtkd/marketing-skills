import { useState } from "react";
import type { Alert, AlertSeverity, PlaybookExecutionResult } from "../hooks/useAlerts";

export type AlertPanelProps = {
  alerts: Alert[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onExecutePlaybook: (chainId: string, runId?: string) => Promise<PlaybookExecutionResult>;
  onDismissAlert?: (alertId: string) => void;
};

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getSeverityClasses(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "border-red-500 bg-red-50 dark:bg-red-900/20";
    case "warning":
      return "border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20";
    case "info":
      return "border-blue-500 bg-blue-50 dark:bg-blue-900/20";
    default:
      return "border-gray-300 bg-gray-50";
  }
}

function getSeverityBadgeClasses(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100";
    case "warning":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100";
    case "info":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

function getSeverityLabel(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "Crítico";
    case "warning":
      return "Aviso";
    case "info":
      return "Info";
    default:
      return severity;
  }
}

export function AlertPanel({
  alerts,
  loading,
  error,
  onRefresh,
  onExecutePlaybook,
  onDismissAlert,
}: AlertPanelProps) {
  const [executingAlertId, setExecutingAlertId] = useState<string | null>(null);
  const [executionFeedback, setExecutionFeedback] = useState<
    Record<string, { success: boolean; message: string; details?: string }>
  >({});

  const handleExecutePlaybook = async (alert: Alert) => {
    if (!alert.playbook_chain_id) return;

    setExecutingAlertId(alert.alert_id);
    setExecutionFeedback((prev) => ({
      ...prev,
      [alert.alert_id]: { success: true, message: "" },
    }));

    try {
      const result = await onExecutePlaybook(alert.playbook_chain_id);

      if (result.errors && result.errors.length > 0) {
        setExecutionFeedback((prev) => ({
          ...prev,
          [alert.alert_id]: {
            success: false,
            message: "Erros durante a execução",
            details: result.errors?.map((e) => e.error).join(", "),
          },
        }));
      } else {
        setExecutionFeedback((prev) => ({
          ...prev,
          [alert.alert_id]: {
            success: true,
            message: `Executado com sucesso - ${result.executed.length} passos executados`,
          },
        }));
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro desconhecido";
      setExecutionFeedback((prev) => ({
        ...prev,
        [alert.alert_id]: {
          success: false,
          message: "Falha na execução",
          details: errorMessage,
        },
      }));
    } finally {
      setExecutingAlertId(null);
    }
  };

  const handleDismiss = (alertId: string) => {
    onDismissAlert?.(alertId);
  };

  // Alert counts
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const warningCount = alerts.filter((a) => a.severity === "warning").length;
  const infoCount = alerts.filter((a) => a.severity === "info").length;

  // Loading state
  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Carregando...</span>
          <button
            data-testid="alerts-refresh-btn"
            onClick={onRefresh}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed rounded-lg"
          >
            Atualizar
          </button>
        </div>
        <div data-testid="alerts-loading" className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent mb-3" />
          <p className="text-gray-600 dark:text-gray-400">Carregando alertas...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div data-testid="alerts-error" className="p-6">
        <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-4 mb-4">
          <p className="text-red-800 dark:text-red-200 font-medium">Erro ao carregar alertas</p>
          <p className="text-red-600 dark:text-red-300 text-sm mt-1">{error}</p>
        </div>
        <button
          data-testid="alerts-refresh-btn"
          onClick={onRefresh}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg transition-colors"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  // Empty state
  if (alerts.length === 0) {
    return (
      <div data-testid="alerts-empty" className="p-6 text-center">
        <div className="text-5xl mb-3">✅</div>
        <p className="text-gray-600 dark:text-gray-400 mb-4">Nenhum alerta ativo</p>
        <button
          data-testid="alerts-refresh-btn"
          onClick={onRefresh}
          disabled={loading}
          className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:bg-gray-100 text-gray-800 dark:text-gray-200 rounded-lg transition-colors"
        >
          Atualizar
        </button>
      </div>
    );
  }

  // Alerts list
  return (
    <div className="p-4">
      {/* Header with summary */}
      <div className="flex items-center justify-between mb-4">
        <div data-testid="alerts-summary" className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {alerts.length} alerta{alerts.length !== 1 ? "s" : ""}
          </span>
          {criticalCount > 0 && (
            <span className="text-xs px-2 py-1 bg-red-100 text-red-800 rounded-full">
              {criticalCount} crítico{criticalCount !== 1 ? "s" : ""}
            </span>
          )}
          {warningCount > 0 && (
            <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full">
              {warningCount} warning
            </span>
          )}
          {infoCount > 0 && (
            <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded-full">
              {infoCount} info
            </span>
          )}
        </div>
        <button
          data-testid="alerts-refresh-btn"
          onClick={onRefresh}
          disabled={loading}
          className="px-3 py-1.5 text-sm bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:bg-gray-100 text-gray-800 dark:text-gray-200 rounded-lg transition-colors"
        >
          Atualizar
        </button>
      </div>

      {/* Alerts list */}
      <div data-testid="alerts-list" className="space-y-3">
        {alerts.map((alert) => {
          const feedback = executionFeedback[alert.alert_id];
          const isExecuting = executingAlertId === alert.alert_id;

          return (
            <div
              key={alert.alert_id}
              data-testid={`alert-item-${alert.alert_id}`}
              className={`border-l-4 rounded-r-lg p-4 ${getSeverityClasses(alert.severity)}`}
            >
              {/* Alert header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span
                    data-testid={`severity-${alert.severity}`}
                    className={`text-xs font-medium px-2 py-1 rounded-full ${getSeverityBadgeClasses(alert.severity)}`}
                  >
                    {getSeverityLabel(alert.severity)}
                  </span>
                  <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                    {alert.cause}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatTimestamp(alert.created_at)}
                  </span>
                  {onDismissAlert && (
                    <button
                      data-testid={`dismiss-alert-btn-${alert.alert_id}`}
                      onClick={() => handleDismiss(alert.alert_id)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-lg leading-none"
                      title="Dismiss alert"
                    >
                      ×
                    </button>
                  )}
                </div>
              </div>

              {/* Recommendation */}
              <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                {alert.recommendation}
              </p>

              {/* Execute playbook CTA */}
              {alert.playbook_chain_id && (
                <div className="mt-3">
                  {!isExecuting && !feedback && (
                    <button
                      data-testid={`execute-playbook-btn-${alert.alert_id}`}
                      onClick={() => handleExecutePlaybook(alert)}
                      className="text-sm px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                    >
                      Executar cadeia recomendada
                    </button>
                  )}

                  {isExecuting && (
                    <div data-testid={`playbook-executing-${alert.alert_id}`} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent" />
                      Executando playbook...
                    </div>
                  )}

                  {feedback && feedback.success && (
                    <div
                      data-testid={`execution-feedback-${alert.alert_id}`}
                      className="text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 p-2 rounded"
                    >
                      ✅ {feedback.message}
                    </div>
                  )}

                  {feedback && !feedback.success && (
                    <div
                      data-testid={`execution-error-${alert.alert_id}`}
                      className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded"
                    >
                      ❌ {feedback.message}
                      {feedback.details && <div className="mt-1 text-xs">{feedback.details}</div>}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
