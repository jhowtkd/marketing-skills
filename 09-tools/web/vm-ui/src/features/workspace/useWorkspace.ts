import { useEffect, useState } from "react";
import {
  WorkflowApi,
  TimelineApi,
  ArtifactApi,
  QualityApi,
  EditorialApi,
  SloApi,
  FirstRunApi,
  CopilotApi,
  fetchTyped,
  postTyped,
} from "../../api/typed-client";
import { computeQualityScore } from "../quality/score";
import type { QualityScore } from "../quality/types";
import { mapTimelineResponse } from "./adapters";
import type {
  WorkflowProfile,
  WorkflowRun,
  TimelineEvent,
  PrimaryArtifact,
  DeepEvaluationApiPayload,
  EditorialDecisions,
  ResolvedBaseline,
  EditorialAuditResponse,
  EditorialInsights,
  EditorialRecommendations,
  EditorialForecast,
  EditorialSLO,
  EditorialDrift,
  AutoRemediationEvent,
  PlaybookExecuteResponse,
  FirstRunRecommendation,
  FirstRunOutcomes,
  CopilotSegmentStatus,
  CopilotSuggestion,
  CopilotFeedbackPayload,
} from "../../types/api";

export type DeepEvaluationState = {
  status: "loading" | "ready" | "error";
  score: QualityScore;
  fallbackApplied: boolean;
  error: string | null;
};

// Re-export types from api.ts for backward compatibility
export type {
  WorkflowProfile,
  WorkflowRun,
  TimelineEvent,
  PrimaryArtifact,
  EditorialDecisions,
  ResolvedBaseline,
  EditorialAuditEvent,
  EditorialAuditResponse,
  EditorialInsights,
  EditorialRecommendation,
  EditorialRecommendations,
  EditorialForecast,
  EditorialSLO,
  EditorialDrift,
  FirstRunRecommendationItem,
  FirstRunRecommendation,
  FirstRunOutcomeAggregate,
  FirstRunOutcomes,
  AutoRemediationEvent,
} from "../../types/api";

export function buildStartRunPayload(input: { mode: string; requestText: string }) {
  return { mode: input.mode, request_text: input.requestText.trim() };
}

function normalizeQualityScore(raw: Partial<QualityScore> | undefined, fallback: QualityScore): QualityScore {
  if (!raw || typeof raw !== "object") return fallback;
  const criteria = raw.criteria ?? fallback.criteria;
  return {
    overall: typeof raw.overall === "number" ? raw.overall : fallback.overall,
    criteria: {
      completude: typeof criteria.completude === "number" ? criteria.completude : fallback.criteria.completude,
      estrutura: typeof criteria.estrutura === "number" ? criteria.estrutura : fallback.criteria.estrutura,
      clareza: typeof criteria.clareza === "number" ? criteria.clareza : fallback.criteria.clareza,
      cta: typeof criteria.cta === "number" ? criteria.cta : fallback.criteria.cta,
      acionabilidade:
        typeof criteria.acionabilidade === "number" ? criteria.acionabilidade : fallback.criteria.acionabilidade,
    },
    recommendations: Array.isArray(raw.recommendations)
      ? raw.recommendations.map((item) => String(item))
      : fallback.recommendations,
    source: raw.source === "deep" || raw.source === "heuristic" ? raw.source : fallback.source,
  };
}

