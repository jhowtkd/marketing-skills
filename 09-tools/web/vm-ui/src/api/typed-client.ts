/**
 * Typed API client wrapper
 * 
 * This module provides type-safe wrapper functions around the basic fetch utilities.
 * It uses types from the auto-generated API client for full type safety.
 */

import type { components, operations } from "../generated/api-client";
import {
  fetchJson,
  postJson,
  patchJson,
} from "./client";
import type {
  Brand,
  BrandsResponse,
  BrandCreateRequest,
  BrandUpdateRequest,
  Project,
  ProjectsResponse,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  Thread,
  ThreadsResponse,
  ThreadCreateRequest,
  ThreadUpdateRequest,
  ThreadModeAddRequest,
  WorkflowProfile,
  WorkflowProfilesResponse,
  WorkflowRun,
  WorkflowRunsResponse,
  TimelineEvent,
  TimelineResponse,
  ArtifactListingResponse,
  ArtifactContentResponse,
  PrimaryArtifact,
  EditorialDecisions,
  EditorialAuditResponse,
  EditorialInsights,
  EditorialRecommendations,
  EditorialForecast,
  EditorialSLO,
  EditorialDrift,
  AutoRemediationResponse,
  AutoRemediationEvent,
  PlaybookExecuteResponse,
  FirstRunRecommendation,
  FirstRunOutcomes,
  ResolvedBaseline,
  CopilotSegmentStatus,
  CopilotSuggestion,
  CopilotFeedbackPayload,
  DeepEvaluationApiPayload,
} from "../types/api";

// Re-export the base client functions for non-typed usage and backward compatibility
export { fetchJson, postJson, patchJson };

// ============================================================================
// Type-safe wrapper functions (using the original client functions)
// ============================================================================

/**
 * Fetch JSON data from an API endpoint with proper typing.
 * This is a type-safe wrapper around fetchJson.
 */
export async function fetchTyped<T>(url: string, options?: RequestInit): Promise<T> {
  return fetchJson<T>(url, options);
}

/**
 * POST JSON data to an API endpoint with proper typing.
 * This is a type-safe wrapper around postJson.
 */
export async function postTyped<T>(
  url: string,
  payload: unknown,
  idempotencyPrefix?: string
): Promise<T> {
  // postJson requires a prefix, provide empty string as default if not provided
  return postJson<T>(url, payload, idempotencyPrefix || "");
}

/**
 * PATCH JSON data to an API endpoint with proper typing.
 * This is a type-safe wrapper around patchJson.
 */
export async function patchTyped<T>(
  url: string,
  payload: unknown,
  idempotencyPrefix?: string
): Promise<T> {
  // patchJson requires a prefix, provide empty string as default if not provided
  return patchJson<T>(url, payload, idempotencyPrefix || "");
}

// ============================================================================
// Brand API
// ============================================================================

export const BrandApi = {
  /** List all brands */
  async listBrands(): Promise<BrandsResponse> {
    return fetchJson<BrandsResponse>("/api/v2/brands");
  },

  /** Create a new brand */
  async createBrand(data: BrandCreateRequest): Promise<{ brand_id: string; name: string }> {
    return postJson("/api/v2/brands", data, "brand-create");
  },

  /** Update a brand */
  async updateBrand(brandId: string, data: BrandUpdateRequest): Promise<void> {
    return patchJson(`/api/v2/brands/${brandId}`, data, "brand-edit");
  },
};

// ============================================================================
// Project API
// ============================================================================

export const ProjectApi = {
  /** List projects for a brand */
  async listProjects(brandId: string): Promise<ProjectsResponse> {
    return fetchJson<ProjectsResponse>(`/api/v2/projects?brand_id=${encodeURIComponent(brandId)}`);
  },

  /** Create a new project */
  async createProject(data: ProjectCreateRequest): Promise<void> {
    return postJson("/api/v2/projects", data, "project-create");
  },

  /** Update a project */
  async updateProject(projectId: string, data: ProjectUpdateRequest): Promise<void> {
    return patchJson(`/api/v2/projects/${projectId}`, data, "project-edit");
  },
};

// ============================================================================
// Thread API
// ============================================================================

export const ThreadApi = {
  /** List threads for a project */
  async listThreads(projectId: string): Promise<ThreadsResponse> {
    return fetchJson<ThreadsResponse>(`/api/v2/threads?project_id=${encodeURIComponent(projectId)}`);
  },

  /** Create a new thread */
  async createThread(data: ThreadCreateRequest): Promise<void> {
    return postJson("/api/v2/threads", data, "thread-create");
  },

  /** Update a thread */
  async updateThread(threadId: string, data: ThreadUpdateRequest): Promise<void> {
    return patchJson(`/api/v2/threads/${threadId}`, data, "thread-edit");
  },

  /** Add a mode to a thread */
  async addMode(threadId: string, mode: string): Promise<void> {
    return postJson(`/api/v2/threads/${threadId}/modes`, { mode }, "mode-add");
  },

  /** Remove a mode from a thread */
  async removeMode(threadId: string, mode: string): Promise<void> {
    return postJson(
      `/api/v2/threads/${threadId}/modes/${encodeURIComponent(mode)}/remove`,
      {},
      "mode-remove"
    );
  },
};

