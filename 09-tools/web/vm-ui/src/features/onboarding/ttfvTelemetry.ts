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
 * Track onboarding started event
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
 * Track step viewed event
 */
export async function trackStepViewed(userId: string, step: string): Promise<void> {
  await sendTTFVTelemetry({
    event: TTFVEvent.STEP_VIEWED,
    userId,
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    step,
  });
}

/**
 * Track step completed event with duration
 */
export async function trackStepCompleted(
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
 * Track first value reached (TTFV) event
 */
export async function trackFirstValueReached(
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
 * Track dropoff reason
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
    result[cohort] = calculateMedian(ttfvValues);
  }

  return result;
}

/**
 * Calculate median of an array of numbers
 */
function calculateMedian(values: number[]): number {
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
