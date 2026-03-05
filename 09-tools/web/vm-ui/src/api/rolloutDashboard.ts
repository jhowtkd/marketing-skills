/**
 * API client for Rollout Dashboard
 * Handles fetching rollout policies and approval actions
 */

import { fetchJson, postJson } from "./client";

// ============================================================================
// Types
// ============================================================================

export type RolloutStatus =
  | "promoted"
  | "blocked"
  | "rolled_back"
  | "pending_review"
  | "evaluating";

export type RolloutMode = "AUTOMATIC" | "SUPERVISED" | "SHADOW";

export interface TimelineEvent {
  timestamp: string;
  action: string;
  operator?: string;
  reason?: string;
}

export interface MetricsSnapshot {
  total_evaluations: number;
  success_rate: number;
  avg_latency_ms: number;
  error_rate: number;
}

export interface RolloutPolicy {
  experiment_id: string;
  active_variant: string | null;
  mode: RolloutMode;
  status: RolloutStatus;
  last_evaluation_at: string | null;
  promotion_criteria: {
    min_evaluations: number;
    min_success_rate: number;
    max_error_rate: number;
  };
  timeline: TimelineEvent[];
  metrics: MetricsSnapshot;
  can_rollback: boolean;
}

export interface RolloutDashboardResponse {
  policies: RolloutPolicy[];
  updated_at: string;
}

// ============================================================================
// API Functions
// ============================================================================

const API_BASE = "/api/v2/onboarding";

/**
 * Fetch all rollout policies for the dashboard
 */
export async function fetchRolloutDashboard(): Promise<RolloutPolicy[]> {
  const response = await fetchJson<RolloutDashboardResponse>(
    `${API_BASE}/rollout-dashboard`
  );
  return response.policies || [];
}

export interface ApprovePromotionRequest {
  operator_id: string;
  reason: string;
  variant?: string;
}

/**
 * Approve promotion of an experiment variant
 */
export async function approvePromotion(
  experimentId: string,
  operatorId: string,
  reason: string,
  variant?: string
): Promise<void> {
  await postJson(`${API_BASE}/rollout-policy/${experimentId}/approve`, {
    operator_id: operatorId,
    reason,
    variant,
  } as ApprovePromotionRequest, "approve-promotion");
}

export interface RejectPromotionRequest {
  operator_id: string;
  reason: string;
}

/**
 * Reject promotion of an experiment
 */
export async function rejectPromotion(
  experimentId: string,
  operatorId: string,
  reason: string
): Promise<void> {
  await postJson(`${API_BASE}/rollout-policy/${experimentId}/reject`, {
    operator_id: operatorId,
    reason,
  } as RejectPromotionRequest, "reject-promotion");
}

export interface ManualRollbackRequest {
  operator_id: string;
  reason: string;
}

/**
 * Manually rollback a promoted experiment
 */
export async function manualRollback(
  experimentId: string,
  operatorId: string,
  reason: string
): Promise<void> {
  await postJson(`${API_BASE}/rollout-policy/${experimentId}/rollback`, {
    operator_id: operatorId,
    reason,
  } as ManualRollbackRequest, "manual-rollback");
}

// ============================================================================
// Telemetry
// ============================================================================

interface TelemetryPayload {
  event: string;
  timestamp: string;
  experiment_id?: string;
  metadata?: Record<string, unknown>;
}

async function sendTelemetry(payload: TelemetryPayload): Promise<void> {
  try {
    await fetch(`${API_BASE}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    // Silently fail - telemetry should not block user flow
    console.warn("Telemetry error:", error);
  }
}

/**
 * Track when the rollout dashboard is viewed
 */
export async function trackRolloutDashboardViewed(): Promise<void> {
  await sendTelemetry({
    event: "rollout_dashboard_viewed",
    timestamp: new Date().toISOString(),
  });
}

/**
 * Track approval actions
 */
export async function trackApprovalAction(
  action: "approved" | "rejected" | "rollback",
  experimentId: string,
  operatorId: string
): Promise<void> {
  await sendTelemetry({
    event: `rollout_${action}`,
    timestamp: new Date().toISOString(),
    experiment_id: experimentId,
    metadata: { operator_id: operatorId },
  });
}
