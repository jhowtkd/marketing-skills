import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { OnboardingExperimentPanel } from './OnboardingExperimentPanel';

// Mock the hook
const mockRunEvaluation = vi.fn();
const mockStartExperiment = vi.fn();
const mockPauseExperiment = vi.fn();
const mockPromoteExperiment = vi.fn();
const mockRollbackExperiment = vi.fn();
const mockRefresh = vi.fn();

const defaultMockReturn = {
  status: {
    brand_id: 'test-brand',
    version: 'v32',
    metrics: {
      total_experiments: 4,
      running_experiments: 2,
      assignments_today: 245,
      promotions_auto: 3,
      promotions_approved: 1,
      promotions_blocked: 0,
      rollbacks: 0,
    },
    active_experiments: [
      {
        experiment_id: 'exp-001',
        name: 'Test Experiment 1',
        status: 'running',
        risk_level: 'low',
      },
    ],
  },
  experiments: [
    {
      experiment_id: 'exp-001',
      name: 'Nudge Timing Test',
      description: 'Test different nudge delays',
      hypothesis: 'Shorter delay increases activation',
      primary_metric: 'template_to_first_run_conversion',
      status: 'running',
      risk_level: 'low',
      min_sample_size: 100,
      min_confidence: 0.95,
      max_lift_threshold: 0.10,
      variants: [
        { variant_id: 'control', name: 'Control', config: {}, traffic_allocation: 50 },
        { variant_id: 'treatment', name: 'Treatment', config: {}, traffic_allocation: 50 },
      ],
      created_at: '2026-03-01T00:00:00Z',
      started_at: '2026-03-01T00:00:00Z',
    },
    {
      experiment_id: 'exp-002',
      name: 'Template Order Test',
      description: 'Test template ordering',
      hypothesis: 'Popular first increases conversion',
      primary_metric: 'onboarding_completion_rate',
      status: 'draft',
      risk_level: 'medium',
      min_sample_size: 200,
      min_confidence: 0.95,
      max_lift_threshold: 0.10,
      variants: [
        { variant_id: 'A', name: 'Alphabetical', config: {}, traffic_allocation: 50 },
        { variant_id: 'B', name: 'Popular First', config: {}, traffic_allocation: 50 },
      ],
      created_at: '2026-03-02T00:00:00Z',
    },
  ],
  evaluations: [],
  loading: false,
  error: null,
  runEvaluation: mockRunEvaluation,
  startExperiment: mockStartExperiment,
  pauseExperiment: mockPauseExperiment,
  promoteExperiment: mockPromoteExperiment,
  rollbackExperiment: mockRollbackExperiment,
  refresh: mockRefresh,
};

vi.mock('../hooks/useOnboardingExperiments', () => ({
  useOnboardingExperiments: vi.fn(() => defaultMockReturn),
}));

import { useOnboardingExperiments } from '../hooks/useOnboardingExperiments';

describe('OnboardingExperimentPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useOnboardingExperiments).mockReturnValue(defaultMockReturn);
  });

  afterEach(() => {
    vi.mocked(useOnboardingExperiments).mockReturnValue(defaultMockReturn);
  });

  it('renders panel header with correct governance version', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('Governança v32')).toBeInTheDocument();
    expect(screen.getByText('Onboarding Experiments')).toBeInTheDocument();
  });

  it('displays metrics summary correctly', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('Total Experiments')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('2 running')).toBeInTheDocument();
    
    expect(screen.getByText('Assignments Today')).toBeInTheDocument();
    expect(screen.getByText('245')).toBeInTheDocument();
    
    expect(screen.getByText('Auto-Applied')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('displays running experiments with correct status and risk badges', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('Running Experiments (1)')).toBeInTheDocument();
    expect(screen.getByText('Nudge Timing Test')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('Low Risk')).toBeInTheDocument();
  });

  it('displays draft experiments with start button', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('Draft Experiments (1)')).toBeInTheDocument();
    expect(screen.getByText('Template Order Test')).toBeInTheDocument();
    expect(screen.getByText('Draft')).toBeInTheDocument();
    expect(screen.getByText('Medium Risk')).toBeInTheDocument();
    
    const startButton = screen.getByText('Start');
    expect(startButton).toBeInTheDocument();
  });

  it('calls runEvaluation when Run Weekly Evaluation button is clicked', async () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const runButton = screen.getByText('Run Weekly Evaluation');
    fireEvent.click(runButton);
    
    await waitFor(() => {
      expect(mockRunEvaluation).toHaveBeenCalledTimes(1);
    });
  });

  it('calls startExperiment when Start button is clicked on draft', async () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const startButton = screen.getByText('Start');
    fireEvent.click(startButton);
    
    await waitFor(() => {
      expect(mockStartExperiment).toHaveBeenCalledWith('exp-002');
    });
  });

  it('calls pauseExperiment when Pause button is clicked on running experiment', async () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const pauseButton = screen.getByText('Pause');
    fireEvent.click(pauseButton);
    
    await waitFor(() => {
      expect(mockPauseExperiment).toHaveBeenCalledWith('exp-001', 'Manual pause');
    });
  });

  it('shows auto-promote button for low risk experiments', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const autoPromoteButton = screen.getByText('Auto-Promote');
    expect(autoPromoteButton).toBeInTheDocument();
  });

  it('calls promoteExperiment with autoApply=true when Auto-Promote is clicked', async () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const autoPromoteButton = screen.getByText('Auto-Promote');
    fireEvent.click(autoPromoteButton);
    
    await waitFor(() => {
      expect(mockPromoteExperiment).toHaveBeenCalledWith('exp-001', 'treatment', true);
    });
  });

  it('calls rollbackExperiment when Rollback button is clicked', async () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const rollbackButton = screen.getByText('Rollback');
    fireEvent.click(rollbackButton);
    
    await waitFor(() => {
      expect(mockRollbackExperiment).toHaveBeenCalledWith('exp-001', 'Manual rollback');
    });
  });

  it('calls refresh when Refresh button is clicked', async () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);
    
    await waitFor(() => {
      expect(mockRefresh).toHaveBeenCalledTimes(1);
    });
  });

  it('displays variant allocations correctly', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('Control (50%)')).toBeInTheDocument();
    expect(screen.getByText('Treatment (50%)')).toBeInTheDocument();
  });

  it('displays empty state when no experiments', () => {
    vi.mocked(useOnboardingExperiments).mockReturnValue({
      ...defaultMockReturn,
      status: {
        ...defaultMockReturn.status,
        metrics: {
          ...defaultMockReturn.status.metrics,
          total_experiments: 0,
          running_experiments: 0,
        },
      },
      experiments: [],
    });
    
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('No experiments yet.')).toBeInTheDocument();
    expect(screen.getByText('Create experiments to start A/B testing onboarding variations.')).toBeInTheDocument();
  });
});

