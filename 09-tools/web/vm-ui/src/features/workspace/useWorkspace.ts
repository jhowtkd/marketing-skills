import { useEffect, useState } from "react";
import { fetchJson, postJson } from "../../api/client";
import { computeQualityScore } from "../quality/score";
import type { QualityScore } from "../quality/types";
import { mapTimelineResponse } from "./adapters";

export type WorkflowProfile = {
  mode: string;
  description: string;
};

export type WorkflowRun = {
  run_id: string;
  status: string;
  requested_mode: string;
  request_text?: string;
  created_at?: string;
  objective_key?: string;
};

export type TimelineEvent = {
  event_id: string;
  event_type: string;
  created_at: string;
  payload: any;
};

export type PrimaryArtifact = {
  stageDir: string;
  artifactPath: string;
  content: string;
};

type ArtifactListingResponse = {
  stages?: Array<{ stage_dir: string; artifacts?: Array<string | { path?: string; filename?: string }> }>;
};

type DeepEvaluationApiPayload = {
  score?: Partial<QualityScore>;
  fallback_applied?: boolean;
  fallback_reason?: string;
};

export type DeepEvaluationState = {
  status: "loading" | "ready" | "error";
  score: QualityScore;
  fallbackApplied: boolean;
  error: string | null;
};

export type EditorialDecision = {
  run_id: string;
  justification: string;
  updated_at: string;
  objective_key?: string;
};

export type EditorialDecisions = {
  global: EditorialDecision | null;
  objective: EditorialDecision[];
};

export type ResolvedBaseline = {
  baseline_run_id: string | null;
  source: "objective_golden" | "global_golden" | "previous" | "none";
  objective_key: string;
};

export type EditorialAuditEvent = {
  event_id: string;
  event_type: string;
  actor_id: string;
  actor_role: string;
  scope: "global" | "objective";
  objective_key?: string;
  run_id: string;
  justification: string;
  occurred_at: string;
  reason_code?: string;
};

export type EditorialInsights = {
  thread_id: string;
  totals: {
    marked_total: number;
    by_scope: { global: number; objective: number };
    by_reason_code: Record<string, number>;
  };
  policy: {
    denied_total: number;
  };
  baseline: {
    resolved_total: number;
    by_source: {
      objective_golden: number;
      global_golden: number;
      previous: number;
      none: number;
    };
  };
  recency: {
    last_marked_at: string | null;
    last_actor_id: string | null;
  };
};

export type EditorialAuditResponse = {
  thread_id: string;
  events: EditorialAuditEvent[];
  total: number;
  limit: number;
  offset: number;
};

export type EditorialRecommendation = {
  severity: "info" | "warning" | "critical";
  reason: string;
  action_id: string;
  title: string;
  description: string;
};

export type EditorialRecommendations = {
  thread_id: string;
  recommendations: EditorialRecommendation[];
  generated_at: string;
};

