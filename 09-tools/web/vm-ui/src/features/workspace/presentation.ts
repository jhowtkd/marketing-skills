export function toHumanStatus(status: string): string {
  const map: Record<string, string> = {
    queued: "Em fila",
    running: "Gerando",
    waiting_approval: "Aguardando revisao",
    completed: "Pronto",
    failed: "Falhou",
  };
  return map[status] ?? status;
}

export function toHumanRunName(input: { index: number; requestText?: string; createdAt?: string }): string {
  const short = (input.requestText ?? "").trim().slice(0, 36) || "sem pedido";
  const hhmm = input.createdAt ? new Date(input.createdAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "--:--";
  return `Versao ${input.index} · ${short} · ${hhmm}`;
}

export type TimelineEvent = {
  event_type: string;
  payload?: Record<string, unknown>;
  actor_id?: string;
};

export type TimelineEventDisplay = {
  label: string;
  actor?: string;
  justification?: string;
};

export function toHumanTimelineEvent(event: string | TimelineEvent): string {
  const result = toHumanTimelineEventDetails(event);
  return result.label;
}

export function toHumanTimelineEventDetails(event: string | TimelineEvent): TimelineEventDisplay {
  const eventType = typeof event === "string" ? event : event.event_type;
  const payload = typeof event === "string" ? undefined : event.payload;
  const actorId = typeof event === "string" ? undefined : event.actor_id;

  const map: Record<string, string> = {
    ThreadModeAdded: "Modo adicionado ao job",
    ThreadModeRemoved: "Modo removido do job",
    WorkflowRunQueued: "Versao entrou na fila",
    WorkflowRunStarted: "Geracao iniciada",
    WorkflowRunStageStarted: "Etapa iniciada",
    WorkflowRunStageCompleted: "Etapa concluida",
    WorkflowRunStageFailed: "Etapa falhou",
    WorkflowRunCompleted: "Versao concluida",
    WorkflowRunFailed: "Versao falhou",
    TaskCreated: "Tarefa criada",
    TaskCompleted: "Tarefa concluida",
    ApprovalCreated: "Aprovacao criada",
    ApprovalGranted: "Aprovacao concedida",
    ToolInvoked: "Ferramenta executada",
    EditorialGoldenMarked: "Golden marcado",
  };

  // Special handling for EditorialGoldenMarked with scope awareness
  if (eventType === "EditorialGoldenMarked" && payload) {
    const scope = payload.scope as string | undefined;
    const justification = payload.justification as string | undefined;
    
    let label = map[eventType] ?? eventType;
    if (scope === "global") {
      label = "Golden global definido";
    } else if (scope === "objective") {
      label = "Golden de objetivo definido";
    }
    
    return {
      label,
      actor: actorId,
      justification: justification,
    };
  }

  return { label: map[eventType] ?? eventType };
}

export function canResumeRunStatus(status: string): boolean {
  return status === "waiting_approval" || status === "waiting" || status === "paused";
}

export function summarizeRequestText(requestText?: string): string {
  const normalized = (requestText ?? "").trim();
  if (!normalized) return "Defina o pedido para liberar uma nova versao editorial.";
  if (normalized.length <= 120) return normalized;
  return `${normalized.slice(0, 117)}...`;
}

export type BaselineCandidate = {
  run_id: string;
  created_at?: string;
};

export function pickBaselineRun(
  runs: BaselineCandidate[],
  activeRunId: string | null
): BaselineCandidate | null {
  if (!activeRunId || runs.length < 2) return null;
  const activeIndex = runs.findIndex((run) => run.run_id === activeRunId);
  if (activeIndex < 0) return null;
  if (activeIndex === 0) return runs[1] ?? null;
  return runs[activeIndex - 1] ?? null;
}

export type BaselineSource = "objective_golden" | "global_golden" | "previous" | "none";

export function toBaselineSourceLabel(source: BaselineSource): string {
  const map: Record<BaselineSource, string> = {
    objective_golden: "Golden deste objetivo",
    global_golden: "Golden global",
    previous: "Versao anterior",
    none: "Sem baseline",
  };
  return map[source] ?? source;
}

export function toComparisonLabel(source: BaselineSource): string {
  if (source === "none") return "Sem versao anterior para comparar";
  return `Comparando com: ${toBaselineSourceLabel(source)}`;
}

// Legacy function for backwards compatibility
export function toComparisonLabelLegacy(hasBaseline: boolean): string {
  return hasBaseline ? "Comparando com a versao anterior" : "Sem versao anterior para comparar";
}

export function isGoldenForRun(
  runId: string,
  decisions: { global: { run_id: string } | null; objective: Array<{ run_id: string; objective_key?: string }> } | null
): { isGlobalGolden: boolean; isObjectiveGolden: boolean; objectiveKey?: string } {
  if (!decisions) {
    return { isGlobalGolden: false, isObjectiveGolden: false };
  }
  const isGlobalGolden = decisions.global?.run_id === runId;
  const objectiveDecision = decisions.objective?.find((d) => d.run_id === runId);
  const isObjectiveGolden = Boolean(objectiveDecision);
  return {
    isGlobalGolden,
    isObjectiveGolden,
    objectiveKey: objectiveDecision?.objective_key,
  };
}

// Timeline filter types and helpers
export type TimelineFilter = "all" | "editorial";

export const TIMELINE_FILTER_LABELS: Record<TimelineFilter, string> = {
  all: "Todos",
  editorial: "Editorial",
};

export function isEditorialEvent(eventType: string): boolean {
  return eventType === "EditorialGoldenMarked";
}

export function filterTimelineEvents<T extends { event_type: string }>(
  events: T[],
  filter: TimelineFilter
): T[] {
  if (filter === "all") return events;
  if (filter === "editorial") return events.filter((e) => isEditorialEvent(e.event_type));
  return events;
}

// Editorial Audit helpers
export type AuditScopeFilter = "all" | "global" | "objective";

export const AUDIT_SCOPE_FILTER_LABELS: Record<AuditScopeFilter, string> = {
  all: "Todos",
  global: "Global",
  objective: "Objetivo",
};

export type EditorialAuditEventDisplay = {
  eventId: string;
  eventType: string;
  actorId: string;
  actorRole: string;
  scope: "global" | "objective";
  scopeLabel: string;
  objectiveKey?: string;
  runId: string;
  justification: string;
  occurredAt: string;
  formattedDate: string;
};

export function formatAuditEvent(event: {
  event_id: string;
  event_type: string;
  actor_id: string;
  actor_role: string;
  scope: "global" | "objective";
  objective_key?: string;
  run_id: string;
  justification: string;
  occurred_at: string;
}): EditorialAuditEventDisplay {
  const occurredDate = new Date(event.occurred_at);
  const formattedDate = occurredDate.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return {
    eventId: event.event_id,
    eventType: event.event_type,
    actorId: event.actor_id,
    actorRole: event.actor_role,
    scope: event.scope,
    scopeLabel: event.scope === "global" ? "Global" : "Objetivo",
    objectiveKey: event.objective_key,
    runId: event.run_id,
    justification: event.justification,
    occurredAt: event.occurred_at,
    formattedDate,
  };
}

export function toHumanActorRole(role: string): string {
  const map: Record<string, string> = {
    admin: "Administrador",
    editor: "Editor",
    viewer: "Visualizador",
  };
  return map[role] ?? role;
}
