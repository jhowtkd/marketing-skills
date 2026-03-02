import { useState, useCallback, useMemo } from "react";

export type ExecutionStatus = "pending" | "running" | "completed" | "error" | "paused";

export interface TimelineEvent {
  id: string;
  type: "start" | "stage_complete" | "approval" | "error" | "info" | "warning";
  title: string;
  description?: string;
  timestamp: string;
  actor?: string;
}

export interface SecondaryAction {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: "default" | "outline" | "danger";
}

export interface ExecutionCenterProps {
  // Editor content
  editorContent: string;
  editorTitle?: string;
  editorSubtitle?: string;
  
  // Status
  status: ExecutionStatus;
  statusLabel: string;
  
  // Primary action
  primaryActionLabel: string;
  primaryActionDisabled?: boolean;
  onPrimaryAction: () => void;
  
  // Loading state
  isLoading?: boolean;
  loadingMessage?: string;
  
  // Timeline
  timeline: TimelineEvent[];
  onTimelineEventClick?: (eventId: string) => void;
  maxTimelineEvents?: number;
  
  // Secondary actions
  secondaryActions?: SecondaryAction[];
  
  // Options
  className?: string;
  showTimeline?: boolean;
}

const statusConfig: Record<ExecutionStatus, { color: string; bgColor: string; borderColor: string; icon: string }> = {
  pending: {
    color: "text-slate-600",
    bgColor: "bg-slate-50",
    borderColor: "border-slate-200",
    icon: "⏸",
  },
  running: {
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    icon: "▶",
  },
  completed: {
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-200",
    icon: "✓",
  },
  error: {
    color: "text-red-600",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    icon: "✕",
  },
  paused: {
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
    icon: "⏸",
  },
};

