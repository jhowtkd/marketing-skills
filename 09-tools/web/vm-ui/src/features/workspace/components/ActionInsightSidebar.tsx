import { useState, useCallback, useMemo } from "react";

export type ActionImpact = "low" | "medium" | "high" | "critical";
export type InsightType = "opportunity" | "risk" | "info" | "success";
export type AlertSeverity = "info" | "warning" | "critical";
export type TrendDirection = "up" | "down" | "neutral";

export interface NextAction {
  id: string;
  title: string;
  description: string;
  impact: ActionImpact;
  oneClick: boolean;
  onExecute: () => void;
  disabled?: boolean;
}

export interface InsightCard {
  id: string;
  type: InsightType;
  title: string;
  message: string;
  metric?: string;
  trend?: TrendDirection;
}

export interface AlertItem {
  id: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  timestamp: string;
}

export interface ActionInsightSidebarProps {
  nextActions: NextAction[];
  insights: InsightCard[];
  alerts: AlertItem[];
  onActionExecute?: (actionId: string) => void;
  onInsightClick?: (insightId: string) => void;
  onAlertDismiss?: (alertId: string) => void;
  className?: string;
}

const impactConfig: Record<ActionImpact, { label: string; color: string; bgColor: string; priority: number }> = {
  critical: { label: "Crítico", color: "text-red-600", bgColor: "bg-red-50", priority: 0 },
  high: { label: "Alto", color: "text-amber-600", bgColor: "bg-amber-50", priority: 1 },
  medium: { label: "Médio", color: "text-blue-600", bgColor: "bg-blue-50", priority: 2 },
  low: { label: "Baixo", color: "text-slate-600", bgColor: "bg-slate-50", priority: 3 },
};

const insightTypeConfig: Record<InsightType, { label: string; color: string; bgColor: string; icon: string }> = {
  opportunity: { label: "Oportunidade", color: "text-emerald-600", bgColor: "bg-emerald-50", icon: "↑" },
  risk: { label: "Risco", color: "text-red-600", bgColor: "bg-red-50", icon: "⚠" },
  info: { label: "Info", color: "text-blue-600", bgColor: "bg-blue-50", icon: "ℹ" },
  success: { label: "Sucesso", color: "text-emerald-600", bgColor: "bg-emerald-50", icon: "✓" },
};