// ============================================================================
// Workflow API
// ============================================================================

export const WorkflowApi = {
  /** List all workflow profiles */
  async listProfiles(): Promise<WorkflowProfilesResponse> {
    return fetchJson<WorkflowProfilesResponse>("/api/v2/workflow-profiles");
  },

  /** List workflow runs for a thread */
  async listRuns(threadId: string): Promise<WorkflowRunsResponse> {
    return fetchJson<WorkflowRunsResponse>(`/api/v2/threads/${threadId}/workflow-runs`);
  },

  /** Get details for a specific run */
  async getRun(runId: string): Promise<unknown> {
    return fetchJson<unknown>(`/api/v2/workflow-runs/${runId}`);
  },

  /** Start a new workflow run */
  async startRun(threadId: string, mode: string, requestText: string): Promise<void> {
    return postJson(
      `/api/v2/threads/${threadId}/workflow-runs`,
      { mode, request_text: requestText.trim() },
      "run"
    );
  },

  /** Resume a workflow run */
  async resumeRun(runId: string): Promise<void> {
    return postJson(`/api/v2/workflow-runs/${runId}/resume`, {}, "resume");
  },
};

// ============================================================================
// Timeline API
// ============================================================================

export const TimelineApi = {
  /** Get timeline for a thread */
  async getTimeline(threadId: string): Promise<TimelineResponse> {
    return fetchJson<TimelineResponse>(`/api/v2/threads/${threadId}/timeline`);
  },
};

// ============================================================================
// Artifact API
// ============================================================================

export const ArtifactApi = {
  /** List artifacts for a run */
  async listArtifacts(runId: string): Promise<ArtifactListingResponse> {
    return fetchJson<ArtifactListingResponse>(`/api/v2/workflow-runs/${runId}/artifacts`);
  },

  /** Get artifact content */
  async getContent(
    runId: string,
    stageDir: string,
    artifactPath: string
  ): Promise<ArtifactContentResponse> {
    const params = new URLSearchParams({
      stage_dir: stageDir,
      artifact_path: artifactPath,
    });
    return fetchJson<ArtifactContentResponse>(
      `/api/v2/workflow-runs/${runId}/artifact-content?${params}`
    );
  },

  /** Fetch primary artifact for a run */
  async fetchPrimaryArtifact(runId: string): Promise<PrimaryArtifact | null> {
    const listing = await this.listArtifacts(runId);
    const stages = Array.isArray(listing.stages) ? listing.stages : [];
    
    let targetStage: string | null = null;
    let targetPath: string | null = null;
    
    for (const stage of stages) {
      const artifacts = Array.isArray(stage.artifacts) ? stage.artifacts : [];
      if (artifacts.length === 0) continue;
      
      const first = artifacts[0];
      const path = typeof first === "string" ? first : first.path || (first as { filename?: string }).filename || null;
      if (path) {
        targetStage = stage.stage_dir;
        targetPath = path;
        break;
      }
    }
    
    if (!targetStage || !targetPath) {
      return null;
    }
    
    const contentPayload = await this.getContent(runId, targetStage, targetPath);
    return {
      stageDir: targetStage,
      artifactPath: targetPath,
      content: String(contentPayload.content ?? ""),
    };
  },
};

// ============================================================================
// Quality API
// ============================================================================

export const QualityApi = {
  /** Request deep quality evaluation for a run */
  async evaluate(runId: string): Promise<DeepEvaluationApiPayload> {
    return postJson<DeepEvaluationApiPayload>(
      `/api/v2/workflow-runs/${runId}/quality-evaluation`,
      { depth: "deep", rubric_version: "v1" },
      "quality"
    );
  },

  /** Get resolved baseline for a run */
  async getBaseline(runId: string): Promise<ResolvedBaseline> {
    return fetchJson<ResolvedBaseline>(`/api/v2/workflow-runs/${runId}/baseline`);
  },
};

// ============================================================================
// Editorial API
// ============================================================================

