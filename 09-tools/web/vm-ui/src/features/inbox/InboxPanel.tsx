import { useState } from "react";
import { useInbox } from "./useInbox";
import { splitInboxByStatus } from "./presentation";

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
  const [activeTab, setActiveTab] = useState<"pending" | "history">("pending");

  const { pendingTasks, pendingApprovals, historyTasks, historyApprovals } = splitInboxByStatus({ tasks, approvals });

  return (
    <div className="space-y-4">
      {/* Actions / Refresh */}
      {activeThreadId && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-semibold text-slate-900">Inbox</h2>
            <button
              onClick={() => {
                refreshTasks();
                refreshApprovals();
                if (activeRunId) refreshArtifacts();
              }}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-900"
            >
              Recarregar
            </button>
          </div>
        </section>
      )}

      {/* Tabs */}
      {activeThreadId && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setActiveTab("pending")}
              className={`px-3 py-1 text-xs font-medium rounded-lg ${activeTab === "pending" ? "bg-primary text-white" : "bg-slate-100 text-slate-700"}`}
            >
              Pendentes ({pendingTasks.length + pendingApprovals.length})
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={`px-3 py-1 text-xs font-medium rounded-lg ${activeTab === "history" ? "bg-primary text-white" : "bg-slate-100 text-slate-700"}`}
            >
              Historico ({historyTasks.length + historyApprovals.length})
            </button>
          </div>

          {activeTab === "pending" ? (
            <div className="space-y-4">
              {/* Pending Approvals */}
              <div>
                <h3 className="text-xs font-semibold text-slate-700 mb-2">Aprovacoes pendentes</h3>
                {pendingApprovals.length === 0 ? (
                  <p className="text-xs text-slate-500">Nenhuma aprovacao pendente.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {pendingApprovals.map((approval) => (
                      <div key={approval.approval_id} className="rounded-lg border p-3 border-slate-200 bg-slate-50">
                        <div className="text-xs font-semibold text-slate-900">{approval.approval_id}</div>
                        <div className="text-xs text-slate-600 mb-2">Status: {approval.status} | Role: {approval.required_role}</div>
                        <div className="text-xs text-slate-800 mb-2">{approval.reason}</div>
                        <button
                          type="button"
                          onClick={() => grantApproval(approval.approval_id)}
                          className="rounded bg-primary px-3 py-1 text-xs text-white"
                        >
                          Aprovar
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Pending Tasks */}
              <div>
                <h3 className="text-xs font-semibold text-slate-700 mb-2">Tarefas pendentes</h3>
                {pendingTasks.length === 0 ? (
                  <p className="text-xs text-slate-500">Nenhuma tarefa pendente.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {pendingTasks.map((task) => (
                      <div key={task.task_id} className="rounded-lg border p-3 border-slate-200 bg-slate-50">
                        <div className="text-xs font-semibold text-slate-900">{task.task_id}</div>
                        <div className="text-xs text-slate-600 mb-2">Status: {task.status} | Assigned To: {task.assigned_to}</div>
                        <div className="flex flex-col gap-2">
                          <div className="flex gap-2">
                            <input
                              type="text"
                              placeholder="Adicionar comentario"
                              value={commentInput[task.task_id] || ""}
                              onChange={(e) => setCommentInput({ ...commentInput, [task.task_id]: e.target.value })}
                              className="flex-1 rounded border px-2 py-1 text-xs"
                            />
                            <button
                              type="button"
                              onClick={() => {
                                commentTask(task.task_id, commentInput[task.task_id] || "");
                                setCommentInput({ ...commentInput, [task.task_id]: "" });
                              }}
                              className="rounded bg-slate-200 px-3 py-1 text-xs text-slate-800"
                            >
                              Comentar
                            </button>
                          </div>
                          <button
                            type="button"
                            onClick={() => completeTask(task.task_id)}
                            className="rounded bg-green-600 px-3 py-1 text-xs text-white w-fit"
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
          ) : (
            <div className="space-y-4">
              {/* History Approvals */}
              <div>
                <h3 className="text-xs font-semibold text-slate-700 mb-2">Aprovacoes concluidas</h3>
                {historyApprovals.length === 0 ? (
                  <p className="text-xs text-slate-500">Nenhuma aprovacao no historico.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {historyApprovals.map((approval) => (
                      <div key={approval.approval_id} className="rounded-lg border p-3 border-slate-200 bg-slate-50 opacity-75">
                        <div className="text-xs font-semibold text-slate-900">{approval.approval_id}</div>
                        <div className="text-xs text-slate-600">Status: {approval.status} | Role: {approval.required_role}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* History Tasks */}
              <div>
                <h3 className="text-xs font-semibold text-slate-700 mb-2">Tarefas concluidas</h3>
                {historyTasks.length === 0 ? (
                  <p className="text-xs text-slate-500">Nenhuma tarefa no historico.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {historyTasks.map((task) => (
                      <div key={task.task_id} className="rounded-lg border p-3 border-slate-200 bg-slate-50 opacity-75">
                        <div className="text-xs font-semibold text-slate-900">{task.task_id}</div>
                        <div className="text-xs text-slate-600">Status: {task.status} | Assigned To: {task.assigned_to}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Artifacts */}
      {activeRunId && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Artifacts da Run {activeRunId}</h2>
          {artifactStages.length === 0 ? (
            <p className="mt-2 text-sm text-slate-600">Nenhum artefato encontrado.</p>
          ) : (
            <div className="mt-3 flex flex-col gap-4">
              {artifactStages.map((stage) => (
                <div key={stage.stage_dir} className="border-b pb-3 border-slate-200">
                  <div className="text-xs font-semibold text-slate-800 mb-2">Stage: {stage.stage_dir}</div>
                  {(!stage.artifacts || (Array.isArray(stage.artifacts) && stage.artifacts.length === 0)) ? (
                    <div className="text-xs text-slate-500">Sem artefatos.</div>
                  ) : (
                    <ul className="flex flex-col gap-2">
                      {Array.isArray(stage.artifacts) && stage.artifacts.map((art: any, i) => {
                        const path = typeof art === "string" ? art : art.path || art.filename || String(i);
                        const displayPath = typeof art === "string" ? art : (art.name || art.path || art.filename || JSON.stringify(art));
                        const key = `${stage.stage_dir}/${path}`;
                        return (
                          <li key={i} className="flex flex-col gap-1 rounded bg-slate-50 p-2 text-xs">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-slate-600 break-all">{displayPath}</span>
                              <button
                                onClick={() => loadArtifactContent(stage.stage_dir, path)}
                                className="rounded bg-blue-100 px-2 py-1 text-blue-700 hover:bg-blue-200"
                              >
                                Visualizar
                              </button>
                            </div>
                            {artifactContents[key] && (
                              <pre className="mt-2 p-2 bg-slate-900 text-slate-50 rounded overflow-auto whitespace-pre-wrap max-h-64 text-[10px]">
                                {artifactContents[key]}
                              </pre>
                            )}
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
