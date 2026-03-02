import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ContextualTour } from './ContextualTour';

describe('ContextualTour', () => {
  const mockOnComplete = vi.fn();
  const mockOnSkip = vi.fn();

  const tourSteps = [
    {
      id: 'welcome',
      title: 'Bem-vindo',
      content: 'Bem-vindo ao VM Studio',
      target: '#welcome-target',
    },
    {
      id: 'workspace',
      title: 'Workspace',
      content: 'Configure seu workspace aqui',
      target: '#workspace-target',
    },
    {
      id: 'templates',
      title: 'Templates',
      content: 'Escolha um template para começar',
      target: '#templates-target',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    const localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    };
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
    // Mock document.querySelector
    document.querySelector = vi.fn((selector) => {
      const el = document.createElement('div');
      el.id = selector.replace('#', '');
      return el;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering', () => {
    it('should render first tour step', () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      expect(screen.getByText('Bem-vindo')).toBeInTheDocument();
      expect(screen.getByText('Bem-vindo ao VM Studio')).toBeInTheDocument();
    });

    it('should show progress indicator', () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      expect(screen.getByText(/passo 1 de 3/i)).toBeInTheDocument();
    });

    it('should not render when isOpen is false', () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={false}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      expect(screen.queryByText('Bem-vindo')).not.toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should advance to next step', async () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      const nextBtn = screen.getByRole('button', { name: /próximo/i });
      fireEvent.click(nextBtn);

      await waitFor(() => {
        expect(screen.getByText('Workspace')).toBeInTheDocument();
      });
    });

    it('should show previous step when clicking back', async () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Go to step 2
      fireEvent.click(screen.getByRole('button', { name: /próximo/i }));
      await waitFor(() => {
        expect(screen.getByText('Workspace')).toBeInTheDocument();
      });

      // Go back to step 1
      fireEvent.click(screen.getByRole('button', { name: /anterior/i }));
      await waitFor(() => {
        expect(screen.getByText('Bem-vindo')).toBeInTheDocument();
      });
    });

    it('should disable back button on first step', () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      const backBtn = screen.getByRole('button', { name: /anterior/i });
      expect(backBtn).toBeDisabled();
    });

    it('should show finish button on last step', async () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Navigate to last step
      fireEvent.click(screen.getByRole('button', { name: /próximo/i }));
      await waitFor(() => {});
      fireEvent.click(screen.getByRole('button', { name: /próximo/i }));
      await waitFor(() => {});

      expect(screen.getByRole('button', { name: /finalizar/i })).toBeInTheDocument();
    });
  });

  describe('completion', () => {
    it('should call onComplete when finishing tour', async () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      // Navigate to last step
      fireEvent.click(screen.getByRole('button', { name: /próximo/i }));
      await waitFor(() => {});
      fireEvent.click(screen.getByRole('button', { name: /próximo/i }));
      await waitFor(() => {});

      // Click finish
      fireEvent.click(screen.getByRole('button', { name: /finalizar/i }));

      expect(mockOnComplete).toHaveBeenCalled();
    });

    it('should call onSkip when clicking skip', () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /pular tour/i }));

      expect(mockOnSkip).toHaveBeenCalled();
    });
  });

  describe('resume state', () => {
    it('should start from resumed step when provided', () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
          resumeStepId="templates"
        />
      );

      expect(screen.getByText('Templates')).toBeInTheDocument();
      expect(screen.getByText(/passo 3 de 3/i)).toBeInTheDocument();
    });

    it('should persist current step on unmount', async () => {
      const { unmount } = render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
          tourId="test-tour"
        />
      );

      // Go to step 2
      fireEvent.click(screen.getByRole('button', { name: /próximo/i }));
      await waitFor(() => {
        expect(screen.getByText('Workspace')).toBeInTheDocument();
      });

      unmount();

      // localStorage should have been called with the current step
      expect(localStorage.setItem).toHaveBeenCalledWith(
        'vm_tour_test-tour_progress',
        expect.stringContaining('workspace')
      );
    });
  });

  describe('progress tracking', () => {
    it('should update progress bar on step change', async () => {
      render(
        <ContextualTour
          steps={tourSteps}
          isOpen={true}
          onComplete={mockOnComplete}
          onSkip={mockOnSkip}
        />
      );

      expect(screen.getByText(/passo 1 de 3/i)).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /próximo/i }));
      await waitFor(() => {
        expect(screen.getByText(/passo 2 de 3/i)).toBeInTheDocument();
      });
    });
  });
});
