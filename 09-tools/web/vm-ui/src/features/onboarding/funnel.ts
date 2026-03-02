/**
 * Onboarding funnel analytics for v30 first-success-path
 * Tracks user progression through onboarding steps
 */

import { OnboardingStep } from './telemetry';

export interface FunnelState {
  userId: string;
  currentStep: OnboardingStep;
  startedAt: Date;
  completedSteps: OnboardingStep[];
  lastActivityAt: Date;
}

export interface FunnelMetrics {
  step: OnboardingStep;
  entered: number;
  completed: number;
  dropoff: number;
  conversionRate: number;
  averageTimeSpentMs: number;
}

const STORAGE_KEY = 'vm_onboarding_funnel';

export function saveFunnelState(state: FunnelState): void {
  try {
    localStorage.setItem(
      `${STORAGE_KEY}_${state.userId}`,
      JSON.stringify({
        ...state,
        startedAt: state.startedAt.toISOString(),
        lastActivityAt: state.lastActivityAt.toISOString(),
      })
    );
  } catch (error) {
    console.warn('Failed to save funnel state:', error);
  }
}

export function loadFunnelState(userId: string): FunnelState | null {
  try {
    const data = localStorage.getItem(`${STORAGE_KEY}_${userId}`);
    if (!data) return null;

    const parsed = JSON.parse(data);
    return {
      ...parsed,
      startedAt: new Date(parsed.startedAt),
      lastActivityAt: new Date(parsed.lastActivityAt),
    };
  } catch (error) {
    console.warn('Failed to load funnel state:', error);
    return null;
  }
}

export function clearFunnelState(userId: string): void {
  try {
    localStorage.removeItem(`${STORAGE_KEY}_${userId}`);
  } catch (error) {
    console.warn('Failed to clear funnel state:', error);
  }
}

export function calculateStepDuration(
  state: FunnelState,
  step: OnboardingStep
): number {
  return state.lastActivityAt.getTime() - state.startedAt.getTime();
}

export function canResumeOnboarding(userId: string): boolean {
  const state = loadFunnelState(userId);
  if (!state) return false;

  // Can resume if started but not completed and not older than 7 days
  const maxAgeMs = 7 * 24 * 60 * 60 * 1000;
  const ageMs = Date.now() - state.startedAt.getTime();

  return (
    !state.completedSteps.includes(OnboardingStep.COMPLETION) &&
    ageMs < maxAgeMs
  );
}

export function getNextStep(currentStep: OnboardingStep): OnboardingStep | null {
  const stepOrder = [
    OnboardingStep.WELCOME,
    OnboardingStep.WORKSPACE_SETUP,
    OnboardingStep.TEMPLATE_SELECTION,
    OnboardingStep.CUSTOMIZATION,
    OnboardingStep.FIRST_RUN,
    OnboardingStep.COMPLETION,
  ];

  const currentIndex = stepOrder.indexOf(currentStep);
  if (currentIndex === -1 || currentIndex === stepOrder.length - 1) {
    return null;
  }
  return stepOrder[currentIndex + 1];
}

export function calculateFunnelMetrics(
  states: FunnelState[]
): FunnelMetrics[] {
  const stepOrder = [
    OnboardingStep.WELCOME,
    OnboardingStep.WORKSPACE_SETUP,
    OnboardingStep.TEMPLATE_SELECTION,
    OnboardingStep.CUSTOMIZATION,
    OnboardingStep.FIRST_RUN,
    OnboardingStep.COMPLETION,
  ];

  return stepOrder.map((step) => {
    const entered = states.filter(
      (s) =>
        s.currentStep === step ||
        s.completedSteps.includes(step) ||
        stepOrder.indexOf(s.currentStep) > stepOrder.indexOf(step)
    ).length;

    const completed = states.filter((s) =>
      s.completedSteps.includes(step)
    ).length;

    const dropoff = entered - completed;
    const conversionRate = entered > 0 ? completed / entered : 0;

    const times = states
      .filter((s) => s.completedSteps.includes(step))
      .map((s) => calculateStepDuration(s, step));
    const averageTimeSpentMs =
      times.length > 0
        ? times.reduce((a, b) => a + b, 0) / times.length
        : 0;

    return {
      step,
      entered,
      completed,
      dropoff,
      conversionRate,
      averageTimeSpentMs,
    };
  });
}
