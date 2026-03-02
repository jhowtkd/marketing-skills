export interface TelemetryEvent {
  type: string;
  timestamp: number;
  [key: string]: unknown;
}

export interface TelemetryState {
  sessionId: string;
  sessionStartTime: number;
  events: TelemetryEvent[];
  firstActionTracked: boolean;
  navigationErrorCount: number;
  workflowStats: {
    completed: number;
    total: number;
    rate: number;
  };
  stepHistory: Array<{
    workflow: string;
    step: number;
    stepName: string;
    completed: boolean;
    timestamp: number;
  }>;
}

interface TelemetryConfig {
  onFlush?: (events: TelemetryEvent[]) => void;
  batchSize?: number;
}

let state: TelemetryState | null = null;
let config: TelemetryConfig = {
  batchSize: 10,
};

function generateSessionId(): string {
  return `session_${Math.random().toString(36).substring(2, 10)}`;
}

export function initTelemetry(userConfig?: TelemetryConfig): void {
  if (userConfig) {
    config = { ...config, ...userConfig };
  }
  
  state = {
    sessionId: generateSessionId(),
    sessionStartTime: Date.now(),
    events: [],
    firstActionTracked: false,
    navigationErrorCount: 0,
    workflowStats: {
      completed: 0,
      total: 0,
      rate: 0,
    },
    stepHistory: [],
  };
}

export function getTelemetryState(): TelemetryState {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  return state;
}

export function resetTelemetry(): void {
  state = null;
  config = { batchSize: 10 };
}

function addEvent(event: TelemetryEvent): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  state.events.push(event);
  
  // Check if batch threshold reached
  if (config.batchSize && config.onFlush && state.events.length >= config.batchSize) {
    config.onFlush([...state.events]);
    state.events = [];
  }
}

export function trackFirstAction(action: string): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  // Only track first action once per session
  if (state.firstActionTracked) {
    return;
  }
  
  const timestamp = Date.now();
  const timeToAction = timestamp - state.sessionStartTime;
  
  addEvent({
    type: 'first_action',
    action,
    timestamp,
    timeToAction,
  });
  
  state.firstActionTracked = true;
}

export interface NavigationErrorContext {
  from: string;
  to: string;
  error: string;
}

export function trackNavigationError(context: NavigationErrorContext): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  addEvent({
    type: 'navigation_error',
    timestamp: Date.now(),
    ...context,
  });
  
  state.navigationErrorCount++;
}

export interface WorkflowCompletionContext {
  workflow: string;
  success: boolean;
  stepsCompleted: number;
  totalSteps: number;
}

export function trackWorkflowCompletion(context: WorkflowCompletionContext): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  addEvent({
    type: 'workflow_completion',
    timestamp: Date.now(),
    ...context,
  });
  
  state.workflowStats.total++;
  if (context.success) {
    state.workflowStats.completed++;
  }
  state.workflowStats.rate = state.workflowStats.completed / state.workflowStats.total;
}

export interface StepProgressContext {
  workflow: string;
  step: number;
  stepName: string;
  completed: boolean;
}

export function trackStepProgress(context: StepProgressContext): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  const timestamp = Date.now();
  
  addEvent({
    type: 'step_progress',
    timestamp,
    ...context,
  });
  
  state.stepHistory.push({
    ...context,
    timestamp,
  });
}

// ============================================
// v37: Unified Workspace UX Telemetry
// ============================================

export interface PrimaryActionContext {
  action: string;
  location: 'rail' | 'center' | 'sidebar';
  stepId?: string;
}

export function trackPrimaryAction(context: PrimaryActionContext): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  addEvent({
    type: 'primary_action_clicked',
    timestamp: Date.now(),
    ...context,
  });
}

export interface ContextSwitchContext {
  from: string;
  to: string;
  trigger: 'user' | 'system';
}

export function trackContextSwitch(context: ContextSwitchContext): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  addEvent({
    type: 'context_switch',
    timestamp: Date.now(),
    ...context,
  });
  
  // Increment context switch counter in session
  const currentCount = (state as unknown as { contextSwitchCount?: number }).contextSwitchCount || 0;
  (state as unknown as { contextSwitchCount: number }).contextSwitchCount = currentCount + 1;
}

export function getContextSwitchCount(): number {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  return (state as unknown as { contextSwitchCount?: number }).contextSwitchCount || 0;
}

export interface StepToActionLatencyContext {
  stepId: string;
  action: string;
  latencyMs: number;
}

const stepActionStartTimes: Record<string, number> = {};

export function startStepToActionTracking(stepId: string): void {
  stepActionStartTimes[stepId] = Date.now();
}

export function trackStepToActionLatency(context: Omit<StepToActionLatencyContext, 'latencyMs'>): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  const startTime = stepActionStartTimes[context.stepId];
  if (!startTime) {
    return; // No start time recorded, skip tracking
  }
  
  const latencyMs = Date.now() - startTime;
  
  addEvent({
    type: 'step_to_action_latency',
    timestamp: Date.now(),
    ...context,
    latencyMs,
  });
  
  // Clean up
  delete stepActionStartTimes[context.stepId];
}

export interface ResponsiveLayoutContext {
  breakpoint: 'mobile' | 'tablet' | 'desktop';
  columnsVisible: number;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
}

export function trackResponsiveLayout(context: ResponsiveLayoutContext): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  addEvent({
    type: 'responsive_layout_change',
    timestamp: Date.now(),
    ...context,
  });
}

export interface WorkspaceInteractionContext {
  component: 'unified_task_rail' | 'execution_center' | 'action_insight_sidebar';
  action: string;
  details?: Record<string, unknown>;
}

export function trackWorkspaceInteraction(context: WorkspaceInteractionContext): void {
  if (!state) {
    throw new Error('Telemetry not initialized. Call initTelemetry() first.');
  }
  
  addEvent({
    type: 'workspace_interaction',
    timestamp: Date.now(),
    ...context,
  });
}
