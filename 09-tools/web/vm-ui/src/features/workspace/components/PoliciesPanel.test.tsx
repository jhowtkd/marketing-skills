import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PoliciesPanel } from './PoliciesPanel';
import type { Policy, Proposal, PolicyStatus } from '../hooks/usePolicies';

describe('PoliciesPanel', () => {
  const mockPolicy: Policy = {
    threshold: 0.5,
    mode: 'standard',
    source: 'brand',
    source_brand_id: 'brand1',
    source_segment: null,
  };

  const mockProposals: Proposal[] = [
    {
      proposal_id: 'prop-1',
      brand_id: 'brand1',
      objective_key: 'conversion',
      current_value: 0.5,
      proposed_value: 0.55,
      adjustment_percent: 10,
      status: 'pending' as PolicyStatus,
      created_at: '2026-02-28T10:00:00Z',
    },
    {
      proposal_id: 'prop-2',
      brand_id: 'brand1',
      objective_key: 'awareness',
      current_value: 0.6,
      proposed_value: 0.54,
      adjustment_percent: -10,
      status: 'approved' as PolicyStatus,
      created_at: '2026-02-28T09:00:00Z',
      approved_by: 'admin',
    },
  ];

  const defaultProps = {
    policy: mockPolicy,
    proposals: mockProposals,
    isLoading: false,
    error: null,
    onApprove: vi.fn(),
    onReject: vi.fn(),
    onFreeze: vi.fn(),
    onRollback: vi.fn(),
    isFrozen: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('render effective policy', () => {
    it('should render effective policy with values', () => {
      render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText('Effective Policy')).toBeInTheDocument();
      expect(screen.getByText('0.5')).toBeInTheDocument();
      expect(screen.getByText('standard')).toBeInTheDocument();
    });

    it('should render policy source', () => {
      render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText('Source')).toBeInTheDocument();
      expect(screen.getByText('brand')).toBeInTheDocument();
    });

    it('should show brand info when source is brand', () => {
      render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText(/brand1/)).toBeInTheDocument();
    });
  });

  describe('render proposals', () => {
    it('should render proposals list', () => {
      render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText('Pending Proposals')).toBeInTheDocument();
      expect(screen.getByText('conversion')).toBeInTheDocument();
    });

    it('should render proposal with status', () => {
      render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText('pending')).toBeInTheDocument();
      expect(screen.getByText('approved')).toBeInTheDocument();
    });

    it('should show adjustment percent', () => {
      render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText('+10%')).toBeInTheDocument();
      expect(screen.getByText('-10%')).toBeInTheDocument();
    });

    it('should show approved by when approved', () => {
      render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText(/admin/)).toBeInTheDocument();
    });
  });

  describe('actions - approve/reject', () => {
    it('should call onApprove when approve button clicked', async () => {
      render(<PoliciesPanel {...defaultProps} />);

      const approveButton = screen.getByRole('button', { name: /approve/i });
      fireEvent.click(approveButton);

      await waitFor(() => {
        expect(defaultProps.onApprove).toHaveBeenCalledWith('prop-1');
      });
    });

    it('should call onReject when reject button clicked', async () => {
      render(<PoliciesPanel {...defaultProps} />);

      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);

      await waitFor(() => {
        expect(defaultProps.onReject).toHaveBeenCalledWith('prop-1');
      });
    });

    it('should disable approve/reject for non-pending proposals', () => {
      render(<PoliciesPanel {...defaultProps} />);

      const approvedRow = screen.getByText('approved').closest('tr');
      const buttons = approvedRow?.querySelectorAll('button');
      
      expect(buttons?.length).toBe(0);
    });
  });

  describe('actions - freeze/rollback', () => {
    it('should call onFreeze when freeze button clicked', async () => {
      render(<PoliciesPanel {...defaultProps} />);

      const freezeButton = screen.getByRole('button', { name: /freeze/i });
      fireEvent.click(freezeButton);

      await waitFor(() => {
        expect(defaultProps.onFreeze).toHaveBeenCalled();
      });
    });

    it('should call onRollback when rollback button clicked', async () => {
      render(<PoliciesPanel {...defaultProps} />);

      const rollbackButton = screen.getByRole('button', { name: /rollback/i });
      fireEvent.click(rollbackButton);

      await waitFor(() => {
        expect(defaultProps.onRollback).toHaveBeenCalled();
      });
    });
  });

  describe('loading state', () => {
    it('should show loading indicator when isLoading is true', () => {
      render(<PoliciesPanel {...defaultProps} isLoading={true} />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it('should disable actions when loading', () => {
      render(<PoliciesPanel {...defaultProps} isLoading={true} />);

      const buttons = screen.queryAllByRole('button');
      buttons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe('error state', () => {
    it('should show error message when error exists', () => {
      render(<PoliciesPanel {...defaultProps} error="Failed to load policy" />);

      expect(screen.getByText(/Failed to load policy/)).toBeInTheDocument();
    });

    it('should show error icon', () => {
      render(<PoliciesPanel {...defaultProps} error="Error" />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty message when no proposals', () => {
      render(<PoliciesPanel {...defaultProps} proposals={[]} />);

      expect(screen.getByText('No pending proposals')).toBeInTheDocument();
    });
  });

  describe('frozen state', () => {
    it('should show frozen banner when isFrozen is true', () => {
      render(<PoliciesPanel {...defaultProps} isFrozen={true} />);

      expect(screen.getByText(/frozen/i)).toBeInTheDocument();
    });

    it('should disable new proposals when frozen', () => {
      render(<PoliciesPanel {...defaultProps} isFrozen={true} />);

      const freezeButton = screen.queryByRole('button', { name: /freeze/i });
      expect(freezeButton).toBeDisabled();
    });
  });

  describe('data state transitions', () => {
    it('should update when policy changes', () => {
      const { rerender } = render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText('0.5')).toBeInTheDocument();

      const newPolicy = { ...mockPolicy, threshold: 0.7 };
      rerender(<PoliciesPanel {...defaultProps} policy={newPolicy} />);

      expect(screen.getByText('0.7')).toBeInTheDocument();
    });

    it('should update when proposals change', () => {
      const { rerender } = render(<PoliciesPanel {...defaultProps} />);

      expect(screen.getByText('conversion')).toBeInTheDocument();

      const newProposals = [
        { ...mockProposals[0], objective_key: 'retention' },
      ];
      rerender(<PoliciesPanel {...defaultProps} proposals={newProposals} />);

      expect(screen.getByText('retention')).toBeInTheDocument();
    });
  });
});
