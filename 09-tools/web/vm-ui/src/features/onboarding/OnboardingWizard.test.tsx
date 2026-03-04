import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OnboardingWizard, OnboardingStep } from './OnboardingWizard';

// Mock telemetry
vi.mock('./telemetry', () => ({
  trackOnboardingStarted: vi.fn(),
  trackOnboardingCompleted: vi.fn(),
  trackOnboardingDropoff: vi.fn(),
  OnboardingStep: {
    WELCOME: 'welcome',
    WORKSPACE_SETUP: 'workspace_setup',
    TEMPLATE_SELECTION: 'template_selection',
    CUSTOMIZATION: 'customization',
    FIRST_RUN: 'first_run',
    COMPLETION: 'completion',
  },
}));

// Mock ttfvTelemetry
vi.mock('./ttfvTelemetry', () => ({
  trackFastLanePresented: vi.fn(),
  trackFastLaneAccepted: vi.fn(),
  trackFastLaneRejected: vi.fn(),
}));

// Mock funnel
vi.mock('./funnel', () => ({
  saveFunnelState: vi.fn(),
  loadFunnelState: vi.fn(() => null),
  clearFunnelState: vi.fn(),
  getNextStep: vi.fn((step) => {
    const order = [
      'welcome',
      'workspace_setup',
      'template_selection',
      'customization',
      'completion',
    ];
    const idx = order.indexOf(step);
    return idx >= 0 && idx < order.length - 1 ? order[idx + 1] : null;
  }),
}));

