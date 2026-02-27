import { useEffect, useMemo, useState } from "react";
import GuidedRegenerateModal from "../quality/GuidedRegenerateModal";
import QualityScoreCard from "../quality/QualityScoreCard";
import VersionDiffPanel from "../quality/VersionDiffPanel";
import { computeQualityScore } from "../quality/score";
import ArtifactPreview from "../inbox/ArtifactPreview";
import GoldenDecisionModal from "./GoldenDecisionModal";
import {
  canResumeRunStatus,
  pickBaselineRun,
  summarizeRequestText,
  toComparisonLabel,
  toHumanRunName,
  toHumanStatus,
  toHumanTimelineEvent,
  toHumanTimelineEventDetails,
  isGoldenForRun,
  isEditorialEvent,
  filterTimelineEvents,
  TIMELINE_FILTER_LABELS,
  AUDIT_SCOPE_FILTER_LABELS,
  formatAuditEvent,
  toHumanActorRole,
  toHumanReasonCode,
  getTopReasonCode,
  formatInsightsDate,
  formatConfidence,
  getConfidenceColor,
  formatVolatility,
  getVolatilityColor,
  getTrendLabel,
  getRiskScoreColor,
  getRiskScoreBgColor,
  type BaselineSource,
  type TimelineFilter,
  type AuditScopeFilter,
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
    effectiveActiveRunId,
    runDetail,
    timeline,
    primaryArtifact,
    artifactsByRun,
    deepEvaluationByRun = {},
    editorialDecisions,
    resolvedBaseline,
    loadingPrimaryArtifact,
    startRun,
    resumeRun,
    requestDeepEvaluation,
    loadArtifactForRun,
    markGoldenDecision,
    refreshRuns,
    refreshTimeline,
    refreshPrimaryArtifact,
    editorialAudit,
    auditScopeFilter,
    setAuditScopeFilter,
    auditPagination,
    setAuditPagination,
    refreshEditorialAudit,
    editorialInsights,
    loadingInsights,
    refreshEditorialInsights,
    recommendations,
    loadingRecommendations,
    refreshRecommendations,
    executePlaybookAction,
    editorialForecast,
    loadingForecast,
    refreshEditorialForecast,
    showSuppressedActions,
    setShowSuppressedActions,
  } = useWorkspace(activeThreadId, activeRunId);

  // Use effective run id for all UI rendering (falls back to first run if activeRunId is null)
  const currentRunId = effectiveActiveRunId;

  const [selectedProfile, setSelectedProfile] = useState<string>("");
  const [requestText, setRequestText] = useState<string>("");
  const [activeView, setActiveView] = useState<WorkspaceView>("studio");
  const [guidedModalOpen, setGuidedModalOpen] = useState(false);
  const [goldenModalOpen, setGoldenModalOpen] = useState(false);
  const [goldenModalScope, setGoldenModalScope] = useState<"global" | "objective">("global");
  const [timelineFilter, setTimelineFilter] = useState<TimelineFilter>("all");

  useEffect(() => {
    setActiveView(readWorkspaceView(activeThreadId));
  }, [activeThreadId]);

  useEffect(() => {
    writeWorkspaceView(activeThreadId, activeView);
  }, [activeThreadId, activeView]);

  const sortedTimeline = useMemo(() => {
    const filtered = filterTimelineEvents(timeline, timelineFilter);
    return [...filtered].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
  }, [timeline, timelineFilter]);
  const hasActiveThread = Boolean(activeThreadId);
  const activeRun = runs.find((run) => run.run_id === currentRunId) ?? null;
  const hasActiveRun = Boolean(activeRun);
  const activeStatus = runDetail?.status ?? activeRun?.status ?? "";
  const activeRequestText = activeRun?.request_text ?? "";
  const canRegenerate = Boolean(activeThreadId && activeRun?.requested_mode && activeRequestText.trim());
  const activeArtifactText = primaryArtifact?.content ?? activeRequestText;
  const activeScore = useMemo(() => computeQualityScore(activeArtifactText), [activeArtifactText]);
  const activeDeepEvaluation = activeRun ? deepEvaluationByRun[activeRun.run_id] : null;
  const currentScore = activeDeepEvaluation?.score ?? activeScore;
  const showDeepEvalFallback = Boolean(
    activeDeepEvaluation && (activeDeepEvaluation.status === "error" || activeDeepEvaluation.fallbackApplied)
  );

  // Use resolved baseline from API, fallback to local calculation
  const baselineSource: BaselineSource = resolvedBaseline?.source ?? "none";
  const baselineRunId = resolvedBaseline?.baseline_run_id ?? null;
  const baselineRun = baselineRunId ? runs.find((r) => r.run_id === baselineRunId) ?? null : null;
  const baselineArtifact = baselineRun ? artifactsByRun?.[baselineRun.run_id] ?? null : null;
  const baselineText = baselineArtifact?.content ?? baselineRun?.request_text ?? "";
  const baselineScore = useMemo(
    () => (baselineText.trim() ? computeQualityScore(baselineText) : null),
    [baselineText]
  );
  const weakPoints = useMemo(() => currentScore.recommendations.slice(0, 3), [currentScore.recommendations]);
  const canvasSummary = !hasActiveThread
    ? "Escolha um job para abrir o canvas editorial."
    : hasActiveRun
      ? summarizeRequestText(activeRequestText)
      : "Ainda nao existe uma versao ativa para este job.";

  // Check golden status for active run
  const activeRunGoldenStatus = activeRun
    ? isGoldenForRun(activeRun.run_id, editorialDecisions)
    : { isGlobalGolden: false, isObjectiveGolden: false };

  useEffect(() => {
    if (!baselineRun) return;
    if (Object.prototype.hasOwnProperty.call(artifactsByRun ?? {}, baselineRun.run_id)) return;
    loadArtifactForRun?.(baselineRun.run_id);
  }, [baselineRun, artifactsByRun, loadArtifactForRun]);

  const handleMarkGolden = async (scope: "global" | "objective") => {
    if (!activeRun) return;
    setGoldenModalScope(scope);
    setGoldenModalOpen(true);
  };

  const handleGoldenSubmit = async ({ justification }: { justification: string }) => {
    if (!activeRun) return;
    await markGoldenDecision({
      runId: activeRun.run_id,
      scope: goldenModalScope,
      objectiveKey: activeRun.objective_key,
      justification,
    });
    setGoldenModalOpen(false);
  };

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
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          {hasActiveThread
            ? "Nenhuma versao encontrada. Gere a primeira entrega para inaugurar a timeline editorial."
            : "Escolha um job para abrir o historico desta frente."}
        </div>
      ) : (
        <div className="mt-3 flex flex-col gap-2">
          {runs.map((r, idx) => {
            const goldenStatus = isGoldenForRun(r.run_id, editorialDecisions);
            return (
              <div
                key={r.run_id}
                onClick={() => onSelectRun(r.run_id)}
                className={`cursor-pointer rounded-2xl border p-3 text-sm transition-all duration-200 ${
                  currentRunId === r.run_id
                    ? "border-[var(--vm-primary)] bg-[var(--vm-warm)] shadow-sm ring-1 ring-[color:var(--vm-primary)]/20"
                    : "border-slate-200 bg-white hover:-translate-y-0.5 hover:border-slate-300 hover:bg-slate-50"
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
                {/* Golden Badges */}
                <div className="mt-2 flex flex-wrap gap-1">
                  {goldenStatus.isGlobalGolden && (
                    <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                      Golden global
                    </span>
                  )}
                  {goldenStatus.isObjectiveGolden && (
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                      Golden objetivo
                    </span>
                  )}
                </div>
                {devMode ? <div className="text-[11px] text-slate-400 mt-1">ID: {r.run_id}</div> : null}
              </div>
            );
          })}
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
        {/* Timeline Filter */}
        <div className="flex gap-1">
          {( ["all", "editorial"] as TimelineFilter[] ).map((filter) => (
            <button
              key={filter}
              onClick={() => setTimelineFilter(filter)}
              className={`px-2 py-1 text-xs rounded-full transition-colors ${
                timelineFilter === filter
                  ? "bg-[var(--vm-primary)] text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {TIMELINE_FILTER_LABELS[filter]}
            </button>
          ))}
        </div>
      </div>
      {sortedTimeline.length === 0 ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          {hasActiveThread
            ? timelineFilter === "editorial"
              ? "Nenhum evento editorial na timeline."
              : "Nenhum evento na timeline ainda. As etapas desta versao aparecerao aqui."
            : "A timeline sera preenchida quando um job ativo entrar em execucao."}
        </div>
      ) : (
        <div className="mt-3 flex flex-col gap-2 max-h-64 overflow-auto">
          {sortedTimeline.map((event) => {
            const eventDetails = toHumanTimelineEventDetails({
              event_type: event.event_type,
              payload: event.payload,
              actor_id: event.actor_id,
            });
            const isEditorial = isEditorialEvent(event.event_type);
            return (
              <div key={event.event_id} className={`rounded-lg border p-2 text-xs ${isEditorial ? "border-amber-200 bg-amber-50/50" : "border-slate-200"}`}>
                <div className="font-semibold text-slate-700">{eventDetails.label}</div>
                <div className="text-slate-500">{formatDateTime(event.created_at)}</div>
                {/* Actor and Justification for editorial events */}
                {isEditorial && (eventDetails.actor || eventDetails.justification) ? (
                  <div className="mt-1 text-[11px] text-slate-600">
                    {eventDetails.actor ? (
                      <span className="font-medium">por {eventDetails.actor}</span>
                    ) : null}
                    {eventDetails.actor && eventDetails.justification ? (
                      <span className="mx-1">·</span>
                    ) : null}
                    {eventDetails.justification ? (
                      <span className="italic">&quot;{eventDetails.justification.slice(0, 60)}{eventDetails.justification.length > 60 ? "..." : ""}&quot;</span>
                    ) : null}
                  </div>
                ) : null}
                {devMode ? (
                  <div className="text-[11px] text-slate-400 mt-1">
                    {event.event_type} · {event.event_id}
                  </div>
                ) : null}
              </div>
            );
          })}
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
          <p className="mt-2 max-w-2xl text-sm text-slate-600">{canvasSummary}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="rounded-full border border-slate-200 bg-[var(--vm-warm)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--vm-primary-strong)]">
            {activeStatus ? toHumanStatus(activeStatus) : hasActiveThread ? "Sem versao selecionada" : "Selecione um job"}
          </div>
          {/* Golden Badges for active run */}
          {activeRunGoldenStatus.isGlobalGolden && (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              Golden global
            </span>
          )}
          {activeRunGoldenStatus.isObjectiveGolden && (
            <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
              Golden objetivo
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <div className="rounded-[1.5rem] border border-slate-200 bg-[var(--vm-warm)]/45 p-4 transition-all duration-200">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Objetivo do pedido
              </p>
              <p className="mt-2 text-sm font-medium text-slate-900">{canvasSummary}</p>
            </div>
            <div>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Ultima atualizacao</p>
              <p className="mt-2 text-sm font-medium text-slate-900">{formatDateTime(activeRun?.created_at)}</p>
            </div>
          </div>

          {!hasActiveThread || !hasActiveRun ? (
            <div className="mt-4 rounded-[1.25rem] border border-dashed border-slate-300 bg-white/80 p-4">
              <p className="text-sm font-semibold text-slate-900">
                {!hasActiveThread ? "Escolha um job para abrir o canvas editorial." : "Ainda nao existe uma versao ativa para este job."}
              </p>
              <p className="mt-2 text-sm text-slate-600">
                {!hasActiveThread
                  ? "Use o rail da esquerda para definir cliente, campanha e job. O preview dominante aparece assim que a frente estiver contextualizada."
                  : "Defina o pedido, selecione um perfil e gere a primeira versao para destravar preview, timeline e pendencias."}
              </p>
            </div>
          ) : null}

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
              <button
                type="button"
                disabled={!canRegenerate}
                onClick={() => setGuidedModalOpen(true)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
              >
                Regenerar guiado
              </button>
              <button
                type="button"
                disabled={!activeRun?.run_id || !activeArtifactText.trim() || activeDeepEvaluation?.status === "loading"}
                onClick={() => {
                  if (!activeRun?.run_id) return;
                  requestDeepEvaluation?.(activeRun.run_id, activeArtifactText);
                }}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
              >
                {activeDeepEvaluation?.status === "loading" ? "Avaliando..." : "Avaliar profundo"}
              </button>
              {currentRunId ? (
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

            {/* Golden Decision Buttons */}
            {hasActiveRun && (
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
                <span className="text-xs font-medium text-slate-600">Marcar como:</span>
                <button
                  type="button"
                  disabled={activeRunGoldenStatus.isGlobalGolden}
                  onClick={() => handleMarkGolden("global")}
                  className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800 disabled:opacity-50 hover:bg-amber-100"
                >
                  {activeRunGoldenStatus.isGlobalGolden ? "Golden global" : "Definir como golden global"}
                </button>
                <button
                  type="button"
                  disabled={activeRunGoldenStatus.isObjectiveGolden}
                  onClick={() => handleMarkGolden("objective")}
                  className="rounded-xl border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-800 disabled:opacity-50 hover:bg-blue-100"
                >
                  {activeRunGoldenStatus.isObjectiveGolden ? "Golden objetivo" : "Definir como golden deste objetivo"}
                </button>
              </div>
            )}
          </div>

          {hasActiveRun ? (
            <div className="mt-4 space-y-3">
              {showDeepEvalFallback ? (
                <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Avaliacao profunda indisponivel. Exibindo score heuristico local.
                </p>
              ) : null}
              {/* Baseline Source Label */}
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                {toComparisonLabel(baselineSource)}
              </p>
              <QualityScoreCard current={currentScore} baseline={baselineScore} />
              {baselineScore ? (
                <VersionDiffPanel baselineText={baselineText} currentText={activeArtifactText} />
              ) : (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white/80 p-3 text-sm text-slate-600">
                  Gere pelo menos duas versoes para habilitar o diff textual.
                </div>
              )}
            </div>
          ) : null}
        </div>

        <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 transition-all duration-200">
          {loadingPrimaryArtifact ? (
            <div className="space-y-4" aria-live="polite">
              <div className="h-3 w-36 animate-pulse rounded-full bg-slate-200" />
              <div className="rounded-[1.25rem] border border-slate-200 bg-slate-50/80 p-4">
                <div className="h-4 w-2/3 animate-pulse rounded-full bg-slate-200" />
                <div className="mt-3 h-3 w-full animate-pulse rounded-full bg-slate-100" />
                <div className="mt-2 h-3 w-11/12 animate-pulse rounded-full bg-slate-100" />
                <div className="mt-2 h-3 w-4/5 animate-pulse rounded-full bg-slate-100" />
              </div>
              <p className="text-sm text-slate-600">Preparando o preview da versao ativa...</p>
            </div>
          ) : primaryArtifact?.content ? (
            <ArtifactPreview
              content={primaryArtifact.content}
              filename={`${primaryArtifact.stageDir}-${primaryArtifact.artifactPath}`}
            />
          ) : (
            <div className="rounded-[1.25rem] border border-dashed border-slate-300 bg-slate-50/90 p-5">
              <p className="text-sm font-semibold text-slate-900">
                {activeRun
                  ? "Nenhum artefato principal disponivel para a versao selecionada."
                  : hasActiveThread
                    ? "Ainda nao existe uma versao ativa para este job."
                    : "Escolha um job para abrir o canvas editorial."}
              </p>
              <p className="mt-2 text-sm text-slate-600">
                {activeRun
                  ? "Recarregue a versao ou acompanhe a timeline para quando o entregavel principal estiver pronto."
                  : hasActiveThread
                    ? "Gere ou selecione uma versao para abrir o preview dominante do entregavel."
                    : "A leitura principal da entrega aparece aqui assim que uma frente estiver selecionada."}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );

  const editorialAuditSection = (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Auditoria
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Decisoes Editoriais</h3>
        </div>
        {/* Scope Filter */}
        <div className="flex gap-1">
          {(["all", "global", "objective"] as AuditScopeFilter[]).map((filter) => (
            <button
              key={filter}
              onClick={() => {
                setAuditScopeFilter(filter);
                setAuditPagination({ ...auditPagination, offset: 0 });
                refreshEditorialAudit({ scope: filter, limit: auditPagination.limit, offset: 0 });
              }}
              className={`px-2 py-1 text-xs rounded-full transition-colors ${
                auditScopeFilter === filter
                  ? "bg-[var(--vm-primary)] text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {AUDIT_SCOPE_FILTER_LABELS[filter]}
            </button>
          ))}
        </div>
      </div>
      
      {!editorialAudit || editorialAudit.events.length === 0 ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          {hasActiveThread
            ? "Nenhuma decisao editorial registrada. As marcacoes golden aparecerao aqui."
            : "Escolha um job para visualizar o historico de decisoes editoriais."}
        </div>
      ) : (
        <>
          <div className="mt-3 flex flex-col gap-2 max-h-80 overflow-auto">
            {editorialAudit.events.map((event) => {
              const display = formatAuditEvent(event);
              return (
                <div
                  key={display.eventId}
                  className={`rounded-lg border p-3 text-sm ${
                    display.scope === "global"
                      ? "border-amber-200 bg-amber-50/50"
                      : "border-blue-200 bg-blue-50/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">
                      {display.scope === "global" ? "Golden Global" : "Golden Objetivo"}
                    </span>
                    <span className="text-xs text-slate-500">{display.formattedDate}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-600">
                    <span className="font-medium">Run:</span> {display.runId.slice(0, 12)}...
                  </div>
                  <div className="mt-1 text-xs text-slate-600">
                    <span className="font-medium">Actor:</span>{" "}
                    {display.actorId} ({toHumanActorRole(display.actorRole)})
                  </div>
                  {display.objectiveKey && (
                    <div className="mt-1 text-xs text-slate-600">
                      <span className="font-medium">Objetivo:</span> {display.objectiveKey}
                    </div>
                  )}
                  {display.justification && (
                    <div className="mt-2 text-xs text-slate-700 italic">
                      &quot;{display.justification}&quot;
                    </div>
                  )}
                  {devMode && (
                    <div className="mt-2 text-[10px] text-slate-400">
                      {display.eventId} · {display.eventType}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          
          {/* Pagination */}
          {editorialAudit.total > auditPagination.limit && (
            <div className="mt-3 flex items-center justify-between">
              <button
                type="button"
                disabled={auditPagination.offset === 0}
                onClick={() => {
                  const newOffset = Math.max(0, auditPagination.offset - auditPagination.limit);
                  setAuditPagination({ ...auditPagination, offset: newOffset });
                  refreshEditorialAudit({
                    scope: auditScopeFilter,
                    limit: auditPagination.limit,
                    offset: newOffset,
                  });
                }}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
              >
                Anterior
              </button>
              <span className="text-xs text-slate-500">
                {auditPagination.offset + 1} -{" "}
                {Math.min(auditPagination.offset + auditPagination.limit, editorialAudit.total)} de{" "}
                {editorialAudit.total}
              </span>
              <button
                type="button"
                disabled={auditPagination.offset + auditPagination.limit >= editorialAudit.total}
                onClick={() => {
                  const newOffset = auditPagination.offset + auditPagination.limit;
                  setAuditPagination({ ...auditPagination, offset: newOffset });
                  refreshEditorialAudit({
                    scope: auditScopeFilter,
                    limit: auditPagination.limit,
                    offset: newOffset,
                  });
                }}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
              >
                Proximo
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );

  const editorialInsightsSection = (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Governanca
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Insights Editoriais</h3>
        </div>
        <button
          type="button"
          onClick={() => refreshEditorialInsights()}
          disabled={loadingInsights || !hasActiveThread}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
        >
          {loadingInsights ? "Atualizando..." : "Atualizar insights"}
        </button>
      </div>

      {!hasActiveThread ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          Escolha um job para visualizar os insights de governanca editorial.
        </div>
      ) : loadingInsights ? (
        <div className="mt-3 flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-[var(--vm-primary)]" />
        </div>
      ) : !editorialInsights ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          Erro ao carregar insights. Tente atualizar.
        </div>
      ) : (
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {/* Total de marcacoes */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Total de Marcações
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {editorialInsights.totals.marked_total}
            </p>
            <div className="mt-1 flex gap-2 text-xs text-slate-600">
              <span className="text-amber-600">{editorialInsights.totals.by_scope.global} global</span>
              <span>·</span>
              <span className="text-blue-600">{editorialInsights.totals.by_scope.objective} objetivo</span>
            </div>
          </div>

          {/* Deny total */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Negados por Policy
            </p>
            <p className={`mt-1 text-2xl font-bold ${editorialInsights.policy.denied_total > 0 ? "text-red-600" : "text-slate-900"}`}>
              {editorialInsights.policy.denied_total}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              tentativas bloqueadas
            </p>
          </div>

          {/* Baseline none rate */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Sem Baseline
            </p>
            <p className="mt-1 text-2xl font-bold text-slate-900">
              {(() => {
                const resolved = editorialInsights.baseline.resolved_total;
                const noneCount = editorialInsights.baseline.by_source.none;
                if (resolved === 0) return "0%";
                return `${Math.round((noneCount / resolved) * 100)}%`;
              })()}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {editorialInsights.baseline.by_source.none} de {editorialInsights.baseline.resolved_total} resoluções
            </p>
          </div>

          {/* Top reason code */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Motivo Principal
            </p>
            {(() => {
              const top = getTopReasonCode(editorialInsights.totals.by_reason_code);
              if (!top || editorialInsights.totals.marked_total === 0) {
                return <p className="mt-1 text-lg font-medium text-slate-400">Nenhum</p>;
              }
              return (
                <>
                  <p className="mt-1 text-lg font-bold text-slate-900">
                    {toHumanReasonCode(top.code)}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {top.count} marcações ({Math.round((top.count / editorialInsights.totals.marked_total) * 100)}%)
                  </p>
                </>
              );
            })()}
          </div>

          {/* Ultima marcacao */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 sm:col-span-2 lg:col-span-4">
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Última Marcação
            </p>
            <div className="mt-1 flex items-center justify-between">
              <p className="text-sm font-medium text-slate-900">
                {formatInsightsDate(editorialInsights.recency.last_marked_at)}
              </p>
              {editorialInsights.recency.last_actor_id && (
                <p className="text-xs text-slate-600">
                  por {editorialInsights.recency.last_actor_id}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );

  const editorialForecastSection = (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Governanca
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Forecast de Risco</h3>
        </div>
        <button
          type="button"
          onClick={() => refreshEditorialForecast()}
          disabled={loadingForecast || !hasActiveThread}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
        >
          {loadingForecast ? "Atualizando..." : "Recarregar forecast"}
        </button>
      </div>

      {!hasActiveThread ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          Escolha um job para visualizar o forecast de risco editorial.
        </div>
      ) : loadingForecast ? (
        <div className="mt-3 flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-[var(--vm-primary)]" />
        </div>
      ) : !editorialForecast ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          Erro ao carregar forecast. Tente atualizar.
        </div>
      ) : (
        <div className="mt-3 space-y-3">
          {/* Risk Score Card */}
          <div className={`rounded-xl border p-4 ${getRiskScoreBgColor(editorialForecast.risk_score)}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-600">Risk Score</p>
                <p className={`text-3xl font-bold ${getRiskScoreColor(editorialForecast.risk_score)}`}>
                  {editorialForecast.risk_score}
                  <span className="text-sm font-normal text-slate-500">/100</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs font-medium text-slate-600">Tendência</p>
                <p className="text-lg font-medium text-slate-800">{getTrendLabel(editorialForecast.trend)}</p>
              </div>
            </div>
            <div className="mt-3">
              <p className="text-sm font-medium text-slate-800">{editorialForecast.recommended_focus}</p>
            </div>
          </div>

          {/* Calibration Metrics */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Confiança
                </p>
                <span className="text-xs text-slate-400" title="Quão confiável é este forecast baseado nos dados disponíveis">?</span>
              </div>
              <p className={`mt-1 text-2xl font-bold ${getConfidenceColor(editorialForecast.confidence)}`}>
                {formatConfidence(editorialForecast.confidence)}
              </p>
              <p className="text-xs text-slate-500">
                {(editorialForecast.confidence * 100).toFixed(0)}%
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Volatilidade
                </p>
                <span className="text-xs text-slate-400" title="Quão instável é o padrão de eventos recentes">?</span>
              </div>
              <p className={`mt-1 text-2xl font-bold ${getVolatilityColor(editorialForecast.volatility)}`}>
                {formatVolatility(editorialForecast.volatility)}
              </p>
              <p className="text-xs text-slate-500">
                {editorialForecast.volatility}/100
              </p>
            </div>
          </div>

          {/* Calibration Notes */}
          {editorialForecast.calibration_notes.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
              <p className="text-xs font-medium text-slate-600 mb-2">Como este score foi calculado:</p>
              <ul className="space-y-1">
                {editorialForecast.calibration_notes.map((note, idx) => (
                  <li key={idx} className="text-xs text-slate-600 flex items-start gap-2">
                    <span className="text-slate-400">•</span>
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Drivers */}
          {editorialForecast.drivers.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
              <p className="text-xs font-medium text-slate-600 mb-2">Fatores de risco:</p>
              <div className="flex flex-wrap gap-1">
                {editorialForecast.drivers.map((driver, idx) => (
                  <span
                    key={idx}
                    className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
                  >
                    {driver}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );

  const editorialRecommendationsSection = (
    <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
            Governanca
          </p>
          <h3 className="mt-2 font-serif text-xl text-slate-900">Ações Recomendadas</h3>
        </div>
        <div className="flex items-center gap-2">
          {/* Toggle for suppressed actions */}
          <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={showSuppressedActions}
              onChange={(e) => setShowSuppressedActions(e.target.checked)}
              className="rounded border-slate-300"
            />
            Mostrar suprimidas
          </label>
          <button
            type="button"
            onClick={() => refreshRecommendations()}
            disabled={loadingRecommendations || !hasActiveThread}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
          >
            {loadingRecommendations ? "Atualizando..." : "Recarregar ações"}
          </button>
        </div>
      </div>

      {!hasActiveThread ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          Escolha um job para visualizar as ações recomendadas.
        </div>
      ) : loadingRecommendations ? (
        <div className="mt-3 flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-[var(--vm-primary)]" />
        </div>
      ) : !recommendations ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          Erro ao carregar recomendações. Tente atualizar.
        </div>
      ) : recommendations.recommendations.length === 0 ? (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-4 text-sm text-slate-600">
          Nenhuma ação recomendada no momento. O sistema analisará os KPIs periodicamente.
        </div>
      ) : (
        <div className="mt-3 space-y-3">
          {recommendations.recommendations
            .filter((rec) => showSuppressedActions || !rec.suppressed)
            .map((rec, idx) => (
            <div
              key={`${rec.action_id}-${idx}`}
              className={`rounded-xl border p-4 ${
                rec.suppressed
                  ? "border-slate-200 bg-slate-100/50 opacity-60"
                  : rec.severity === "critical"
                  ? "border-red-200 bg-red-50/50"
                  : rec.severity === "warning"
                  ? "border-amber-200 bg-amber-50/50"
                  : "border-slate-200 bg-slate-50/50"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        rec.suppressed
                          ? "bg-slate-200 text-slate-600"
                          : rec.severity === "critical"
                          ? "bg-red-100 text-red-700"
                          : rec.severity === "warning"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {rec.suppressed ? "Suprimida" : rec.severity === "critical" ? "Crítico" : rec.severity === "warning" ? "Atenção" : "Info"}
                    </span>
                    <h4 className={`font-semibold ${rec.suppressed ? "text-slate-500" : "text-slate-900"}`}>{rec.title}</h4>
                  </div>
                  <p className={`mt-1 text-sm ${rec.suppressed ? "text-slate-500" : "text-slate-600"}`}>{rec.description}</p>
                  <p className="mt-1 text-xs text-slate-500">Motivo: {rec.reason}</p>
                  {rec.suppressed && rec.suppression_reason && (
                    <p className="mt-1 text-xs text-slate-400 italic">
                      Suprimida: {rec.suppression_reason}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => executePlaybookAction?.(rec.action_id, currentRunId || undefined)}
                  disabled={!executePlaybookAction || rec.suppressed}
                  className="rounded-lg bg-[var(--vm-primary)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:opacity-90"
                >
                  Executar
                </button>
              </div>
            </div>
          ))}
          {/* Show count of suppressed actions when not showing them */}
          {!showSuppressedActions && recommendations.recommendations.some((r) => r.suppressed) && (
            <p className="text-xs text-slate-400 text-center">
              {recommendations.recommendations.filter((r) => r.suppressed).length} ação(ões) suprimida(s) oculta(s)
            </p>
          )}
        </div>
      )}
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
              className={`rounded-md px-3 py-1 text-xs font-medium transition-all duration-200 ${
                activeView === "chat" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600"
              }`}
            >
              Chat
            </button>
            <button
              type="button"
              onClick={() => setActiveView("studio")}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-all duration-200 ${
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
          {currentRunId && runDetail && canResumeRunStatus(runDetail.status) ? (
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
          {editorialAuditSection}
          {editorialInsightsSection}
          {editorialForecastSection}
          {editorialRecommendationsSection}
        </>
      ) : (
        <>
          {deliverableCanvas}
          {versionsSection}
          {currentRunId && runDetail && canResumeRunStatus(runDetail.status) ? (
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
          {editorialAuditSection}
          {editorialInsightsSection}
          {editorialForecastSection}
          {editorialRecommendationsSection}
        </>
      )}

      <GuidedRegenerateModal
        isOpen={guidedModalOpen}
        baseRequest={activeRequestText}
        weakPoints={weakPoints}
        onClose={() => setGuidedModalOpen(false)}
        onSubmit={(payload) => {
          if (!activeRun?.requested_mode) return;
          startRun({ mode: activeRun.requested_mode, requestText: payload.requestText });
          setGuidedModalOpen(false);
        }}
      />

      <GoldenDecisionModal
        isOpen={goldenModalOpen}
        scope={goldenModalScope}
        onClose={() => setGoldenModalOpen(false)}
        onSubmit={handleGoldenSubmit}
      />

      {currentRunId && runDetail && devMode ? (
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
