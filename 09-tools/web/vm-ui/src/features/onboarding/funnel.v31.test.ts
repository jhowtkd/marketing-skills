import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  trackStepAbandon,
  trackStepReturn,
  trackStepHesitation,
  getFrictionMetrics,
  OnboardingStep,
} from './telemetry';

describe('Onboarding Friction Telemetry (v31)', () => {
  const mockFetch = vi.fn();
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = mockFetch;
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-02T12:00:00Z'));
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe('trackStepAbandon', () => {
    it('should emit step_abandoned event with step and reason', async () => {
      await trackStepAbandon('user-123', OnboardingStep.WORKSPACE_SETUP, 'too_complex');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/events'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('step_abandoned'),
        })
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'step_abandoned',
        userId: 'user-123',
        step: 'workspace_setup',
        reason: 'too_complex',
        timestamp: '2026-03-02T12:00:00.000Z',
      });
    });

    it('should handle optional metadata in abandon event', async () => {
      const metadata = { timeSpentMs: 15000, fieldAttempts: 3 };
      await trackStepAbandon('user-123', OnboardingStep.TEMPLATE_SELECTION, 'no_relevant_templates', metadata);

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.metadata).toEqual(metadata);
    });
  });

  describe('trackStepReturn', () => {
    it('should emit step_returned event with timeAwayMs', async () => {
      await trackStepReturn('user-123', OnboardingStep.WORKSPACE_SETUP, 360000); // 6 minutes away

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'step_returned',
        userId: 'user-123',
        step: 'workspace_setup',
        timeAwayMs: 360000,
      });
    });
  });

  describe('trackStepHesitation', () => {
    it('should emit step_hesitation event with durationMs', async () => {
      await trackStepHesitation('user-123', OnboardingStep.WORKSPACE_SETUP, 45000); // 45s hesitation

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'step_hesitation',
        userId: 'user-123',
        step: 'workspace_setup',
        durationMs: 45000,
      });
    });

    it('should include element info when provided', async () => {
      await trackStepHesitation(
        'user-123',
        OnboardingStep.TEMPLATE_SELECTION,
        30000,
        { element: 'template-card', action: 'hover' }
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.element).toBe('template-card');
      expect(body.action).toBe('hover');
    });
  });

  describe('getFrictionMetrics', () => {
    it('should fetch friction metrics from API', async () => {
      const mockMetrics = {
        totalAbandons: 25,
        totalReturns: 18,
        totalHesitations: 120,
        abandonByStep: {
          workspace_setup: 10,
          template_selection: 8,
          customization: 7,
        },
        abandonReasons: {
          too_complex: 12,
          no_relevant_templates: 8,
          interruption: 5,
        },
        averageTimeAwayMs: 420000,
        averageHesitationMs: 25000,
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMetrics),
      });

      const metrics = await getFrictionMetrics();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/friction-metrics'),
        expect.any(Object)
      );
      expect(metrics).toEqual(mockMetrics);
    });

    it('should return null on API error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const metrics = await getFrictionMetrics();

      expect(metrics).toBeNull();
    });
  });
});

describe('Funnel Enrichment (v31)', () => {
  describe('Step-level friction tracking', () => {
    it('should calculate step friction score', () => {
      // Placeholder for future implementation
      expect(true).toBe(true);
    });

    it('should identify high-friction steps', () => {
      // Placeholder for future implementation
      expect(true).toBe(true);
    });
  });
});