const eventTypeConfig: Record<TimelineEvent["type"], { color: string; icon: string }> = {
  start: { color: "bg-blue-500", icon: "▶" },
  stage_complete: { color: "bg-emerald-500", icon: "✓" },
  approval: { color: "bg-amber-500", icon: "👤" },
  error: { color: "bg-red-500", icon: "✕" },
  info: { color: "bg-slate-400", icon: "ℹ" },
  warning: { color: "bg-amber-400", icon: "⚠" },
};

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ExecutionCenter({
  editorContent,
  editorTitle = "Versão Ativa",
  editorSubtitle,
  status,
  statusLabel,
  primaryActionLabel,
  primaryActionDisabled = false,
  onPrimaryAction,
  isLoading = false,
  loadingMessage = "Carregando...",
  timeline,
  onTimelineEventClick,
  maxTimelineEvents = 5,
  secondaryActions = [],
  className = "",
  showTimeline = true,
}: ExecutionCenterProps) {
  const [showAllEvents, setShowAllEvents] = useState(false);
  const statusStyle = statusConfig[status];

  const handlePrimaryAction = useCallback(() => {
    if (!primaryActionDisabled && !isLoading) {
      onPrimaryAction();
    }
  }, [onPrimaryAction, primaryActionDisabled, isLoading]);

  const handleTimelineEventClick = useCallback(
    (eventId: string) => {
      onTimelineEventClick?.(eventId);
    },
    [onTimelineEventClick]
  );

  const sortedTimeline = useMemo(() => {
    return [...timeline].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [timeline]);

  const displayEvents = showAllEvents
    ? sortedTimeline
    : sortedTimeline.slice(0, maxTimelineEvents);
  const hasMoreEvents = sortedTimeline.length > maxTimelineEvents;

  return (
    <div
      data-testid="execution-center"
      className={`h-full flex flex-col gap-4 ${className}`}
    >
      {/* Editor Section */}
      <section
        aria-label="Editor de conteúdo"
        className="flex-1 min-h-0 rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/95 shadow-[0_18px_40px_rgba(22,32,51,0.08)] overflow-hidden flex flex-col"
      >
        {/* Editor Header */}
        <div className="p-4 border-b border-slate-200 flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h2 className="font-serif text-xl text-slate-900">{editorTitle}</h2>
              {/* Status Badge */}
              <span
                data-testid="status-badge"
                data-status={status}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${statusStyle.bgColor} ${statusStyle.color} ${statusStyle.borderColor}`}
              >
                <span>{statusStyle.icon}</span>
                {statusLabel}
              </span>
            </div>
            {editorSubtitle && (
              <p className="mt-1 text-sm text-slate-500">{editorSubtitle}</p>
            )}
          </div>
        </div>

        {/* Editor Content */}
        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="h-full flex flex-col items-center justify-center gap-4">
              <div className="w-8 h-8 border-2 border-slate-200 border-t-[var(--vm-primary)] rounded-full animate-spin" />
              <p className="text-sm text-slate-600">{loadingMessage}</p>
            </div>
          ) : editorContent ? (
            <div className="prose prose-slate max-w-none">
              <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 bg-slate-50 rounded-xl p-4">
                {editorContent}
              </pre>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                <span className="text-2xl text-slate-400">📝</span>
              </div>
              <p className="text-slate-600 font-medium">Nenhum conteúdo disponível</p>
              <p className="text-sm text-slate-400 mt-1">
                Execute uma ação para gerar conteúdo
              </p>
            </div>
          )}
        </div>

        {/* Editor Actions */}
        <div className="p-4 border-t border-slate-200 bg-slate-50/50">
          <div className="flex flex-wrap items-center gap-3">
            {/* Primary Action */}
            <button
              type="button"
              onClick={handlePrimaryAction}
              disabled={primaryActionDisabled || isLoading}
              aria-busy={isLoading}
              className={`
                rounded-xl px-5 py-2.5 text-sm font-medium
                transition-all duration-200
                ${
                  primaryActionDisabled || isLoading
                    ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                    : "bg-[var(--vm-primary)] text-white hover:opacity-90 shadow-sm"
                }
              `}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {loadingMessage}
                </span>
              ) : (
                primaryActionLabel
              )}
            </button>

            {/* Secondary Actions */}
            {secondaryActions.map((action, index) => (
              <button
                key={index}
                type="button"
                onClick={action.onClick}
                disabled={action.disabled}
                className={`
                  rounded-xl px-4 py-2.5 text-sm font-medium
                  transition-all duration-200
                  ${
                    action.disabled
                      ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                      : action.variant === "danger"
                      ? "bg-red-50 text-red-600 border border-red-200 hover:bg-red-100"
                      : action.variant === "outline"
                      ? "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
                      : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
                  }
                `}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Compact Timeline Section */}
      {showTimeline && (
        <section
          aria-label="Timeline de eventos"
          className="flex-shrink-0 rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm"
        >
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-serif text-lg text-slate-900">Timeline</h3>
            <span className="text-xs text-slate-500">
              {sortedTimeline.length} eventos
            </span>
          </div>

          {sortedTimeline.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-4">
              Nenhum evento registrado
            </p>
          ) : (
            <div data-testid="compact-timeline" className="space-y-2">
              {displayEvents.map((event) => {
                const eventStyle = eventTypeConfig[event.type];
                return (
                  <div
                    key={event.id}
                    data-testid="timeline-event"
                    onClick={() => handleTimelineEventClick(event.id)}
                    className={`
                      group flex items-start gap-3 p-2.5 rounded-xl
                      ${onTimelineEventClick ? "cursor-pointer hover:bg-slate-50" : ""}
                      transition-colors duration-200
                    `}
                  >
                    {/* Event Icon */}
                    <div
                      className={`flex-shrink-0 w-7 h-7 rounded-full ${eventStyle.color} flex items-center justify-center text-white text-xs font-bold`}
                    >
                      {eventStyle.icon}
                    </div>

                    {/* Event Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-slate-900 truncate">
                          {event.title}
                        </p>
                        <span
                          data-testid="timeline-timestamp"
                          className="flex-shrink-0 text-xs text-slate-400"
                        >
                          {formatTimestamp(event.timestamp)}
                        </span>
                      </div>
                      {event.description && (
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                          {event.description}
                        </p>
                      )}
                      {event.actor && (
                        <p className="text-xs text-slate-400 mt-0.5">
                          por {event.actor}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* View More Link */}
              {hasMoreEvents && (
                <button
                  type="button"
                  onClick={() => setShowAllEvents(!showAllEvents)}
                  className="w-full py-2 text-xs font-medium text-[var(--vm-primary)] hover:text-[var(--vm-primary-strong)] transition-colors"
                >
                  {showAllEvents
                    ? "Ver menos"
                    : `Ver mais (${sortedTimeline.length - maxTimelineEvents})`}
                </button>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
