import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  trackFastLanePresented,
  trackFastLaneAccepted,
  trackFastLaneRejected,
  trackOnboardingProgressSaved,
  trackOnboardingResumePresented,
  trackOnboardingResumeAccepted,
  trackOnboardingResumeRejected,
  trackOnboardingResumeFailed,
  FastLaneEvent,
  SaveResumeEvent,
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

  // v40: Save/Resume telemetry tests
  describe('trackOnboardingProgressSaved', () => {
    it('should emit progress_saved event with auto_save source', async () => {
      await trackOnboardingProgressSaved('user-123', 'workspace_setup', 'auto_save');

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
        step: 'progress_save',
        metadata: {
          save_resume_event: SaveResumeEvent.PROGRESS_SAVED,
          savedStep: 'workspace_setup',
          source: 'auto_save',
        },
      });
    });

    it('should emit progress_saved event with manual source', async () => {
      await trackOnboardingProgressSaved('user-456', 'template_selection', 'manual');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.metadata).toMatchObject({
        save_resume_event: SaveResumeEvent.PROGRESS_SAVED,
        savedStep: 'template_selection',
        source: 'manual',
      });
    });

    it('should emit progress_saved event with resume source', async () => {
      await trackOnboardingProgressSaved('user-789', 'customization', 'resume');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.metadata).toMatchObject({
        save_resume_event: SaveResumeEvent.PROGRESS_SAVED,
        savedStep: 'customization',
        source: 'resume',
      });
    });
  });

  describe('trackOnboardingResumePresented', () => {
    it('should emit resume_presented event with last step', async () => {
      await trackOnboardingResumePresented('user-123', 'workspace_setup');

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
        step: 'resume_prompt',
        metadata: {
          save_resume_event: SaveResumeEvent.RESUME_PRESENTED,
          lastStep: 'workspace_setup',
        },
      });
    });

    it('should emit resume_presented event for template_selection step', async () => {
      await trackOnboardingResumePresented('user-456', 'template_selection');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.metadata.lastStep).toBe('template_selection');
    });
  });

  describe('trackOnboardingResumeAccepted', () => {
    it('should emit resume_accepted event with resumed step', async () => {
      await trackOnboardingResumeAccepted('user-123', 'customization');

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
        step: 'resume_accept',
        metadata: {
          save_resume_event: SaveResumeEvent.RESUME_ACCEPTED,
          resumedStep: 'customization',
        },
      });
    });
  });

  describe('trackOnboardingResumeRejected', () => {
    it('should emit resume_rejected event with reason', async () => {
      await trackOnboardingResumeRejected('user-123', 'user_chose_fresh_start');

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
        step: 'resume_reject',
        reason: 'user_chose_fresh_start',
        metadata: {
          save_resume_event: SaveResumeEvent.RESUME_REJECTED,
        },
      });
    });

    it('should emit resume_rejected event with different reason', async () => {
      await trackOnboardingResumeRejected('user-456', 'user_prefers_clean_slate');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.reason).toBe('user_prefers_clean_slate');
    });
  });

  describe('trackOnboardingResumeFailed', () => {
    it('should emit resume_failed event with error details', async () => {
      await trackOnboardingResumeFailed('user-123', 'Progress data corrupted', 'workspace_setup');

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
        step: 'resume_fail',
        reason: 'resume_failed',
        metadata: {
          save_resume_event: SaveResumeEvent.RESUME_FAILED,
          error: 'Progress data corrupted',
          failedStep: 'workspace_setup',
        },
      });
    });

    it('should emit resume_failed event for hydration error', async () => {
      await trackOnboardingResumeFailed('user-789', 'Failed to hydrate state', 'template_selection');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.metadata.error).toBe('Failed to hydrate state');
      expect(body.metadata.failedStep).toBe('template_selection');
    });
  });

  describe('Save/Resume error handling', () => {
    it('should silently fail when save telemetry fails', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await trackOnboardingProgressSaved('user-123', 'workspace_setup', 'auto_save');

      expect(consoleSpy).toHaveBeenCalledWith(
        'TTFV telemetry error:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('should silently fail when resume telemetry fails', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await trackOnboardingResumeAccepted('user-123', 'workspace_setup');

      expect(consoleSpy).toHaveBeenCalledWith(
        'TTFV telemetry error:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });
  });
});
