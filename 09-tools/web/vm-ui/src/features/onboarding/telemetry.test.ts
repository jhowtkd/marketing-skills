import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  trackOnboardingStarted,
  trackOnboardingCompleted,
  trackOnboardingDropoff,
  trackTimeToFirstValue,
  getOnboardingMetrics,
  OnboardingStep,
  OnboardingEvent,
} from './telemetry';

describe('Onboarding Telemetry', () => {
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

  describe('trackOnboardingStarted', () => {
    it('should emit onboarding_started event', async () => {
      await trackOnboardingStarted('user-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/events'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('onboarding_started'),
        })
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'onboarding_started',
        userId: 'user-123',
        timestamp: '2026-03-02T12:00:00.000Z',
      });
    });
  });

  describe('trackOnboardingCompleted', () => {
    it('should emit onboarding_completed event with duration', async () => {
      await trackOnboardingCompleted('user-123', 125000); // 2m 5s

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'onboarding_completed',
        userId: 'user-123',
        durationMs: 125000,
      });
    });
  });

  describe('trackOnboardingDropoff', () => {
    it('should emit onboarding_dropoff event with step', async () => {
      await trackOnboardingDropoff('user-123', OnboardingStep.WORKSPACE_SETUP);

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'onboarding_dropoff',
        userId: 'user-123',
        step: 'workspace_setup',
      });
    });
  });

  describe('trackTimeToFirstValue', () => {
    it('should emit ttfv event with template used', async () => {
      await trackTimeToFirstValue('user-123', 45000, 'blog-post-template');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'time_to_first_value',
        userId: 'user-123',
        durationMs: 45000,
        templateId: 'blog-post-template',
      });
    });

    it('should emit ttfv event without template', async () => {
      await trackTimeToFirstValue('user-123', 60000);

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        event: 'time_to_first_value',
        userId: 'user-123',
        durationMs: 60000,
      });
      expect(body.templateId).toBeUndefined();
    });
  });

  describe('getOnboardingMetrics', () => {
    it('should fetch metrics from API', async () => {
      const mockMetrics = {
        totalStarted: 100,
        totalCompleted: 80,
        completionRate: 0.8,
        averageTimeToFirstValueMs: 45000,
        dropoffByStep: {
          workspace_setup: 5,
          template_selection: 10,
          customization: 5,
        },
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMetrics),
      });

      const metrics = await getOnboardingMetrics();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/metrics'),
        expect.any(Object)
      );
      expect(metrics).toEqual(mockMetrics);
    });

    it('should return null on API error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const metrics = await getOnboardingMetrics();

      expect(metrics).toBeNull();
    });
  });
});
