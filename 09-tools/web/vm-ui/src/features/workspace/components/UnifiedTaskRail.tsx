import { useState, useCallback } from "react";

export type StepStatus = "pending" | "active" | "done" | "blocked";
export type QueuePriority = "low" | "medium" | "high" | "critical";
export type QueueItemStatus = "pending" | "in_progress" | "completed" | "blocked";

export interface WorkflowStep {
  id: string;
  label: string;
  order: number;
  description?: string;
}

export interface QueueItem {
  id: string;
  title: string;
  priority: QueuePriority;
  status: QueueItemStatus;
  assignee?: string;
  createdAt: string;
  dueDate?: string;
}

export interface UnifiedTaskRailProps {
  steps: WorkflowStep[];
  activeStepId?: string;
  completedStepIds?: string[];
  stepStatuses?: Record<string, StepStatus>;
  queue: QueueItem[];
  onStepSelect?: (stepId: string) => void;
  onQueueItemSelect?: (itemId: string) => void;
  onStepComplete?: (stepId: string) => void;
  className?: string;
}

const statusConfig: Record<StepStatus, { label: string; color: string; bgColor: string; icon: string }> = {
  pending: { label: "Pendente", color: "text-slate-500", bgColor: "bg-slate-100", icon: "○" },
  active: { label: "Em andamento", color: "text-blue-600", bgColor: "bg-blue-50", icon: "●" },
  done: { label: "Concluído", color: "text-emerald-600", bgColor: "bg-emerald-50", icon: "✓" },
  blocked: { label: "Bloqueado", color: "text-amber-600", bgColor: "bg-amber-50", icon: "⊘" },
};

const priorityConfig: Record<QueuePriority, { label: string; color: string; bgColor: string }> = {
  low: { label: "Baixa", color: "text-slate-600", bgColor: "bg-slate-100" },
  medium: { label: "Média", color: "text-blue-600", bgColor: "bg-blue-50" },
  high: { label: "Alta", color: "text-amber-600", bgColor: "bg-amber-50" },
  critical: { label: "Crítica", color: "text-red-600", bgColor: "bg-red-50" },
};

const queueStatusConfig: Record<QueueItemStatus, { label: string; color: string }> = {
  pending: { label: "Pendente", color: "text-slate-500" },
  in_progress: { label: "Em progresso", color: "text-blue-600" },
  completed: { label: "Concluído", color: "text-emerald-600" },
  blocked: { label: "Bloqueado", color: "text-amber-600" },
};