type PostJsonLike = <T>(url: string, payload: unknown, prefix: string) => Promise<T>;

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
  post?: PostJsonLike;
}): Promise<DeepEvaluationState> {
  const fallbackScore = computeQualityScore(input.artifactText);
  const post = input.post ?? postJson;
  try {
    const payload = await post<DeepEvaluationApiPayload>(
      `/api/v2/workflow-runs/${input.runId}/quality-evaluation`,
      { depth: "deep", rubric_version: "v1" },
      "quality"
    );
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
  const [runDetail, setRunDetail] = useState<any>(null);
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
      const data = await fetchJson<{ profiles: WorkflowProfile[] }>("/api/v2/workflow-profiles");
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
      const data = await fetchJson<{ runs?: WorkflowRun[]; items?: WorkflowRun[] }>(`/api/v2/threads/${activeThreadId}/workflow-runs`);
      // Accept both 'runs' and 'items' keys for compatibility
      const runsArray = data.runs || data.items || [];
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
      const data = await fetchJson<any>(`/api/v2/workflow-runs/${runId}`);
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
      const data = await fetchJson<unknown>(`/api/v2/threads/${activeThreadId}/timeline`);
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
      const data = await fetchJson<EditorialDecisions>(`/api/v2/threads/${activeThreadId}/editorial-decisions`);
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
    const searchParams = new URLSearchParams();
    if (params?.scope && params.scope !== "all") {
      searchParams.set("scope", params.scope);
    }
    if (params?.limit) {
      searchParams.set("limit", String(params.limit));
    }
    if (params?.offset !== undefined) {
      searchParams.set("offset", String(params.offset));
    }
    const queryString = searchParams.toString();
    const url = `/api/v2/threads/${activeThreadId}/editorial-decisions/audit${queryString ? `?${queryString}` : ""}`;
    
    try {
      const data = await fetchJson<EditorialAuditResponse>(url);
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
      const data = await fetchJson<EditorialInsights>(`/api/v2/threads/${activeThreadId}/editorial-decisions/insights`);
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
      const data = await fetchJson<EditorialRecommendations>(`/api/v2/threads/${activeThreadId}/editorial-decisions/recommendations`);
      setRecommendations(data);
    } catch (e) {
      console.error("Failed to fetch recommendations", e);
      // Fallback: keep current state (null or previous)
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const executePlaybookAction = async (actionId: string, runId?: string, note?: string) => {
    if (!activeThreadId) return;
    try {
      const result = await postJson<{
        status: string;
        executed_action: string;
        created_entities: Array<{ entity_type: string; entity_id: string }>;
      }>(
        `/api/v2/threads/${activeThreadId}/editorial-decisions/playbook/execute`,
        {
          action_id: actionId,
          run_id: runId,
          note: note,
        },
        "/api"
      );
      // Refresh recommendations after executing action
      await fetchRecommendations();
      return result;
    } catch (e) {
      console.error("Failed to execute playbook action", e);
      throw e;
    }
  };

  const fetchResolvedBaseline = async (runId?: string) => {
    const targetRunId = runId || effectiveActiveRunId;
    if (!targetRunId) {
      setResolvedBaseline(null);
      return;
    }
    try {
      const data = await fetchJson<ResolvedBaseline>(`/api/v2/workflow-runs/${targetRunId}/baseline`);
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
      await postJson(
        `/api/v2/threads/${activeThreadId}/editorial-decisions/golden`,
        {
          run_id: input.runId,
          scope: input.scope,
          objective_key: input.objectiveKey || null,
          justification: input.justification,
        },
        "editorial"
      );
      // Refresh decisions after marking
      await fetchEditorialDecisions();
    } catch (e) {
      console.error("Failed to mark golden decision", e);
      throw e;
    }
  };

  const fetchPrimaryArtifactForRun = async (runId: string): Promise<PrimaryArtifact | null> => {
    try {
      const listing = await fetchJson<ArtifactListingResponse>(
        `/api/v2/workflow-runs/${runId}/artifacts`
      );
      const stages = Array.isArray(listing.stages) ? listing.stages : [];
      let targetStage: string | null = null;
      let targetPath: string | null = null;
      for (const stage of stages) {
        const artifacts = Array.isArray(stage.artifacts) ? stage.artifacts : [];
        if (artifacts.length === 0) continue;
        const first = artifacts[0];
        const path = typeof first === "string" ? first : first.path || first.filename || null;
        if (path) {
          targetStage = stage.stage_dir;
          targetPath = path;
          break;
        }
      }
      if (!targetStage || !targetPath) {
        return null;
      }
      const contentPayload = await fetchJson<{ content?: string }>(
        `/api/v2/workflow-runs/${runId}/artifact-content?stage_dir=${encodeURIComponent(targetStage)}&artifact_path=${encodeURIComponent(targetPath)}`
      );
      return {
        stageDir: targetStage,
        artifactPath: targetPath,
        content: String(contentPayload.content ?? ""),
      };
    } catch (e) {
      console.error("Failed to fetch artifact", e);
      return null;
    }
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
      await postJson(`/api/v2/threads/${activeThreadId}/workflow-runs`, buildStartRunPayload(input), "run");
      fetchRuns();
      fetchTimeline();
    } catch (e) {
      console.error("Failed to start run", e);
    }
  };

  const resumeRun = async () => {
    if (!activeRunId) return;
    try {
      await postJson(`/api/v2/workflow-runs/${activeRunId}/resume`, {}, "resume");
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
  };
}
