import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  trackFastLanePresented,
  trackFastLaneAccepted,
  trackFastLaneRejected,
  FastLaneEvent,
  setSessionId,
  getSessionId,
} from './ttfvTelemetry';

describe('TTFV Fast Lane Telemetry', () => {
  const mockFetch = vi.fn();
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = mockFetch;
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-04T14:00:00Z'));
    setSessionId('test-session-123');
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe('trackFastLanePresented', () => {
    it('should emit fast_lane_presented event with all metadata', async () => {
      await trackFastLanePresented(
        'user-123',
        0.85,
        'fast_lane',
        4.5,
        ['customization', 'first_run'],
        ['Perfil de baixo risco', 'Dados de contexto disponíveis']
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/events'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        userId: 'user-123',
        sessionId: 'test-session-123',
        step: 'fast_lane_offer',
        metadata: {
          fast_lane_event: FastLaneEvent.FAST_LANE_PRESENTED,
          confidence: 0.85,
          recommendedPath: 'fast_lane',
          timeSavedMinutes: 4.5,
          skippedSteps: ['customization', 'first_run'],
          reasons: ['Perfil de baixo risco', 'Dados de contexto disponíveis'],
        },
      });
    });

    it('should include timestamp in ISO format', async () => {
      await trackFastLanePresented(
        'user-123',
        0.75,
        'standard',
        0,
        [],
        []
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.timestamp).toBe('2026-03-04T14:00:00.000Z');
    });
  });

  describe('trackFastLaneAccepted', () => {
    it('should emit fast_lane_accepted event with metadata', async () => {
      await trackFastLaneAccepted(
        'user-456',
        0.92,
        3.5,
        ['customization']
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/events'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        userId: 'user-456',
        sessionId: 'test-session-123',
        step: 'fast_lane_accept',
        metadata: {
          fast_lane_event: FastLaneEvent.FAST_LANE_ACCEPTED,
          confidence: 0.92,
          timeSavedMinutes: 3.5,
          skippedSteps: ['customization'],
        },
      });
    });

    it('should handle multiple skipped steps', async () => {
      await trackFastLaneAccepted(
        'user-789',
        0.88,
        6.0,
        ['customization', 'first_run', 'tutorial']
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.metadata.skippedSteps).toEqual(['customization', 'first_run', 'tutorial']);
      expect(body.metadata.timeSavedMinutes).toBe(6.0);
    });
  });

  describe('trackFastLaneRejected', () => {
    it('should emit fast_lane_rejected event with metadata', async () => {
      await trackFastLaneRejected(
        'user-abc',
        0.65,
        ['Perfil médio risco']
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/events'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({
        userId: 'user-abc',
        sessionId: 'test-session-123',
        step: 'fast_lane_reject',
        reason: 'user_rejected_fast_lane',
        metadata: {
          fast_lane_event: FastLaneEvent.FAST_LANE_REJECTED,
          confidence: 0.65,
          reasons: ['Perfil médio risco'],
        },
      });
    });

    it('should handle multiple rejection reasons', async () => {
      await trackFastLaneRejected(
        'user-def',
        0.70,
        ['Perfil médio risco', 'Poucos dados de contexto', 'Histórico incompleto']
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.metadata.reasons).toEqual(['Perfil médio risco', 'Poucos dados de contexto', 'Histórico incompleto']);
    });
  });

  describe('error handling', () => {
    it('should silently fail when fetch fails', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await trackFastLaneAccepted('user-123', 0.85, 4.5, ['customization']);

      expect(consoleSpy).toHaveBeenCalledWith(
        'TTFV telemetry error:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('should use current session ID', async () => {
      setSessionId('custom-session-456');

      await trackFastLanePresented(
        'user-123',
        0.85,
        'fast_lane',
        4.5,
        ['customization'],
        ['Low risk']
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.sessionId).toBe('custom-session-456');
    });
  });
});