export default function UnifiedTaskRail({
  steps,
  activeStepId,
  completedStepIds = [],
  stepStatuses = {},
  queue,
  onStepSelect,
  onQueueItemSelect,
  onStepComplete,
  className = "",
}: UnifiedTaskRailProps) {
  const [stepsExpanded, setStepsExpanded] = useState(true);
  const [queueExpanded, setQueueExpanded] = useState(true);

  const handleStepClick = useCallback(
    (stepId: string) => {
      onStepSelect?.(stepId);
    },
    [onStepSelect]
  );

  const handleQueueItemClick = useCallback(
    (itemId: string) => {
      onQueueItemSelect?.(itemId);
    },
    [onQueueItemSelect]
  );

  const handleStepComplete = useCallback(
    (stepId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      onStepComplete?.(stepId);
    },
    [onStepComplete]
  );

  const sortedSteps = [...steps].sort((a, b) => a.order - b.order);
  const sortedQueue = [...queue].sort((a, b) => {
    const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  });

  const getStepStatus = (stepId: string): StepStatus => {
    if (stepStatuses[stepId]) return stepStatuses[stepId];
    if (completedStepIds.includes(stepId)) return "done";
    if (stepId === activeStepId) return "active";
    return "pending";
  };

  return (
    <div
      data-testid="unified-task-rail"
      className={`h-full flex flex-col bg-white/90 rounded-[1.5rem] border border-[color:var(--vm-line)] shadow-sm ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <h2 className="font-serif text-lg text-slate-900">Etapas & Fila</h2>
        <p className="text-xs text-slate-500 mt-1">
          {steps.length} etapas · {queue.length} itens
        </p>
      </div>

      {/* Steps Section */}
      <div className="flex-1 overflow-auto">
        {/* Steps Header */}
        <button
          data-testid="steps-header"
          onClick={() => setStepsExpanded(!stepsExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
          aria-label="Etapas do workflow"
          aria-expanded={stepsExpanded}
        >
          <span className="text-sm font-semibold text-slate-700">Workflow</span>
          <span className="text-xs text-slate-400">{stepsExpanded ? "▼" : "▶"}</span>
        </button>

        {/* Steps List */}
        {stepsExpanded && (
          <div data-testid="steps-list" className="px-2 pb-2">
            {sortedSteps.length === 0 ? (
              <p className="text-sm text-slate-500 px-2 py-3 text-center">Nenhuma etapa definida</p>
            ) : (
              <div className="space-y-1" role="list" aria-label="Etapas do workflow">
                {sortedSteps.map((step, index) => {
                  const status = getStepStatus(step.id);
                  const config = statusConfig[status];
                  const isActive = step.id === activeStepId;

                  return (
                    <div
                      key={step.id}
                      data-testid={`step-${step.id}`}
                      data-status={status}
                      role="listitem"
                      aria-current={isActive ? "step" : undefined}
                      onClick={() => handleStepClick(step.id)}
                      className={`
                        group relative flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer
                        transition-all duration-200
                        ${isActive 
                          ? "bg-[var(--vm-warm)] ring-1 ring-[color:var(--vm-primary)]/20" 
                          : "hover:bg-slate-50"
                        }
                      `}
                    >
                      {/* Step Number/Icon */}
                      <span
                        className={`
                          flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center
                          text-xs font-semibold ${config.color} ${config.bgColor}
                        `}
                      >
                        {status === "done" ? config.icon : index + 1}
                      </span>

                      {/* Step Content */}
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium truncate ${isActive ? "text-slate-900" : "text-slate-700"}`}>
                          {step.label}
                        </p>
                        {step.description && (
                          <p className="text-xs text-slate-500 truncate">{step.description}</p>
                        )}
                      </div>

                      {/* Status Badge */}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${config.bgColor} ${config.color}`}>
                        {config.label}
                      </span>

                      {/* Complete Button (only for active steps) */}
                      {status === "active" && onStepComplete && (
                        <button
                          data-testid={`complete-step-${step.id}`}
                          onClick={(e) => handleStepComplete(step.id, e)}
                          className="opacity-0 group-hover:opacity-100 flex-shrink-0 p-1 rounded-lg bg-emerald-100 text-emerald-600 hover:bg-emerald-200 transition-all"
                          title="Marcar como concluído"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                      )}

                      {/* Connector Line */}
                      {index < sortedSteps.length - 1 && (
                        <div
                          className={`
                            absolute left-[22px] top-[38px] w-0.5 h-[calc(100%-8px)]
                            ${status === "done" ? "bg-emerald-300" : "bg-slate-200"}
                          `}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Divider */}
        <div className="h-px bg-slate-200 my-2" />

        {/* Queue Header */}
        <button
          data-testid="queue-header"
          onClick={() => setQueueExpanded(!queueExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
          aria-label="Fila operacional"
          aria-expanded={queueExpanded}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-700">Fila Operacional</span>
            {queue.length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                {queue.length}
              </span>
            )}
          </div>
          <span className="text-xs text-slate-400">{queueExpanded ? "▼" : "▶"}</span>
        </button>

        {/* Queue List */}
        {queueExpanded && (
          <div data-testid="queue-list" className="px-2 pb-4">
            {sortedQueue.length === 0 ? (
              <p className="text-sm text-slate-500 px-2 py-3 text-center">Fila vazia</p>
            ) : (
              <div className="space-y-2" role="list" aria-label="Itens da fila">
                {sortedQueue.map((item) => {
                  const priorityConfig_item = priorityConfig[item.priority];
                  const statusConfig_item = queueStatusConfig[item.status];

                  return (
                    <div
                      key={item.id}
                      data-testid={`queue-item-${item.id}`}
                      data-priority={item.priority}
                      role="listitem"
                      onClick={() => handleQueueItemClick(item.id)}
                      className="group p-3 rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm cursor-pointer transition-all duration-200"
                    >
                      {/* Title & Priority */}
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-slate-900 line-clamp-2 flex-1">
                          {item.title}
                        </p>
                        <span
                          className={`flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full font-medium ${priorityConfig_item.bgColor} ${priorityConfig_item.color}`}
                        >
                          {priorityConfig_item.label}
                        </span>
                      </div>

                      {/* Meta Info */}
                      <div className="mt-2 flex items-center gap-3 text-xs">
                        <span className={statusConfig_item.color}>{statusConfig_item.label}</span>
                        {item.assignee && (
                          <>
                            <span className="text-slate-300">·</span>
                            <span className="text-slate-500">{item.assignee}</span>
                          </>
                        )}
                        {item.dueDate && (
                          <>
                            <span className="text-slate-300">·</span>
                            <span className="text-slate-500">
                              {new Date(item.dueDate).toLocaleDateString("pt-BR")}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/50 rounded-b-[1.5rem]">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            {completedStepIds.length}/{steps.length} etapas
          </span>
          <span>
            {queue.filter((q) => q.status === "pending").length} pendentes
          </span>
        </div>
      </div>
    </div>
  );
}
