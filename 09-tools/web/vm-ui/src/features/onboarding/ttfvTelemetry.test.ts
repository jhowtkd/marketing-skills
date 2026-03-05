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
  trackOnboardingStarted,
  trackFirstValueReachedLegacy,
  trackExperimentExposed,
  TTFVEvent,
  FastLaneEvent,
  SaveResumeEvent,
  ExperimentEvent,
  setSessionId,
  getSessionId,
  setActiveExperiment,
  clearActiveExperiment,
  getActiveExperiment,
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

  // ==========================================
  // v43: CONTRACT TESTS - Eventos Essenciais
  // ==========================================
  // Estes testes validam a emissão dos eventos essenciais e
  // o shape mínimo de payload (campos obrigatórios)
  describe('CONTRATO: Eventos essenciais de onboarding', () => {
    it('deve emitir evento onboarding_started com shape mínimo válido', async () => {
      await trackOnboardingStarted('user-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/onboarding/events'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
      
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      
      // CONTRATO: Shape mínimo obrigatório
      expect(body).toMatchObject({
        event: TTFVEvent.ONBOARDING_STARTED,
        userId: 'user-123',
        sessionId: expect.any(String),
        timestamp: expect.any(String),
      });
      
      // CONTRATO: Campos obrigatórios não podem ser vazios
      expect(body.userId).not.toBe('');
      expect(body.sessionId).not.toBe('');
      expect(body.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/); // ISO format
    });

    it('deve emitir evento onboarding_progress_saved com campos obrigatórios', async () => {
      await trackOnboardingProgressSaved('user-123', 'workspace_setup', 'auto_save');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      
      // CONTRATO: Shape mínimo obrigatório
      expect(body).toMatchObject({
        event: expect.any(String),
        userId: 'user-123',
        sessionId: expect.any(String),
        timestamp: expect.any(String),
        step: 'progress_save',
        metadata: {
          save_resume_event: SaveResumeEvent.PROGRESS_SAVED,
          savedStep: 'workspace_setup',
          source: 'auto_save',
        },
      });
      
      // CONTRATO: savedStep deve ser um step válido
      expect(['welcome', 'template_selection', 'workspace_setup', 'customization', 'completion'])
        .toContain(body.metadata.savedStep);
      
      // CONTRATO: source deve ser um valor válido
      expect(['manual', 'auto_save', 'resume']).toContain(body.metadata.source);
    });

    it('deve emitir evento fast_lane_presented com todos os campos obrigatórios', async () => {
      await trackFastLanePresented(
        'user-123',
        0.85,
        'fast_lane',
        4.5,
        ['customization'],
        ['Perfil de baixo risco']
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      
      // CONTRATO: Shape mínimo obrigatório
      expect(body).toMatchObject({
        userId: 'user-123',
        sessionId: expect.any(String),
        timestamp: expect.any(String),
        step: 'fast_lane_offer',
        metadata: {
          fast_lane_event: FastLaneEvent.FAST_LANE_PRESENTED,
          confidence: 0.85,
          recommendedPath: 'fast_lane',
          timeSavedMinutes: 4.5,
          skippedSteps: ['customization'],
          reasons: ['Perfil de baixo risco'],
        },
      });
      
      // CONTRATO: confidence deve estar entre 0 e 1
      expect(body.metadata.confidence).toBeGreaterThanOrEqual(0);
      expect(body.metadata.confidence).toBeLessThanOrEqual(1);
      
      // CONTRATO: recommendedPath deve ser fast_lane ou standard
      expect(['fast_lane', 'standard']).toContain(body.metadata.recommendedPath);
      
      // CONTRATO: skippedSteps deve ser um array
      expect(Array.isArray(body.metadata.skippedSteps)).toBe(true);
      
      // CONTRATO: reasons deve ser um array
      expect(Array.isArray(body.metadata.reasons)).toBe(true);
    });

    it('deve emitir evento fast_lane_accepted com shape válido', async () => {
      await trackFastLaneAccepted(
        'user-123',
        0.92,
        3.5,
        ['customization', 'first_run']
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      
      // CONTRATO: Shape mínimo obrigatório
      expect(body).toMatchObject({
        userId: 'user-123',
        sessionId: expect.any(String),
        timestamp: expect.any(String),
        step: 'fast_lane_accept',
        metadata: {
          fast_lane_event: FastLaneEvent.FAST_LANE_ACCEPTED,
          confidence: 0.92,
          timeSavedMinutes: 3.5,
          skippedSteps: ['customization', 'first_run'],
        },
      });
      
      // CONTRATO: timeSavedMinutes deve ser positivo
      expect(body.metadata.timeSavedMinutes).toBeGreaterThan(0);
    });

    it('deve emitir evento fast_lane_rejected com shape válido', async () => {
      await trackFastLaneRejected(
        'user-123',
        0.65,
        ['Perfil médio risco', 'Poucos dados']
      );

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      
      // CONTRATO: Shape mínimo obrigatório
      expect(body).toMatchObject({
        userId: 'user-123',
        sessionId: expect.any(String),
        timestamp: expect.any(String),
        step: 'fast_lane_reject',
        reason: 'user_rejected_fast_lane',
        metadata: {
          fast_lane_event: FastLaneEvent.FAST_LANE_REJECTED,
          confidence: 0.65,
          reasons: ['Perfil médio risco', 'Poucos dados'],
        },
      });
      
      // CONTRATO: reason deve ser preenchido
      expect(body.reason).not.toBe('');
    });

    it('deve emitir evento first_value_reached com shape mínimo válido', async () => {
      await trackFirstValueReachedLegacy('user-123', 120000, 'blog-post');

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      
      // CONTRATO: Shape mínimo obrigatório
      expect(body).toMatchObject({
        event: TTFVEvent.FIRST_VALUE_REACHED,
        userId: 'user-123',
        sessionId: expect.any(String),
        timestamp: expect.any(String),
        ttfvMs: 120000,
        ttfvMinutes: 2, // 120000ms = 2min
        templateId: 'blog-post',
      });
      
      // CONTRATO: ttfvMs deve ser positivo
      expect(body.ttfvMs).toBeGreaterThan(0);
      
      // CONTRATO: ttfvMinutes deve ser consistente com ttfvMs
      expect(body.ttfvMinutes).toBeCloseTo(body.ttfvMs / 60000, 1);
    });
  });

  // ==========================================
  // v43: FALLBACK TESTS - Telemetry Errors
  // ==========================================
  describe('FALLBACK: Telemetry de erro é emitida em falhas', () => {
    it('deve logar erro silenciosamente quando telemetry falha', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Simula falha de rede
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await trackOnboardingStarted('user-123');

      // CONTRATO: Erro deve ser logado mas não lançar exceção
      expect(consoleSpy).toHaveBeenCalledWith(
        'TTFV telemetry error:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('deve logar erro quando API retorna status 500', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await trackFastLanePresented(
        'user-123',
        0.85,
        'fast_lane',
        4.5,
        ['customization'],
        ['Low risk']
      );

      // CONTRATO: Erro HTTP deve ser logado
      expect(consoleSpy).toHaveBeenCalledWith(
        'TTFV telemetry error:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('deve logar erro quando API retorna 429 (rate limit)', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
      });

      await trackOnboardingProgressSaved('user-123', 'workspace_setup', 'auto_save');

      // CONTRATO: Rate limit deve ser logado silenciosamente
      expect(consoleSpy).toHaveBeenCalledWith(
        'TTFV telemetry error:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('deve continuar funcionando mesmo quando todas as chamadas de telemetry falham', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Todas as chamadas falham
      mockFetch.mockRejectedValue(new Error('Service unavailable'));

      // Nenhuma deve lançar exceção
      await expect(trackOnboardingStarted('user-1')).resolves.not.toThrow();
      await expect(trackFastLanePresented('user-2', 0.8, 'fast_lane', 3, [], [])).resolves.not.toThrow();
      await expect(trackFastLaneAccepted('user-3', 0.9, 4, ['customization'])).resolves.not.toThrow();
      await expect(trackOnboardingProgressSaved('user-4', 'workspace_setup', 'auto_save')).resolves.not.toThrow();

      // Todas as falhas devem ter sido logadas
      expect(consoleSpy).toHaveBeenCalledTimes(4);

      consoleSpy.mockRestore();
    });
  });

  // ==========================================
  // v44: EXPERIMENT TESTS
  // ==========================================
  describe('v44: Experiment Telemetry', () => {
    beforeEach(() => {
      clearActiveExperiment();
    });

    afterEach(() => {
      clearActiveExperiment();
    });

    describe('trackExperimentExposed', () => {
      it('should emit experiment_exposed event with experiment and variant IDs', async () => {
        await trackExperimentExposed('user-123', 'onboarding_cta_v44', 'variant_a');

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
          step: 'experiment_exposed',
          experimentId: 'onboarding_cta_v44',
          variantId: 'variant_a',
          metadata: {
            experiment_event: ExperimentEvent.EXPERIMENT_EXPOSED,
            exposedAt: expect.any(String),
          },
        });
      });

      it('should set active experiment context when tracking exposure', async () => {
        expect(getActiveExperiment()).toBeNull();

        await trackExperimentExposed('user-123', 'onboarding_cta_v44', 'variant_b');

        expect(getActiveExperiment()).toEqual({
          experimentId: 'onboarding_cta_v44',
          variantId: 'variant_b',
          userId: 'user-123',
        });
      });

      it('should include timestamp in ISO format', async () => {
        await trackExperimentExposed('user-456', 'onboarding_resume_timing_v44', 'variant_delayed_2s');

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.timestamp).toBe('2026-03-04T14:00:00.000Z');
        expect(body.metadata.exposedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
      });
    });

    describe('Active Experiment Context', () => {
      it('should include experiment data in subsequent events after exposure', async () => {
        // First, expose the experiment
        await trackExperimentExposed('user-123', 'onboarding_cta_v44', 'variant_a');

        // Clear mock to check next call
        mockFetch.mockClear();

        // Track another event
        await trackOnboardingStarted('user-123');

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body).toMatchObject({
          event: TTFVEvent.ONBOARDING_STARTED,
          userId: 'user-123',
          experimentId: 'onboarding_cta_v44',
          variantId: 'variant_a',
        });
      });

      it('should include experiment data in fast lane events', async () => {
        await trackExperimentExposed('user-123', 'onboarding_cta_v44', 'variant_start_now');
        mockFetch.mockClear();

        await trackFastLanePresented('user-123', 0.85, 'fast_lane', 4.5, ['customization'], ['Low risk']);

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.experimentId).toBe('onboarding_cta_v44');
        expect(body.variantId).toBe('variant_start_now');
      });

      it('should include experiment data in save/resume events', async () => {
        await trackExperimentExposed('user-123', 'onboarding_cta_v44', 'variant_a');
        mockFetch.mockClear();

        await trackOnboardingProgressSaved('user-123', 'workspace_setup', 'auto_save');

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.experimentId).toBe('onboarding_cta_v44');
        expect(body.variantId).toBe('variant_a');
      });

      it('should not include experiment data before exposure', async () => {
        // Track event without exposure
        await trackOnboardingStarted('user-123');

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.experimentId).toBeUndefined();
        expect(body.variantId).toBeUndefined();
      });

      it('should not include experiment data after clearing context', async () => {
        // Expose and then clear
        await trackExperimentExposed('user-123', 'onboarding_cta_v44', 'variant_a');
        clearActiveExperiment();
        mockFetch.mockClear();

        // Track event after clearing
        await trackOnboardingStarted('user-123');

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.experimentId).toBeUndefined();
        expect(body.variantId).toBeUndefined();
      });
    });

    describe('Backward Compatibility', () => {
      it('should work without experiment data (no exposure)', async () => {
        await trackOnboardingStarted('user-123');

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body).toMatchObject({
          event: TTFVEvent.ONBOARDING_STARTED,
          userId: 'user-123',
          sessionId: expect.any(String),
          timestamp: expect.any(String),
        });
        // No experiment fields when not in experiment
        expect(body.experimentId).toBeUndefined();
        expect(body.variantId).toBeUndefined();
      });

      it('should work without experiment data for fast lane events', async () => {
        await trackFastLanePresented('user-123', 0.85, 'fast_lane', 4.5, ['customization'], ['Low risk']);

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.metadata.fast_lane_event).toBe(FastLaneEvent.FAST_LANE_PRESENTED);
        expect(body.experimentId).toBeUndefined();
        expect(body.variantId).toBeUndefined();
      });

      it('should work without experiment data for save/resume events', async () => {
        await trackOnboardingResumeAccepted('user-123', 'workspace_setup');

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.metadata.save_resume_event).toBe(SaveResumeEvent.RESUME_ACCEPTED);
        expect(body.experimentId).toBeUndefined();
        expect(body.variantId).toBeUndefined();
      });
    });

    describe('setActiveExperiment / getActiveExperiment / clearActiveExperiment', () => {
      it('should set and get active experiment', () => {
        expect(getActiveExperiment()).toBeNull();

        setActiveExperiment('exp_123', 'variant_a', 'user-456');

        expect(getActiveExperiment()).toEqual({
          experimentId: 'exp_123',
          variantId: 'variant_a',
          userId: 'user-456',
        });
      });

      it('should update active experiment', () => {
        setActiveExperiment('exp_123', 'variant_a', 'user-456');
        setActiveExperiment('exp_123', 'variant_b', 'user-456');

        expect(getActiveExperiment()?.variantId).toBe('variant_b');
      });

      it('should clear active experiment', () => {
        setActiveExperiment('exp_123', 'variant_a', 'user-456');
        clearActiveExperiment();

        expect(getActiveExperiment()).toBeNull();
      });
    });

    describe('Error Handling', () => {
      it('should silently fail when experiment exposure tracking fails', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        mockFetch.mockRejectedValueOnce(new Error('Network error'));

        // Should not throw
        await expect(trackExperimentExposed('user-123', 'exp_1', 'variant_a')).resolves.not.toThrow();

        expect(consoleSpy).toHaveBeenCalledWith(
          'TTFV telemetry error:',
          expect.any(Error)
        );

        consoleSpy.mockRestore();
      });
    });
  });
});