describe('OnboardingWizard', () => {
  const mockOnComplete = vi.fn();
  const mockOnSkip = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render wizard with initial welcome step', () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      expect(screen.getByText(/vm studio/i)).toBeInTheDocument();
    });

    it('should show progress indicator', () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.getByText(/passo 1 de 5/i)).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should advance to next step when clicking continue', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      const continueBtn = screen.getByRole('button', { name: /continuar/i });
      fireEvent.click(continueBtn);

      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });
    });

    it('should show back button after first step', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      const continueBtn = screen.getByRole('button', { name: /continuar/i });
      fireEvent.click(continueBtn);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /voltar/i })).toBeInTheDocument();
      });
    });

    it('should go back to previous step when clicking back', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Go to step 2
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      // Go back
      fireEvent.click(screen.getByRole('button', { name: /voltar/i }));
      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });
    });
  });

  describe('step validation', () => {
    it('should disable continue when workspace name is empty', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Go to workspace step
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        const continueBtn = screen.getByRole('button', { name: /continuar/i });
        expect(continueBtn).toBeDisabled();
      });
    });

    it('should enable continue when workspace name is filled', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Go to workspace step
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        const input = screen.getByPlaceholderText(/nome do workspace/i);
        fireEvent.change(input, { target: { value: 'Meu Workspace' } });
      });

      const continueBtn = screen.getByRole('button', { name: /continuar/i });
      expect(continueBtn).not.toBeDisabled();
    });
  });

  describe('completion', () => {
    it('should call onComplete when finishing all steps', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Step 1: Welcome -> click continue
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      // Step 2: Workspace -> fill name and continue
      const input = screen.getByPlaceholderText(/nome do workspace/i);
      fireEvent.change(input, { target: { value: 'Meu Workspace' } });
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/escolha um template/i)).toBeInTheDocument();
      });

      // Step 3: Template -> select template and continue
      const templateBtn = screen.getByText(/blog post/i);
      fireEvent.click(templateBtn);
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/personalização/i)).toBeInTheDocument();
      });

      // Step 4: Customization -> continue to completion
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/concluída/i)).toBeInTheDocument();
      });

      // Click finish on completion step
      const finishBtn = screen.getByRole('button', { name: /começar a usar/i });
      fireEvent.click(finishBtn);

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalled();
      });
    });
  });

  describe('skip', () => {
    it('should call onSkip when clicking skip button', () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      const skipBtn = screen.getByRole('button', { name: /pular/i });
      fireEvent.click(skipBtn);

      expect(mockOnSkip).toHaveBeenCalled();
    });
  });

  describe('progress tracking', () => {
    it('should update progress bar as steps advance', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      expect(screen.getByText(/passo 1 de 5/i)).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        expect(screen.getByText(/passo 2 de 5/i)).toBeInTheDocument();
      });
    });
  });

  // v38: Smart prefill tests
  describe('smart prefill', () => {
    let mockFetch: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should fetch prefill data on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          prefill_source: 'utm_campaign',
          confidence: 'high',
          fields: { template_id: 'blog-post' },
          context: { has_utm: true, has_referrer: false, has_segment: false },
        }),
      });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/onboarding/prefill',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: expect.stringContaining('user-123'),
          })
        );
      });
    });

    it('should auto-select template from prefill without explicit input', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          prefill_source: 'utm_campaign',
          confidence: 'high',
          fields: { template_id: 'landing-page' },
          context: { has_utm: true, has_referrer: false, has_segment: false },
        }),
      });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Navigate to template selection step
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/nome do workspace/i);
      fireEvent.change(input, { target: { value: 'Meu Workspace' } });
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        expect(screen.getByText(/escolha um template/i)).toBeInTheDocument();
      });

      // Check that prefill indicator is shown
      await waitFor(() => {
        expect(screen.getByTestId('prefill-indicator')).toBeInTheDocument();
      });
    });

    it('should not overwrite explicit template selection with prefill', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          prefill_source: 'utm_campaign',
          confidence: 'high',
          fields: { template_id: 'landing-page' },
          context: { has_utm: true, has_referrer: false, has_segment: false },
        }),
      });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Navigate to template selection step
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/nome do workspace/i);
      fireEvent.change(input, { target: { value: 'Meu Workspace' } });
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        expect(screen.getByText(/escolha um template/i)).toBeInTheDocument();
      });

      // User explicitly selects a different template
      const emailTemplate = screen.getByTestId('template-email');
      fireEvent.click(emailTemplate);

      // The explicit selection should win
      await waitFor(() => {
        expect(emailTemplate).toHaveClass('border-blue-500');
      });
    });

    it('should show campaign context message for high confidence prefill', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          prefill_source: 'utm_campaign',
          confidence: 'high',
          fields: { template_id: 'blog-post' },
          context: { has_utm: true, has_referrer: false, has_segment: false },
        }),
      });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Navigate to template selection step
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/nome do workspace/i);
      fireEvent.change(input, { target: { value: 'Meu Workspace' } });
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        expect(screen.getByText(/escolha um template/i)).toBeInTheDocument();
      });

      // Check for the campaign context message
      await waitFor(() => {
        expect(screen.getByText(/detectamos que você veio de uma campanha/i)).toBeInTheDocument();
      });
    });

    it('should gracefully handle prefill fetch failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Failed to fetch prefill data:',
          expect.any(Error)
        );
      });

      // Wizard should still work normally
      expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();

      consoleSpy.mockRestore();
    });
  });

  // v38: Fast lane tests
  describe('fast lane', () => {
    let mockFetch: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should fetch fast lane data on mount', async () => {
      // Mock prefill first, then fast-lane
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            is_fast_lane: true,
            skipped_steps: ['customization'],
            remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'completion'],
            estimated_time_saved_minutes: 4.0,
            justification: 'Low risk user',
            risk_level: 'low',
          }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/onboarding/fast-lane',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: expect.stringContaining('user-123'),
          })
        );
      });
    });

    it('should display fast lane badge for eligible users', async () => {
      // Mock prefill first, then fast-lane
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            is_fast_lane: true,
            skipped_steps: ['customization'],
            remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'completion'],
            estimated_time_saved_minutes: 4.0,
            justification: 'Low risk user',
          }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('fast-lane-badge')).toBeInTheDocument();
      });

      expect(screen.getByText(/fast lane ativado/i)).toBeInTheDocument();
      expect(screen.getByText(/economize até 4 minutos/i)).toBeInTheDocument();
    });

    it('should not show fast lane badge for standard path users', async () => {
      // Mock prefill first, then fast-lane, then recommendation
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            is_fast_lane: false,
            skipped_steps: [],
            remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'customization', 'completion'],
            estimated_time_saved_minutes: 0,
            reason: 'High risk user',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            recommended_path: 'standard',
            confidence: 0.45,
            reasons: ['High risk user'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Wait for any effects to complete
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });

      // Fast lane badge should not be present
      expect(screen.queryByTestId('fast-lane-badge')).not.toBeInTheDocument();
    });

    it('should gracefully handle fast lane fetch failure', async () => {
      // Mock prefill success, then fast-lane failure
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockRejectedValueOnce(new Error('Network error'));
      
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Failed to fetch fast lane data:',
          expect.any(Error)
        );
      });

      // Wizard should still work normally
      expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();

      consoleSpy.mockRestore();
    });
  });

  // v39: Fast lane CTA tests
  describe('fast lane CTA', () => {
    let mockFetch: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should show CTA when fast lane recommendation is available', async () => {
      // Mock prefill, fast-lane, and recommendation
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            is_fast_lane: false,
            skipped_steps: [],
            remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'customization', 'completion'],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            recommended_path: 'fast_lane',
            confidence: 0.85,
            reasons: ['Perfil de baixo risco', 'Dados de contexto disponíveis'],
            skipped_steps: ['customization'],
            estimated_time_saved_minutes: 4.5,
          }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('fast-lane-cta')).toBeInTheDocument();
      });

      expect(screen.getByText(/caminho recomendado disponível/i)).toBeInTheDocument();
      // Text is split across elements, check separately
      expect(screen.getByText(/economiza/i)).toBeInTheDocument();
      expect(screen.getByText(/4\.5/)).toBeInTheDocument();
      expect(screen.getByText(/minutos/)).toBeInTheDocument();
      expect(screen.getByTestId('fast-lane-accept')).toBeInTheDocument();
      expect(screen.getByTestId('fast-lane-reject')).toBeInTheDocument();
    });

    it('should call trackFastLaneAccepted when accepting fast lane', async () => {
      const { trackFastLaneAccepted } = await import('./ttfvTelemetry');
      
      // Mock prefill, fast-lane, and recommendation
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            is_fast_lane: false,
            skipped_steps: [],
            remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'customization', 'completion'],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            recommended_path: 'fast_lane',
            confidence: 0.85,
            reasons: ['Perfil de baixo risco'],
            skipped_steps: ['customization'],
            estimated_time_saved_minutes: 4.5,
          }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('fast-lane-cta')).toBeInTheDocument();
      });

      const acceptButton = screen.getByTestId('fast-lane-accept');
      fireEvent.click(acceptButton);

      await waitFor(() => {
        expect(trackFastLaneAccepted).toHaveBeenCalledWith(
          'user-123',
          0.85,
          4.5,
          ['customization']
        );
      });
    });

    it('should call trackFastLaneRejected when rejecting fast lane', async () => {
      const { trackFastLaneRejected } = await import('./ttfvTelemetry');
      
      // Mock prefill, fast-lane, and recommendation
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            is_fast_lane: false,
            skipped_steps: [],
            remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'customization', 'completion'],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            recommended_path: 'fast_lane',
            confidence: 0.85,
            reasons: ['Perfil de baixo risco', 'Dados de contexto disponíveis'],
            skipped_steps: ['customization'],
            estimated_time_saved_minutes: 4.5,
          }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('fast-lane-cta')).toBeInTheDocument();
      });

      const rejectButton = screen.getByTestId('fast-lane-reject');
      fireEvent.click(rejectButton);

      await waitFor(() => {
        expect(trackFastLaneRejected).toHaveBeenCalledWith(
          'user-123',
          0.85,
          ['Perfil de baixo risco', 'Dados de contexto disponíveis']
        );
      });
    });

    it('should apply skip steps when accepting fast lane', async () => {
      // Mock prefill, fast-lane, and recommendation
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'default',
            confidence: 'low',
            fields: {},
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            is_fast_lane: false,
            skipped_steps: [],
            remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'customization', 'completion'],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            recommended_path: 'fast_lane',
            confidence: 0.85,
            reasons: ['Perfil de baixo risco'],
            skipped_steps: ['customization'],
            estimated_time_saved_minutes: 4.5,
          }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('fast-lane-cta')).toBeInTheDocument();
      });

      // Accept fast lane
      fireEvent.click(screen.getByTestId('fast-lane-accept'));

      // Wait for CTA to disappear and fast lane badge to appear
      await waitFor(() => {
        expect(screen.queryByTestId('fast-lane-cta')).not.toBeInTheDocument();
      });

      // Fast lane badge should now be visible
      await waitFor(() => {
        expect(screen.getByTestId('fast-lane-badge')).toBeInTheDocument();
      });

      expect(screen.getByText(/fast lane ativado/i)).toBeInTheDocument();
    });
  });
});
