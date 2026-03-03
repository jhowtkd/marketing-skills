/**
 * Re-exports of types from the auto-generated API client.
 * This file provides a clean interface for types used throughout the application.
 */

import type { components, operations, paths } from "../generated/api-client";

// ============================================================================
// Brand Types
// ============================================================================

/** Brand data from the API */
export type Brand = components["schemas"]["BrandResponse"];

/** Response from list brands endpoint */
export type BrandsResponse = {
  brands: Brand[];
};

/** Request body for creating a brand */
export type BrandCreateRequest = components["schemas"]["BrandCreateRequest"];

/** Request body for updating a brand */
export type BrandUpdateRequest = components["schemas"]["BrandUpdateRequest"];

// ============================================================================
// Project Types
// ============================================================================

/** Project data from the API */
export type Project = components["schemas"]["ProjectCreateRequest"] & {
  project_id: string;
};

/** Response from list projects endpoint */
export type ProjectsResponse = {
  projects: Project[];
};

/** Request body for creating a project */
export type ProjectCreateRequest = components["schemas"]["ProjectCreateRequest"];

/** Request body for updating a project */
export type ProjectUpdateRequest = components["schemas"]["ProjectUpdateRequest"];

// ============================================================================
// Thread Types
// ============================================================================

/** Thread data from the API */
export type Thread = {
  thread_id: string;
  project_id: string;
  brand_id: string;
  title: string;
  status?: string;
  modes?: string[];
};

/** Response from list threads endpoint */
export type ThreadsResponse = {
  threads: Thread[];
};

/** Request body for creating a thread */
export type ThreadCreateRequest = components["schemas"]["ThreadCreateV2Request"];

/** Request body for updating a thread */
export type ThreadUpdateRequest = components["schemas"]["ThreadUpdateRequest"];

/** Request body for adding a mode to a thread */
export type ThreadModeAddRequest = components["schemas"]["ThreadModeAddRequest"];

// ============================================================================
// Workflow Types
// ============================================================================

/** Workflow profile from the API */
export type WorkflowProfile = {
  mode: string;
  description: string;
};

/** Workflow run data */
export type WorkflowRun = {
  run_id: string;
  status: string;
  requested_mode: string;
  request_text?: string;
  created_at?: string;
  objective_key?: string;
};

/** Response from list workflow profiles endpoint */
export type WorkflowProfilesResponse = {
  profiles: WorkflowProfile[];
};

/** Response from list workflow runs endpoint */
export type WorkflowRunsResponse = {
  runs?: WorkflowRun[];
  items?: WorkflowRun[];
};

// ============================================================================
// Timeline Types
// ============================================================================

/** Timeline event from the API */
export type TimelineEvent = {
  event_id: string;
  event_type: string;
  created_at: string;
  payload: unknown;
  actor_id?: string;
};

/** Response from timeline endpoint */
export type TimelineResponse = {
  events: TimelineEvent[];
};

// ============================================================================
// Artifact Types
// ============================================================================

/** Primary artifact data */
export type PrimaryArtifact = {
  stageDir: string;
  artifactPath: string;
  content: string;
};

/** Artifact listing item */
export type ArtifactListingItem = {
  stage_dir: string;
  artifacts?: Array<string | { path?: string; filename?: string }>;
};

/** Response from artifact listing endpoint */
export type ArtifactListingResponse = {
  stages?: ArtifactListingItem[];
};

/** Response from artifact content endpoint */
export type ArtifactContentResponse = {
  content?: string;
};

// ============================================================================
// Editorial Types
// ============================================================================

/** Editorial decision data */
export type EditorialDecision = {
  run_id: string;
  justification: string;
  updated_at: string;
  objective_key?: string;
};

/** All editorial decisions for a thread */
export type EditorialDecisions = {
  global: EditorialDecision | null;
  objective: EditorialDecision[];
};

/** Resolved baseline information */
export type ResolvedBaseline = {
  baseline_run_id: string | null;
  source: "objective_golden" | "global_golden" | "previous" | "none";
  objective_key: string;
};

/** Editorial audit event */
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

/** Editorial audit response */
export type EditorialAuditResponse = {
  thread_id: string;
  events: EditorialAuditEvent[];
  total: number;
  limit: number;
  offset: number;
};

/** Editorial insights data */
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

/** Editorial recommendation item */
export type EditorialRecommendation = {
  severity: "info" | "warning" | "critical";
  reason: string;
  action_id: string;
  title: string;
  description: string;
  impact_score: number;
  effort_score: number;
  priority_score: number;
  why_priority: string;
  suppressed: boolean;
  suppression_reason: string;
};

