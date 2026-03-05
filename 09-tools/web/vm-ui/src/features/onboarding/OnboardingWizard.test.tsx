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
  trackOnboardingProgressSaved: vi.fn(),
  trackOnboardingResumePresented: vi.fn(),
  trackOnboardingResumeAccepted: vi.fn(),
  trackOnboardingResumeRejected: vi.fn(),
  trackOnboardingResumeFailed: vi.fn(),
  setActiveExperiment: vi.fn(),
  clearActiveExperiment: vi.fn(),
}));

// Mock funnel
// v42 Variant A: Template First - reordered steps for better TTFV
vi.mock('./funnel', () => ({
  saveFunnelState: vi.fn(),
  loadFunnelState: vi.fn(() => null),
  clearFunnelState: vi.fn(),
  getNextStep: vi.fn((step) => {
    const order = [
      'welcome',
      'template_selection',  // Moved before workspace_setup
      'workspace_setup',
      'customization',
      'completion',
    ];
    const idx = order.indexOf(step);
    return idx >= 0 && idx < order.length - 1 ? order[idx + 1] : null;
  }),
}));

// v44: Mock useExperiment hook
const mockUseExperimentResults: Map<string, { variantId: string; config: Record<string, unknown>; isInExperiment: boolean; isExposed: boolean }> = new Map();

const mockUseExperiment = vi.fn((options: { experimentId: string; variants: unknown[]; userId: string }) => {
  // Return stored result for this experiment or default control
  const stored = mockUseExperimentResults.get(options.experimentId);
  if (stored) {
    return stored;
  }
  // Default: control group (backward compatible)
  return {
    variantId: 'control',
    config: {},
    isInExperiment: false,
    isExposed: false,
  };
});

vi.mock('../../hooks/useExperiment', () => ({
  useExperiment: (...args: unknown[]) => mockUseExperiment(...args),
}));

