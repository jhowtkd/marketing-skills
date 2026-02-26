import { useState } from "react";
import { useInbox } from "./useInbox";
import { splitInboxByStatus } from "./presentation";
import ArtifactPreview from "./ArtifactPreview";

type MaybeId = string | null;

type Props = {
  activeThreadId: MaybeId;
  activeRunId: MaybeId;
  devMode: boolean;
};

export default function InboxPanel({ activeThreadId, activeRunId, devMode }: Props) {
  const {
    tasks,
    approvals,
    artifactStages,
    artifactContents,
    completeTask,
    commentTask,
    grantApproval,
    loadArtifactContent,
    refreshTasks,
    refreshApprovals,
    refreshArtifacts,
  } = useInbox(activeThreadId, activeRunId);

  const [commentInput, setCommentInput] = useState<Record<string, string>>({});

  const { pendingTasks, pendingApprovals, historyTasks, historyApprovals } = splitInboxByStatus({ tasks, approvals });
  const blockersCount = pendingTasks.length + pendingApprovals.length;
  const hasActiveThread = Boolean(activeThreadId);
  const hasActiveRun = Boolean(activeRunId);

  return (
    <div className="space-y-4">
      {hasActiveThread ? (
        <>
          <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/95 p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
                  Action rail
                </p>
                <h2 className="mt-2 font-serif text-2xl text-slate-900">Pendencias desta versao</h2>
                <p className="mt-2 text-sm text-slate-600">
                  Resolva bloqueios da versao ativa antes de abrir historico ou artefatos secundarios.
                </p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span className="rounded-full bg-[var(--vm-warm)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--vm-primary-strong)]">
                  {blockersCount} bloqueio{blockersCount === 1 ? "" : "s"}
                </span>
                <button
                  onClick={() => {
                    refreshTasks();
                    refreshApprovals();
                    if (activeRunId) refreshArtifacts();
                  }}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-900"
                >
                  Recarregar
                </button>
              </div>
            </div>
          </section>

          {!hasActiveRun ? (
            <section className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50/90 p-5">
              <p className="text-sm font-semibold text-slate-900">
                Gere ou selecione uma versao para ver pendencias acionaveis.
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Assim que uma versao estiver ativa, este rail organiza aprovacoes, tarefas e artefatos de apoio na
                ordem de bloqueio do fluxo.
              </p>
            </section>
          ) : (
            <>
              <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/95 p-4 shadow-sm">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--vm-primary)]">
                      Aprovacoes pendentes
                    </h3>
                    {pendingApprovals.length === 0 ? (
                      <p className="mt-2 text-sm text-slate-500">Nenhuma aprovacao bloqueando esta versao.</p>
                    ) : (
                      <div className="mt-3 flex flex-col gap-3">
                        {pendingApprovals.map((approval) => (
                          <div
                            key={approval.approval_id}
                            className="rounded-2xl border border-amber-200 bg-amber-50 p-4 transition-all duration-200"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-sm font-semibold text-slate-900">
                                  {devMode ? approval.approval_id : "Aprovacao pendente"}
                                </p>
                                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-amber-800">
                                  Role {approval.required_role}
                                </p>
                              </div>
                              <span className="rounded-full bg-white px-2 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-amber-700">
                                {approval.status}
                              </span>
                            </div>
                            <p className="mt-3 text-sm text-slate-700">{approval.reason}</p>
                            <button
                              type="button"
                              onClick={() => grantApproval(approval.approval_id)}
                              className="mt-4 rounded-xl bg-primary px-3 py-2 text-sm font-medium text-white"
                            >
                              Aprovar
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--vm-primary)]">
                      Tarefas pendentes
                    </h3>
                    {pendingTasks.length === 0 ? (
                      <p className="mt-2 text-sm text-slate-500">Nenhuma tarefa pendente para esta versao.</p>
                    ) : (
                      <div className="mt-3 flex flex-col gap-3">
                        {pendingTasks.map((task) => (
                          <div
                            key={task.task_id}
                            className="rounded-2xl border border-slate-200 bg-[var(--vm-warm)]/45 p-4 transition-all duration-200"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-sm font-semibold text-slate-900">
                                  {devMode ? task.task_id : "Tarefa pendente"}
                                </p>
                                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">
                                  Responsavel {task.assigned_to || "nao definido"}
                                </p>
                              </div>
                              <span className="rounded-full bg-white px-2 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-slate-600">
                                {task.status}
                              </span>
                            </div>
                            <div className="mt-4 flex flex-col gap-2">
                              <div className="flex gap-2">
                                <input
                                  type="text"
                                  placeholder="Adicionar comentario"
                                  value={commentInput[task.task_id] || ""}
                                  onChange={(e) =>
                                    setCommentInput({ ...commentInput, [task.task_id]: e.target.value })
                                  }
                                  className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                                />
                                <button
                                  type="button"
                                  onClick={() => {
                                    commentTask(task.task_id, commentInput[task.task_id] || "");
                                    setCommentInput({ ...commentInput, [task.task_id]: "" });
                                  }}
                                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800"
                                >
                                  Comentar
                                </button>
                              </div>
                              <button
                                type="button"
                                onClick={() => completeTask(task.task_id)}
                                className="w-fit rounded-xl bg-green-600 px-3 py-2 text-sm font-medium text-white"
                              >
                                Concluir
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </section>

              <details className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50/80 p-4">
                <summary className="cursor-pointer list-none text-sm font-semibold text-slate-700">
                  Historico recente
                </summary>
                <div className="mt-4 space-y-4">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Aprovacoes concluidas
                    </h3>
                    {historyApprovals.length === 0 ? (
                      <p className="mt-2 text-sm text-slate-500">Nenhuma aprovacao no historico.</p>
                    ) : (
                      <div className="mt-3 flex flex-col gap-2">
                        {historyApprovals.map((approval) => (
                          <div
                            key={approval.approval_id}
                            className="rounded-2xl border border-slate-200 bg-white p-3 opacity-80"
                          >
                            <p className="text-sm font-medium text-slate-900">
                              {devMode ? approval.approval_id : "Aprovacao concluida"}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {approval.status} · role {approval.required_role}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Tarefas concluidas
                    </h3>
                    {historyTasks.length === 0 ? (
                      <p className="mt-2 text-sm text-slate-500">Nenhuma tarefa no historico.</p>
                    ) : (
                      <div className="mt-3 flex flex-col gap-2">
                        {historyTasks.map((task) => (
                          <div
                            key={task.task_id}
                            className="rounded-2xl border border-slate-200 bg-white p-3 opacity-80"
                          >
                            <p className="text-sm font-medium text-slate-900">
                              {devMode ? task.task_id : "Tarefa concluida"}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {task.status} · responsavel {task.assigned_to || "nao definido"}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </details>

              <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/95 p-4 shadow-sm">
                <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--vm-primary)]">
                  Artefatos de apoio
                </h3>
                {artifactStages.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-600">Nenhum artefato secundario encontrado.</p>
                ) : (
                  <div className="mt-3 flex flex-col gap-4">
                    {artifactStages.map((stage) => (
                      <div key={stage.stage_dir} className="border-b border-slate-200 pb-3 last:border-b-0">
                        <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                          {stage.stage_dir}
                        </div>
                        {(!stage.artifacts || (Array.isArray(stage.artifacts) && stage.artifacts.length === 0)) ? (
                          <div className="text-xs text-slate-500">Sem artefatos.</div>
                        ) : (
                          <ul className="flex flex-col gap-2">
                            {Array.isArray(stage.artifacts) &&
                              stage.artifacts.map((art: any, i) => {
                                const path = typeof art === "string" ? art : art.path || art.filename || String(i);
                                const displayPath =
                                  typeof art === "string"
                                    ? art
                                    : art.name || art.path || art.filename || JSON.stringify(art);
                                const key = `${stage.stage_dir}/${path}`;
                                return (
                                  <li key={i} className="rounded-xl bg-slate-50 p-3 text-xs">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="break-all font-mono text-slate-600">{displayPath}</span>
                                      <button
                                        onClick={() => loadArtifactContent(stage.stage_dir, path)}
                                        className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700"
                                      >
                                        Visualizar
                                      </button>
                                    </div>
                                    {artifactContents[key] ? (
                                      <div className="mt-3">
                                        <ArtifactPreview
                                          content={artifactContents[key]}
                                          filename={typeof art === "string" ? art : art.name || art.path}
                                        />
                                      </div>
                                    ) : null}
                                  </li>
                                );
                              })}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </>
      ) : (
        <section className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50/80 p-4">
          <h2 className="text-sm font-semibold text-slate-900">Pendencias desta versao</h2>
          <p className="mt-2 text-sm text-slate-500">Escolha um job para abrir a action rail da versao.</p>
        </section>
      )}

      {devMode ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Debug</h2>
          <pre className="mt-3 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
{JSON.stringify(
  {
    activeThreadId,
    activeRunId,
    tasksCount: tasks.length,
    approvalsCount: approvals.length,
    artifactStagesCount: artifactStages.length,
  },
  null,
  2
)}
          </pre>
        </section>
      ) : null}
    </div>
  );
}
