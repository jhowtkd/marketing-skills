import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RecoveryOrchestrationPanel } from './RecoveryOrchestrationPanel';

// Mock the hook
vi.mock('../hooks/useRecoveryOrchestration', () => ({
  useRecoveryOrchestration: vi.fn(),
}));

import { useRecoveryOrchestration } from '../hooks/useRecoveryOrchestration';

const mockedUseRecoveryOrchestration = vi.mocked(useRecoveryOrchestration);

describe('RecoveryOrchestrationPanel', () => {
  const defaultProps = {
    brandId: 'brand-001',
  };

  const mockHandlers = {
    fetchStatus: vi.fn(),
    startRecovery: vi.fn(),
    approveRecovery: vi.fn(),
    rejectRecovery: vi.fn(),
    freezeRecovery: vi.fn(),
    rollbackRecovery: vi.fn(),
    retryRecovery: vi.fn(),
    getSeverityColor: vi.fn((severity: string) => `bg-${severity}-100`),
    getStatusColor: vi.fn((status: string) => `bg-${status}-100`),
    canApprove: vi.fn(() => true),
    canReject: vi.fn(() => true),
    canFreeze: vi.fn(() => true),
    canRollback: vi.fn(() => true),
    canRetry: vi.fn(() => true),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading state when loading is true', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: null,
        runs: [],
        events: [],
        loading: true,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('recovery-orchestration-loading')).toBeInTheDocument();
      expect(screen.getByText('Loading Recovery Orchestration...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error state when error exists', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: null,
        runs: [],
        events: [],
        loading: false,
        error: 'Failed to load recovery data',
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('recovery-orchestration-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to load recovery data')).toBeInTheDocument();
    });

    it('should call fetchStatus when retry button is clicked', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: null,
        runs: [],
        events: [],
        loading: false,
        error: 'Failed to load',
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      expect(mockHandlers.fetchStatus).toHaveBeenCalledWith('brand-001');
    });
  });

  describe('Main Panel State', () => {
    const mockStatus = {
      brand_id: 'brand-001',
      state: 'idle',
      version: 'v28',
      metrics: {
        total_runs: 15,
        successful_runs: 12,
        failed_runs: 2,
        auto_runs: 10,
        manual_runs: 5,
        pending_approvals: 1,
      },
      active_incidents: [],
      pending_approvals: [],
    };

    it('should render panel with correct data-testid', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('recovery-orchestration-panel')).toBeInTheDocument();
    });

    it('should display version badge', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByText('v28')).toBeInTheDocument();
    });

    it('should display state badge', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('recovery-state')).toHaveTextContent('idle');
    });
  });

  describe('Metrics Display', () => {
    const mockStatus = {
      brand_id: 'brand-001',
      state: 'idle',
      version: 'v28',
      metrics: {
        total_runs: 15,
        successful_runs: 12,
        failed_runs: 2,
        auto_runs: 10,
        manual_runs: 5,
        pending_approvals: 1,
      },
      active_incidents: [],
      pending_approvals: [],
    };

    it('should display total runs metric', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('metric-total-runs')).toHaveTextContent('15');
    });

    it('should display successful runs metric', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('metric-successful')).toHaveTextContent('12');
    });

    it('should display failed runs metric', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('metric-failed')).toHaveTextContent('2');
    });

    it('should display pending approvals metric', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('metric-pending-approvals')).toHaveTextContent('1');
    });

    it('should display auto runs metric', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('metric-auto-runs')).toHaveTextContent('10');
    });

    it('should display manual runs metric', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('metric-manual-runs')).toHaveTextContent('5');
    });
  });

  describe('Actions', () => {
    const mockStatus = {
      brand_id: 'brand-001',
      state: 'idle',
      version: 'v28',
      metrics: {
        total_runs: 15,
        successful_runs: 12,
        failed_runs: 2,
        auto_runs: 10,
        manual_runs: 5,
        pending_approvals: 0,
      },
      active_incidents: [],
      pending_approvals: [],
    };

    it('should call startRecovery when start button is clicked', async () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      const startButton = screen.getByTestId('start-recovery-button');
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(mockHandlers.startRecovery).toHaveBeenCalledWith(
          'brand-001',
          'handoff_timeout',
          'medium',
          'Manual recovery start'
        );
      });
    });

    it('should disable start button when processing', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatus,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: true,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('start-recovery-button')).toBeDisabled();
    });
  });

  describe('Pending Approvals', () => {
    const mockStatusWithApprovals = {
      brand_id: 'brand-001',
      state: 'awaiting_approval',
      version: 'v28',
      metrics: {
        total_runs: 15,
        successful_runs: 12,
        failed_runs: 2,
        auto_runs: 10,
        manual_runs: 5,
        pending_approvals: 2,
      },
      active_incidents: [],
      pending_approvals: [
        {
          request_id: 'approval-001',
          run_id: 'run-001',
          brand_id: 'brand-001',
          incident_type: 'handoff_timeout',
          severity: 'high',
          requested_at: '2026-03-02T10:00:00Z',
          status: 'pending',
        },
        {
          request_id: 'approval-002',
          run_id: 'run-002',
          brand_id: 'brand-001',
          incident_type: 'approval_sla_breach',
          severity: 'medium',
          requested_at: '2026-03-02T11:00:00Z',
          status: 'pending',
        },
      ],
    };

    it('should display approvals section when pending approvals exist', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatusWithApprovals,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('approvals-section')).toBeInTheDocument();
      expect(screen.getByText('Pending Approvals (2)')).toBeInTheDocument();
    });

    it('should display approval cards', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatusWithApprovals,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('approval-card-approval-001')).toBeInTheDocument();
      expect(screen.getByTestId('approval-card-approval-002')).toBeInTheDocument();
    });

    it('should call approveRecovery when approve button is clicked', async () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatusWithApprovals,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      const approveButtons = screen.getAllByTestId('approve-button');
      fireEvent.click(approveButtons[0]);

      await waitFor(() => {
        expect(mockHandlers.approveRecovery).toHaveBeenCalledWith(
          'brand-001',
          'approval-001',
          'user-001',
          'Approved via Studio'
        );
      });
    });

    it('should call rejectRecovery when reject button is clicked', async () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatusWithApprovals,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      const rejectButtons = screen.getAllByTestId('reject-button');
      fireEvent.click(rejectButtons[0]);

      await waitFor(() => {
        expect(mockHandlers.rejectRecovery).toHaveBeenCalledWith(
          'brand-001',
          'approval-001',
          'user-001',
          'Rejected via Studio'
        );
      });
    });
  });

  describe('Active Incidents', () => {
    const mockStatusWithIncidents = {
      brand_id: 'brand-001',
      state: 'active',
      version: 'v28',
      metrics: {
        total_runs: 15,
        successful_runs: 12,
        failed_runs: 2,
        auto_runs: 10,
        manual_runs: 5,
        pending_approvals: 0,
      },
      active_incidents: [
        {
          incident_id: 'inc-001',
          type: 'handoff_timeout',
          severity: 'high',
          description: 'Handoff queue timeout exceeded',
          timestamp: '2026-03-02T10:00:00Z',
        },
      ],
      pending_approvals: [],
    };

    it('should display incidents section when active incidents exist', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatusWithIncidents,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('incidents-section')).toBeInTheDocument();
      expect(screen.getByText('Active Incidents (1)')).toBeInTheDocument();
    });

    it('should display incident cards', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatusWithIncidents,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('incident-card-inc-001')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    const mockStatusEmpty = {
      brand_id: 'brand-001',
      state: 'idle',
      version: 'v28',
      metrics: {
        total_runs: 0,
        successful_runs: 0,
        failed_runs: 0,
        auto_runs: 0,
        manual_runs: 0,
        pending_approvals: 0,
      },
      active_incidents: [],
      pending_approvals: [],
    };

    it('should display empty state when no data', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: mockStatusEmpty,
        runs: [],
        events: [],
        loading: false,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.getByText('No active recoveries or pending approvals')).toBeInTheDocument();
    });
  });

  describe('Freeze/Rollback/Retry Actions (implied)', () => {
    it('should have canFreeze handler available', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: null,
        runs: [],
        events: [],
        loading: true,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(mockHandlers.canFreeze).toBeDefined();
    });

    it('should have canRollback handler available', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: null,
        runs: [],
        events: [],
        loading: true,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(mockHandlers.canRollback).toBeDefined();
    });

    it('should have canRetry handler available', () => {
      mockedUseRecoveryOrchestration.mockReturnValue({
        status: null,
        runs: [],
        events: [],
        loading: true,
        error: null,
        processing: false,
        ...mockHandlers,
      });

      render(<RecoveryOrchestrationPanel {...defaultProps} />);

      expect(mockHandlers.canRetry).toBeDefined();
    });
  });
});
