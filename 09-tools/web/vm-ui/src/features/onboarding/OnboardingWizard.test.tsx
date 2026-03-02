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
});