describe('OnboardingExperimentPanel with evaluations', () => {
  const mockWithEvaluations = {
    ...defaultMockReturn,
    status: {
      ...defaultMockReturn.status,
      metrics: {
        ...defaultMockReturn.status.metrics,
        total_experiments: 2,
        running_experiments: 1,
      },
    },
    experiments: [],
    evaluations: [
      {
        experiment_id: 'exp-001',
        variant_id: 'treatment',
        sample_size: 500,
        control_conversion_rate: 0.10,
        treatment_conversion_rate: 0.12,
        absolute_lift: 0.02,
        relative_lift: 0.20,
        confidence: 0.96,
        is_significant: true,
        reason: 'Significant positive lift',
        decision: 'auto_apply',
        requires_approval: false,
      },
      {
        experiment_id: 'exp-002',
        variant_id: 'treatment',
        sample_size: 300,
        control_conversion_rate: 0.15,
        treatment_conversion_rate: 0.16,
        absolute_lift: 0.01,
        relative_lift: 0.07,
        confidence: 0.82,
        is_significant: false,
        reason: 'Not enough confidence',
        decision: 'continue',
        requires_approval: false,
      },
    ],
  };

  beforeEach(() => {
    vi.mocked(useOnboardingExperiments).mockReturnValue(mockWithEvaluations);
  });

  it('displays evaluations with correct decision badges', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('Latest Evaluations')).toBeInTheDocument();
    expect(screen.getByText('Auto-Apply')).toBeInTheDocument();
    expect(screen.getByText('Continue')).toBeInTheDocument();
    expect(screen.getByText('✓ Significant')).toBeInTheDocument();
  });

  it('displays evaluation metrics correctly', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText(/Sample: 500/)).toBeInTheDocument();
    expect(screen.getByText(/Lift: 20.0%/)).toBeInTheDocument();
    expect(screen.getByText(/Confidence: 96%/)).toBeInTheDocument();
  });
});

describe('OnboardingExperimentPanel error state', () => {
  const mockWithError = {
    ...defaultMockReturn,
    status: null,
    experiments: [],
    error: 'Failed to connect to API',
  };

  beforeEach(() => {
    vi.mocked(useOnboardingExperiments).mockReturnValue(mockWithError);
  });

  it('displays error state with retry button', () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    expect(screen.getByText('Error Loading Experiments')).toBeInTheDocument();
    expect(screen.getByText('Failed to connect to API')).toBeInTheDocument();
    
    const retryButton = screen.getByText('Retry');
    expect(retryButton).toBeInTheDocument();
  });

  it('calls refresh when retry button is clicked', async () => {
    render(<OnboardingExperimentPanel brandId="test-brand" />);
    
    const retryButton = screen.getByText('Retry');
    fireEvent.click(retryButton);
    
    await waitFor(() => {
      expect(mockRefresh).toHaveBeenCalledTimes(1);
    });
  });
});