describe('OnboardingWizard', () => {
  const mockOnComplete = vi.fn();
  const mockOnSkip = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseExperimentResults.clear();
    // Mock sessionStorage
    const storage: Record<string, string> = {};
    Object.defineProperty(window, 'sessionStorage', {
      value: {
        getItem: (key: string) => storage[key] || null,
        setItem: (key: string, value: string) => { storage[key] = value; },
        removeItem: (key: string) => { delete storage[key]; },
      },
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockUseExperimentResults.clear();
  });

  // ==========================================
  // v43: CONTRACT TESTS - STEP ORDER v42
  // ==========================================
  // Estes testes são contratos que falham se STEP_ORDER for alterado
  // sem atualização explícita. Template First é a ordem oficial v42.
  describe('CONTRATO: Ordem oficial de steps v42 (Template First)', () => {
    it('deve seguir ordem oficial de steps v42: welcome -> template_selection -> workspace_setup -> customization -> completion', async () => {
      // Este teste é um CONTRATO - falha se a ordem for alterada inadvertidamente
      // v42 Variant A: Template First - template_selection vem antes de workspace_setup
      const mockFetch = vi.fn();
      global.fetch = mockFetch;

      // Mock APIs: progress, prefill, fast-lane, recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      // Step 1: WELCOME
      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/passo 1 de 5/i)).toBeInTheDocument();

      // Avança para step 2
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      
      // CONTRATO: Step 2 DEVE ser TEMPLATE_SELECTION (não workspace_setup)
      // Esta é a ordem v42 Template First
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/passo 2 de 5/i)).toBeInTheDocument();

      // Seleciona template e avança
      const templateBtn = screen.getByText(/blog post/i);
      fireEvent.click(templateBtn);
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      // CONTRATO: Step 3 DEVE ser WORKSPACE_SETUP
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/passo 3 de 5/i)).toBeInTheDocument();

      // Preenche workspace e avança
      const input = screen.getByPlaceholderText(/nome do workspace/i);
      fireEvent.change(input, { target: { value: 'Meu Workspace' } });
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      // CONTRATO: Step 4 DEVE ser CUSTOMIZATION
      await waitFor(() => {
        expect(screen.getByText(/personalização/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/passo 4 de 5/i)).toBeInTheDocument();

      // Avança para completion
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      // CONTRATO: Step 5 DEVE ser COMPLETION
      await waitFor(() => {
        expect(screen.getByText(/concluída/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/passo 5 de 5/i)).toBeInTheDocument();

      vi.restoreAllMocks();
    });

    it('deve permitir navegação back respeitando a ordem v42', async () => {
      const mockFetch = vi.fn();
      global.fetch = mockFetch;

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      // Avança: welcome -> template_selection
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Avança: template_selection -> workspace_setup
      const templateBtn = screen.getByText(/blog post/i);
      fireEvent.click(templateBtn);
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      // Volta: workspace_setup -> template_selection
      fireEvent.click(screen.getByRole('button', { name: /voltar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Volta: template_selection -> welcome
      fireEvent.click(screen.getByRole('button', { name: /voltar/i }));
      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });

      vi.restoreAllMocks();
    });

    it('deve permitir skip em qualquer step', async () => {
      const mockFetch = vi.fn();
      global.fetch = mockFetch;

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /pular/i })).toBeInTheDocument();
      });

      // Skip deve chamar onSkip
      fireEvent.click(screen.getByRole('button', { name: /pular/i }));
      expect(mockOnSkip).toHaveBeenCalled();

      vi.restoreAllMocks();
    });
  });

  describe('rendering', () => {
    let mockFetch: ReturnType<typeof vi.fn>;
    
    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
      
      // Default mocks for basic rendering tests (order: progress, prefill, fast-lane, recommend)
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        });
    });
    
    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should render wizard with initial welcome step', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/vm studio/i)).toBeInTheDocument();
    });

    it('should show progress indicator', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
      });
      expect(screen.getByText(/passo 1 de 5/i)).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    let mockFetch: ReturnType<typeof vi.fn>;
    
    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
      
      // Default mocks for navigation tests (order: progress, prefill, fast-lane, recommend)
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        });
    });
    
    afterEach(() => {
      vi.restoreAllMocks();
    });

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
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
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

      // Go to step 2 (template selection - new order)
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Go back
      fireEvent.click(screen.getByRole('button', { name: /voltar/i }));
      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });
    });
  });

  describe('step validation', () => {
    let mockFetch: ReturnType<typeof vi.fn>;
    
    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
      
      // Default mocks for step validation tests (order: progress, prefill, fast-lane, recommend)
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        });
    });
    
    afterEach(() => {
      vi.restoreAllMocks();
    });

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

      // Go to template step first (new order)
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });
      
      // Select template and continue to workspace step
      const templateBtn = screen.getByText(/blog post/i);
      fireEvent.click(templateBtn);
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
    let mockFetch: ReturnType<typeof vi.fn>;
    
    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
      
      // Default mocks for completion tests (order: progress, prefill, fast-lane, recommend, auto-save)
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
    });
    
    afterEach(() => {
      vi.restoreAllMocks();
    });

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
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Step 2: Template -> select template and continue
      const templateBtn = screen.getByText(/blog post/i);
      fireEvent.click(templateBtn);
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      // Step 3: Workspace -> fill name and continue
      const input = screen.getByPlaceholderText(/nome do workspace/i);
      fireEvent.change(input, { target: { value: 'Meu Workspace' } });
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
    let mockFetch: ReturnType<typeof vi.fn>;
    
    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
      
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        });
    });
    
    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should call onSkip when clicking skip button', async () => {
      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /pular/i })).toBeInTheDocument();
      });

      const skipBtn = screen.getByRole('button', { name: /pular/i });
      fireEvent.click(skipBtn);

      expect(mockOnSkip).toHaveBeenCalled();
    });
  });

  describe('progress tracking', () => {
    it('should update progress bar as steps advance', async () => {
      // Need to mock auto-save call
      const mockFetch = vi.fn();
      global.fetch = mockFetch;
      
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/passo 1 de 5/i)).toBeInTheDocument();
      });

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
    
    // Helper to setup default mocks including progress check
    const setupDefaultMocks = () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        });
    };

    it('should fetch prefill data on mount', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'utm_campaign',
            confidence: 'high',
            fields: { template_id: 'blog-post' },
            context: { has_utm: true, has_referrer: false, has_segment: false },
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'utm_campaign',
            confidence: 'high',
            fields: { template_id: 'landing-page' },
            context: { has_utm: true, has_referrer: false, has_segment: false },
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /continuar/i })).toBeInTheDocument();
      });

      // Navigate to template selection step (step 2 in new order)
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Check that prefill indicator is shown in template step (v42: Template First)
      await waitFor(() => {
        expect(screen.getByTestId('prefill-indicator')).toBeInTheDocument();
      });
      
      // Continue to workspace
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });
    });

    it('should not overwrite explicit template selection with prefill', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'utm_campaign',
            confidence: 'high',
            fields: { template_id: 'landing-page' },
            context: { has_utm: true, has_referrer: false, has_segment: false },
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /continuar/i })).toBeInTheDocument();
      });

      // Navigate to template selection step (step 2 in new order)
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // User explicitly selects a template
      const emailTemplate = screen.getByTestId('template-email');
      fireEvent.click(emailTemplate);

      // The explicit selection should win
      await waitFor(() => {
        expect(emailTemplate).toHaveClass('border-blue-500');
      });

      // Continue to workspace setup
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });
    });

    it('should show campaign context message for high confidence prefill', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            user_id: 'user-123',
            prefill_source: 'utm_campaign',
            confidence: 'high',
            fields: { template_id: 'blog-post' },
            context: { has_utm: true, has_referrer: false, has_segment: false },
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /continuar/i })).toBeInTheDocument();
      });

      // Navigate to template selection step (step 2 in new order)
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Check for the campaign context message on template step
      await waitFor(() => {
        expect(screen.getByText(/detectamos que você veio de uma campanha/i)).toBeInTheDocument();
      });

      // Continue to workspace
      const templateBtn = screen.getByTestId('template-blog-post');
      fireEvent.click(templateBtn);
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
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
    
    // Helper to setup default mocks including progress check
    const setupDefaultMocks = () => {
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        });
    };

    it('should fetch fast lane data on mount', async () => {
      // Mock progress check, prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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
      // Mock progress check, prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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

      await waitFor(() => {
        expect(screen.getByTestId('fast-lane-badge')).toBeInTheDocument();
      });

      expect(screen.getByText(/fast lane ativado/i)).toBeInTheDocument();
      expect(screen.getByText(/economize até 4 minutos/i)).toBeInTheDocument();
    });

    it('should not show fast lane badge for standard path users', async () => {
      // Mock progress check, prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
        expect(mockFetch).toHaveBeenCalledTimes(4);
      });

      // Fast lane badge should not be present
      expect(screen.queryByTestId('fast-lane-badge')).not.toBeInTheDocument();
    });

    it('should gracefully handle fast lane fetch failure', async () => {
      // Mock progress check success, prefill success, then fast-lane failure
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
      // Mock progress check, prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
      
      // Mock progress check, prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
      
      // Mock progress check, prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
      // Mock progress check, prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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

  // v40: Save/Resume tests
  describe('save/resume functionality', () => {
    let mockFetch: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should show resume prompt when there is saved progress', async () => {
      const { trackOnboardingResumePresented } = await import('./ttfvTelemetry');
      
      // Mock progress check (with saved progress), prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            has_progress: true,
            current_step: 'workspace_setup',
            updated_at: '2026-03-04T10:30:00Z',
            step_data: { workspaceName: 'Meu Workspace' },
            completed_steps: ['welcome'],
          }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      await waitFor(() => {
        expect(screen.getByTestId('resume-prompt')).toBeInTheDocument();
      });

      expect(screen.getByText(/retomar de onde parou/i)).toBeInTheDocument();
      expect(screen.getByText(/workspace setup/i)).toBeInTheDocument();
      expect(trackOnboardingResumePresented).toHaveBeenCalledWith('user-123', 'workspace_setup');
    });

    it('should call API and hydrate state when accepting resume', async () => {
      const { trackOnboardingResumeAccepted } = await import('./ttfvTelemetry');
      
      // Mock progress check (with saved progress), prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            has_progress: true,
            current_step: 'template_selection',
            updated_at: '2026-03-04T10:30:00Z',
            step_data: { workspaceName: 'Meu Workspace Salvo', selectedTemplate: 'blog-post' },
            completed_steps: ['welcome', 'workspace_setup'],
          }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      await waitFor(() => {
        expect(screen.getByTestId('resume-prompt')).toBeInTheDocument();
      });

      // Accept resume
      const acceptButton = screen.getByTestId('resume-accept');
      fireEvent.click(acceptButton);

      await waitFor(() => {
        expect(trackOnboardingResumeAccepted).toHaveBeenCalledWith('user-123', 'template_selection');
      });

      // Should navigate to the saved step
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });
    });

    it('should call API to clear progress when rejecting resume', async () => {
      const { trackOnboardingResumeRejected } = await import('./ttfvTelemetry');
      
      // Mock progress check (with saved progress), prefill, fast-lane, recommend, and delete
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            has_progress: true,
            current_step: 'workspace_setup',
            updated_at: '2026-03-04T10:30:00Z',
            step_data: { workspaceName: 'Meu Workspace' },
            completed_steps: ['welcome'],
          }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('resume-prompt')).toBeInTheDocument();
      });

      // Reject resume (start fresh)
      const rejectButton = screen.getByTestId('resume-reject');
      fireEvent.click(rejectButton);

      await waitFor(() => {
        expect(trackOnboardingResumeRejected).toHaveBeenCalledWith('user-123', 'user_chose_fresh_start');
      });

      // Should call DELETE API
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/onboarding/progress/user-123',
          expect.objectContaining({ method: 'DELETE' })
        );
      });

      // Prompt should disappear
      await waitFor(() => {
        expect(screen.queryByTestId('resume-prompt')).not.toBeInTheDocument();
      });
    });

    it('should trigger auto-save when completing a step', async () => {
      const { trackOnboardingProgressSaved } = await import('./ttfvTelemetry');
      
      // Mock progress check (no saved progress), prefill, fast-lane, recommend, and auto-save
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Wait for initial load and all API calls to complete
      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });
      
      // Wait for loading to complete (progress check, prefill, fast-lane, recommend)
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(4);
      });
      
      // Wait for Continue button to be enabled
      await waitFor(() => {
        const continueBtn = screen.getByRole('button', { name: /continuar/i });
        expect(continueBtn).not.toBeDisabled();
      });

      // Go to next step (template selection in new order)
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Select a template and continue to workspace
      const templateBtn = screen.getByText(/blog post/i);
      fireEvent.click(templateBtn);
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      // Auto-save should be called when completing workspace step
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/onboarding/progress/user-123',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: expect.stringContaining('auto_save'),
          })
        );
      });

      await waitFor(() => {
        expect(trackOnboardingProgressSaved).toHaveBeenCalledWith('user-123', 'workspace_setup', 'auto_save');
      });
    });

    it('should hydrate workspace name when resuming', async () => {
      // Mock progress check (with saved progress), prefill, fast-lane, and recommend
      // With new order (Template First): welcome -> template_selection -> workspace_setup
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            has_progress: true,
            current_step: 'workspace_setup',
            updated_at: '2026-03-04T10:30:00Z',
            step_data: { workspaceName: 'Workspace Hidratado', selectedTemplate: 'blog-post' },
            completed_steps: ['welcome', 'template_selection'],
          }),
        })
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
            remaining_steps: ['welcome', 'template_selection', 'workspace_setup', 'customization', 'completion'],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      await waitFor(() => {
        expect(screen.getByTestId('resume-prompt')).toBeInTheDocument();
      });

      // Accept resume
      fireEvent.click(screen.getByTestId('resume-accept'));

      // Should navigate to workspace setup with hydrated workspace name (new order)
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/nome do workspace/i) as HTMLInputElement;
      expect(input.value).toBe('Workspace Hidratado');

      // Go back to template selection
      fireEvent.click(screen.getByRole('button', { name: /voltar/i }));
      
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Template should also be preserved
      const selectedTemplate = screen.getByTestId('template-blog-post');
      expect(selectedTemplate).toHaveClass('border-blue-500');
    });

    it('should not show resume prompt when there is no saved progress', async () => {
      // Mock progress check (no progress), prefill, fast-lane, and recommend
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        });

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Wait for all effects to complete
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(4);
      });

      // Resume prompt should not be shown
      expect(screen.queryByTestId('resume-prompt')).not.toBeInTheDocument();
    });

    it('should handle progress check failure gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Create a new mock for this test
      const testMockFetch = vi.fn();
      global.fetch = testMockFetch;
      
      // Mock progress check failure, prefill, fast-lane, and recommend
      testMockFetch
        .mockRejectedValueOnce(new Error('Network error'))
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          'Failed to check saved progress:',
          expect.any(Error)
        );
      });

      // Wizard should still work normally
      expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();

      consoleSpy.mockRestore();
    });
  });

  // ==========================================
  // v43: FALLBACK TESTS - API Resilience
  // ==========================================
  // Testes garantem que o wizard continua funcionando mesmo
  // quando APIs falham (graceful degradation)
  describe('FALLBACK: API progress falha - wizard continua funcionando', () => {
    it('deve continuar funcionando quando API de progresso retorna 500', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const { trackOnboardingStarted } = await import('./telemetry');
      
      const testMockFetch = vi.fn();
      global.fetch = testMockFetch;
      
      // API progress falha com 500, mas outras APIs funcionam
      testMockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ error: 'Internal Server Error' }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      // Wizard deve continuar funcionando
      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });

      // Telemetry de início deve ser emitido
      expect(trackOnboardingStarted).toHaveBeenCalledWith('user-123');

      // Usuário deve conseguir avançar
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });

    it('deve continuar funcionando quando API de progresso retorna timeout', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      const testMockFetch = vi.fn();
      global.fetch = testMockFetch;
      
      // API progress timeout
      testMockFetch
        .mockRejectedValueOnce(new Error('Timeout'))
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
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

      // Wizard deve continuar funcionando mesmo com timeout
      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });

      // Não deve mostrar prompt de resume
      expect(screen.queryByTestId('resume-prompt')).not.toBeInTheDocument();

      consoleSpy.mockRestore();
    });

    it('deve continuar funcionando quando auto-save falha silenciosamente', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const { trackOnboardingProgressSaved } = await import('./ttfvTelemetry');
      
      const testMockFetch = vi.fn();
      global.fetch = testMockFetch;
      
      // Setup mocks: progress, prefill, fast-lane, recommend, auto-save (falha)
      testMockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ has_progress: false }),
        })
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
            recommended_path: 'standard',
            confidence: 0.5,
            reasons: ['Standard path'],
            skipped_steps: [],
            estimated_time_saved_minutes: 0,
          }),
        })
        .mockRejectedValueOnce(new Error('Auto-save failed')); // auto-save falha

      render(
        <OnboardingWizard
          userId="user-123"
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
      });

      // Avança para template selection
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));
      await waitFor(() => {
        expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
      });

      // Seleciona template
      const templateBtn = screen.getByText(/blog post/i);
      fireEvent.click(templateBtn);

      // Avança - isso dispara auto-save que vai falhar
      fireEvent.click(screen.getByRole('button', { name: /continuar/i }));

      // Mesmo com falha no auto-save, deve continuar para workspace_setup
      await waitFor(() => {
        expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });
  });

  // ==========================================
  // v44: EXPERIMENT TESTS
  // ==========================================
  describe('v44: Experiment System', () => {
    let mockFetch: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockFetch = vi.fn();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    describe('CTA Copy Experiment', () => {
      it('should apply variant button text when in experiment', async () => {
        // Configure mock for CTA experiment
        mockUseExperimentResults.set('onboarding_cta_v44', {
          variantId: 'variant_start_now',
          config: { buttonText: 'Começar Agora' },
          isInExperiment: true,
          isExposed: true,
        });
        mockUseExperimentResults.set('onboarding_resume_timing_v44', {
          variantId: 'control',
          config: { delayMs: 0 },
          isInExperiment: false,
          isExposed: false,
        });

        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ has_progress: false }),
          })
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
              recommended_path: 'standard',
              confidence: 0.5,
              reasons: ['Standard path'],
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

        await waitFor(() => {
          expect(screen.getByTestId('continue-button')).toBeInTheDocument();
        });

        // Should show variant text
        expect(screen.getByTestId('continue-button')).toHaveTextContent('Começar Agora');
      });

      it('should fallback to default text when in control group', async () => {
        // Configure mock for control group (default behavior)
        mockUseExperimentResults.set('onboarding_cta_v44', {
          variantId: 'control',
          config: {},
          isInExperiment: false,
          isExposed: false,
        });
        mockUseExperimentResults.set('onboarding_resume_timing_v44', {
          variantId: 'control',
          config: { delayMs: 0 },
          isInExperiment: false,
          isExposed: false,
        });

        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ has_progress: false }),
          })
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
              recommended_path: 'standard',
              confidence: 0.5,
              reasons: ['Standard path'],
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

        await waitFor(() => {
          expect(screen.getByTestId('continue-button')).toBeInTheDocument();
        });

        // Should show default text
        expect(screen.getByTestId('continue-button')).toHaveTextContent('Continuar');
      });

      it('should apply different variant texts correctly', async () => {
        const variants = [
          { id: 'variant_start_now', text: 'Começar Agora' },
          { id: 'variant_continue_journey', text: 'Continuar Jornada' },
          { id: 'variant_next_step', text: 'Próximo Passo' },
        ];

        for (const variant of variants) {
          vi.clearAllMocks();
          mockUseExperimentResults.clear();
          
          // Configure mock for this variant
          mockUseExperimentResults.set('onboarding_cta_v44', {
            variantId: variant.id,
            config: { buttonText: variant.text },
            isInExperiment: true,
            isExposed: true,
          });
          mockUseExperimentResults.set('onboarding_resume_timing_v44', {
            variantId: 'control',
            config: { delayMs: 0 },
            isInExperiment: false,
            isExposed: false,
          });

          mockFetch
            .mockResolvedValueOnce({
              ok: true,
              json: () => Promise.resolve({ has_progress: false }),
            })
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
                recommended_path: 'standard',
                confidence: 0.5,
                reasons: ['Standard path'],
                skipped_steps: [],
                estimated_time_saved_minutes: 0,
              }),
            });

          const { unmount } = render(
            <OnboardingWizard
              userId="user-123"
              onComplete={mockOnComplete}
              onSkip={mockOnSkip}
            />
          );

          await waitFor(() => {
            expect(screen.getByTestId('continue-button')).toBeInTheDocument();
          });

          expect(screen.getByTestId('continue-button')).toHaveTextContent(variant.text);
          
          unmount();
        }
      });
    });

    describe('Resume Timing Experiment', () => {
      it('should call useExperiment with correct resume timing config', async () => {
        // Configure mocks for experiments
        mockUseExperimentResults.set('onboarding_cta_v44', {
          variantId: 'control',
          config: {},
          isInExperiment: false,
          isExposed: false,
        });
        mockUseExperimentResults.set('onboarding_resume_timing_v44', {
          variantId: 'variant_delayed_2s',
          config: { delayMs: 2000 },
          isInExperiment: true,
          isExposed: true,
        });

        // Mock all necessary API calls (for prefill, fast-lane, etc.)
        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: vi.fn().mockResolvedValue({ has_progress: false }),
          })
          .mockResolvedValueOnce({
            ok: true,
            json: vi.fn().mockResolvedValue({
              user_id: 'user-123',
              prefill_source: 'default',
              confidence: 'low',
              fields: {},
            }),
          })
          .mockResolvedValueOnce({
            ok: true,
            json: vi.fn().mockResolvedValue({
              user_id: 'user-123',
              is_fast_lane: false,
              skipped_steps: [],
              remaining_steps: ['welcome', 'workspace_setup', 'template_selection', 'customization', 'completion'],
              estimated_time_saved_minutes: 0,
            }),
          })
          .mockResolvedValueOnce({
            ok: true,
            json: vi.fn().mockResolvedValue({
              recommended_path: 'standard',
              confidence: 0.5,
              reasons: ['Standard path'],
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

        await waitFor(() => {
          expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
        });

        // Verify useExperiment was called with resume timing experiment config
        const calls = mockUseExperiment.mock.calls;
        const resumeTimingCall = calls.find((call: [{ experimentId: string }]) => 
          call[0].experimentId === 'onboarding_resume_timing_v44'
        );
        
        expect(resumeTimingCall).toBeDefined();
        expect(resumeTimingCall[0]).toMatchObject({
          experimentId: 'onboarding_resume_timing_v44',
          userId: 'user-123',
        });
        expect(resumeTimingCall[0].variants).toEqual(
          expect.arrayContaining([
            expect.objectContaining({ id: 'control', config: { delayMs: 0 } }),
            expect.objectContaining({ id: 'variant_delayed_2s', config: { delayMs: 2000 } }),
            expect.objectContaining({ id: 'variant_delayed_5s', config: { delayMs: 5000 } }),
          ])
        );
      });

      it('should show resume prompt immediately in control group', async () => {
        const { trackOnboardingResumePresented } = await import('./ttfvTelemetry');

        // Configure mocks for control group (no delay)
        mockUseExperimentResults.set('onboarding_cta_v44', {
          variantId: 'control',
          config: {},
          isInExperiment: false,
          isExposed: false,
        });
        mockUseExperimentResults.set('onboarding_resume_timing_v44', {
          variantId: 'control',
          config: { delayMs: 0 },
          isInExperiment: false,
          isExposed: false,
        });

        // Mock all necessary API calls
        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
              has_progress: true,
              current_step: 'workspace_setup',
              updated_at: '2026-03-04T10:30:00Z',
              step_data: { workspaceName: 'Meu Workspace' },
              completed_steps: ['welcome'],
            }),
          })
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
              recommended_path: 'standard',
              confidence: 0.5,
              reasons: ['Standard path'],
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

        // Should show prompt immediately (no delay)
        await waitFor(() => {
          expect(screen.getByTestId('resume-prompt')).toBeInTheDocument();
        });

        expect(trackOnboardingResumePresented).toHaveBeenCalledWith('user-123', 'workspace_setup');
      }, 10000);
    });

    describe('Experiment Integration', () => {
      it('should maintain v42 flow compatibility with experiments', async () => {
        // Configure mocks for experiments
        mockUseExperimentResults.set('onboarding_cta_v44', {
          variantId: 'variant_start_now',
          config: { buttonText: 'Começar Agora' },
          isInExperiment: true,
          isExposed: true,
        });
        mockUseExperimentResults.set('onboarding_resume_timing_v44', {
          variantId: 'control',
          config: { delayMs: 0 },
          isInExperiment: false,
          isExposed: false,
        });

        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ has_progress: false }),
          })
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
              recommended_path: 'standard',
              confidence: 0.5,
              reasons: ['Standard path'],
              skipped_steps: [],
              estimated_time_saved_minutes: 0,
            }),
          })
          .mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

        render(
          <OnboardingWizard
            userId="user-123"
            onComplete={mockOnComplete}
            onSkip={mockOnSkip}
          />
        );

        // Step 1: WELCOME
        await waitFor(() => {
          expect(screen.getByText(/bem-vindo/i)).toBeInTheDocument();
        });

        // Button should have variant text
        expect(screen.getByTestId('continue-button')).toHaveTextContent('Começar Agora');

        // Navigate through v42 flow
        fireEvent.click(screen.getByTestId('continue-button'));
        
        // CONTRATO: Step 2 DEVE ser TEMPLATE_SELECTION
        await waitFor(() => {
          expect(screen.getByText(/Escolha um Template/i)).toBeInTheDocument();
        });

        // Complete flow
        const templateBtn = screen.getByText(/blog post/i);
        fireEvent.click(templateBtn);
        fireEvent.click(screen.getByTestId('continue-button'));

        await waitFor(() => {
          expect(screen.getByText(/configurar workspace/i)).toBeInTheDocument();
        });
      }, 10000);
    });
  });
});
