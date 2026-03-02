import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PredictiveResiliencePanel } from './PredictiveResiliencePanel';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('PredictiveResiliencePanel', () => {
  const brandId = 'test-brand-001';

  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Loading and Error States
  // ===========================================================================

  describe('Loading State', () => {
    it('should show loading state initially', () => {
      mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<PredictiveResiliencePanel brandId={brandId} />);

      expect(screen.getByTestId('predictive-resilience-loading')).toBeInTheDocument();
      expect(screen.getByText('Loading Predictive Resilience...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error message when fetch fails', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('predictive-resilience-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    it('should have retry button on error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Main Panel States
  // ===========================================================================

  describe('Idle State', () => {
    it('should render panel with idle state', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'idle',
          version: 'v27',
          cycles_total: 0,
          proposals_total: 0,
          proposals_applied: 0,
          false_positives_total: 0,
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('predictive-resilience-panel')).toBeInTheDocument();
      });

      expect(screen.getByTestId('resilience-state')).toHaveTextContent('idle');
    });

    it('should show empty state when no signals or proposals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'idle',
          version: 'v27',
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      });

      expect(screen.getByText('No active signals or proposals')).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('should show observing state', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          version: 'v27',
          cycles_total: 5,
          proposals_total: 10,
          proposals_applied: 8,
          false_positives_total: 1,
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('resilience-state')).toHaveTextContent('observing');
      });
    });
  });

  describe('Frozen State', () => {
    it('should show frozen state with unfreeze button', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'frozen',
          version: 'v27',
          cycles_total: 3,
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('resilience-state')).toHaveTextContent('frozen');
      });

      expect(screen.getByTestId('unfreeze-button')).toBeInTheDocument();
      expect(screen.queryByTestId('freeze-button')).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Resilience Score Display
  // ===========================================================================

  describe('Resilience Score', () => {
    it('should display composite score', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          resilience_score: {
            incident_component: 0.80,
            handoff_component: 0.85,
            approval_component: 0.81,
            composite_score: 0.82,
            risk_class: 'medium',
            timestamp: '2026-03-01T12:00:00Z',
          },
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('resilience-score')).toBeInTheDocument();
      });

      expect(screen.getByTestId('composite-score')).toHaveTextContent('82.0%');
    });

    it('should show risk class badge', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          resilience_score: {
            incident_component: 0.80,
            handoff_component: 0.85,
            approval_component: 0.81,
            composite_score: 0.82,
            risk_class: 'medium',
            timestamp: '2026-03-01T12:00:00Z',
          },
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('risk-class-badge')).toHaveTextContent('MEDIUM');
      });
    });

    it('should show component breakdown', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          resilience_score: {
            incident_component: 0.80,
            handoff_component: 0.85,
            approval_component: 0.81,
            composite_score: 0.82,
            risk_class: 'medium',
            timestamp: '2026-03-01T12:00:00Z',
          },
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('incident-component')).toBeInTheDocument();
        expect(screen.getByTestId('handoff-component')).toBeInTheDocument();
        expect(screen.getByTestId('approval-component')).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Stats Display
  // ===========================================================================

  describe('Stats Section', () => {
    it('should show cycle count', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          cycles_total: 42,
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('stat-cycles')).toHaveTextContent('42');
      });
    });

    it('should show proposals count', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          proposals_total: 15,
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('stat-proposals')).toHaveTextContent('15');
      });
    });

    it('should show applied count', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          proposals_applied: 12,
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('stat-applied')).toHaveTextContent('12');
      });
    });

    it('should show false positives count', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          false_positives_total: 2,
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('stat-false-positives')).toHaveTextContent('2');
      });
    });
  });

  // ===========================================================================
  // Signals Display
  // ===========================================================================

  describe('Active Signals', () => {
    it('should display active signals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_signals: [
            {
              signal_id: 'sig-001',
              metric_name: 'incident_rate',
              current_value: 0.12,
              predicted_value: 0.18,
              delta: 0.06,
              delta_pct: 0.50,
              confidence: 0.85,
              forecast_horizon_hours: 4,
              severity: 'medium',
              timestamp: '2026-03-01T12:00:00Z',
            },
          ],
          active_proposals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('signals-section')).toBeInTheDocument();
      });

      expect(screen.getByTestId('signal-card-sig-001')).toBeInTheDocument();
      expect(screen.getByTestId('signal-metric')).toHaveTextContent('incident_rate');
    });

    it('should show signal severity', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_signals: [
            {
              signal_id: 'sig-001',
              metric_name: 'incident_rate',
              current_value: 0.12,
              predicted_value: 0.18,
              delta: 0.06,
              delta_pct: 0.50,
              confidence: 0.85,
              forecast_horizon_hours: 4,
              severity: 'high',
              timestamp: '2026-03-01T12:00:00Z',
            },
          ],
          active_proposals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('signal-severity')).toHaveTextContent('high');
      });
    });

    it('should show signal delta', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_signals: [
            {
              signal_id: 'sig-001',
              metric_name: 'incident_rate',
              current_value: 0.12,
              predicted_value: 0.18,
              delta: 0.06,
              delta_pct: 0.50,
              confidence: 0.85,
              forecast_horizon_hours: 4,
              severity: 'medium',
              timestamp: '2026-03-01T12:00:00Z',
            },
          ],
          active_proposals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('signal-delta')).toHaveTextContent('(+50.0%)');
      });
    });
  });

  // ===========================================================================
  // Proposals Display and Actions
  // ===========================================================================

  describe('Pending Proposals', () => {
    it('should display pending proposals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: { incident_rate: -0.05 },
              state: 'pending',
              created_at: '2026-03-01T12:00:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('proposals-section')).toBeInTheDocument();
      });

      expect(screen.getByTestId('proposal-card-prop-001')).toBeInTheDocument();
    });

    it('should show proposal type and severity', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: {},
              state: 'pending',
              created_at: '2026-03-01T12:00:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-type')).toHaveTextContent('auto_adjust');
        expect(screen.getByTestId('proposal-severity')).toHaveTextContent('low');
      });
    });

    it('should show auto-apply badge for low risk', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: {},
              state: 'pending',
              created_at: '2026-03-01T12:00:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-auto-apply')).toHaveTextContent('Auto');
      });
    });
  });

  describe('Apply Action', () => {
    it('should show apply button for low-risk pending proposals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: {},
              state: 'pending',
              created_at: '2026-03-01T12:00:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('apply-button')).toBeInTheDocument();
      });
    });

    it('should call apply API when apply button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [
              {
                proposal_id: 'prop-001',
                signal_id: 'sig-001',
                mitigation_type: 'auto_adjust',
                severity: 'low',
                description: 'Auto-adjust threshold',
                can_auto_apply: true,
                requires_escalation: false,
                estimated_impact: {},
                state: 'pending',
                created_at: '2026-03-01T12:00:00Z',
              },
            ],
            active_signals: [],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [],
            active_signals: [],
          }),
        });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('apply-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('apply-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/proposals/prop-001/apply'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('should show requires approval for medium/high risk', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-002',
              signal_id: 'sig-002',
              mitigation_type: 'adjust_with_approval',
              severity: 'medium',
              description: 'Adjust with approval',
              can_auto_apply: false,
              requires_escalation: false,
              estimated_impact: {},
              state: 'pending',
              created_at: '2026-03-01T12:00:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('requires-approval')).toHaveTextContent('Requires approval');
      });

      expect(screen.queryByTestId('apply-button')).not.toBeInTheDocument();
    });
  });

  describe('Reject Action', () => {
    it('should show reject button for pending proposals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: {},
              state: 'pending',
              created_at: '2026-03-01T12:00:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('reject-button')).toBeInTheDocument();
      });
    });

    it('should call reject API when reject button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [
              {
                proposal_id: 'prop-001',
                signal_id: 'sig-001',
                mitigation_type: 'auto_adjust',
                severity: 'low',
                description: 'Auto-adjust threshold',
                can_auto_apply: true,
                requires_escalation: false,
                estimated_impact: {},
                state: 'pending',
                created_at: '2026-03-01T12:00:00Z',
              },
            ],
            active_signals: [],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [],
            active_signals: [],
          }),
        });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('reject-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('reject-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/proposals/prop-001/reject'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });
  });

  describe('Rollback Action', () => {
    it('should show rollback button for applied proposals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: {},
              state: 'applied',
              created_at: '2026-03-01T12:00:00Z',
              applied_at: '2026-03-01T12:05:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('rollback-button')).toBeInTheDocument();
      });
    });

    it('should show applied state for applied proposals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: {},
              state: 'applied',
              created_at: '2026-03-01T12:00:00Z',
              applied_at: '2026-03-01T12:05:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-state')).toHaveTextContent('applied');
      });
    });

    it('should call rollback API when rollback button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [
              {
                proposal_id: 'prop-001',
                signal_id: 'sig-001',
                mitigation_type: 'auto_adjust',
                severity: 'low',
                description: 'Auto-adjust threshold',
                can_auto_apply: true,
                requires_escalation: false,
                estimated_impact: {},
                state: 'applied',
                created_at: '2026-03-01T12:00:00Z',
                applied_at: '2026-03-01T12:05:00Z',
              },
            ],
            active_signals: [],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ rolled_back: ['prop-001'] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [],
            active_signals: [],
          }),
        });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('rollback-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('rollback-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/rollback'),
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ proposal_id: 'prop-001' }),
          })
        );
      });
    });
  });

  // ===========================================================================
  // Freeze/Unfreeze Actions
  // ===========================================================================

  describe('Freeze Action', () => {
    it('should show freeze button when not frozen', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('freeze-button')).toBeInTheDocument();
        expect(screen.queryByTestId('unfreeze-button')).not.toBeInTheDocument();
      });
    });

    it('should call freeze API when freeze button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [],
            active_signals: [],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ brand_id: brandId, state: 'frozen' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'frozen',
            active_proposals: [],
            active_signals: [],
          }),
        });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('freeze-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('freeze-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/freeze'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });
  });

  describe('Unfreeze Action', () => {
    it('should show unfreeze button when frozen', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'frozen',
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('unfreeze-button')).toBeInTheDocument();
        expect(screen.queryByTestId('freeze-button')).not.toBeInTheDocument();
      });
    });

    it('should call unfreeze API when unfreeze button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'frozen',
            active_proposals: [],
            active_signals: [],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ brand_id: brandId, state: 'active' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [],
            active_signals: [],
          }),
        });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('unfreeze-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('unfreeze-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/unfreeze'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });
  });

  // ===========================================================================
  // Run Cycle Action
  // ===========================================================================

  describe('Run Cycle Action', () => {
    it('should show run cycle button', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'idle',
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('run-cycle-button')).toBeInTheDocument();
      });
    });

    it('should call run cycle API when button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'idle',
            active_proposals: [],
            active_signals: [],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            cycle_id: 'cycle-001',
            brand_id: brandId,
            enabled: true,
            score: {
              incident_component: 0.80,
              handoff_component: 0.85,
              approval_component: 0.81,
              composite_score: 0.82,
              risk_class: 'medium',
              timestamp: '2026-03-01T12:00:00Z',
            },
            signals_detected: 2,
            proposals_generated: 1,
            proposals_applied: 1,
            proposals_pending: 0,
            freeze_triggered: false,
            proposals: [],
            signals: [],
            applied_ids: ['prop-001'],
            pending_ids: [],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            brand_id: brandId,
            state: 'observing',
            active_proposals: [],
            active_signals: [],
          }),
        });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('run-cycle-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('run-cycle-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/run'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('should disable run cycle button when frozen', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'frozen',
          active_proposals: [],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('run-cycle-button')).toBeDisabled();
      });
    });
  });

  // ===========================================================================
  // Proposal Impact Display
  // ===========================================================================

  describe('Proposal Impact', () => {
    it('should show estimated impact when available', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          brand_id: brandId,
          state: 'observing',
          active_proposals: [
            {
              proposal_id: 'prop-001',
              signal_id: 'sig-001',
              mitigation_type: 'auto_adjust',
              severity: 'low',
              description: 'Auto-adjust threshold',
              can_auto_apply: true,
              requires_escalation: false,
              estimated_impact: { incident_rate: -0.05, v1_score: 0.02 },
              state: 'pending',
              created_at: '2026-03-01T12:00:00Z',
            },
          ],
          active_signals: [],
        }),
      });

      render(<PredictiveResiliencePanel brandId={brandId} />);

      await waitFor(() => {
        expect(screen.getByTestId('proposal-impact')).toBeInTheDocument();
      });

      expect(screen.getByTestId('proposal-impact')).toHaveTextContent('incident_rate: -5.0%');
      expect(screen.getByTestId('proposal-impact')).toHaveTextContent('v1_score: +2.0%');
    });
  });
});
