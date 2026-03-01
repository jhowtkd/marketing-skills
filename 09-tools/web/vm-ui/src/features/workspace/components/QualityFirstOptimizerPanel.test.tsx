import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QualityFirstOptimizerPanel } from './QualityFirstOptimizerPanel';

// Mock the hook
const mockUseQualityOptimizer = vi.fn();
vi.mock('../hooks/useQualityOptimizer', () => ({
  useQualityOptimizer: () => mockUseQualityOptimizer(),
}));

describe('QualityFirstOptimizerPanel', () => {
  const defaultMockReturn = {
    status: {
      version: 'v25',
      total_proposals: 2,
      proposals_by_state: {
        pending: 1,
        applied: 1,
        rejected: 0,
        frozen: 0,
        rolled_back: 0,
      },
    },
    proposals: [
      {
        proposal_id: 'prop-001',
        run_id: 'run-001',
        state: 'pending',
        recommended_params: { temperature: 0.8, max_tokens: 2200 },
        estimated_v1_improvement: 8.5,
        estimated_cost_delta_pct: 8.2,
        estimated_mttc_delta_pct: 7.5,
        estimated_incident_rate: 0.04,
        feasibility_check_passed: true,
        quality_score: 75.5,
        created_at: '2026-03-01T10:00:00Z',
      },
      {
        proposal_id: 'prop-002',
        run_id: 'run-001',
        state: 'applied',
        recommended_params: { temperature: 0.7, max_tokens: 2000 },
        estimated_v1_improvement: 5.0,
        estimated_cost_delta_pct: 5.0,
        estimated_mttc_delta_pct: 4.0,
        estimated_incident_rate: 0.03,
        feasibility_check_passed: true,
        quality_score: 70.0,
        created_at: '2026-03-01T09:00:00Z',
        applied_at: '2026-03-01T09:30:00Z',
      },
    ],
    selectedProposal: null,
    snapshot: null,
    loading: false,
    error: null,
    processing: false,
    fetchStatus: vi.fn(),
    fetchProposals: vi.fn(),
    selectProposal: vi.fn(),
    fetchSnapshot: vi.fn(),
    applyProposal: vi.fn().mockResolvedValue(true),
    rejectProposal: vi.fn().mockResolvedValue(true),
    freezeProposal: vi.fn().mockResolvedValue(true),
    rollbackProposal: vi.fn().mockResolvedValue(true),
    runOptimizer: vi.fn(),
    canApply: vi.fn((p) => p.state === 'pending' && p.feasibility_check_passed),
    canReject: vi.fn((p) => p.state === 'pending'),
    canFreeze: vi.fn((p) => p.state === 'pending'),
    canRollback: vi.fn((p) => p.state === 'applied'),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQualityOptimizer.mockReturnValue({ ...defaultMockReturn });
  });

  describe('Rendering', () => {
    it('should render panel with title', () => {
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByText('Quality-First Optimizer v25')).toBeInTheDocument();
    });

    it('should show loading state', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        loading: true,
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('quality-optimizer-loading')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should show error state', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        error: 'Failed to fetch data',
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('quality-optimizer-error')).toBeInTheDocument();
      expect(screen.getByText('Error: Failed to fetch data')).toBeInTheDocument();
    });

    it('should render optimizer status', () => {
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('optimizer-status')).toBeInTheDocument();
      expect(screen.getByText('Total Proposals: 2')).toBeInTheDocument();
    });

    it('should render proposals list', () => {
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('proposals-list')).toBeInTheDocument();
      expect(screen.getByText(/Proposals for Run: run-001/)).toBeInTheDocument();
    });

    it('should show message when no proposals', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        proposals: [],
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('no-proposals')).toBeInTheDocument();
      expect(screen.getByText('No proposals found for this run.')).toBeInTheDocument();
    });
  });

  describe('Proposal States', () => {
    it('should display pending state correctly', () => {
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const pendingState = screen.getByTestId('proposal-state-prop-001');
      expect(pendingState).toHaveTextContent('pending');
      expect(pendingState).toHaveClass('bg-yellow-100');
    });

    it('should display applied state correctly', () => {
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const appliedState = screen.getByTestId('proposal-state-prop-002');
      expect(appliedState).toHaveTextContent('applied');
      expect(appliedState).toHaveClass('bg-green-100');
    });

    it('should display feasibility badge', () => {
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const feasibility = screen.getByTestId('proposal-feasibility-prop-001');
      expect(feasibility).toHaveTextContent('Feasible');
      expect(feasibility).toHaveClass('bg-green-100');
    });
  });

  describe('Proposal Selection', () => {
    it('should select proposal on click', async () => {
      const mockSelectProposal = vi.fn();
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectProposal: mockSelectProposal,
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const proposalItem = screen.getByTestId('proposal-item-prop-001');
      fireEvent.click(proposalItem);
      
      await waitFor(() => {
        expect(mockSelectProposal).toHaveBeenCalledWith(
          expect.objectContaining({ proposal_id: 'prop-001' })
        );
      });
    });

    it('should show proposal details when selected', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('proposal-details')).toBeInTheDocument();
      expect(screen.getByText('Proposal Details')).toBeInTheDocument();
    });

    it('should display recommended params', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const params = screen.getByTestId('recommended-params');
      expect(params).toBeInTheDocument();
      expect(params).toHaveTextContent('temperature: 0.8');
      expect(params).toHaveTextContent('max_tokens: 2200');
    });
  });

  describe('Actions - Apply', () => {
    it('should enable apply button for feasible pending proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        canApply: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const applyBtn = screen.getByTestId('apply-button');
      expect(applyBtn).not.toBeDisabled();
      expect(applyBtn).toHaveTextContent('Apply');
    });

    it('should disable apply button for infeasible proposal', () => {
      const infeasibleProposal = {
        ...defaultMockReturn.proposals[0],
        feasibility_check_passed: false,
      };
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: infeasibleProposal,
        canApply: vi.fn(() => false),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const applyBtn = screen.getByTestId('apply-button');
      expect(applyBtn).toBeDisabled();
    });

    it('should disable apply button for non-pending proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[1], // applied
        canApply: vi.fn(() => false),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const applyBtn = screen.getByTestId('apply-button');
      expect(applyBtn).toBeDisabled();
    });

    it('should call applyProposal when apply button clicked', async () => {
      const mockApply = vi.fn().mockResolvedValue(true);
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        applyProposal: mockApply,
        canApply: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const applyBtn = screen.getByTestId('apply-button');
      fireEvent.click(applyBtn);
      
      await waitFor(() => {
        expect(mockApply).toHaveBeenCalledWith('prop-001');
      });
    });
  });

  describe('Actions - Reject', () => {
    it('should enable reject button for pending proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        canReject: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const rejectBtn = screen.getByTestId('reject-button');
      expect(rejectBtn).not.toBeDisabled();
      expect(rejectBtn).toHaveTextContent('Reject');
    });

    it('should disable reject button for applied proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[1],
        canReject: vi.fn(() => false),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const rejectBtn = screen.getByTestId('reject-button');
      expect(rejectBtn).toBeDisabled();
    });

    it('should call rejectProposal when reject button clicked', async () => {
      const mockReject = vi.fn().mockResolvedValue(true);
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        rejectProposal: mockReject,
        canReject: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const rejectBtn = screen.getByTestId('reject-button');
      fireEvent.click(rejectBtn);
      
      await waitFor(() => {
        expect(mockReject).toHaveBeenCalledWith('prop-001');
      });
    });
  });

  describe('Actions - Freeze', () => {
    it('should enable freeze button for pending proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        canFreeze: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const freezeBtn = screen.getByTestId('freeze-button');
      expect(freezeBtn).not.toBeDisabled();
      expect(freezeBtn).toHaveTextContent('Freeze');
    });

    it('should disable freeze button for applied proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[1],
        canFreeze: vi.fn(() => false),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const freezeBtn = screen.getByTestId('freeze-button');
      expect(freezeBtn).toBeDisabled();
    });

    it('should call freezeProposal when freeze button clicked', async () => {
      const mockFreeze = vi.fn().mockResolvedValue(true);
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        freezeProposal: mockFreeze,
        canFreeze: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const freezeBtn = screen.getByTestId('freeze-button');
      fireEvent.click(freezeBtn);
      
      await waitFor(() => {
        expect(mockFreeze).toHaveBeenCalledWith('prop-001');
      });
    });
  });

  describe('Actions - Rollback', () => {
    it('should enable rollback button for applied proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[1],
        canRollback: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const rollbackBtn = screen.getByTestId('rollback-button');
      expect(rollbackBtn).not.toBeDisabled();
      expect(rollbackBtn).toHaveTextContent('Rollback');
    });

    it('should disable rollback button for pending proposal', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        canRollback: vi.fn(() => false),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const rollbackBtn = screen.getByTestId('rollback-button');
      expect(rollbackBtn).toBeDisabled();
    });

    it('should call rollbackProposal when rollback button clicked', async () => {
      const mockRollback = vi.fn().mockResolvedValue(true);
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[1],
        rollbackProposal: mockRollback,
        canRollback: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      const rollbackBtn = screen.getByTestId('rollback-button');
      fireEvent.click(rollbackBtn);
      
      await waitFor(() => {
        expect(mockRollback).toHaveBeenCalledWith('prop-002');
      });
    });
  });

  describe('Snapshot Display', () => {
    it('should show view snapshot button for applied proposals', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[1],
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('view-snapshot-button')).toBeInTheDocument();
    });

    it('should not show view snapshot button for pending proposals', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.queryByTestId('view-snapshot-button')).not.toBeInTheDocument();
    });

    it('should display snapshot when available', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[1],
        snapshot: {
          proposal_id: 'prop-002',
          previous_params: { temperature: 0.6 },
          applied_params: { temperature: 0.7 },
          applied_at: '2026-03-01T09:30:00Z',
        },
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('snapshot-display')).toBeInTheDocument();
      expect(screen.getByText('Snapshot (for Rollback)')).toBeInTheDocument();
    });
  });

  describe('Impact Metrics', () => {
    it('should display expected impact metrics', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByText('Expected Impact')).toBeInTheDocument();
      expect(screen.getByText(/V1 Improvement/)).toBeInTheDocument();
      expect(screen.getByText('+8.5 pts')).toBeInTheDocument();
    });

    it('should show constraints info', () => {
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByText('Constraints (v25)')).toBeInTheDocument();
      expect(screen.getByText(/Max Cost Increase: \+10%/)).toBeInTheDocument();
    });
  });

  describe('Processing State', () => {
    it('should disable all buttons when processing', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        processing: true,
        canApply: vi.fn(() => true),
        canReject: vi.fn(() => true),
        canFreeze: vi.fn(() => true),
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByTestId('apply-button')).toBeDisabled();
      expect(screen.getByTestId('reject-button')).toBeDisabled();
      expect(screen.getByTestId('freeze-button')).toBeDisabled();
    });

    it('should show processing text on buttons', () => {
      mockUseQualityOptimizer.mockReturnValue({
        ...defaultMockReturn,
        selectedProposal: defaultMockReturn.proposals[0],
        processing: true,
      });
      
      render(<QualityFirstOptimizerPanel runId="run-001" />);
      
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });
  });
});