export const EditorialApi = {
  /** Get editorial decisions for a thread */
  async getDecisions(threadId: string): Promise<EditorialDecisions> {
    return fetchJson<EditorialDecisions>(`/api/v2/threads/${threadId}/editorial-decisions`);
  },

  /** Mark a golden decision */
  async markGolden(
    threadId: string,
    data: {
      runId: string;
      scope: "global" | "objective";
      objectiveKey?: string;
      justification: string;
    }
  ): Promise<void> {
    return postJson(
      `/api/v2/threads/${threadId}/editorial-decisions/golden`,
      {
        run_id: data.runId,
        scope: data.scope,
        objective_key: data.objectiveKey || null,
        justification: data.justification,
      },
      "editorial"
    );
  },

  /** Get editorial audit trail */
  async getAudit(
    threadId: string,
    params?: { scope?: string; limit?: number; offset?: number }
  ): Promise<EditorialAuditResponse> {
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
    const url = `/api/v2/threads/${threadId}/editorial-decisions/audit${queryString ? `?${queryString}` : ""}`;
    return fetchJson<EditorialAuditResponse>(url);
  },

  /** Get editorial insights */
  async getInsights(threadId: string): Promise<EditorialInsights> {
    return fetchJson<EditorialInsights>(`/api/v2/threads/${threadId}/editorial-decisions/insights`);
  },

  /** Get editorial recommendations */
  async getRecommendations(threadId: string): Promise<EditorialRecommendations> {
    return fetchJson<EditorialRecommendations>(
      `/api/v2/threads/${threadId}/editorial-decisions/recommendations`
    );
  },

  /** Get editorial forecast */
  async getForecast(threadId: string): Promise<EditorialForecast> {
    return fetchJson<EditorialForecast>(`/api/v2/threads/${threadId}/editorial-decisions/forecast`);
  },

  /** Get editorial drift */
  async getDrift(threadId: string): Promise<EditorialDrift> {
    return fetchJson<EditorialDrift>(`/api/v2/threads/${threadId}/editorial-decisions/drift`);
  },

  /** Execute auto-remediation */
  async autoRemediate(threadId: string): Promise<AutoRemediationResponse> {
    return postJson(
      `/api/v2/threads/${threadId}/editorial-decisions/auto-remediate`,
      { auto_execute: true },
      "workspace"
    );
  },

  /** Get auto-remediation history */
  async getAutoRemediationHistory(threadId: string): Promise<{ events: AutoRemediationEvent[] }> {
    return fetchJson<{
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
    }>(`/api/v2/threads/${threadId}/events?event_types=AutoRemediationExecuted,AutoRemediationSkipped&limit=10`);
  },

  /** Execute a playbook action */
  async executePlaybookAction(
    threadId: string,
    actionId: string,
    runId?: string,
    note?: string
  ): Promise<PlaybookExecuteResponse> {
    return postJson(
      `/api/v2/threads/${threadId}/editorial-decisions/playbook/execute`,
      {
        action_id: actionId,
        run_id: runId,
        note: note,
      },
      "/api"
    );
  },
};

// ============================================================================
// SLO API
// ============================================================================

export const SloApi = {
  /** Get editorial SLO for a brand */
  async get(brandId: string): Promise<EditorialSLO> {
    return fetchJson<EditorialSLO>(`/api/v2/brands/${brandId}/editorial-slo`);
  },

  /** Update editorial SLO for a brand */
  async update(
    brandId: string,
    updates: Partial<Omit<EditorialSLO, "brand_id" | "updated_at">>
  ): Promise<EditorialSLO> {
    return postJson(`/api/v2/brands/${brandId}/editorial-slo`, updates, "workspace");
  },
};

// ============================================================================
// First Run API
// ============================================================================

export const FirstRunApi = {
  /** Get first run recommendation for a thread */
  async getRecommendation(threadId: string): Promise<FirstRunRecommendation> {
    return fetchJson<FirstRunRecommendation>(`/api/v2/threads/${threadId}/first-run-recommendation`);
  },

  /** Get first run outcomes for a thread */
  async getOutcomes(threadId: string): Promise<FirstRunOutcomes> {
    return fetchJson<FirstRunOutcomes>(`/api/v2/threads/${threadId}/first-run-outcomes`);
  },
};

// ============================================================================
// Copilot API
// ============================================================================

export const CopilotApi = {
  /** Get copilot suggestions for a thread */
  async getSuggestions(
    threadId: string,
    phase: "initial" | "refine" | "strategy" = "initial"
  ): Promise<{ suggestions: CopilotSuggestion[]; guardrail_applied?: boolean }> {
    return fetchJson<{ suggestions: CopilotSuggestion[]; guardrail_applied?: boolean }>(
      `/api/v2/threads/${threadId}/copilot/suggestions?phase=${phase}`
    );
  },

  /** Submit copilot feedback */
  async submitFeedback(threadId: string, payload: CopilotFeedbackPayload): Promise<unknown> {
    return postJson(`/api/v2/threads/${threadId}/copilot/feedback`, payload, "copilot");
  },

  /** Get copilot segment status */
  async getSegmentStatus(threadId: string): Promise<CopilotSegmentStatus> {
    return fetchJson<CopilotSegmentStatus>(`/api/v2/threads/${threadId}/copilot/segment-status`);
  },
};

// ============================================================================
// Unified API Client Export
// ============================================================================

export const ApiClient = {
  brand: BrandApi,
  project: ProjectApi,
  thread: ThreadApi,
  workflow: WorkflowApi,
  timeline: TimelineApi,
  artifact: ArtifactApi,
  quality: QualityApi,
  editorial: EditorialApi,
  slo: SloApi,
  firstRun: FirstRunApi,
  copilot: CopilotApi,
  
  // Raw typed fetch utilities
  fetch: fetchTyped,
  post: postTyped,
  patch: patchTyped,
};

export default ApiClient;