/** Editorial recommendations response */
export type EditorialRecommendations = {
  thread_id: string;
  recommendations: EditorialRecommendation[];
  generated_at: string;
};

/** Editorial forecast data */
export type EditorialForecast = {
  thread_id: string;
  risk_score: number;
  trend: "improving" | "stable" | "degrading";
  drivers: string[];
  recommended_focus: string;
  confidence: number;
  volatility: number;
  calibration_notes: string[];
  generated_at: string;
};

/** Editorial SLO configuration */
export type EditorialSLO = {
  brand_id: string;
  max_baseline_none_rate: number;
  max_policy_denied_rate: number;
  min_confidence: number;
  auto_remediation_enabled: boolean;
  updated_at: string;
};

/** Editorial drift data */
export type EditorialDrift = {
  thread_id: string;
  drift_score: number;
  drift_severity: "none" | "low" | "medium" | "high";
  drift_flags: string[];
  primary_driver: string;
  recommended_actions: string[];
  details: Record<string, number | string>;
  generated_at: string;
};

// ============================================================================
// Copilot Types
// ============================================================================

/** Copilot segment status */
export type CopilotSegmentStatus = {
  thread_id: string;
  brand_id: string;
  project_id?: string;
  segment_key: string;
  segment_status: "eligible" | "insufficient_volume" | "frozen" | "fallback";
  is_eligible: boolean;
  segment_runs_total: number;
  segment_success_24h_rate: number;
  segment_v1_score_avg: number;
  segment_regen_rate: number;
  adjustment_factor: number;
  minimum_runs_threshold: number;
  explanation: string;
};

/** Copilot suggestion */
export type CopilotSuggestion = {
  suggestion_id: string;
  content: string;
  confidence: number;
  reason_codes: string[];
  why: string;
  expected_impact: { quality_delta: number; approval_lift: number };
  created_at: string;
};

/** Copilot feedback payload */
export type CopilotFeedbackPayload = {
  suggestion_id: string;
  phase: "initial" | "refine" | "strategy";
  action: "accepted" | "edited" | "ignored";
  edited_content?: string;
};

// ============================================================================
// First Run Types
// ============================================================================

/** First run recommendation item */
export type FirstRunRecommendationItem = {
  profile: string;
  mode: string;
  score: number;
  confidence: number;
  reason_codes: string[];
};

/** First run recommendation response */
export type FirstRunRecommendation = {
  thread_id: string;
  scope: string;
  recommendations: FirstRunRecommendationItem[];
};

/** First run outcome aggregate */
export type FirstRunOutcomeAggregate = {
  profile: string;
  mode: string;
  total_runs: number;
  success_24h_count: number;
  success_rate: number;
  avg_quality_score: number;
  avg_duration_ms: number;
};

/** First run outcomes response */
export type FirstRunOutcomes = {
  thread_id: string;
  aggregates: FirstRunOutcomeAggregate[];
};

// ============================================================================
// Auto Remediation Types
// ============================================================================

/** Auto remediation event */
export type AutoRemediationEvent = {
  event_type: "AutoRemediationExecuted" | "AutoRemediationSkipped";
  occurred_at: string;
  action_id?: string;
  proposed_action?: string;
  auto_executed: boolean;
  reason: string;
};

/** Auto remediation response */
export type AutoRemediationResponse = {
  status: string;
  executed: string[];
  skipped: string[];
  event_id?: string;
};

// ============================================================================
// Playbook Types
// ============================================================================

/** Playbook action execution request */
export type PlaybookExecuteRequest = {
  action_id: string;
  run_id?: string;
  note?: string;
};

/** Playbook action execution response */
export type PlaybookExecuteResponse = {
  status: string;
  executed_action: string;
  created_entities: Array<{ entity_type: string; entity_id: string }>;
};

// ============================================================================
// Quality Types
// ============================================================================

/** Deep evaluation API payload */
export type DeepEvaluationApiPayload = {
  score?: {
    overall?: number;
    criteria?: {
      completude?: number;
      estrutura?: number;
      clareza?: number;
      cta?: number;
      acionabilidade?: number;
    };
    recommendations?: string[];
    source?: "deep" | "heuristic";
  };
  fallback_applied?: boolean;
  fallback_reason?: string;
};

// ============================================================================
// API Client Types
// ============================================================================

/** Generic API response wrapper */
export type ApiResponse<T> = {
  data: T;
  status: number;
};

/** API error response */
export type ApiError = {
  detail?: string;
  message?: string;
  status?: number;
};

/** Request options for typed API client */
export type RequestOptions = {
  idempotencyKey?: string;
  onError?: (error: Error) => void;
};

// Re-export paths and operations for advanced use cases
export type { paths, operations };
