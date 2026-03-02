import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  initTelemetry,
  trackFirstAction,
  trackNavigationError,
  trackWorkflowCompletion,
  trackStepProgress,
  getTelemetryState,
  resetTelemetry,
  TelemetryEvent,
} from './telemetry';

describe('UX Telemetry', () => {
  beforeEach(() => {
    resetTelemetry();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('initTelemetry', () => {
    it('should initialize telemetry with session id and start time', () => {
      initTelemetry();
      const state = getTelemetryState();
      
      expect(state.sessionId).toBeDefined();
      expect(state.sessionId).toMatch(/^session_[a-z0-9]+$/);
      expect(state.sessionStartTime).toBeDefined();
      expect(state.events).toEqual([]);
    });
  });

  describe('trackFirstAction', () => {
    it('should track first action event with timestamp and action type', () => {
      initTelemetry();
      const timestamp = Date.now();
      vi.setSystemTime(timestamp);
      
      trackFirstAction('create_campaign');
      const state = getTelemetryState();
      
      expect(state.events).toHaveLength(1);
      expect(state.events[0]).toMatchObject({
        type: 'first_action',
        action: 'create_campaign',
        timestamp,
      });
    });

    it('should calculate time to first action from session start', () => {
      initTelemetry();
      const startTime = Date.now();
      vi.setSystemTime(startTime);
      
      // Simulate 5 seconds passing
      vi.advanceTimersByTime(5000);
      
      trackFirstAction('edit_settings');
      const state = getTelemetryState();
      
      expect(state.events[0].timeToAction).toBe(5000);
    });

    it('should only track first action once per session', () => {
      initTelemetry();
      trackFirstAction('action_1');
      trackFirstAction('action_2');
      
      const state = getTelemetryState();
      expect(state.events).toHaveLength(1);
      expect(state.events[0].action).toBe('action_1');
    });
  });

  describe('trackNavigationError', () => {
    it('should track navigation error with context', () => {
      initTelemetry();
      const timestamp = Date.now();
      vi.setSystemTime(timestamp);
      
      trackNavigationError({
        from: '/studio',
        to: '/inbox',
        error: 'route_not_found',
      });
      
      const state = getTelemetryState();
      expect(state.events).toHaveLength(1);
      expect(state.events[0]).toMatchObject({
        type: 'navigation_error',
        from: '/studio',
        to: '/inbox',
        error: 'route_not_found',
        timestamp,
      });
    });

    it('should increment error count for multiple errors', () => {
      initTelemetry();
      
      trackNavigationError({ from: '/a', to: '/b', error: 'error1' });
      trackNavigationError({ from: '/b', to: '/c', error: 'error2' });
      
      const state = getTelemetryState();
      expect(state.navigationErrorCount).toBe(2);
    });
  });

  describe('trackWorkflowCompletion', () => {
    it('should track workflow completion with metadata', () => {
      initTelemetry();
      const timestamp = Date.now();
      vi.setSystemTime(timestamp);
      
      trackWorkflowCompletion({
        workflow: 'campaign_creation',
        success: true,
        stepsCompleted: 5,
        totalSteps: 5,
      });
      
      const state = getTelemetryState();
      expect(state.events).toHaveLength(1);
      expect(state.events[0]).toMatchObject({
        type: 'workflow_completion',
        workflow: 'campaign_creation',
        success: true,
        stepsCompleted: 5,
        totalSteps: 5,
        timestamp,
      });
    });

    it('should calculate completion rate percentage', () => {
      initTelemetry();
      
      trackWorkflowCompletion({
        workflow: 'campaign_creation',
        success: true,
        stepsCompleted: 5,
        totalSteps: 5,
      });
      
      trackWorkflowCompletion({
        workflow: 'settings_update',
        success: false,
        stepsCompleted: 2,
        totalSteps: 4,
      });
      
      const state = getTelemetryState();
      expect(state.workflowStats.completed).toBe(1);
      expect(state.workflowStats.total).toBe(2);
      expect(state.workflowStats.rate).toBe(0.5);
    });
  });

  describe('trackStepProgress', () => {
    it('should track step progression in workflow', () => {
      initTelemetry();
      
      trackStepProgress({
        workflow: 'campaign_creation',
        step: 1,
        stepName: 'select_template',
        completed: true,
      });
      
      const state = getTelemetryState();
      expect(state.events).toHaveLength(1);
      expect(state.events[0]).toMatchObject({
        type: 'step_progress',
        workflow: 'campaign_creation',
        step: 1,
        stepName: 'select_template',
        completed: true,
      });
    });

    it('should build step progression history', () => {
      initTelemetry();
      
      trackStepProgress({ workflow: 'test', step: 1, stepName: 'step1', completed: true });
      trackStepProgress({ workflow: 'test', step: 2, stepName: 'step2', completed: true });
      trackStepProgress({ workflow: 'test', step: 3, stepName: 'step3', completed: false });
      
      const state = getTelemetryState();
      expect(state.stepHistory).toHaveLength(3);
      expect(state.stepHistory[2].stepName).toBe('step3');
    });
  });

  describe('telemetry batching', () => {
    it('should batch events and flush when threshold reached', () => {
      const mockFlush = vi.fn();
      initTelemetry({ onFlush: mockFlush, batchSize: 3 });
      
      trackStepProgress({ workflow: 'test', step: 1, stepName: 's1', completed: true });
      trackStepProgress({ workflow: 'test', step: 2, stepName: 's2', completed: true });
      
      // Should not flush yet
      expect(mockFlush).not.toHaveBeenCalled();
      
      // This should trigger flush
      trackStepProgress({ workflow: 'test', step: 3, stepName: 's3', completed: true });
      
      expect(mockFlush).toHaveBeenCalledTimes(1);
      expect(mockFlush).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ stepName: 's1' }),
          expect.objectContaining({ stepName: 's2' }),
          expect.objectContaining({ stepName: 's3' }),
        ])
      );
    });
  });
});
