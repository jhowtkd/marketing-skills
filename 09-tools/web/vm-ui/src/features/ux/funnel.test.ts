import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  createFunnel,
  trackFunnelStep,
  getFunnelMetrics,
  getFunnelDropOffPoints,
  resetFunnel,
  FunnelStage,
} from './funnel';

describe('UX Funnel', () => {
  beforeEach(() => {
    resetFunnel();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('createFunnel', () => {
    it('should create funnel with defined stages', () => {
      const stages: FunnelStage[] = [
        { id: 'landing', name: 'Landing Page', order: 1 },
        { id: 'studio', name: 'Studio Entry', order: 2 },
        { id: 'create', name: 'Create Campaign', order: 3 },
        { id: 'publish', name: 'Publish', order: 4 },
      ];

      const funnel = createFunnel('campaign_creation', stages);
      
      expect(funnel.id).toBe('campaign_creation');
      expect(funnel.stages).toHaveLength(4);
      expect(funnel.stages[0].id).toBe('landing');
    });

    it('should sort stages by order', () => {
      const stages: FunnelStage[] = [
        { id: 'publish', name: 'Publish', order: 4 },
        { id: 'landing', name: 'Landing Page', order: 1 },
        { id: 'create', name: 'Create Campaign', order: 3 },
      ];

      const funnel = createFunnel('test', stages);
      
      expect(funnel.stages[0].id).toBe('landing');
      expect(funnel.stages[1].id).toBe('create');
      expect(funnel.stages[2].id).toBe('publish');
    });
  });

  describe('trackFunnelStep', () => {
    it('should track user progression through funnel stages', () => {
      const stages: FunnelStage[] = [
        { id: 'step1', name: 'Step 1', order: 1 },
        { id: 'step2', name: 'Step 2', order: 2 },
      ];
      
      createFunnel('test_funnel', stages);
      const timestamp = Date.now();
      vi.setSystemTime(timestamp);
      
      trackFunnelStep('test_funnel', 'step1', 'user_123');
      
      const metrics = getFunnelMetrics('test_funnel');
      expect(metrics.stages[0].entries).toBe(1);
      expect(metrics.stages[0].uniqueUsers).toContain('user_123');
    });

    it('should track time spent in each stage', () => {
      const stages: FunnelStage[] = [
        { id: 'step1', name: 'Step 1', order: 1 },
        { id: 'step2', name: 'Step 2', order: 2 },
      ];
      
      createFunnel('test_funnel', stages);
      
      const startTime = Date.now();
      vi.setSystemTime(startTime);
      trackFunnelStep('test_funnel', 'step1', 'user_123');
      
      // Advance 10 seconds
      vi.advanceTimersByTime(10000);
      trackFunnelStep('test_funnel', 'step2', 'user_123');
      
      const metrics = getFunnelMetrics('test_funnel');
      expect(metrics.stages[0].avgTimeSpent).toBeGreaterThanOrEqual(10000);
    });

    it('should handle multiple users in same stage', () => {
      const stages: FunnelStage[] = [
        { id: 'step1', name: 'Step 1', order: 1 },
      ];
      
      createFunnel('test_funnel', stages);
      
      trackFunnelStep('test_funnel', 'step1', 'user_1');
      trackFunnelStep('test_funnel', 'step1', 'user_2');
      trackFunnelStep('test_funnel', 'step1', 'user_3');
      
      const metrics = getFunnelMetrics('test_funnel');
      expect(metrics.stages[0].entries).toBe(3);
      expect(metrics.stages[0].uniqueUsers).toHaveLength(3);
    });
  });

  describe('getFunnelMetrics', () => {
    it('should calculate conversion rates between stages', () => {
      const stages: FunnelStage[] = [
        { id: 'step1', name: 'Step 1', order: 1 },
        { id: 'step2', name: 'Step 2', order: 2 },
        { id: 'step3', name: 'Step 3', order: 3 },
      ];
      
      createFunnel('test_funnel', stages);
      
      // 100 users enter step 1
      for (let i = 0; i < 100; i++) {
        trackFunnelStep('test_funnel', 'step1', `user_${i}`);
      }
      
      // 70 proceed to step 2
      for (let i = 0; i < 70; i++) {
        trackFunnelStep('test_funnel', 'step2', `user_${i}`);
      }
      
      // 40 complete step 3
      for (let i = 0; i < 40; i++) {
        trackFunnelStep('test_funnel', 'step3', `user_${i}`);
      }
      
      const metrics = getFunnelMetrics('test_funnel');
      
      expect(metrics.stages[0].conversionRate).toBe(1); // Entry point = 100%
      expect(metrics.stages[1].conversionRate).toBe(0.7); // 70/100
      expect(metrics.stages[2].conversionRate).toBe(0.57); // 40/70 rounded
      expect(metrics.overallConversionRate).toBe(0.4); // 40/100
    });

    it('should return null for non-existent funnel', () => {
      const metrics = getFunnelMetrics('non_existent');
      expect(metrics).toBeNull();
    });
  });

  describe('getFunnelDropOffPoints', () => {
    it('should identify stages with highest drop-off rates', () => {
      const stages: FunnelStage[] = [
        { id: 'step1', name: 'Step 1', order: 1 },
        { id: 'step2', name: 'Step 2', order: 2 },
        { id: 'step3', name: 'Step 3', order: 3 },
      ];
      
      createFunnel('test_funnel', stages);
      
      // 100 users enter
      for (let i = 0; i < 100; i++) {
        trackFunnelStep('test_funnel', 'step1', `user_${i}`);
      }
      
      // Only 50 proceed (50% drop-off at step1->step2)
      for (let i = 0; i < 50; i++) {
        trackFunnelStep('test_funnel', 'step2', `user_${i}`);
      }
      
      // 40 complete (20% drop-off at step2->step3)
      for (let i = 0; i < 40; i++) {
        trackFunnelStep('test_funnel', 'step3', `user_${i}`);
      }
      
      const dropOffs = getFunnelDropOffPoints('test_funnel');
      
      expect(dropOffs).toHaveLength(2);
      expect(dropOffs[0].stageId).toBe('step1');
      expect(dropOffs[0].dropOffRate).toBe(0.5);
      expect(dropOffs[1].stageId).toBe('step2');
      expect(dropOffs[1].dropOffRate).toBe(0.2);
    });

    it('should return empty array for completed funnels', () => {
      const stages: FunnelStage[] = [
        { id: 'step1', name: 'Step 1', order: 1 },
        { id: 'step2', name: 'Step 2', order: 2 },
      ];
      
      createFunnel('test_funnel', stages);
      
      // All users complete
      for (let i = 0; i < 10; i++) {
        trackFunnelStep('test_funnel', 'step1', `user_${i}`);
        trackFunnelStep('test_funnel', 'step2', `user_${i}`);
      }
      
      const dropOffs = getFunnelDropOffPoints('test_funnel');
      expect(dropOffs).toEqual([]);
    });
  });

  describe('funnel targeting v29 metrics', () => {
    it('should track time to first action metric', () => {
      const stages: FunnelStage[] = [
        { id: 'entry', name: 'Entry', order: 1 },
        { id: 'first_action', name: 'First Action', order: 2 },
      ];
      
      createFunnel('v29_onboarding', stages);
      
      const startTime = Date.now();
      vi.setSystemTime(startTime);
      trackFunnelStep('v29_onboarding', 'entry', 'user_1');
      
      vi.advanceTimersByTime(3000); // 3 seconds
      trackFunnelStep('v29_onboarding', 'first_action', 'user_1');
      
      const metrics = getFunnelMetrics('v29_onboarding');
      expect(metrics.timeToFirstAction).toBe(3000);
    });

    it('should track navigation error rate', () => {
      const stages: FunnelStage[] = [
        { id: 'page_a', name: 'Page A', order: 1 },
        { id: 'page_b', name: 'Page B', order: 2 },
      ];
      
      createFunnel('v29_navigation', stages);
      
      // 10 navigation attempts
      for (let i = 0; i < 10; i++) {
        trackFunnelStep('v29_navigation', 'page_a', `user_${i}`);
      }
      
      // 7 users successfully navigate to page_b (3 errors)
      for (let i = 0; i < 7; i++) {
        trackFunnelStep('v29_navigation', 'page_b', `user_${i}`);
      }
      
      const metrics = getFunnelMetrics('v29_navigation');
      expect(metrics.navigationErrorRate).toBe(0.3); // 30% error rate
    });

    it('should track workflow completion rate', () => {
      const stages: FunnelStage[] = [
        { id: 'start', name: 'Start', order: 1 },
        { id: 'middle', name: 'Middle', order: 2 },
        { id: 'complete', name: 'Complete', order: 3 },
      ];
      
      createFunnel('v29_workflow', stages);
      
      // 20 start
      for (let i = 0; i < 20; i++) {
        trackFunnelStep('v29_workflow', 'start', `user_${i}`);
        trackFunnelStep('v29_workflow', 'middle', `user_${i}`);
      }
      
      // 15 complete
      for (let i = 0; i < 15; i++) {
        trackFunnelStep('v29_workflow', 'complete', `user_${i}`);
      }
      
      const metrics = getFunnelMetrics('v29_workflow');
      expect(metrics.workflowCompletionRate).toBe(0.75); // 75% completion
    });
  });
});
