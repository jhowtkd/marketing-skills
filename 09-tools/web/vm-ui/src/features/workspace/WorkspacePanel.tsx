import { useEffect, useMemo, useState } from "react";
import ArtifactPreview from "../inbox/ArtifactPreview";
import {
  canResumeRunStatus,
  summarizeRequestText,
  toHumanRunName,
  toHumanStatus,
  toHumanTimelineEvent,
} from "./presentation";
import { useWorkspace } from "./useWorkspace";
import { readWorkspaceView, writeWorkspaceView, type WorkspaceView } from "./viewState";

type MaybeId = string | null;

type Props = {
  activeThreadId: MaybeId;
  activeRunId: MaybeId;
  onSelectRun: (runId: MaybeId) => void;
  devMode: boolean;
};

function formatDateTime(value?: string): string {
  if (!value) return "--";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("pt-BR", { hour12: false });
}

export default function WorkspacePanel({ activeThreadId, activeRunId, onSelectRun, devMode }: Props) {
  const {
    profiles,
    runs,
    runDetail,
    timeline,
    primaryArtifact,
    loadingPrimaryArtifact,
    startRun,
    resumeRun,
    refreshRuns,
    refreshTimeline,
    refreshPrimaryArtifact,
  } = useWorkspace(activeThreadId, activeRunId);

  const [selectedProfile, setSelectedProfile] = useState<string>("");
  const [requestText, setRequestText] = useState<string>("");
  const [activeView, setActiveView] = useState<WorkspaceView>("studio");

  useEffect(() => {
    setActiveView(readWorkspaceView(activeThreadId));
  }, [activeThreadId]);

  useEffect(() => {
    writeWorkspaceView(activeThreadId, activeView);
  }, [activeThreadId, activeView]);

  const sortedTimeline = useMemo(
    () => [...timeline].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)),
    [timeline]
  );
  const activeRun = runs.find((run) => run.run_id === activeRunId) ?? runs[0] ?? null;
  const activeStatus = runDetail?.status ?? activeRun?.status ?? "";
  const activeRequestText = activeRun?.request_text ?? "";
  const canRegenerate = Boolean(activeThreadId && activeRun?.requested_mode && activeRequestText.trim());

  const versionsSection = (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Historico
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Versoes</h3>
        </div>
        <p className="text-xs uppercase tracking-[0.14em] text-slate-400">Selecione uma versao para revisar</p>
      </div>
      {runs.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">Nenhuma versao encontrada.</p>
      ) : (
        <div className="mt-3 flex flex-col gap-2">
          {runs.map((r, idx) => (
            <div
              key={r.run_id}
              onClick={() => onSelectRun(r.run_id)}
              className={`cursor-pointer rounded-2xl border p-3 text-sm transition-colors ${
                activeRunId === r.run_id
                  ? "border-[var(--vm-primary)] bg-[var(--vm-warm)]"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-900">
                  {toHumanRunName({
                    index: idx + 1,
                    requestText: r.request_text || r.requested_mode,
                    createdAt: r.created_at,
                  })}
                </span>
                <span className="text-xs font-semibold text-slate-500">{toHumanStatus(r.status)}</span>
              </div>
              {devMode ? <div className="text-[11px] text-slate-400 mt-1">ID: {r.run_id}</div> : null}
            </div>
          ))}
        </div>
      )}
    </section>
  );

  const timelineSection = (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Bastidores
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Timeline</h3>
        </div>
      </div>
      {sortedTimeline.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">Nenhum evento na timeline.</p>
      ) : (
        <div className="mt-3 flex flex-col gap-2 max-h-64 overflow-auto">
          {sortedTimeline.map((event) => (
            <div key={event.event_id} className="rounded-lg border border-slate-200 p-2 text-xs">
              <div className="font-semibold text-slate-700">{toHumanTimelineEvent(event.event_type)}</div>
              <div className="text-slate-500">{formatDateTime(event.created_at)}</div>
              {devMode ? (
                <div className="text-[11px] text-slate-400 mt-1">
                  {event.event_type} · {event.event_id}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </section>
  );

  const deliverableCanvas = (
    <section className="rounded-[1.75rem] border border-[color:var(--vm-line)] bg-white/95 p-4 shadow-[0_18px_40px_rgba(22,32,51,0.08)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Entregavel principal
          </p>
          <h2 className="mt-2 font-serif text-2xl text-slate-900">Versao ativa</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">{summarizeRequestText(activeRequestText)}</p>
        </div>
        <div className="rounded-full border border-slate-200 bg-[var(--vm-warm)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--vm-primary-strong)]">
          {activeStatus ? toHumanStatus(activeStatus) : "Sem versao selecionada"}
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <div className="rounded-[1.5rem] border border-slate-200 bg-[var(--vm-warm)]/45 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Objetivo do pedido
              </p>
              <p className="mt-2 text-sm font-medium text-slate-900">{summarizeRequestText(activeRequestText)}</p>
            </div>
            <div>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Ultima atualizacao</p>
              <p className="mt-2 text-sm font-medium text-slate-900">{formatDateTime(activeRun?.created_at)}</p>
            </div>
          </div>

          <div className="mt-4 flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-slate-700">Objetivo do pedido</label>
              <input
                type="text"
                value={requestText}
                onChange={(e) => setRequestText(e.target.value)}
                disabled={!activeThreadId}
                placeholder="Descreva o que voce precisa..."
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 disabled:opacity-50"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-slate-700">Perfil</label>
              <select
                value={selectedProfile}
                onChange={(e) => setSelectedProfile(e.target.value)}
                disabled={!activeThreadId}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
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
                className="rounded-xl bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Gerar nova versao
              </button>
              <button
                type="button"
                disabled={!canRegenerate}
                onClick={() => {
                  if (!activeRun?.requested_mode) return;
                  startRun({ mode: activeRun.requested_mode, requestText: activeRequestText });
                }}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
              >
                Regenerar
              </button>
              {activeRunId ? (
                <button
                  type="button"
                  onClick={() => onSelectRun(null)}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900"
                >
                  Limpar versao ativa
                </button>
              ) : null}
              <button
                type="button"
                disabled={!activeThreadId}
                onClick={() => {
                  refreshRuns();
                  refreshTimeline();
                  refreshPrimaryArtifact();
                }}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
              >
                Recarregar
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
          {loadingPrimaryArtifact ? (
            <p className="text-sm text-slate-600">Carregando artefato...</p>
          ) : primaryArtifact?.content ? (
            <ArtifactPreview
              content={primaryArtifact.content}
              filename={`${primaryArtifact.stageDir}-${primaryArtifact.artifactPath}`}
            />
          ) : (
            <p className="text-sm text-slate-600">
              {activeRun
                ? "Nenhum artefato principal disponivel para a versao selecionada."
                : "Selecione uma versao para abrir o preview dominante do entregavel."}
            </p>
          )}
        </div>
      </div>
    </section>
  );

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-slate-600">
            <span className="font-semibold text-slate-700">Glossario:</span> Cliente = empresa, Campanha =
            iniciativa, Job = frente de trabalho, Versao = execucao do workflow.
          </div>
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
            <button
              type="button"
              onClick={() => setActiveView("chat")}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                activeView === "chat" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600"
              }`}
            >
              Chat
            </button>
            <button
              type="button"
              onClick={() => setActiveView("studio")}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                activeView === "studio" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600"
              }`}
            >
              Studio
            </button>
          </div>
        </div>
      </section>

      {activeView === "chat" ? (
        <>
          <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Chat</h2>
            <p className="mt-2 text-sm text-slate-600">
              Fluxo linear: descreva a solicitacao, escolha o perfil e gere uma nova versao.
            </p>
          </section>
          {deliverableCanvas}
          {versionsSection}
          {activeRunId && runDetail && canResumeRunStatus(runDetail.status) ? (
            <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-amber-900">Acao necessaria</h2>
              <p className="mt-2 text-sm text-amber-800">
                Esta versao esta aguardando continuidade apos aprovacao. Clique para prosseguir o workflow.
              </p>
              <button
                type="button"
                onClick={resumeRun}
                className="mt-3 rounded bg-amber-600 px-3 py-2 text-sm font-medium text-white"
              >
                Aprovar e continuar
              </button>
            </section>
          ) : null}
          {timelineSection}
        </>
      ) : (
        <>
          {deliverableCanvas}
          {versionsSection}
          {activeRunId && runDetail && canResumeRunStatus(runDetail.status) ? (
            <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-amber-900">Acao necessaria</h2>
              <p className="mt-2 text-sm text-amber-800">
                Esta versao esta aguardando continuidade apos aprovacao. Clique para prosseguir o workflow.
              </p>
              <button
                type="button"
                onClick={resumeRun}
                className="mt-3 rounded bg-amber-600 px-3 py-2 text-sm font-medium text-white"
              >
                Aprovar e continuar
              </button>
            </section>
          ) : null}
          {timelineSection}
        </>
      )}

      {activeRunId && runDetail && devMode ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900 flex justify-between">
            Debug da versao {activeRunId}
            {canResumeRunStatus(runDetail.status) && (
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
      ) : null}
    </div>
  );
}
