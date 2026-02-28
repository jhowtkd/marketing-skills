/**
 * Tests for RoiOptimizerPanel (v19)
 * 
 * Test coverage:
 * - Loading/empty/error/data states
 * - Score display with pillar contributions
 * - Proposal actions (apply/reject/rollback/freeze)
 * - Autoapply eligibility indicators
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { RoiOptimizerPanel } from './RoiOptimizerPanel';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('RoiOptimizerPanel', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('Loading state', () => {
    it('shows loading spinner while fetching initial data', async () => {
      // Delay the response to keep loading state visible
      mockFetch.mockImplementation(() => new Promise(() => {}));

      render(<RoiOptimizerPanel />);

      expect(screen.getByTestId('roi-panel-loading')).toBeInTheDocument();
      expect(screen.getByText('Carregando...')).toBeInTheDocument();
    });
  });

  describe('Empty state', () => {
    it('shows empty state when no data available', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => null,
      });

      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('roi-panel-empty')).toBeInTheDocument();
      });

      expect(screen.getByText('Otimizador de ROI')).toBeInTheDocument();
      expect(screen.getByText('Nenhuma otimização executada ainda.')).toBeInTheDocument();
      expect(screen.getByTestId('btn-run-empty')).toBeInTheDocument();
    });

    it('allows running optimization from empty state', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => null,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            proposals: [
              {
                id: 'prop-001',
                description: 'Test proposal',
                expected_roi_delta: 0.05,
                risk_level: 'low',
                status: 'pending',
                adjustments: { param1: 0.05 },
                autoapply_eligible: true,
                created_at: '2026-02-28T12:00:00Z',
              },
            ],
            score_before: 0.70,
            score_after: 0.75,
          }),
        });

      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('roi-panel-empty')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-run-empty'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/roi/run',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });
  });

  describe('Error state', () => {
    it('shows error message when fetch fails', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('roi-panel-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Erro')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    it('shows error banner when action fails', async () => {
      // Initial load succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          mode: 'semi-automatic',
          cadence: 'weekly',
          weights: { business: 0.40, quality: 0.35, efficiency: 0.25 },
          current_score: {
            total: 0.72,
            business: 0.68,
            quality: 0.75,
            efficiency: 0.73,
          },
          last_run_at: '2026-02-28T12:00:00Z',
        }),
      });

      // Proposals load succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            id: 'prop-001',
            description: 'Test proposal',
            expected_roi_delta: 0.05,
            risk_level: 'low',
            status: 'pending',
            adjustments: {},
            autoapply_eligible: true,
            created_at: '2026-02-28T12:00:00Z',
          },
        ],
      });

      // Apply fails
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Server error',
      });

      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('roi-optimizer-panel')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-apply-prop-001'));

      await waitFor(() => {
        expect(screen.getByTestId('roi-error-banner')).toBeInTheDocument();
      });

      expect(screen.getByTestId('roi-error-banner')).toHaveTextContent('Server error');
    });
  });

  describe('Data state - Score display', () => {
    beforeEach(() => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            mode: 'semi-automatic',
            cadence: 'weekly',
            weights: { business: 0.40, quality: 0.35, efficiency: 0.25 },
            current_score: {
              total: 0.72,
              business: 0.68,
              quality: 0.75,
              efficiency: 0.73,
            },
            last_run_at: '2026-02-28T12:00:00Z',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        });
    });

    it('displays mode and cadence badges', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('roi-mode')).toHaveTextContent('semi-automatic');
        expect(screen.getByTestId('roi-cadence')).toHaveTextContent('weekly');
      });
    });

    it('displays composite score with correct percentage', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('score-card-total')).toBeInTheDocument();
        expect(screen.getByTestId('total-value')).toHaveTextContent('72.0%');
      });
    });

    it('displays all three pillar scores with weights', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        // Business: 40%
        expect(screen.getByTestId('score-card-business')).toBeInTheDocument();
        expect(screen.getByTestId('business-value')).toHaveTextContent('68.0%');
        expect(screen.getByTestId('business-weight')).toHaveTextContent('40%');

        // Quality: 35%
        expect(screen.getByTestId('score-card-quality')).toBeInTheDocument();
        expect(screen.getByTestId('quality-value')).toHaveTextContent('75.0%');
        expect(screen.getByTestId('quality-weight')).toHaveTextContent('35%');

        // Efficiency: 25%
        expect(screen.getByTestId('score-card-efficiency')).toBeInTheDocument();
        expect(screen.getByTestId('efficiency-value')).toHaveTextContent('73.0%');
        expect(screen.getByTestId('efficiency-weight')).toHaveTextContent('25%');
      });
    });
  });

  describe('Proposal actions', () => {
    const mockProposals = [
      {
        id: 'prop-001',
        description: 'Increase approval rate',
        expected_roi_delta: 0.05,
        risk_level: 'low',
        status: 'pending',
        adjustments: { approval_boost: 0.05 },
        autoapply_eligible: true,
        created_at: '2026-02-28T12:00:00Z',
      },
      {
        id: 'prop-002',
        description: 'Reduce regen',
        expected_roi_delta: 0.03,
        risk_level: 'medium',
        status: 'pending',
        adjustments: { regen_reduction: -0.05 },
        autoapply_eligible: false,
        created_at: '2026-02-28T12:00:00Z',
      },
    ];

    beforeEach(() => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            mode: 'semi-automatic',
            cadence: 'weekly',
            weights: { business: 0.40, quality: 0.35, efficiency: 0.25 },
            current_score: {
              total: 0.72,
              business: 0.68,
              quality: 0.75,
              efficiency: 0.73,
            },
            last_run_at: '2026-02-28T12:00:00Z',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockProposals,
        });
    });

    it('displays pending proposals with apply/reject buttons', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-prop-001')).toBeInTheDocument();
        expect(screen.getByTestId('proposal-prop-002')).toBeInTheDocument();
      });

      // Check proposal details
      expect(screen.getByTestId('proposal-desc-prop-001')).toHaveTextContent('Increase approval rate');
      expect(screen.getByTestId('proposal-delta-prop-001')).toHaveTextContent('Δ ROI: +5.0%');

      // Check action buttons exist
      expect(screen.getByTestId('btn-apply-prop-001')).toBeInTheDocument();
      expect(screen.getByTestId('btn-reject-prop-001')).toBeInTheDocument();
    });

    it('shows risk level indicators', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-risk-prop-001')).toHaveTextContent('LOW');
        expect(screen.getByTestId('proposal-risk-prop-002')).toHaveTextContent('MEDIUM');
      });
    });

    it('shows autoapply eligibility badge', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-autoapply-prop-001')).toBeInTheDocument();
        expect(screen.getByTestId('proposal-autoapply-prop-001')).toHaveTextContent('Auto-aplicável');
      });

      // prop-002 is not autoapply eligible
      expect(screen.queryByTestId('proposal-autoapply-prop-002')).not.toBeInTheDocument();
    });

    it('shows autoapply hint when eligible proposals exist', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('autoapply-hint')).toBeInTheDocument();
        expect(screen.getByTestId('autoapply-hint')).toHaveTextContent('Propostas elegíveis para auto-aplicação');
      });
    });

    it('calls API when applying a proposal', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'applied' }),
      });

      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-apply-prop-001')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-apply-prop-001'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/roi/proposals/prop-001/apply',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('calls API when rejecting a proposal', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'rejected' }),
      });

      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-reject-prop-001')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-reject-prop-001'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/roi/proposals/prop-001/reject',
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('Rejected by user'),
          })
        );
      });
    });
  });

  describe('Rollback action', () => {
    const mockAppliedProposals = [
      {
        id: 'prop-001',
        description: 'Applied proposal',
        expected_roi_delta: 0.05,
        risk_level: 'low',
        status: 'applied',
        adjustments: {},
        autoapply_eligible: false,
        created_at: '2026-02-28T12:00:00Z',
        applied_at: '2026-02-28T12:30:00Z',
      },
    ];

    beforeEach(() => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            mode: 'semi-automatic',
            cadence: 'weekly',
            weights: { business: 0.40, quality: 0.35, efficiency: 0.25 },
            current_score: null,
            last_run_at: '2026-02-28T12:00:00Z',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockAppliedProposals,
        });
    });

    it('shows rollback button when there are applied proposals', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-rollback')).toBeInTheDocument();
        expect(screen.getByTestId('btn-rollback')).toHaveTextContent('Rollback (1)');
      });
    });

    it('shows applied proposals in separate group', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('applied-proposals')).toBeInTheDocument();
        expect(screen.getByText('Aplicadas (1)')).toBeInTheDocument();
      });
    });

    it('calls rollback API when clicking rollback button', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ rolled_back_proposal: { id: 'prop-001' } }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => [],
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            mode: 'semi-automatic',
            cadence: 'weekly',
            weights: { business: 0.40, quality: 0.35, efficiency: 0.25 },
            current_score: null,
            last_run_at: '2026-02-28T12:00:00Z',
          }),
        });

      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-rollback')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-rollback'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/v2/roi/rollback',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });
  });

  describe('Blocked proposals', () => {
    const mockBlockedProposals = [
      {
        id: 'prop-001',
        description: 'Would increase incident rate',
        expected_roi_delta: 0.0,
        risk_level: 'critical',
        status: 'blocked',
        adjustments: {},
        autoapply_eligible: false,
        block_reason: 'Optimization blocked: would increase incident rate',
        created_at: '2026-02-28T12:00:00Z',
      },
    ];

    beforeEach(() => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            mode: 'semi-automatic',
            cadence: 'weekly',
            weights: { business: 0.40, quality: 0.35, efficiency: 0.25 },
            current_score: null,
            last_run_at: '2026-02-28T12:00:00Z',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockBlockedProposals,
        });
    });

    it('shows blocked proposals with block reason', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('blocked-proposals')).toBeInTheDocument();
        expect(screen.getByText('Bloqueadas (1)')).toBeInTheDocument();
      });

      expect(screen.getByTestId('proposal-block-reason-prop-001')).toBeInTheDocument();
      expect(screen.getByTestId('proposal-block-reason-prop-001')).toHaveTextContent('would increase incident rate');
    });

    it('shows critical risk level for blocked proposals', async () => {
      render(<RoiOptimizerPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-risk-prop-001')).toHaveTextContent('CRITICAL');
      });
    });
  });
});
