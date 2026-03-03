/**
 * TTFV Telemetry tests for v38 onboarding acceleration
 * Validates event emission and median_ttfv_minutes calculation by cohort
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  TTFVEvent,
  trackOnboardingStarted,
  trackStepViewed,
  trackStepCompleted,
  trackFirstValueReached,
  trackDropoffReason,
  calculateMedianTTFVByCohort,
  getSessionId,
  setSessionId,
} from './ttfvTelemetry';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('TTFV Telemetry', () => {
  const mockUserId = 'user-123';
  const mockSessionId = 'session-456';

  beforeEach(() => {
    vi.clearAllMocks();
    setSessionId(mockSessionId);
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Event emission', () => {
    it('should emit onboarding_started event with correct payload', async () => {
      await trackOnboardingStarted(mockUserId);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      const payload = JSON.parse(options.body);

      expect(payload.event).toBe(TTFVEvent.ONBOARDING_STARTED);
      expect(payload.userId).toBe(mockUserId);
      expect(payload.sessionId).toBe(mockSessionId);
      expect(payload.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
      expect(payload.metadata).toBeUndefined();
    });

    it('should emit step_viewed event with step information', async () => {
      const step = 'workspace_setup';
      await trackStepViewed(mockUserId, step);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      const payload = JSON.parse(options.body);

      expect(payload.event).toBe(TTFVEvent.STEP_VIEWED);
      expect(payload.step).toBe(step);
      expect(payload.userId).toBe(mockUserId);
      expect(payload.sessionId).toBe(mockSessionId);
    });

    it('should emit step_completed event with duration', async () => {
      const step = 'template_selection';
      const durationMs = 15000;
      await trackStepCompleted(mockUserId, step, durationMs);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      const payload = JSON.parse(options.body);

      expect(payload.event).toBe(TTFVEvent.STEP_COMPLETED);
      expect(payload.step).toBe(step);
      expect(payload.durationMs).toBe(durationMs);
    });

    it('should emit first_value_reached event with TTFV data', async () => {
      const ttfvMs = 120000;
      const templateId = 'blog-post';
      await trackFirstValueReached(mockUserId, ttfvMs, templateId);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      const payload = JSON.parse(options.body);

      expect(payload.event).toBe(TTFVEvent.FIRST_VALUE_REACHED);
      expect(payload.ttfvMs).toBe(ttfvMs);
      expect(payload.ttfvMinutes).toBe(2); // 120000ms / 60000
      expect(payload.templateId).toBe(templateId);
    });

    it('should emit dropoff_reason event with reason and step', async () => {
      const step = 'customization';
      const reason = 'too_complex';
      const metadata = { timeSpentMs: 5000 };
      await trackDropoffReason(mockUserId, step, reason, metadata);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      const payload = JSON.parse(options.body);

      expect(payload.event).toBe(TTFVEvent.DROPOFF_REASON);
      expect(payload.step).toBe(step);
      expect(payload.reason).toBe(reason);
      expect(payload.metadata).toEqual(metadata);
    });
  });

  describe('Session management', () => {
    it('should generate unique session ID if not set', () => {
      setSessionId(null as unknown as string);
      const sessionId = getSessionId();
      expect(sessionId).toMatch(/^sess_[a-z0-9]{12}$/);
    });

    it('should persist session ID across calls', () => {
      const sessionId1 = getSessionId();
      const sessionId2 = getSessionId();
      expect(sessionId1).toBe(sessionId2);
    });

    it('should allow manual session ID override', () => {
      const customSessionId = 'custom-session-789';
      setSessionId(customSessionId);
      expect(getSessionId()).toBe(customSessionId);
    });
  });

  describe('Median TTFV calculation by cohort', () => {
    it('should calculate median TTFV for single cohort', () => {
      const events = [
        { userId: 'u1', ttfvMinutes: 5, cohort: '2024-01' },
        { userId: 'u2', ttfvMinutes: 10, cohort: '2024-01' },
        { userId: 'u3', ttfvMinutes: 15, cohort: '2024-01' },
      ];

      const result = calculateMedianTTFVByCohort(events);

      expect(result['2024-01']).toBe(10);
    });

    it('should calculate median TTFV for even number of events', () => {
      const events = [
        { userId: 'u1', ttfvMinutes: 5, cohort: '2024-01' },
        { userId: 'u2', ttfvMinutes: 10, cohort: '2024-01' },
        { userId: 'u3', ttfvMinutes: 15, cohort: '2024-01' },
        { userId: 'u4', ttfvMinutes: 20, cohort: '2024-01' },
      ];

      const result = calculateMedianTTFVByCohort(events);

      expect(result['2024-01']).toBe(12.5); // (10 + 15) / 2
    });

    it('should group by cohort correctly', () => {
      const events = [
        { userId: 'u1', ttfvMinutes: 5, cohort: '2024-01' },
        { userId: 'u2', ttfvMinutes: 10, cohort: '2024-02' },
        { userId: 'u3', ttfvMinutes: 15, cohort: '2024-01' },
        { userId: 'u4', ttfvMinutes: 20, cohort: '2024-02' },
      ];

      const result = calculateMedianTTFVByCohort(events);

      expect(result['2024-01']).toBe(10);
      expect(result['2024-02']).toBe(15);
    });

    it('should return empty object for empty events array', () => {
      const result = calculateMedianTTFVByCohort([]);
      expect(result).toEqual({});
    });

    it('should handle cohorts with single event', () => {
      const events = [
        { userId: 'u1', ttfvMinutes: 8, cohort: '2024-01' },
        { userId: 'u2', ttfvMinutes: 12, cohort: '2024-02' },
      ];

      const result = calculateMedianTTFVByCohort(events);

      expect(result['2024-01']).toBe(8);
      expect(result['2024-02']).toBe(12);
    });
  });

  describe('Error handling', () => {
    it('should not throw when fetch fails', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      await expect(trackOnboardingStarted(mockUserId)).resolves.not.toThrow();
      expect(consoleSpy).toHaveBeenCalledWith('TTFV telemetry error:', expect.any(Error));

      consoleSpy.mockRestore();
    });

    it('should not throw when server returns error', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 500 });
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      await expect(trackOnboardingStarted(mockUserId)).resolves.not.toThrow();
      expect(consoleSpy).toHaveBeenCalledWith('TTFV telemetry error:', expect.any(Error));

      consoleSpy.mockRestore();
    });
  });
});
