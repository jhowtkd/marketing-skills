/**
 * Tests for AgentDagOpsPanel (v22)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AgentDagOpsPanel } from './AgentDagOpsPanel';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('AgentDagOpsPanel', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('Initial load', () => {
    it('renders panel with title', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: [
            { run_id: 'run_001', dag_id: 'dag_001', status: 'running', nodes: 3 },
          ],
        }),
      });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('agent-dag-ops-panel')).toBeInTheDocument();
      });

      expect(screen.getByText('Agent DAG Ops v22')).toBeInTheDocument();
    });

    it('loads and displays DAG runs on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: [
            { run_id: 'run_001', dag_id: 'dag_001', status: 'running', nodes: 3 },
            { run_id: 'run_002', dag_id: 'dag_002', status: 'completed', nodes: 5 },
          ],
        }),
      });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('dag-run-run_001')).toBeInTheDocument();
        expect(screen.getByTestId('dag-run-run_002')).toBeInTheDocument();
      });
    });

    it('displays node status for each run', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          runs: [
            { 
              run_id: 'run_001', 
              dag_id: 'dag_001', 
              status: 'running', 
              nodes: 3,
              node_states: {
                node_a: { status: 'completed' },
                node_b: { status: 'running' },
                node_c: { status: 'pending' },
              }
            },
          ],
        }),
      });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('node-status-node_a')).toHaveTextContent('completed');
        expect(screen.getByTestId('node-status-node_b')).toHaveTextContent('running');
        expect(screen.getByTestId('node-status-node_c')).toHaveTextContent('pending');
      });
    });
  });

  describe('Actions', () => {
    it('pauses a DAG run when pause button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            runs: [{ run_id: 'run_001', dag_id: 'dag_001', status: 'running', nodes: 3 }],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ run_id: 'run_001', status: 'paused' }),
        });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-pause-run_001')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-pause-run_001'));

      await waitFor(() => {
        expect(screen.getByTestId('dag-run-run_001')).toHaveTextContent('paused');
      });
    });

    it('resumes a paused DAG run when resume button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            runs: [{ run_id: 'run_001', dag_id: 'dag_001', status: 'paused', nodes: 3 }],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ run_id: 'run_001', status: 'running' }),
        });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-resume-run_001')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-resume-run_001'));

      await waitFor(() => {
        expect(screen.getByTestId('dag-run-run_001')).toHaveTextContent('running');
      });
    });

    it('aborts a DAG run when abort button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            runs: [{ run_id: 'run_001', dag_id: 'dag_001', status: 'running', nodes: 3 }],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ run_id: 'run_001', status: 'aborted' }),
        });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-abort-run_001')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-abort-run_001'));

      await waitFor(() => {
        expect(screen.getByTestId('dag-run-run_001')).toHaveTextContent('aborted');
      });
    });

    it('retries a node when retry button clicked', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            runs: [{
              run_id: 'run_001',
              dag_id: 'dag_001',
              status: 'running',
              nodes: 1,
              node_states: { node_a: { status: 'failed', attempts: 2 } },
            }],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ run_id: 'run_001', node_id: 'node_a', status: 'pending' }),
        });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-retry-node_a')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('btn-retry-node_a'));

      await waitFor(() => {
        expect(screen.getByTestId('node-status-node_a')).toHaveTextContent('pending');
      });
    });
  });

  describe('Approvals', () => {
    it('shows pending approvals with grant/reject buttons', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          runs: [{
            run_id: 'run_001',
            dag_id: 'dag_001',
            status: 'running',
            nodes: 1,
            pending_approvals: [{ request_id: 'req_001', node_id: 'node_a', risk_level: 'high' }],
          }],
        }),
      });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('btn-grant-req_001')).toBeInTheDocument();
        expect(screen.getByTestId('btn-reject-req_001')).toBeInTheDocument();
      });
    });
  });

  describe('Error handling', () => {
    it('displays error message on API failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('dag-ops-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  describe('Loading states', () => {
    it('shows loading while fetching runs', async () => {
      mockFetch.mockImplementation(() => new Promise(() => {}));

      render(<AgentDagOpsPanel />);

      expect(screen.getByTestId('dag-ops-loading')).toBeInTheDocument();
    });

    it('displays empty state when no runs', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ runs: [] }),
      });

      render(<AgentDagOpsPanel />);

      await waitFor(() => {
        expect(screen.getByTestId('dag-ops-empty')).toBeInTheDocument();
      });
    });
  });
});
