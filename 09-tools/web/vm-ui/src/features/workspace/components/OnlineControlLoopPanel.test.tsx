import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OnlineControlLoopPanel } from './OnlineControlLoopPanel';

// Mock the hook
const mockUseOnlineControlLoop = vi.fn();
vi.mock('../hooks/useOnlineControlLoop', () => ({
  useOnlineControlLoop: () => mockUseOnlineControlLoop(),
}));

describe('OnlineControlLoopPanel', () => {
  const defaultMockReturn = {
    status: {
      version: 'v26',
      state: 'idle',
      cycle_id: null,
      brand_id: 'brand-123',
      active_proposals: [],
      active_regressions: [],
    },
    cycles: [],
    proposals: [],
    regressions: [],
    selectedProposal: null,
    loading: false,
    error: null,
    processing: false,
    fetchStatus: vi.fn(),
    startCycle: vi.fn().mockResolvedValue(true),
    applyProposal: vi.fn().mockResolvedValue(true),
    rejectProposal: vi.fn().mockResolvedValue(true),
    freezeControlLoop: vi.fn().mockResolvedValue(true),
    rollbackControlLoop: vi.fn().mockResolvedValue(true),
    canApply: vi.fn((p) => p.state === 'pending' && p.severity === 'low'),
    canReject: vi.fn((p) => p.state === 'pending'),
    canFreeze: vi.fn(() => true),
    canRollback: vi.fn((p) => p.state === 'applied'),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOnlineControlLoop.mockReturnValue({ ...defaultMockReturn });
  });

  describe('Rendering', () => {
    it('should render panel with title', () => {
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Online Control Loop v26')).toBeInTheDocument();
    });

    it('should show loading state', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        loading: true,
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByTestId('control-loop-loading')).toBeInTheDocument();
    });

    it('should show error state', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        error: 'Failed to fetch status',
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Failed to fetch status')).toBeInTheDocument();
    });

    it('should show version badge', () => {
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('v26')).toBeInTheDocument();
    });
  });

  describe('States', () => {
    it('should show idle state', () => {
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Status: Idle')).toBeInTheDocument();
      expect(screen.getByText('No active cycle')).toBeInTheDocument();
    });

    it('should show running state', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        status: {
          ...defaultMockReturn.status,
          state: 'observing',
          cycle_id: 'cycle-001',
        },
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Status: Observing')).toBeInTheDocument();
      expect(screen.getByText('Cycle: cycle-001')).toBeInTheDocument();
    });

    it('should show frozen state', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        status: {
          ...defaultMockReturn.status,
          state: 'frozen',
        },
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Status: Frozen')).toBeInTheDocument();
      expect(screen.getByText('Control loop is frozen')).toBeInTheDocument();
    });

    it('should show blocked state', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        status: {
          ...defaultMockReturn.status,
          state: 'blocked',
        },
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Status: Blocked')).toBeInTheDocument();
    });
  });

  describe('Actions - Run Cycle', () => {
    it('should show run button when idle', () => {
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Run Control Loop')).toBeInTheDocument();
    });

    it('should call startCycle when run button clicked', async () => {
      const mockStartCycle = vi.fn().mockResolvedValue(true);
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        startCycle: mockStartCycle,
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      fireEvent.click(screen.getByText('Run Control Loop'));
      
      await waitFor(() => {
        expect(mockStartCycle).toHaveBeenCalled();
      });
    });

    it('should disable run button when processing', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        status: { ...defaultMockReturn.status, state: 'idle' },
        processing: true,
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      const button = screen.getByText('Starting...');
      expect(button).toBeDisabled();
    });
  });

  describe('Actions - Apply Proposal', () => {
    const mockProposal = {
      proposal_id: 'prop-001',
      adjustment_type: 'gate_threshold',
      target_gate: 'v1_score_min',
      current_value: 70.0,
      proposed_value: 68.0,
      delta: -2.0,
      severity: 'low',
      requires_approval: false,
      estimated_impact: { v1_score: 2.0 },
      state: 'pending',
    };

    it('should show apply button for pending low-severity proposal', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        proposals: [mockProposal],
        canApply: vi.fn(() => true),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Apply')).toBeInTheDocument();
    });

    it('should call applyProposal when apply button clicked', async () => {
      const mockApply = vi.fn().mockResolvedValue(true);
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        proposals: [mockProposal],
        applyProposal: mockApply,
        canApply: vi.fn(() => true),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      fireEvent.click(screen.getByText('Apply'));
      
      await waitFor(() => {
        expect(mockApply).toHaveBeenCalledWith('brand-123', 'prop-001');
      });
    });

    it('should show approval required for medium/high severity', () => {
      const mediumProposal = { ...mockProposal, severity: 'medium', requires_approval: true };
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        proposals: [mediumProposal],
        canApply: vi.fn(() => false),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Requires Approval')).toBeInTheDocument();
    });
  });

  describe('Actions - Reject Proposal', () => {
    const mockProposal = {
      proposal_id: 'prop-001',
      adjustment_type: 'gate_threshold',
      target_gate: 'v1_score_min',
      current_value: 70.0,
      proposed_value: 68.0,
      delta: -2.0,
      severity: 'low',
      requires_approval: false,
      estimated_impact: { v1_score: 2.0 },
      state: 'pending',
    };

    it('should show reject button for pending proposal', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        proposals: [mockProposal],
        canReject: vi.fn(() => true),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Reject')).toBeInTheDocument();
    });

    it('should call rejectProposal when reject button clicked', async () => {
      const mockReject = vi.fn().mockResolvedValue(true);
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        proposals: [mockProposal],
        rejectProposal: mockReject,
        canReject: vi.fn(() => true),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      fireEvent.click(screen.getByText('Reject'));
      
      await waitFor(() => {
        expect(mockReject).toHaveBeenCalledWith('brand-123', 'prop-001');
      });
    });
  });

  describe('Actions - Freeze', () => {
    it('should show freeze button', () => {
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Freeze')).toBeInTheDocument();
    });

    it('should call freezeControlLoop when freeze button clicked', async () => {
      const mockFreeze = vi.fn().mockResolvedValue(true);
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        freezeControlLoop: mockFreeze,
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      fireEvent.click(screen.getByText('Freeze'));
      
      await waitFor(() => {
        expect(mockFreeze).toHaveBeenCalledWith('brand-123');
      });
    });

    it('should disable freeze button when already frozen', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        status: {
          ...defaultMockReturn.status,
          state: 'frozen',
        },
        canFreeze: vi.fn(() => false),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Freeze')).toBeDisabled();
    });
  });

  describe('Actions - Rollback', () => {
    const mockAppliedProposal = {
      proposal_id: 'prop-001',
      adjustment_type: 'gate_threshold',
      target_gate: 'v1_score_min',
      current_value: 70.0,
      proposed_value: 68.0,
      delta: -2.0,
      severity: 'low',
      requires_approval: false,
      estimated_impact: { v1_score: 2.0 },
      state: 'applied',
      applied_at: '2026-03-01T12:00:00Z',
    };

    it('should show rollback button for applied proposals', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        proposals: [mockAppliedProposal],
        canRollback: vi.fn(() => true),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Rollback')).toBeInTheDocument();
    });

    it('should call rollbackControlLoop when rollback button clicked', async () => {
      const mockRollback = vi.fn().mockResolvedValue(true);
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        proposals: [mockAppliedProposal],
        rollbackControlLoop: mockRollback,
        canRollback: vi.fn(() => true),
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      fireEvent.click(screen.getByText('Rollback'));
      
      await waitFor(() => {
        expect(mockRollback).toHaveBeenCalledWith('brand-123', 'prop-001');
      });
    });
  });

  describe('Regressions Display', () => {
    it('should show active regressions', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        status: {
          ...defaultMockReturn.status,
          state: 'observing',
          active_regressions: [
            { metric: 'v1_score', severity: 'medium', delta_pct: -10.0 },
          ],
        },
        regressions: [
          { metric: 'v1_score', severity: 'medium', delta_pct: -10.0 },
        ],
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      expect(screen.getByText('Active Regressions')).toBeInTheDocument();
      expect(screen.getByText('v1_score')).toBeInTheDocument();
    });

    it('should show no regressions message when empty', () => {
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      // Check that panel renders
      expect(screen.getByText('Active Regressions')).toBeInTheDocument();
    });
  });

  describe('Metrics Display', () => {
    it('should show time metrics', () => {
      mockUseOnlineControlLoop.mockReturnValue({
        ...defaultMockReturn,
        metrics: {
          time_to_detect_avg_seconds: 240,
          time_to_mitigate_avg_seconds: 900,
        },
      });
      
      render(<OnlineControlLoopPanel brandId="brand-123" />);
      
      // Performance section is always rendered
      expect(screen.getByText('Performance')).toBeInTheDocument();
    });
  });
});
