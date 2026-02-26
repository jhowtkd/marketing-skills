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
