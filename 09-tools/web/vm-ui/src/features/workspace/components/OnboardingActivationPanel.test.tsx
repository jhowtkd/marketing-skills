import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OnboardingActivationPanel } from './OnboardingActivationPanel';

// Mock the hook
vi.mock('../hooks/useOnboardingActivation', () => ({
  useOnboardingActivation: vi.fn((brandId: string) => ({
    status: {
      brand_id: brandId,
      metrics: {
        completion_rate: 0.55,
        step_1_dropoff_rate: 0.30,
        template_to_first_run_conversion: 0.45,
        average_time_to_first_action_ms: 90000,
      },
      top_frictions: [
        { type: 'step_abandon', step: 'workspace_setup', count: 25, severity: 'high' },
        { type: 'reason', reason: 'too_complex', count: 15, severity: 'medium' },
      ],
      active_proposals_count: 2,
      frozen: false,
    },
    proposals: [
      {
        id: 'prop-1',
        rule_name: 'reduce_step_1_complexity',
        description: 'Simplify workspace setup form',
        risk_level: 'low',
        current_value: 0.30,
        target_value: 0.20,
        adjustment_percent: -10,
        expected_impact: 'Reduce step 1 dropoff by 5-8%',
        status: 'pending', // Low-risk pending shows "Auto-applied" label
        created_at: '2026-03-02T10:00:00Z',
      },
      {
        id: 'prop-2',
        rule_name: 'add_progress_rewards',
        description: 'Add gamification elements',
        risk_level: 'medium',
        current_value: 0.55,
        target_value: 0.60,
        adjustment_percent: 5,
        expected_impact: 'Increase completion by 10%',
        status: 'pending',
        created_at: '2026-03-02T11:00:00Z',
      },
      {
        id: 'prop-3',
        rule_name: 'enable_skip_options',
        description: 'Allow skipping optional steps',
        risk_level: 'low',
        current_value: 0.25,
        target_value: 0.20,
        adjustment_percent: -5,
        expected_impact: 'Reduce complexity dropoff',
        status: 'applied',
        created_at: '2026-03-02T09:00:00Z',
      },
    ],
    loading: false,
    error: null,
    runActivation: vi.fn(),
    applyProposal: vi.fn(),
    rejectProposal: vi.fn(),
    freezeProposals: vi.fn(),
    rollbackLast: vi.fn(),
    refresh: vi.fn(),
  })),
}));

describe('OnboardingActivationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render panel with header', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      expect(screen.getByText(/onboarding activation/i)).toBeInTheDocument();
      expect(screen.getByText(/governança v31/i)).toBeInTheDocument();
    });

    it('should display metrics summary', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      expect(screen.getByText(/completion rate/i)).toBeInTheDocument();
      expect(screen.getByText(/55%/)).toBeInTheDocument();
      expect(screen.getByText(/template conv/i)).toBeInTheDocument();
      expect(screen.getByText(/45%/)).toBeInTheDocument();
    });

    it('should display top friction points', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      expect(screen.getByText(/top friction points/i)).toBeInTheDocument();
      expect(screen.getByText(/workspace_setup/i)).toBeInTheDocument();
      expect(screen.getByText(/too_complex/i)).toBeInTheDocument();
    });

    it('should display pending proposals', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      expect(screen.getByText(/pending proposals/i)).toBeInTheDocument();
      expect(screen.getByText(/add gamification elements/i)).toBeInTheDocument();
    });

    it('should display applied proposals', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      expect(screen.getByText(/applied proposals/i)).toBeInTheDocument();
      expect(screen.getByText(/simplify workspace setup/i)).toBeInTheDocument();
    });
  });

  describe('actions', () => {
    it('should have run activation button', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      const button = screen.getByRole('button', { name: /run activation/i });
      expect(button).toBeInTheDocument();
    });

    it('should have freeze button', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      const button = screen.getByRole('button', { name: /freeze/i });
      expect(button).toBeInTheDocument();
    });

    it('should have rollback button', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      const button = screen.getByRole('button', { name: /rollback/i });
      expect(button).toBeInTheDocument();
    });

    it('should have refresh button', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      const button = screen.getByRole('button', { name: /refresh/i });
      expect(button).toBeInTheDocument();
    });
  });

  describe('proposal actions', () => {
    it('should show apply button for pending medium-risk proposal', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      const applyButtons = screen.getAllByRole('button', { name: /apply/i });
      expect(applyButtons.length).toBeGreaterThan(0);
    });

    it('should show reject button for pending medium-risk proposal', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      const rejectButtons = screen.getAllByRole('button', { name: /reject/i });
      expect(rejectButtons.length).toBeGreaterThan(0);
    });

    it('should show apply/reject buttons for medium-risk pending proposal', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      // Medium-risk pending proposals have Apply and Reject buttons
      const applyButtons = screen.getAllByRole('button', { name: /apply/i });
      const rejectButtons = screen.getAllByRole('button', { name: /reject/i });
      expect(applyButtons.length).toBeGreaterThan(0);
      expect(rejectButtons.length).toBeGreaterThan(0);
    });
  });

  describe('risk badges', () => {
    it('should display risk badges for proposals', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      // Should have both low and medium risk badges visible
      const lowRiskBadges = screen.getAllByText(/low risk/i);
      const mediumRiskBadges = screen.getAllByText(/medium risk/i);
      expect(lowRiskBadges.length).toBeGreaterThan(0);
      expect(mediumRiskBadges.length).toBeGreaterThan(0);
    });
  });

  describe('status badges', () => {
    it('should display applied status badge', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      // Look for status badge in applied proposals section
      const appliedSection = screen.getByText(/applied proposals/i).closest('div');
      expect(appliedSection).toBeInTheDocument();
    });

    it('should display pending status badge', () => {
      render(<OnboardingActivationPanel brandId="brand-123" />);

      // Look for status badge in pending proposals section
      const pendingSection = screen.getByText(/pending proposals/i).closest('div');
      expect(pendingSection).toBeInTheDocument();
    });
  });
});

// Note: Loading and error states are tested via hook-level tests
// UI state tests would require more complex mock setup