const alertSeverityConfig: Record<AlertSeverity, { label: string; color: string; bgColor: string; borderColor: string; icon: string; priority: number }> = {
  critical: { label: "Crítico", color: "text-red-600", bgColor: "bg-red-50", borderColor: "border-red-200", icon: "🚨", priority: 0 },
  warning: { label: "Aviso", color: "text-amber-600", bgColor: "bg-amber-50", borderColor: "border-amber-200", icon: "⚠", priority: 1 },
  info: { label: "Info", color: "text-blue-600", bgColor: "bg-blue-50", borderColor: "border-blue-200", icon: "ℹ", priority: 2 },
};

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Agora";
  if (diffMins < 60) return `${diffMins}m atrás`;
  if (diffHours < 24) return `${diffHours}h atrás`;
  if (diffDays < 7) return `${diffDays}d atrás`;
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export default function ActionInsightSidebar({
  nextActions,
  insights,
  alerts,
  onActionExecute,
  onInsightClick,
  onAlertDismiss,
  className = "",
}: ActionInsightSidebarProps) {
  const [actionsExpanded, setActionsExpanded] = useState(true);
  const [insightsExpanded, setInsightsExpanded] = useState(true);
  const [alertsExpanded, setAlertsExpanded] = useState(true);

  const handleActionExecute = useCallback(
    (action: NextAction) => {
      if (!action.disabled) {
        action.onExecute();
        onActionExecute?.(action.id);
      }
    },
    [onActionExecute]
  );

  const handleInsightClick = useCallback(
    (insight: InsightCard) => {
      onInsightClick?.(insight.id);
    },
    [onInsightClick]
  );

  const handleAlertDismiss = useCallback(
    (alertId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      onAlertDismiss?.(alertId);
    },
    [onAlertDismiss]
  );

  // Sort actions by impact priority
  const sortedActions = useMemo(() => {
    return [...nextActions].sort(
      (a, b) => impactConfig[a.impact].priority - impactConfig[b.impact].priority
    );
  }, [nextActions]);

  // Sort alerts by severity priority
  const sortedAlerts = useMemo(() => {
    return [...alerts].sort(
      (a, b) => alertSeverityConfig[a.severity].priority - alertSeverityConfig[b.severity].priority
    );
  }, [alerts]);

  return (
    <div
      data-testid="action-insight-sidebar"
      className={`h-full flex flex-col bg-white/90 rounded-[1.5rem] border border-[color:var(--vm-line)] shadow-sm overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <h2 className="font-serif text-lg text-slate-900">Ações & Insights</h2>
        <p className="text-xs text-slate-500 mt-1">
          {nextActions.length} ações · {insights.length} insights · {alerts.length} alertas
        </p>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-auto">
        {/* Next Actions Section */}
        <div className="border-b border-slate-200">
          <button
            data-testid="actions-header"
            onClick={() => setActionsExpanded(!actionsExpanded)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
            aria-label="Próximas ações recomendadas"
            aria-expanded={actionsExpanded}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-700">Próximas Ações</span>
              {nextActions.length > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--vm-primary)] text-white font-medium">
                  {nextActions.length}
                </span>
              )}
            </div>
            <span className="text-xs text-slate-400">{actionsExpanded ? "▼" : "▶"}</span>
          </button>

          {actionsExpanded && (
            <div data-testid="actions-list" className="px-3 pb-3 space-y-2">
              {sortedActions.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">Nenhuma ação recomendada</p>
              ) : (
                sortedActions.map((action) => {
                  const impact = impactConfig[action.impact];
                  return (
                    <div
                      key={action.id}
                      data-testid={`action-${action.id}`}
                      data-impact={action.impact}
                      onClick={() => handleActionExecute(action)}
                      className={`
                        group p-3 rounded-xl border transition-all duration-200
                        ${action.disabled 
                          ? "border-slate-100 bg-slate-50 opacity-50 cursor-not-allowed" 
                          : "border-slate-200 bg-white hover:border-[var(--vm-primary)] hover:shadow-sm cursor-pointer"
                        }
                      `}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="text-sm font-semibold text-slate-900 line-clamp-1 flex-1">
                          {action.title}
                        </h4>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          {action.oneClick && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 font-medium">
                              1-clique
                            </span>
                          )}
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${impact.bgColor} ${impact.color} font-medium`}>
                            {impact.label}
                          </span>
                        </div>
                      </div>

                      {/* Description */}
                      <p className="text-xs text-slate-600 mt-1.5 line-clamp-2">
                        {action.description}
                      </p>

                      {/* Execute Hint */}
                      {!action.disabled && (
                        <div className="mt-2 flex items-center gap-1 text-xs text-[var(--vm-primary)] opacity-0 group-hover:opacity-100 transition-opacity">
                          <span>Clique para executar</span>
                          <span>→</span>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* Insights Section */}
        <div className="border-b border-slate-200">
          <button
            data-testid="insights-header"
            onClick={() => setInsightsExpanded(!insightsExpanded)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
            aria-label="Insights e observações"
            aria-expanded={insightsExpanded}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-700">Insights</span>
              {insights.length > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                  {insights.length}
                </span>
              )}
            </div>
            <span className="text-xs text-slate-400">{insightsExpanded ? "▼" : "▶"}</span>
          </button>

          {insightsExpanded && (
            <div data-testid="insights-list" className="px-3 pb-3 space-y-2">
              {insights.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">Nenhum insight disponível</p>
              ) : (
                insights.map((insight) => {
                  const typeConfig = insightTypeConfig[insight.type];
                  return (
                    <div
                      key={insight.id}
                      data-testid={`insight-${insight.id}`}
                      data-type={insight.type}
                      onClick={() => handleInsightClick(insight)}
                      className={`
                        p-3 rounded-xl border transition-all duration-200 cursor-pointer
                        ${typeConfig.bgColor} ${typeConfig.borderColor || "border-slate-200"}
                        hover:shadow-sm
                      `}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-lg ${typeConfig.color}`}>{typeConfig.icon}</span>
                          <h4 className="text-sm font-semibold text-slate-900">
                            {insight.title}
                          </h4>
                        </div>
                        {insight.metric && (
                          <div className="flex items-center gap-1">
                            <span className={`text-sm font-bold ${typeConfig.color}`}>
                              {insight.metric}
                            </span>
                            {insight.trend && (
                              <span
                                data-testid={`trend-${insight.id}`}
                                data-trend={insight.trend}
                                className={`text-xs ${
                                  insight.trend === "up" ? "text-emerald-500" : "text-red-500"
                                }`}
                              >
                                {insight.trend === "up" ? "↑" : "↓"}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Message */}
                      <p className="text-xs text-slate-600 mt-1.5">
                        {insight.message}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* Alerts Section */}
        <div>
          <button
            data-testid="alerts-header"
            onClick={() => setAlertsExpanded(!alertsExpanded)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
            aria-label="Alertas ativos"
            aria-expanded={alertsExpanded}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-700">Alertas</span>
              {alerts.length > 0 && (
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  alerts.some(a => a.severity === "critical")
                    ? "bg-red-100 text-red-600"
                    : alerts.some(a => a.severity === "warning")
                    ? "bg-amber-100 text-amber-600"
                    : "bg-blue-100 text-blue-600"
                }`}>
                  {alerts.length}
                </span>
              )}
            </div>
            <span className="text-xs text-slate-400">{alertsExpanded ? "▼" : "▶"}</span>
          </button>

          {alertsExpanded && (
            <div data-testid="alerts-list" className="px-3 pb-3 space-y-2">
              {sortedAlerts.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">Nenhum alerta ativo</p>
              ) : (
                sortedAlerts.map((alert) => {
                  const severity = alertSeverityConfig[alert.severity];
                  return (
                    <div
                      key={alert.id}
                      data-testid={`alert-${alert.id}`}
                      data-severity={alert.severity}
                      className={`p-3 rounded-xl border ${severity.bgColor} ${severity.borderColor}`}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="text-lg">{severity.icon}</span>
                          <h4 className="text-sm font-semibold text-slate-900 truncate">
                            {alert.title}
                          </h4>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span
                            data-testid="alert-timestamp"
                            className="text-xs text-slate-400"
                          >
                            {formatTimestamp(alert.timestamp)}
                          </span>
                          {onAlertDismiss && (
                            <button
                              data-testid="dismiss-alert"
                              onClick={(e) => handleAlertDismiss(alert.id, e)}
                              className="p-1 rounded hover:bg-white/50 text-slate-400 hover:text-slate-600 transition-colors"
                              title="Descartar alerta"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Message */}
                      <p className="text-xs text-slate-600 mt-1">
                        {alert.message}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
