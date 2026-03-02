/**
 * OutcomeRoiPanel Tests (v36)
 * 
 * Vitest tests for the Outcome ROI governance panel.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OutcomeRoiPanel } from './OutcomeRoiPanel';
import * as useOutcomeRoiModule from '../hooks/useOutcomeRoi';

// Mock the hook
vi.mock('../hooks/useOutcomeRoi');

describe('OutcomeRoiPanel', () => {
  const mockRefresh = vi.fn();
  const mockRunAttribution = vi.fn();
  const mockApplyProposal = vi.fn();
  const mockRejectProposal = vi.fn();
  const mockFreeze = vi.fn();
  const mockRollback = vi.fn();

  const defaultMockReturn = {
    status: null,
    proposals: [],
    metrics: null,
    loading: false,
    error: null,
    refresh: mockRefresh,
    runAttribution: mockRunAttribution,
    applyProposal: mockApplyProposal,
    rejectProposal: mockRejectProposal,
    freeze: mockFreeze,
    rollback: mockRollback,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue(defaultMockReturn);
  });

  it('renders loading state', () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      loading: true,
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    expect(screen.getByText(/Outcome Attribution & Hybrid ROI/i)).toBeInTheDocument();
  });

  it('renders metrics when available', () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      metrics: {
        outcomes_attributed: 156,
        proposals_generated: 24,
        proposals_auto_applied: 16,
        proposals_pending_approval: 4,
        proposals_approved: 3,
        proposals_rejected: 1,
        proposals_blocked: 0,
        hybrid_roi_index_avg: 0.245,
        payback_time_avg_days: 4.2,
        guardrail_violations: 3,
      },
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    expect(screen.getByText('156')).toBeInTheDocument(); // outcomes
    expect(screen.getByText('24')).toBeInTheDocument(); // proposals
    expect(screen.getByText('16')).toBeInTheDocument(); // auto-applied
    expect(screen.getByText('4')).toBeInTheDocument(); // pending
  });

  it('renders proposals list', () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      proposals: [
        {
          proposal_id: 'prop-001',
          brand_id: 'brand-001',
          touchpoint_type: 'onboarding_step',
          action: 'increase_priority',
          expected_impact: { completion_rate: 0.05 },
          hybrid_index: 0.25,
          risk_level: 'low',
          status: 'pending',
          score_explanation: 'Financial: 0.4, Operational: 0.3',
          created_at: '2026-03-01T10:00:00Z',
        },
        {
          proposal_id: 'prop-002',
          brand_id: 'brand-001',
          touchpoint_type: 'recovery_action',
          action: 'reduce_steps',
          expected_impact: { human_minutes: -10 },
          hybrid_index: 0.12,
          risk_level: 'medium',
          status: 'pending',
          score_explanation: 'Financial: 0.2, Operational: 0.2',
          created_at: '2026-03-01T11:00:00Z',
        },
      ],
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    expect(screen.getByText('increase_priority')).toBeInTheDocument();
    expect(screen.getByText('reduce_steps')).toBeInTheDocument();
    // Check for risk levels - use getAllByText since they appear in multiple places
    expect(screen.getAllByText('Baixo').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Médio').length).toBeGreaterThan(0);
  });

  it('calls runAttribution when execute button clicked', async () => {
    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    const button = screen.getByText('Executar Atribuição');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockRunAttribution).toHaveBeenCalled();
    });
  });

  it('calls applyProposal when apply button clicked', async () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      proposals: [
        {
          proposal_id: 'prop-001',
          brand_id: 'brand-001',
          touchpoint_type: 'onboarding_step',
          action: 'increase_priority',
          expected_impact: {},
          hybrid_index: 0.25,
          risk_level: 'low',
          status: 'pending',
          score_explanation: 'Test',
          created_at: '2026-03-01T10:00:00Z',
        },
      ],
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    const button = screen.getByText('Aplicar');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockApplyProposal).toHaveBeenCalledWith('prop-001');
    });
  });

  it('calls rejectProposal when reject button clicked', async () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      proposals: [
        {
          proposal_id: 'prop-001',
          brand_id: 'brand-001',
          touchpoint_type: 'onboarding_step',
          action: 'increase_priority',
          expected_impact: {},
          hybrid_index: 0.25,
          risk_level: 'low',
          status: 'pending',
          score_explanation: 'Test',
          created_at: '2026-03-01T10:00:00Z',
        },
      ],
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    // Get all Rejeitar buttons and click the first one (the proposal card button)
    const buttons = screen.getAllByText('Rejeitar');
    fireEvent.click(buttons[0]);
    
    // Should have been called
    await waitFor(() => {
      expect(mockRejectProposal).toHaveBeenCalled();
    });
  });

  it('shows frozen state', () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      status: {
        brand_id: 'brand-001',
        state: 'frozen',
        version: 'v36',
        frozen: true,
        metrics: defaultMockReturn.metrics!,
        attribution_summary: {
          total_outcomes: 10,
          total_touchpoints: 30,
          by_outcome_type: {},
          window_days: 30,
        },
        roi_summary: {
          total_proposals: 5,
          avg_hybrid_index: 0.2,
          by_risk_level: {},
        },
      },
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    expect(screen.getByText(/Operações congeladas/i)).toBeInTheDocument();
  });

  it('displays error message', () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      error: 'Failed to fetch data',
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    expect(screen.getByText('Failed to fetch data')).toBeInTheDocument();
  });

  it('renders empty state when no proposals', () => {
    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    expect(screen.getByText('Nenhuma proposal gerada')).toBeInTheDocument();
  });

  it('displays hybrid index values', () => {
    vi.mocked(useOutcomeRoiModule.useOutcomeRoi).mockReturnValue({
      ...defaultMockReturn,
      proposals: [
        {
          proposal_id: 'prop-001',
          brand_id: 'brand-001',
          touchpoint_type: 'onboarding_step',
          action: 'test_action',
          expected_impact: {},
          hybrid_index: 0.325,
          risk_level: 'low',
          status: 'pending',
          score_explanation: 'Test explanation',
          created_at: '2026-03-01T10:00:00Z',
        },
      ],
    });

    render(<OutcomeRoiPanel brandId="brand-001" />);
    
    expect(screen.getByText('0.325')).toBeInTheDocument();
  });
});
