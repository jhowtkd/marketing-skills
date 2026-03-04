/**
 * TTFV Telemetry tracking for v38 onboarding acceleration
 * Tracks: onboarding_started, step_viewed, step_completed, first_value_reached, dropoff_reason
 * Calculates: median_ttfv_minutes by cohort
 */

const API_BASE = '/api/v2';

// Session ID storage (in-memory for SPA, survives navigation)
let sessionIdCache: string | null = null;

export enum TTFVEvent {
  ONBOARDING_STARTED = 'onboarding_started',
  STEP_VIEWED = 'step_viewed',
  STEP_COMPLETED = 'step_completed',
  FIRST_VALUE_REACHED = 'first_value_reached',
  DROPOFF_REASON = 'dropoff_reason',
}

export interface TTFVTelemetryPayload {
  event: TTFVEvent;
  userId: string;
  timestamp: string;
  sessionId: string;
  step?: string;
  durationMs?: number;
  ttfvMs?: number;
  ttfvMinutes?: number;
  templateId?: string;
  reason?: string;
  metadata?: Record<string, unknown>;
}

export interface TTFVCohortEvent {
  userId: string;
  ttfvMinutes: number;
  cohort: string;
}

// v38: Event data for median calculation
export interface TTFVCalculationEvent {
  ttfvMinutes: number;
}

/**
 * Generate a unique session ID
 */
function generateSessionId(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = 'sess_';
  for (let i = 0; i < 12; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Get or create session ID
 */
export function getSessionId(): string {
  if (!sessionIdCache) {
    sessionIdCache = generateSessionId();
  }
  return sessionIdCache;
}

/**
 * Set session ID (for testing or session restore)
 */
export function setSessionId(id: string): void {
  sessionIdCache = id;
}

async function sendTTFVTelemetry(payload: TTFVTelemetryPayload): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/onboarding/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    // Silently fail - telemetry should not block user flow
    console.warn('TTFV telemetry error:', error);
  }
}

/**
 * Track onboarding started event (v38 spec compliant)
 * @param sessionId - Session identifier
 */
export async function trackOnboardingStart(sessionId: string): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.ONBOARDING_STARTED,
    userId: 'anonymous', // Will be enriched server-side
    timestamp: new Date().toISOString(),
    sessionId,
  });
}

/**
 * Track onboarding started event (legacy with userId)
 */
export async function trackOnboardingStarted(userId: string): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.ONBOARDING_STARTED,
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
  });
}

/**
 * Track step viewed event (v38 spec compliant)
 * @param stepId - Step identifier
 * @param sessionId - Session identifier
 */
export async function trackStepViewed(stepId: string, sessionId: string): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.STEP_VIEWED,
    userId: 'anonymous', // Will be enriched server-side
    timestamp: new Date().toISOString(),
    sessionId,
    step: stepId,
  });
}

/**
 * Track step viewed event (legacy with userId)
 */
export async function trackStepViewedLegacy(userId: string, step: string): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.STEP_VIEWED,
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    step,
  });
}

/**
 * Track step completed event with duration (v38 spec compliant)
 * @param stepId - Step identifier
 * @param durationMs - Duration in milliseconds
 * @param sessionId - Session identifier
 */
export async function trackStepCompleted(
  stepId: string,
  durationMs: number,
  sessionId: string
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.STEP_COMPLETED,
    userId: 'anonymous', // Will be enriched server-side
    timestamp: new Date().toISOString(),
    sessionId,
    step: stepId,
    durationMs,
  });
}

/**
 * Track step completed event (legacy with userId)
 */
export async function trackStepCompletedLegacy(
  userId: string,
  step: string,
  durationMs: number
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.STEP_COMPLETED,
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    step,
    durationMs,
  });
}

/**
 * Track first value reached (TTFV) event (v38 spec compliant)
 * @param templateType - Type of template used
 * @param sessionId - Session identifier
 */
export async function trackFirstValueReached(
  templateType: string,
  sessionId: string
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.FIRST_VALUE_REACHED,
    userId: 'anonymous', // Will be enriched server-side
    timestamp: new Date().toISOString(),
    sessionId,
    templateId: templateType,
  });
}

/**
 * Track first value reached (legacy with userId and ttfvMs)
 */
export async function trackFirstValueReachedLegacy(
  userId: string,
  ttfvMs: number,
  templateId?: string
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.FIRST_VALUE_REACHED,
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    ttfvMs,
    ttfvMinutes: Math.round((ttfvMs / 60000) * 100) / 100,
    templateId,
  });
}

/**
 * Track dropoff reason (v38 spec compliant)
 * @param reason - Reason for dropoff
 * @param lastStep - Last step before dropoff
 * @param sessionId - Session identifier
 */
export async function trackDropoff(
  reason: string,
  lastStep: string,
  sessionId: string
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.DROPOFF_REASON,
    userId: 'anonymous', // Will be enriched server-side
    timestamp: new Date().toISOString(),
    sessionId,
    step: lastStep,
    reason,
  });
}