export async function requestDeepEvaluationForRun(input: {
  runId: string;
  artifactText: string;
}): Promise<DeepEvaluationState> {
  const fallbackScore = computeQualityScore(input.artifactText);
  try {
    const payload = await QualityApi.evaluate(input.runId);
    return {
      status: "ready",
      score: normalizeQualityScore(payload.score, fallbackScore),
      fallbackApplied: Boolean(payload.fallback_applied),
      error: payload.fallback_applied ? String(payload.fallback_reason ?? "deep evaluation unavailable") : null,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "deep evaluation unavailable";
    return {
      status: "error",
      score: fallbackScore,
      fallbackApplied: true,
      error: message,
    };
  }
}

export function useWorkspace(activeThreadId: string | null, activeRunId: string | null) {
  const [profiles, setProfiles] = useState<WorkflowProfile[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [runDetail, setRunDetail] = useState<unknown>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [primaryArtifact, setPrimaryArtifact] = useState<PrimaryArtifact | null>(null);
  const [artifactsByRun, setArtifactsByRun] = useState<Record<string, PrimaryArtifact | null>>({});
  const [deepEvaluationByRun, setDeepEvaluationByRun] = useState<Record<string, DeepEvaluationState>>({});
  const [editorialDecisions, setEditorialDecisions] = useState<EditorialDecisions | null>(null);
  const [resolvedBaseline, setResolvedBaseline] = useState<ResolvedBaseline | null>(null);
  const [editorialAudit, setEditorialAudit] = useState<EditorialAuditResponse | null>(null);
  const [editorialInsights, setEditorialInsights] = useState<EditorialInsights | null>(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [recommendations, setRecommendations] = useState<EditorialRecommendations | null>(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [editorialForecast, setEditorialForecast] = useState<EditorialForecast | null>(null);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [showSuppressedActions, setShowSuppressedActions] = useState(false);
  const [editorialSLO, setEditorialSLO] = useState<EditorialSLO | null>(null);
  const [loadingSLO, setLoadingSLO] = useState(false);
  const [editorialDrift, setEditorialDrift] = useState<EditorialDrift | null>(null);
  const [loadingDrift, setLoadingDrift] = useState(false);
  const [autoRemediationHistory, setAutoRemediationHistory] = useState<AutoRemediationEvent[]>([]);
  const [loadingAutoHistory, setLoadingAutoHistory] = useState(false);
  // v12 First-run recommendation state
  const [firstRunRecommendation, setFirstRunRecommendation] = useState<FirstRunRecommendation | null>(null);
  const [loadingFirstRunRecommendation, setLoadingFirstRunRecommendation] = useState(false);
  const [firstRunOutcomes, setFirstRunOutcomes] = useState<FirstRunOutcomes | null>(null);
  const [loadingFirstRunOutcomes, setLoadingFirstRunOutcomes] = useState(false);
  const [auditScopeFilter, setAuditScopeFilter] = useState<"all" | "global" | "objective">("all");
  const [auditPagination, setAuditPagination] = useState({ limit: 20, offset: 0 });
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingRunDetail, setLoadingRunDetail] = useState(false);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [loadingPrimaryArtifact, setLoadingPrimaryArtifact] = useState(false);

  // Derive effective active run id: use provided, or first run if available
  const effectiveActiveRunId = activeRunId || runs[0]?.run_id || null;

  // Local baseline calculation (fallback when API fails)
  const localBaseline = (() => {
    if (!effectiveActiveRunId || runs.length < 2) return null;
    const activeIndex = runs.findIndex((run) => run.run_id === effectiveActiveRunId);
    if (activeIndex < 0) return null;
    // Return previous run in the list (chronologically older)
    return runs[activeIndex + 1] ?? null;
  })();

  const fetchProfiles = async () => {
    setLoadingProfiles(true);
    try {
      const data = await WorkflowApi.listProfiles();
      setProfiles(data.profiles || []);
    } catch (e) {
      console.error("Failed to fetch profiles", e);
    } finally {
      setLoadingProfiles(false);
    }
  };

  const fetchRuns = async () => {
    if (!activeThreadId) {
      setRuns([]);
      return;
    }
    setLoadingRuns(true);
    try {
      const data = await WorkflowApi.listRuns(activeThreadId);
      // Accept both 'runs' and 'items' keys for compatibility
      const runsArray = (data as { runs?: WorkflowRun[]; items?: WorkflowRun[] }).runs || 
                        (data as { runs?: WorkflowRun[]; items?: WorkflowRun[] }).items || [];
      setRuns(runsArray);
    } catch (e) {
      console.error("Failed to fetch runs", e);
    } finally {
      setLoadingRuns(false);
    }
  };

  const fetchRunDetail = async (targetRunId?: string) => {
    const runId = targetRunId || effectiveActiveRunId || runs[0]?.run_id;
    if (!runId) {
      setRunDetail(null);
      return;
    }
    setLoadingRunDetail(true);
    try {
      const data = await WorkflowApi.getRun(runId);
      setRunDetail(data);
    } catch (e) {
      console.error("Failed to fetch run detail", e);
    } finally {
      setLoadingRunDetail(false);
    }
  };

  const fetchTimeline = async () => {
    if (!activeThreadId) {
      setTimeline([]);
      return;
    }
    setLoadingTimeline(true);
    try {
      const data = await TimelineApi.getTimeline(activeThreadId);
      setTimeline(mapTimelineResponse(data));
    } catch (e) {
      console.error("Failed to fetch timeline", e);
    } finally {
      setLoadingTimeline(false);
    }
  };

  const fetchEditorialDecisions = async () => {
    if (!activeThreadId) {
      setEditorialDecisions(null);
      return;
    }
    try {
      const data = await EditorialApi.getDecisions(activeThreadId);
      setEditorialDecisions(data);
    } catch (e) {
      console.error("Failed to fetch editorial decisions", e);
      // Fallback: keep current state (null or previous)
    }
  };

  const fetchEditorialAudit = async (params?: { scope?: string; limit?: number; offset?: number }) => {
    if (!activeThreadId) {
      setEditorialAudit(null);
      return;
    }
    try {
      const data = await EditorialApi.getAudit(activeThreadId, params);
      setEditorialAudit(data);
    } catch (e) {
      console.error("Failed to fetch editorial audit", e);
      // Fallback: keep current state (null or previous)
    }
  };

  const fetchEditorialInsights = async () => {
    if (!activeThreadId) {
      setEditorialInsights(null);
      return;
    }
    setLoadingInsights(true);
    try {
      const data = await EditorialApi.getInsights(activeThreadId);
      setEditorialInsights(data);
    } catch (e) {
      console.error("Failed to fetch editorial insights", e);
      // Fallback: keep current state (null or previous)
    } finally {
      setLoadingInsights(false);
    }
  };

  const fetchRecommendations = async () => {
    if (!activeThreadId) {
      setRecommendations(null);
      return;
    }
    setLoadingRecommendations(true);
    try {
      const data = await EditorialApi.getRecommendations(activeThreadId);
      setRecommendations(data);
    } catch (e) {
      console.error("Failed to fetch recommendations", e);
      // Fallback: keep current state (null or previous)
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const fetchEditorialForecast = async () => {
    if (!activeThreadId) {
      setEditorialForecast(null);
      return;
    }
    setLoadingForecast(true);
    try {
      const data = await EditorialApi.getForecast(activeThreadId);
      setEditorialForecast(data);
    } catch (e) {
      console.error("Failed to fetch editorial forecast", e);
      // Fallback: keep current state (null or previous)
    } finally {
      setLoadingForecast(false);
    }
  };

  const fetchEditorialSLO = async (brandId: string) => {
    if (!brandId) {
      setEditorialSLO(null);
      return;
    }
    setLoadingSLO(true);
    try {
      const data = await SloApi.get(brandId);
      setEditorialSLO(data);
    } catch (e) {
      console.error("Failed to fetch editorial SLO", e);
      setEditorialSLO(null);
    } finally {
      setLoadingSLO(false);
    }
  };

  const updateEditorialSLO = async (brandId: string, updates: Partial<Omit<EditorialSLO, "brand_id" | "updated_at">>) => {
    if (!brandId) return null;
    setLoadingSLO(true);
    try {
      const data = await SloApi.update(brandId, updates);
      setEditorialSLO(data);
      return data;
    } catch (e) {
      console.error("Failed to update editorial SLO", e);
      throw e;
    } finally {
      setLoadingSLO(false);
    }
  };

  const fetchEditorialDrift = async () => {
    if (!activeThreadId) {
      setEditorialDrift(null);
      return;
    }
    setLoadingDrift(true);
    try {
      const data = await EditorialApi.getDrift(activeThreadId);
      setEditorialDrift(data);
    } catch (e) {
      console.error("Failed to fetch editorial drift", e);
      setEditorialDrift(null);
    } finally {
      setLoadingDrift(false);
    }
  };

  const triggerAutoRemediation = async () => {
    if (!activeThreadId) return null;
    try {
      const data = await EditorialApi.autoRemediate(activeThreadId);
      // Refresh auto-remediation history after trigger
      await fetchAutoRemediationHistory();
      return data;
    } catch (e) {
      console.error("Failed to trigger auto-remediation", e);
      throw e;
    }
  };

  const fetchAutoRemediationHistory = async () => {
    if (!activeThreadId) {
      setAutoRemediationHistory([]);
      return;
    }
    setLoadingAutoHistory(true);
    try {
      // Get auto-remediation events from timeline
      const data = await fetchTyped<{
        events: Array<{
          event_type: string;
          occurred_at: string;
          payload?: {
            action_id?: string;
            proposed_action?: string;
            auto_executed?: boolean;
            reason?: string;
          };
        }>;
      }>(`/api/v2/threads/${activeThreadId}/events?event_types=AutoRemediationExecuted,AutoRemediationSkipped&limit=10`);
      
      const history: AutoRemediationEvent[] = (data.events || []).map(event => ({
        event_type: event.event_type as AutoRemediationEvent["event_type"],
        occurred_at: event.occurred_at,
        action_id: event.payload?.action_id,
        proposed_action: event.payload?.proposed_action,
        auto_executed: event.payload?.auto_executed ?? false,
        reason: event.payload?.reason || "",
      }));
      
      setAutoRemediationHistory(history);
    } catch (e) {
      console.error("Failed to fetch auto-remediation history", e);
      setAutoRemediationHistory([]);
    } finally {
      setLoadingAutoHistory(false);
    }
  };

  const executePlaybookAction = async (actionId: string, runId?: string, note?: string) => {
    if (!activeThreadId) return;
    try {
      const result = await EditorialApi.executePlaybookAction(activeThreadId, actionId, runId, note);
      // Refresh recommendations after executing action
      await fetchRecommendations();
      return result;
    } catch (e) {
      console.error("Failed to execute playbook action", e);
      throw e;
    }
  };

  // v12 First-run recommendation functions
  const fetchFirstRunRecommendation = async () => {
    if (!activeThreadId) {
      setFirstRunRecommendation(null);
      return;
    }
    setLoadingFirstRunRecommendation(true);
    try {
      const data = await FirstRunApi.getRecommendation(activeThreadId);
      setFirstRunRecommendation(data);
    } catch (e) {
      console.error("Failed to fetch first-run recommendation", e);
      // Fallback: keep current state (null or previous)
    } finally {
      setLoadingFirstRunRecommendation(false);
    }
  };

  const fetchFirstRunOutcomes = async () => {
    if (!activeThreadId) {
      setFirstRunOutcomes(null);
      return;
    }
    setLoadingFirstRunOutcomes(true);
    try {
      const data = await FirstRunApi.getOutcomes(activeThreadId);
      setFirstRunOutcomes(data);
    } catch (e) {
      console.error("Failed to fetch first-run outcomes", e);
      // Fallback: keep current state (null or previous)
    } finally {
      setLoadingFirstRunOutcomes(false);
    }
  };

  const fetchResolvedBaseline = async (runId?: string) => {
    const targetRunId = runId || effectiveActiveRunId;
    if (!targetRunId) {
      setResolvedBaseline(null);
      return;
    }
    try {
      const data = await QualityApi.getBaseline(targetRunId);
      setResolvedBaseline(data);
    } catch (e) {
      console.error("Failed to fetch resolved baseline", e);
      // Fallback: use local baseline calculation
      if (localBaseline) {
        setResolvedBaseline({
          baseline_run_id: localBaseline.run_id,
          source: "previous",
          objective_key: localBaseline.objective_key || "",
        });
      } else {
        setResolvedBaseline({ baseline_run_id: null, source: "none", objective_key: "" });
      }
    }
  };

  const markGoldenDecision = async (input: {
    runId: string;
    scope: "global" | "objective";
    objectiveKey?: string;
    justification: string;
  }) => {
    if (!activeThreadId) return;
    try {
      await EditorialApi.markGolden(activeThreadId, {
        runId: input.runId,
        scope: input.scope,
        objectiveKey: input.objectiveKey,
        justification: input.justification,
      });
      // Refresh decisions after marking
      await fetchEditorialDecisions();
    } catch (e) {
      console.error("Failed to mark golden decision", e);
      throw e;
    }
  };

  const fetchPrimaryArtifactForRun = async (runId: string): Promise<PrimaryArtifact | null> => {
    return ArtifactApi.fetchPrimaryArtifact(runId);
  };

  const loadArtifactForRun = async (runId: string): Promise<PrimaryArtifact | null> => {
    if (!runId) return null;
    if (Object.prototype.hasOwnProperty.call(artifactsByRun, runId)) {
      return artifactsByRun[runId] ?? null;
    }
    const loaded = await fetchPrimaryArtifactForRun(runId);
    setArtifactsByRun((current) => ({ ...current, [runId]: loaded }));
    return loaded;
  };

  const fetchPrimaryArtifact = async (targetRunId?: string) => {
    const runId = targetRunId || effectiveActiveRunId || runs[0]?.run_id;
    if (!runId) {
      setPrimaryArtifact(null);
      return;
    }
    setLoadingPrimaryArtifact(true);
    const loaded = await fetchPrimaryArtifactForRun(runId);
    setPrimaryArtifact(loaded);
    setArtifactsByRun((current) => ({ ...current, [runId]: loaded }));
    setLoadingPrimaryArtifact(false);
  };

  const startRun = async (input: { mode: string; requestText: string }) => {
    if (!activeThreadId) return;
    try {
      await WorkflowApi.startRun(activeThreadId, input.mode, input.requestText);
      fetchRuns();
      fetchTimeline();
    } catch (e) {
      console.error("Failed to start run", e);
    }
  };

  const resumeRun = async () => {
    if (!activeRunId) return;
    try {
      await WorkflowApi.resumeRun(activeRunId);
      fetchRunDetail();
      fetchRuns();
      fetchTimeline();
    } catch (e) {
      console.error("Failed to resume run", e);
    }
  };

  const requestDeepEvaluation = async (runId: string, artifactText: string) => {
    if (!runId) return null;
    setDeepEvaluationByRun((current) => ({
      ...current,
      [runId]: {
        status: "loading",
        score: computeQualityScore(artifactText),
        fallbackApplied: false,
        error: null,
      },
    }));
    const result = await requestDeepEvaluationForRun({ runId, artifactText });
    setDeepEvaluationByRun((current) => ({ ...current, [runId]: result }));
    return result;
  };

  useEffect(() => {
    fetchProfiles();
  }, []);

  useEffect(() => {
    fetchRuns();
    fetchTimeline();
    fetchEditorialDecisions();
    fetchEditorialAudit({ scope: auditScopeFilter, ...auditPagination });
    fetchEditorialInsights();
    fetchRecommendations();
    fetchEditorialForecast();
    // v12 First-run recommendation
    fetchFirstRunRecommendation();
    fetchFirstRunOutcomes();
  }, [activeThreadId]);

  // ============================================================================
  // v13 Editorial Copilot State and Methods
  // ============================================================================

  const [copilotSuggestions, setCopilotSuggestions] = useState<CopilotSuggestion[]>([]);
  const [copilotPhase, setCopilotPhase] = useState<"initial" | "refine" | "strategy">("initial");
  const [copilotGuardrailApplied, setCopilotGuardrailApplied] = useState(false);
  const [loadingCopilot, setLoadingCopilot] = useState(false);

  // v14: Segment Status State
  const [copilotSegmentStatus, setCopilotSegmentStatus] = useState<CopilotSegmentStatus | null>(null);
  const [loadingCopilotSegmentStatus, setLoadingCopilotSegmentStatus] = useState(false);

  const refreshCopilotSuggestions = async (
    phase: "initial" | "refine" | "strategy" = "initial"
  ) => {
    if (!activeThreadId) return;
    setLoadingCopilot(true);
    setCopilotPhase(phase);
    try {
      const response = await CopilotApi.getSuggestions(activeThreadId, phase);
      if (response && Array.isArray(response.suggestions)) {
        setCopilotSuggestions(response.suggestions);
        setCopilotGuardrailApplied(response.guardrail_applied || false);
      } else {
        setCopilotSuggestions([]);
        setCopilotGuardrailApplied(false);
      }
    } catch {
      setCopilotSuggestions([]);
      setCopilotGuardrailApplied(false);
    } finally {
      setLoadingCopilot(false);
    }
  };

  const submitCopilotFeedback = async (payload: CopilotFeedbackPayload) => {
    if (!activeThreadId) throw new Error("No active thread");
    const response = await CopilotApi.submitFeedback(activeThreadId, payload);
    return response;
  };

  // v14: Segment Status Methods
  const refreshCopilotSegmentStatus = async () => {
    if (!activeThreadId) return;
    setLoadingCopilotSegmentStatus(true);
    try {
      const response = await CopilotApi.getSegmentStatus(activeThreadId);
      if (response && response.segment_key) {
        setCopilotSegmentStatus(response);
      } else {
        setCopilotSegmentStatus(null);
      }
    } catch {
      // Silently fail - segment status is optional enhancement
      setCopilotSegmentStatus(null);
    } finally {
      setLoadingCopilotSegmentStatus(false);
    }
  };

  // v14: Auto-load segment status when thread changes
  useEffect(() => {
    if (activeThreadId) {
      refreshCopilotSegmentStatus();
    } else {
      setCopilotSegmentStatus(null);
    }
  }, [activeThreadId]);

  useEffect(() => {
    const targetRunId = effectiveActiveRunId || runs[0]?.run_id || null;
    if (targetRunId) {
      fetchRunDetail(targetRunId);
      fetchPrimaryArtifact(targetRunId);
      fetchResolvedBaseline(targetRunId);
    }
  }, [effectiveActiveRunId, runs]);

  useEffect(() => {
    if (!activeThreadId) return;
    const timer = window.setInterval(() => {
      fetchRuns();
      fetchTimeline();
      if (activeRunId) {
        fetchRunDetail();
        fetchResolvedBaseline();
      }
    }, 4000);
    return () => window.clearInterval(timer);
  }, [activeThreadId, activeRunId]);

  return {
    profiles,
    runs,
    effectiveActiveRunId: effectiveActiveRunId || runs[0]?.run_id || null,
    runDetail,
    timeline,
    primaryArtifact,
    artifactsByRun,
    deepEvaluationByRun,
    editorialDecisions,
    resolvedBaseline,
    localBaseline,
    loadingProfiles,
    loadingRuns,
    loadingRunDetail,
    loadingTimeline,
    loadingPrimaryArtifact,
    startRun,
    resumeRun,
    requestDeepEvaluation,
    loadArtifactForRun,
    markGoldenDecision,
    refreshRuns: fetchRuns,
    refreshTimeline: fetchTimeline,
    refreshPrimaryArtifact: () => fetchPrimaryArtifact(),
    editorialAudit,
    auditScopeFilter,
    setAuditScopeFilter,
    auditPagination,
    setAuditPagination,
    refreshEditorialAudit: fetchEditorialAudit,
    editorialInsights,
    loadingInsights,
    refreshEditorialInsights: fetchEditorialInsights,
    recommendations,
    loadingRecommendations,
    refreshRecommendations: fetchRecommendations,
    executePlaybookAction,
    editorialForecast,
    loadingForecast,
    refreshEditorialForecast: fetchEditorialForecast,
    showSuppressedActions,
    setShowSuppressedActions,
    // Editorial SLO
    editorialSLO,
    loadingSLO,
    refreshEditorialSLO: fetchEditorialSLO,
    updateEditorialSLO,
    // Editorial Drift
    editorialDrift,
    loadingDrift,
    refreshEditorialDrift: fetchEditorialDrift,
    // Auto-remediation
    autoRemediationHistory,
    loadingAutoHistory,
    refreshAutoRemediationHistory: fetchAutoRemediationHistory,
    triggerAutoRemediation,
    // v12 First-run recommendation
    firstRunRecommendation,
    loadingFirstRunRecommendation,
    refreshFirstRunRecommendation: fetchFirstRunRecommendation,
    firstRunOutcomes,
    loadingFirstRunOutcomes,
    refreshFirstRunOutcomes: fetchFirstRunOutcomes,
    // v13 Editorial Copilot
    copilotSuggestions,
    copilotPhase,
    copilotGuardrailApplied,
    loadingCopilot,
    refreshCopilotSuggestions,
    submitCopilotFeedback,
    // v14 Segmented Copilot
    copilotSegmentStatus,
    loadingCopilotSegmentStatus,
    refreshCopilotSegmentStatus,
  };
}
