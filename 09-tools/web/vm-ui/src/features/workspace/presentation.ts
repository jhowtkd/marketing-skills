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

export function toHumanTimelineEvent(eventType: string): string {
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
  };
  return map[eventType] ?? eventType;
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

export function toComparisonLabel(hasBaseline: boolean): string {
  return hasBaseline ? "Comparando com a versao anterior" : "Sem versao anterior para comparar";
}