/**
 * Track dropoff reason (legacy with userId)
 */
export async function trackDropoffReason(
  userId: string,
  step: string,
  reason: string,
  metadata?: Record<string, unknown>
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.DROPOFF_REASON,
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    step,
    reason,
    metadata,
  });
}

/**
 * Calculate median TTFV (Time To First Value) in minutes (v38 spec compliant)
 * @param events - Array of events with ttfvMinutes
 * @returns Median TTFV in minutes
 */
export function calculateMedianTTFV(events: TTFVCalculationEvent[]): number {
  if (events.length === 0) {
    return 0;
  }

  const values = events.map(e => e.ttfvMinutes);
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);

  if (sorted.length % 2 === 0) {
    // Even number of elements: average of two middle values
    return (sorted[mid - 1] + sorted[mid]) / 2;
  } else {
    // Odd number of elements: middle value
    return sorted[mid];
  }
}

/**
 * Calculate median TTFV (Time To First Value) in minutes by cohort
 * @param events Array of TTFV cohort events
 * @returns Record of cohort -> median TTFV minutes
 */
export function calculateMedianTTFVByCohort(
  events: TTFVCohortEvent[]
): Record<string, number> {
  const cohorts: Record<string, number[]> = {};

  // Group TTFV minutes by cohort
  for (const event of events) {
    if (!cohorts[event.cohort]) {
      cohorts[event.cohort] = [];
    }
    cohorts[event.cohort].push(event.ttfvMinutes);
  }

  // Calculate median for each cohort
  const result: Record<string, number> = {};
  for (const [cohort, ttfvValues] of Object.entries(cohorts)) {
    result[cohort] = calculateMedianFromValues(ttfvValues);
  }

  return result;
}

/**
 * Calculate median of an array of numbers
 */
function calculateMedianFromValues(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }

  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);

  if (sorted.length % 2 === 0) {
    // Even number of elements: average of two middle values
    return (sorted[mid - 1] + sorted[mid]) / 2;
  } else {
    // Odd number of elements: middle value
    return sorted[mid];
  }
}

// v39: Fast lane telemetry events
export enum FastLaneEvent {
  FAST_LANE_PRESENTED = 'fast_lane_presented',
  FAST_LANE_ACCEPTED = 'fast_lane_accepted',
  FAST_LANE_REJECTED = 'fast_lane_rejected',
}

export interface FastLaneTelemetryPayload {
  event: FastLaneEvent;
  userId: string;
  timestamp: string;
  sessionId: string;
  confidence?: number;
  recommendedPath?: 'fast_lane' | 'standard';
  timeSavedMinutes?: number;
  skippedSteps?: string[];
  reasons?: string[];
}

/**
 * Track fast lane presented to user (v39 spec compliant)
 * @param userId - User identifier
 * @param confidence - Confidence score (0-1)
 * @param recommendedPath - Recommended path ('fast_lane' or 'standard')
 * @param timeSavedMinutes - Estimated time saved in minutes
 * @param skippedSteps - Steps that will be skipped
 * @param reasons - Reasons for recommendation
 */
export async function trackFastLanePresented(
  userId: string,
  confidence: number,
  recommendedPath: 'fast_lane' | 'standard',
  timeSavedMinutes: number,
  skippedSteps: string[],
  reasons: string[]
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.STEP_VIEWED, // Use existing enum for base event
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    step: 'fast_lane_offer',
    metadata: {
      fast_lane_event: FastLaneEvent.FAST_LANE_PRESENTED,
      confidence,
      recommendedPath,
      timeSavedMinutes,
      skippedSteps,
      reasons,
    },
  });
}

/**
 * Track fast lane accepted by user (v39 spec compliant)
 * @param userId - User identifier
 * @param confidence - Confidence score (0-1)
 * @param timeSavedMinutes - Estimated time saved in minutes
 * @param skippedSteps - Steps that will be skipped
 */
export async function trackFastLaneAccepted(
  userId: string,
  confidence: number,
  timeSavedMinutes: number,
  skippedSteps: string[]
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.STEP_COMPLETED, // Use existing enum for base event
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    step: 'fast_lane_accept',
    metadata: {
      fast_lane_event: FastLaneEvent.FAST_LANE_ACCEPTED,
      confidence,
      timeSavedMinutes,
      skippedSteps,
    },
  });
}

/**
 * Track fast lane rejected by user (v39 spec compliant)
 * @param userId - User identifier
 * @param confidence - Confidence score (0-1)
 * @param reasons - Reasons shown to user
 */
export async function trackFastLaneRejected(
  userId: string,
  confidence: number,
  reasons: string[]
): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.DROPOFF_REASON, // Use existing enum for base event
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    step: 'fast_lane_reject',
    reason: 'user_rejected_fast_lane',
    metadata: {
      fast_lane_event: FastLaneEvent.FAST_LANE_REJECTED,
      confidence,
      reasons,
    },
  });
}
