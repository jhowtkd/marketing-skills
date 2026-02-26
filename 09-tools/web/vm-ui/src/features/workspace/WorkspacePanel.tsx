import { useState } from "react";
import { useWorkspace } from "./useWorkspace";
import { toHumanStatus, toHumanRunName } from "./presentation";

type MaybeId = string | null;

type Props = {
  activeThreadId: MaybeId;
  activeRunId: MaybeId;
  onSelectRun: (runId: MaybeId) => void;
  devMode: boolean;
};

export default function WorkspacePanel({ activeThreadId, activeRunId, onSelectRun, devMode }: Props) {
  const {
    profiles,
    runs,
    runDetail,
    timeline,
    startRun,
    resumeRun,
    refreshRuns,
    refreshTimeline,
  } = useWorkspace(activeThreadId, activeRunId);

  const [selectedProfile, setSelectedProfile] = useState<string>("");
  const [requestText, setRequestText] = useState<string>("");

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Studio</h2>
        <p className="mt-2 text-sm text-slate-600">
          {activeThreadId
            ? "Job selecionado. Clique em 'Gerar nova versao' para criar conteudo."
            : "Selecione um Job na coluna da esquerda para comecar."}
        </p>
        <div className="mt-4 flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <label className="text-xs font-medium text-slate-700">Objetivo do pedido</label>
            <input
              type="text"
              value={requestText}
              onChange={(e) => setRequestText(e.target.value)}
              disabled={!activeThreadId}
              placeholder="Descreva o que voce precisa..."
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 disabled:opacity-50 w-full"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-xs font-medium text-slate-700">Perfil</label>
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              disabled={!activeThreadId}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
            >
              <option value="">Selecione um perfil</option>
              {profiles.map((p) => (
                <option key={p.mode} value={p.mode}>
                  {p.mode}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={!activeThreadId || !selectedProfile || !requestText.trim()}
              onClick={() => {
                startRun({ mode: selectedProfile, requestText });
                setRequestText("");
              }}
              className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Gerar nova versao
            </button>
            {activeRunId ? (
              <button
                type="button"
                onClick={() => onSelectRun(null)}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900"
              >
                Limpar run ativa
              </button>
            ) : null}
            <button
              type="button"
              disabled={!activeThreadId}
              onClick={() => {
                refreshRuns();
                refreshTimeline();
              }}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
            >
              Recarregar
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Versoes</h2>
        {runs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">Nenhuma versao encontrada.</p>
        ) : (
          <div className="mt-3 flex flex-col gap-2">
            {runs.map((r, idx) => (
              <div
                key={r.run_id}
                onClick={() => onSelectRun(r.run_id)}
                className={`cursor-pointer rounded-lg border p-3 text-sm ${
                  activeRunId === r.run_id
                    ? "border-primary bg-blue-50"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-900">{r.run_id}</span>
                  <span className="text-xs font-semibold text-slate-500">{toHumanStatus(r.status)}</span>
                </div>
                <div className="text-xs text-slate-500">{toHumanRunName({ index: idx + 1, requestText: r.request_text || r.requested_mode, createdAt: r.created_at })}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {activeRunId && runDetail && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 flex justify-between">
            Detalhes da Versao {activeRunId}
            {(runDetail.status === "paused" || runDetail.status === "waiting") && (
              <button
                type="button"
                onClick={resumeRun}
                className="rounded bg-blue-600 px-2 py-1 text-xs text-white"
              >
                Resume Run
              </button>
            )}
          </h2>
          <pre className="mt-3 max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            {JSON.stringify(runDetail, null, 2)}
          </pre>
        </section>
      )}

      {activeThreadId && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Timeline</h2>
          {timeline.length === 0 ? (
            <p className="mt-2 text-sm text-slate-600">Nenhum evento na timeline.</p>
          ) : (
            <div className="mt-3 flex flex-col gap-2 max-h-64 overflow-auto">
              {timeline.map((event) => (
                <div key={event.event_id} className="rounded-lg border border-slate-200 p-2 text-xs">
                  <div className="font-semibold text-slate-700">{event.event_type}</div>
                  <div className="text-slate-500">{event.created_at}</div>
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
