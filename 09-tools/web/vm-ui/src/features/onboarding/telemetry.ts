/**
 * Onboarding telemetry tracking for v30 first-success-path
 * Tracks: started, completed, dropoff, time-to-first-value (ttfv)
 */

const API_BASE = '/api/v2';

export enum OnboardingStep {
  WELCOME = 'welcome',
  WORKSPACE_SETUP = 'workspace_setup',
  TEMPLATE_SELECTION = 'template_selection',
  CUSTOMIZATION = 'customization',
  FIRST_RUN = 'first_run',
  COMPLETION = 'completion',
}

export enum OnboardingEvent {
  STARTED = 'onboarding_started',
  COMPLETED = 'onboarding_completed',
  DROPOFF = 'onboarding_dropoff',
  TIME_TO_FIRST_VALUE = 'time_to_first_value',
}

interface TelemetryPayload {
  event: string;
  userId: string;
  timestamp: string;
  durationMs?: number;
  step?: string;
  templateId?: string;
}

interface OnboardingMetrics {
  totalStarted: number;
  totalCompleted: number;
  completionRate: number;
  averageTimeToFirstValueMs: number;
  dropoffByStep: Record<string, number>;
}

async function sendTelemetry(payload: TelemetryPayload): Promise<void> {
  try {
    await fetch(`${API_BASE}/onboarding/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    // Silently fail - telemetry should not block user flow
    console.warn('Telemetry error:', error);
  }
}

export async function trackOnboardingStarted(userId: string): Promise<void> {
  await sendTelemetry({
    event: OnboardingEvent.STARTED,
    userId,
    timestamp: new Date().toISOString(),
  });
}

export async function trackOnboardingCompleted(
  userId: string,
  durationMs: number
): Promise<void> {
  await sendTelemetry({
    event: OnboardingEvent.COMPLETED,
    userId,
    timestamp: new Date().toISOString(),
    durationMs,
  });
}

export async function trackOnboardingDropoff(
  userId: string,
  step: OnboardingStep
): Promise<void> {
  await sendTelemetry({
    event: OnboardingEvent.DROPOFF,
    userId,
    timestamp: new Date().toISOString(),
    step,
  });
}

export async function trackTimeToFirstValue(
  userId: string,
  durationMs: number,
  templateId?: string
): Promise<void> {
  const payload: TelemetryPayload = {
    event: OnboardingEvent.TIME_TO_FIRST_VALUE,
    userId,
    timestamp: new Date().toISOString(),
    durationMs,
  };
  if (templateId) {
    payload.templateId = templateId;
  }
  await sendTelemetry(payload);
}

export async function getOnboardingMetrics(): Promise<OnboardingMetrics | null> {
  try {
    const response = await fetch(`${API_BASE}/onboarding/metrics`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.warn('Failed to fetch onboarding metrics:', error);
    return null;
  }
}

// v31: Friction telemetry for onboarding activation learning loop

export enum FrictionEvent {
  STEP_ABANDONED = 'step_abandoned',
  STEP_RETURNED = 'step_returned',
  STEP_HESITATION = 'step_hesitation',
}

export interface FrictionMetrics {
  totalAbandons: number;
  totalReturns: number;
  totalHesitations: number;
  abandonByStep: Record<string, number>;
  abandonReasons: Record<string, number>;
  averageTimeAwayMs: number;
  averageHesitationMs: number;
}

interface FrictionPayload extends TelemetryPayload {
  reason?: string;
  metadata?: Record<string, unknown>;
  timeAwayMs?: number;
  durationMs?: number;
  element?: string;
  action?: string;
}

export async function trackStepAbandon(
  userId: string,
  step: OnboardingStep,
  reason: string,
  metadata?: Record<string, unknown>
): Promise<void> {
  const payload: FrictionPayload = {
    event: FrictionEvent.STEP_ABANDONED,
    userId,
    timestamp: new Date().toISOString(),
    step,
    reason,
  };
  if (metadata) {
    payload.metadata = metadata;
  }
  await sendTelemetry(payload);
}

export async function trackStepReturn(
  userId: string,
  step: OnboardingStep,
  timeAwayMs: number
): Promise<void> {
  const payload: FrictionPayload = {
    event: FrictionEvent.STEP_RETURNED,
    userId,
    timestamp: new Date().toISOString(),
    step,
    timeAwayMs,
  };
  await sendTelemetry(payload);
}

export async function trackStepHesitation(
  userId: string,
  step: OnboardingStep,
  durationMs: number,
  context?: { element?: string; action?: string }
): Promise<void> {
  const payload: FrictionPayload = {
    event: FrictionEvent.STEP_HESITATION,
    userId,
    timestamp: new Date().toISOString(),
    step,
    durationMs,
  };
  if (context?.element) {
    payload.element = context.element;
  }
  if (context?.action) {
    payload.action = context.action;
  }
  await sendTelemetry(payload);
}

export async function getFrictionMetrics(): Promise<FrictionMetrics | null> {
  try {
    const response = await fetch(`${API_BASE}/onboarding/friction-metrics`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.warn('Failed to fetch friction metrics:', error);
    return null;
  }
}
