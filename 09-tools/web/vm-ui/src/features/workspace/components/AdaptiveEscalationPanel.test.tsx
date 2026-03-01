/**
 * Tests for AdaptiveEscalationPanel (v21)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AdaptiveEscalationPanel } from './AdaptiveEscalationPanel';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('AdaptiveEscalationPanel', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('Initial load', () => {
    it('renders panel with title', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          approver_count: 5,
          total_approvals: 100,
          total_timeouts: 10,
          timeout_rate: 0.1,
        }),
      });

      render(<AdaptiveEscalationPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('adaptive-escalation-panel')).toBeInTheDocument();
      });

      expect(screen.getByText('Escalonamento Adaptativo v21')).toBeInTheDocument();
    });

    it('loads and displays metrics on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          approver_count: 5,
          total_approvals: 100,
          total_timeouts: 10,
          timeout_rate: 0.1,
        }),
      });

      render(<AdaptiveEscalationPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('metric-approver-count')).toHaveTextContent('5');
        expect(screen.getByTestId('metric-total-approvals')).toHaveTextContent('100');
        expect(screen.getByTestId('metric-timeout-rate')).toHaveTextContent('10.0%');
      });
    });
  });

  describe('Calculate windows', () => {
    it('calculates escalation windows on button click', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            approver_count: 5,
            total_approvals: 100,
            total_timeouts: 10,
            timeout_rate: 0.1,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            windows: [600, 1200, 2400],
            adaptive_factors: {
              risk_level: 'medium',
              pending_load: 5,
            },
          }),
        });

      render(<AdaptiveEscalationPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-calculate-windows')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-calculate-windows'));

      await waitFor(() => {
        expect(screen.getByTestId('escalation-windows')).toBeInTheDocument();
        expect(screen.getByTestId('window-level-0')).toHaveTextContent('Nível 1');
        expect(screen.getByTestId('window-level-1')).toHaveTextContent('Nível 2');
        expect(screen.getByTestId('window-level-2')).toHaveTextContent('Nível 3');
      });
    });

    it('displays adaptive factors', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            approver_count: 5,
            total_approvals: 100,
            total_timeouts: 10,
            timeout_rate: 0.1,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            windows: [600, 1200, 2400],
            adaptive_factors: {
              risk_level: 'high',
              pending_load: 10,
            },
          }),
        });

      render(<AdaptiveEscalationPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-calculate-windows')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-calculate-windows'));

      await waitFor(() => {
        expect(screen.getByTestId('adaptive-factors')).toBeInTheDocument();
        expect(screen.getByText('HIGH')).toBeInTheDocument();
        expect(screen.getByText('10')).toBeInTheDocument();
      });
    });
  });

  describe('Approver profile', () => {
    it('loads and displays approver profile', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            approver_count: 5,
            total_approvals: 100,
            total_timeouts: 10,
            timeout_rate: 0.1,
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            approver_id: 'admin@example.com',
            avg_response_time_minutes: 12.5,
            approvals_count: 50,
            timeouts_count: 5,
            timeout_rate: 0.09,
            total_count: 55,
          }),
        });

      render(<AdaptiveEscalationPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-load-profile')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-load-profile'));

      await waitFor(() => {
        expect(screen.getByTestId('approver-profile')).toBeInTheDocument();
        expect(screen.getByTestId('profile-id')).toHaveTextContent('admin@example.com');
        expect(screen.getByTestId('profile-avg-response')).toHaveTextContent('12.5m');
        expect(screen.getByTestId('profile-approvals')).toHaveTextContent('50');
        expect(screen.getByTestId('profile-timeouts')).toHaveTextContent('5');
      });
    });
  });

  describe('Error handling', () => {
    it('displays error message on API failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<AdaptiveEscalationPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('escalation-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  describe('Loading states', () => {
    it('shows loading while fetching metrics', async () => {
      mockFetch.mockImplementation(() => new Promise(() => {}));

      render(<AdaptiveEscalationPanel />);

      expect(screen.getByTestId('metrics-loading')).toBeInTheDocument();
    });

    it('disables buttons while loading', async () => {
      mockFetch.mockImplementation(() => new Promise(() => {}));

      render(<AdaptiveEscalationPanel />);

      expect(screen.getByTestId('btn-calculate-windows')).toBeDisabled();
      expect(screen.getByTestId('btn-load-profile')).toBeDisabled();
    });
  });
});
