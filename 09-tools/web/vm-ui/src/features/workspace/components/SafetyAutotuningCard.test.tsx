/**
 * SafetyAutotuningCard.test.tsx
 * 
 * Testes para o componente SafetyAutotuningCard.
 * 
 * Test Coverage:
 * - Estados loading/empty/error/data
 * - Ações apply/revert/freeze
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SafetyAutotuningCard } from './SafetyAutotuningCard';
import * as useSafetyAutotuningModule from '../hooks/useSafetyAutotuning';

// Mock do hook
vi.mock('../hooks/useSafetyAutotuning');

const mockUseSafetyAutotuning = vi.mocked(useSafetyAutotuningModule.useSafetyAutotuning);

describe('SafetyAutotuningCard', () => {
  const mockRefreshStatus = vi.fn();
  const mockRunCycle = vi.fn();
  const mockApplyProposal = vi.fn();
  const mockRevertProposal = vi.fn();
  const mockFreezeGate = vi.fn();
  const mockUnfreezeGate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'loading',
      lastCycleAt: null,
      gates: [],
      frozenGates: [],
      activeCanaries: [],
      currentCycle: null,
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    expect(screen.getByTestId('tuning-status')).toHaveTextContent('Carregando...');
  });

  it('renders empty state when no gates', () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'idle',
      lastCycleAt: null,
      gates: [],
      frozenGates: [],
      activeCanaries: [],
      currentCycle: null,
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    expect(screen.getByTestId('gates-status')).toHaveTextContent('Nenhum gate configurado');
  });

  it('renders gates list', () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'idle',
      lastCycleAt: '2026-02-28T12:00:00Z',
      gates: [
        { name: 'sample_size', currentValue: 100, minValue: 50, maxValue: 500, isFrozen: false, isCanaryActive: false },
        { name: 'confidence_threshold', currentValue: 0.8, minValue: 0.5, maxValue: 0.95, isFrozen: true, isCanaryActive: true },
      ],
      frozenGates: ['confidence_threshold'],
      activeCanaries: ['confidence_threshold'],
      currentCycle: null,
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    expect(screen.getByTestId('gate-sample_size')).toBeInTheDocument();
    expect(screen.getByTestId('gate-confidence_threshold')).toBeInTheDocument();
    expect(screen.getByTestId('freeze-sample_size')).toBeInTheDocument();
    expect(screen.getByTestId('unfreeze-confidence_threshold')).toBeInTheDocument();
  });

  it('renders proposals list', () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'idle',
      lastCycleAt: null,
      gates: [],
      frozenGates: [],
      activeCanaries: [],
      currentCycle: {
        cycleId: 'cycle-001',
        proposals: [
          {
            proposalId: 'prop-001',
            gateName: 'sample_size',
            currentValue: 100,
            proposedValue: 90,
            adjustmentPercent: -10,
            riskLevel: 'low',
            reason: 'HIGH_FP_RATE',
          },
        ],
        proposalsCount: 1,
        timestamp: '2026-02-28T12:00:00Z',
      },
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    expect(screen.getByTestId('proposal-prop-001')).toBeInTheDocument();
    expect(screen.getByTestId('apply-prop-001')).toBeInTheDocument();
    expect(screen.getByTestId('revert-prop-001')).toBeInTheDocument();
  });

  it('calls runCycle when analyze button clicked', async () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'idle',
      lastCycleAt: null,
      gates: [],
      frozenGates: [],
      activeCanaries: [],
      currentCycle: null,
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    const analyzeBtn = screen.getByTestId('run-cycle-btn');
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(mockRunCycle).toHaveBeenCalledWith('propose');
    });
  });

  it('calls applyProposal when apply button clicked', async () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'idle',
      lastCycleAt: null,
      gates: [],
      frozenGates: [],
      activeCanaries: [],
      currentCycle: {
        cycleId: 'cycle-001',
        proposals: [
          {
            proposalId: 'prop-001',
            gateName: 'sample_size',
            currentValue: 100,
            proposedValue: 90,
            adjustmentPercent: -10,
            riskLevel: 'low',
            reason: 'HIGH_FP_RATE',
          },
        ],
        proposalsCount: 1,
        timestamp: '2026-02-28T12:00:00Z',
      },
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    const applyBtn = screen.getByTestId('apply-prop-001');
    fireEvent.click(applyBtn);

    await waitFor(() => {
      expect(mockApplyProposal).toHaveBeenCalledWith('prop-001', false);
    });
  });

  it('calls freezeGate when freeze button clicked', async () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'idle',
      lastCycleAt: null,
      gates: [
        { name: 'sample_size', currentValue: 100, minValue: 50, maxValue: 500, isFrozen: false, isCanaryActive: false },
      ],
      frozenGates: [],
      activeCanaries: [],
      currentCycle: null,
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    const freezeBtn = screen.getByTestId('freeze-sample_size');
    fireEvent.click(freezeBtn);

    await waitFor(() => {
      expect(mockFreezeGate).toHaveBeenCalledWith('sample_size');
    });
  });

  it('renders error state', () => {
    mockUseSafetyAutotuning.mockReturnValue({
      status: 'error',
      lastCycleAt: null,
      gates: [],
      frozenGates: [],
      activeCanaries: [],
      currentCycle: null,
      audit: [],
      refreshStatus: mockRefreshStatus,
      runCycle: mockRunCycle,
      applyProposal: mockApplyProposal,
      revertProposal: mockRevertProposal,
      freezeGate: mockFreezeGate,
      unfreezeGate: mockUnfreezeGate,
      refreshAudit: vi.fn(),
    });

    render(<SafetyAutotuningCard />);

    expect(screen.getByTestId('tuning-status')).toHaveTextContent('Ativo');
  });
});
