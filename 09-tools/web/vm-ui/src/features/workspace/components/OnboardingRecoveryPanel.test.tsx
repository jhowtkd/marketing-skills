/**
 * OnboardingRecoveryPanel Tests (v34)
 * 
 * Vitest tests for the Onboarding Recovery Panel component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock the hook
vi.mock('../hooks/useOnboardingRecovery', () => ({
  useOnboardingRecovery: vi.fn(),
}));

import { OnboardingRecoveryPanel } from './OnboardingRecoveryPanel';
import { useOnboardingRecovery } from '../hooks/useOnboardingRecovery';

const mockedUseOnboardingRecovery = vi.mocked(useOnboardingRecovery);

describe('OnboardingRecoveryPanel', () => {
  const mockRefresh = vi.fn();
  const mockApplyCase = vi.fn();
  const mockRejectCase = vi.fn();
  const mockFreeze = vi.fn();
  const mockRollback = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockedUseOnboardingRecovery.mockReturnValue({
      status: null,
      cases: [],
      pendingApprovals: [],
      metrics: null,
      loading: true,
      error: null,
      refresh: mockRefresh,
      runDetection: vi.fn(),
      applyCase: mockApplyCase,
      rejectCase: mockRejectCase,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingRecoveryPanel brandId="brand-001" />);
    
    expect(screen.getByText('Atualizando...')).toBeInTheDocument();
  });

  it('renders metrics when loaded', () => {
    mockedUseOnboardingRecovery.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v34',
        frozen: false,
        metrics: {
          cases_total: 45,
          cases_recoverable: 12,
          cases_recovered: 28,
          cases_expired: 5,
          priority_high: 8,
          priority_medium: 20,
          priority_low: 17,
          proposals_generated: 45,
          proposals_auto_applied: 17,
          proposals_approved: 22,
          proposals_rejected: 6,
        },
        recoverable_cases: [],
        pending_approvals: [],
      },
      cases: [],
      pendingApprovals: [],
      metrics: {
        cases_total: 45,
        cases_recoverable: 12,
        cases_recovered: 28,
        cases_expired: 5,
        priority_high: 8,
        priority_medium: 20,
        priority_low: 17,
        proposals_generated: 45,
        proposals_auto_applied: 17,
        proposals_approved: 22,
        proposals_rejected: 6,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      runDetection: vi.fn(),
      applyCase: mockApplyCase,
      rejectCase: mockRejectCase,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingRecoveryPanel brandId="brand-001" />);
    
    expect(screen.getByText('Casos Detectados')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('Recuperáveis')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('renders recovery cases', () => {
    mockedUseOnboardingRecovery.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v34',
        frozen: false,
        metrics: {
          cases_total: 2,
          cases_recoverable: 2,
          cases_recovered: 0,
          cases_expired: 0,
          priority_high: 1,
          priority_medium: 1,
          priority_low: 0,
          proposals_generated: 2,
          proposals_auto_applied: 0,
          proposals_approved: 0,
          proposals_rejected: 0,
        },
        recoverable_cases: [
          {
            case_id: 'case-001',
            user_id: 'user-001',
            brand_id: 'brand-001',
            reason: 'abandoned_step',
            status: 'recoverable',
            priority: 'high',
            current_step: 5,
            total_steps: 7,
            progress_percentage: 71,
            is_late_stage: true,
            dropoff_at: '2026-03-01T10:00:00Z',
          },
          {
            case_id: 'case-002',
            user_id: 'user-002',
            brand_id: 'brand-001',
            reason: 'timeout',
            status: 'recoverable',
            priority: 'medium',
            current_step: 3,
            total_steps: 7,
            progress_percentage: 43,
            is_late_stage: false,
            dropoff_at: '2026-03-01T08:00:00Z',
          },
        ],
        pending_approvals: [],
      },
      cases: [
        {
          case_id: 'case-001',
          user_id: 'user-001',
          brand_id: 'brand-001',
          reason: 'abandoned_step',
          status: 'recoverable',
          priority: 'high',
          current_step: 5,
          total_steps: 7,
          progress_percentage: 71,
          is_late_stage: true,
          dropoff_at: '2026-03-01T10:00:00Z',
        },
        {
          case_id: 'case-002',
          user_id: 'user-002',
          brand_id: 'brand-001',
          reason: 'timeout',
          status: 'recoverable',
          priority: 'medium',
          current_step: 3,
          total_steps: 7,
          progress_percentage: 43,
          is_late_stage: false,
          dropoff_at: '2026-03-01T08:00:00Z',
        },
      ],
      pendingApprovals: [],
      metrics: {
        cases_total: 2,
        cases_recoverable: 2,
        cases_recovered: 0,
        cases_expired: 0,
        priority_high: 1,
        priority_medium: 1,
        priority_low: 0,
        proposals_generated: 2,
        proposals_auto_applied: 0,
        proposals_approved: 0,
        proposals_rejected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      runDetection: vi.fn(),
      applyCase: mockApplyCase,
      rejectCase: mockRejectCase,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingRecoveryPanel brandId="brand-001" />);
    
    expect(screen.getByText('user-001')).toBeInTheDocument();
    expect(screen.getByText('user-002')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
  });

  it('calls applyCase when apply button is clicked', async () => {
    mockedUseOnboardingRecovery.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v34',
        frozen: false,
        metrics: {
          cases_total: 1,
          cases_recoverable: 1,
          cases_recovered: 0,
          cases_expired: 0,
          priority_high: 0,
          priority_medium: 1,
          priority_low: 0,
          proposals_generated: 1,
          proposals_auto_applied: 0,
          proposals_approved: 0,
          proposals_rejected: 0,
        },
        recoverable_cases: [
          {
            case_id: 'case-001',
            user_id: 'user-001',
            brand_id: 'brand-001',
            reason: 'timeout',
            status: 'recoverable',
            priority: 'medium',
            current_step: 2,
            total_steps: 7,
            progress_percentage: 29,
            is_late_stage: false,
            dropoff_at: '2026-03-01T10:00:00Z',
          },
        ],
        pending_approvals: [],
      },
      cases: [
        {
          case_id: 'case-001',
          user_id: 'user-001',
          brand_id: 'brand-001',
          reason: 'timeout',
          status: 'recoverable',
          priority: 'medium',
          current_step: 2,
          total_steps: 7,
          progress_percentage: 29,
          is_late_stage: false,
          dropoff_at: '2026-03-01T10:00:00Z',
        },
      ],
      pendingApprovals: [],
      metrics: {
        cases_total: 1,
        cases_recoverable: 1,
        cases_recovered: 0,
        cases_expired: 0,
        priority_high: 0,
        priority_medium: 1,
        priority_low: 0,
        proposals_generated: 1,
        proposals_auto_applied: 0,
        proposals_approved: 0,
        proposals_rejected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      runDetection: vi.fn(),
      applyCase: mockApplyCase,
      rejectCase: mockRejectCase,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingRecoveryPanel brandId="brand-001" />);
    
    const applyButton = screen.getByText('Aplicar');
    fireEvent.click(applyButton);
    
    await waitFor(() => {
      expect(mockApplyCase).toHaveBeenCalledWith('case-001', 'current-user');
    });
  });

  it('calls freeze when freeze button is clicked', async () => {
    mockedUseOnboardingRecovery.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v34',
        frozen: false,
        metrics: {
          cases_total: 0,
          cases_recoverable: 0,
          cases_recovered: 0,
          cases_expired: 0,
          priority_high: 0,
          priority_medium: 0,
          priority_low: 0,
          proposals_generated: 0,
          proposals_auto_applied: 0,
          proposals_approved: 0,
          proposals_rejected: 0,
        },
        recoverable_cases: [],
        pending_approvals: [],
      },
      cases: [],
      pendingApprovals: [],
      metrics: {
        cases_total: 0,
        cases_recoverable: 0,
        cases_recovered: 0,
        cases_expired: 0,
        priority_high: 0,
        priority_medium: 0,
        priority_low: 0,
        proposals_generated: 0,
        proposals_auto_applied: 0,
        proposals_approved: 0,
        proposals_rejected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      runDetection: vi.fn(),
      applyCase: mockApplyCase,
      rejectCase: mockRejectCase,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingRecoveryPanel brandId="brand-001" />);
    
    const freezeButton = screen.getByText('Congelar');
    fireEvent.click(freezeButton);
    
    await waitFor(() => {
      expect(mockFreeze).toHaveBeenCalledWith('current-user', 'Emergency freeze from UI');
    });
  });

  it('displays frozen state correctly', () => {
    mockedUseOnboardingRecovery.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'frozen',
        version: 'v34',
        frozen: true,
        metrics: {
          cases_total: 0,
          cases_recoverable: 0,
          cases_recovered: 0,
          cases_expired: 0,
          priority_high: 0,
          priority_medium: 0,
          priority_low: 0,
          proposals_generated: 0,
          proposals_auto_applied: 0,
          proposals_approved: 0,
          proposals_rejected: 0,
        },
        recoverable_cases: [],
        pending_approvals: [],
      },
      cases: [],
      pendingApprovals: [],
      metrics: {
        cases_total: 0,
        cases_recoverable: 0,
        cases_recovered: 0,
        cases_expired: 0,
        priority_high: 0,
        priority_medium: 0,
        priority_low: 0,
        proposals_generated: 0,
        proposals_auto_applied: 0,
        proposals_approved: 0,
        proposals_rejected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      runDetection: vi.fn(),
      applyCase: mockApplyCase,
      rejectCase: mockRejectCase,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingRecoveryPanel brandId="brand-001" />);
    
    expect(screen.getByText('Congelado')).toBeInTheDocument();
  });

  it('renders pending approvals section', () => {
    mockedUseOnboardingRecovery.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v34',
        frozen: false,
        metrics: {
          cases_total: 1,
          cases_recoverable: 1,
          cases_recovered: 0,
          cases_expired: 0,
          priority_high: 1,
          priority_medium: 0,
          priority_low: 0,
          proposals_generated: 1,
          proposals_auto_applied: 0,
          proposals_approved: 0,
          proposals_rejected: 0,
        },
        recoverable_cases: [],
        pending_approvals: [
          {
            case_id: 'case-001',
            user_id: 'user-001',
            brand_id: 'brand-001',
            strategy: {
              strategy: 'guided_resume',
              strategy_type: 'high_touch',
              reason: 'Error recovery needs guidance',
              expected_impact: 0.45,
            },
            resume_path: {
              entry_point: 'step_4',
              prefill_data: {},
              skip_steps: [],
              highlight_changes: ['issues_resolved'],
              estimated_completion_minutes: 8,
              friction_score: 0.3,
            },
            requires_approval: true,
            priority: 'high',
            reason: 'error',
            created_at: '2026-03-01T12:00:00Z',
          },
        ],
      },
      cases: [],
      pendingApprovals: [
        {
          case_id: 'case-001',
          user_id: 'user-001',
          brand_id: 'brand-001',
          strategy: {
            strategy: 'guided_resume',
            strategy_type: 'high_touch',
            reason: 'Error recovery needs guidance',
            expected_impact: 0.45,
          },
          resume_path: {
            entry_point: 'step_4',
            prefill_data: {},
            skip_steps: [],
            highlight_changes: ['issues_resolved'],
            estimated_completion_minutes: 8,
            friction_score: 0.3,
          },
          requires_approval: true,
          priority: 'high',
          reason: 'error',
          created_at: '2026-03-01T12:00:00Z',
        },
      ],
      metrics: {
        cases_total: 1,
        cases_recoverable: 1,
        cases_recovered: 0,
        cases_expired: 0,
        priority_high: 1,
        priority_medium: 0,
        priority_low: 0,
        proposals_generated: 1,
        proposals_auto_applied: 0,
        proposals_approved: 0,
        proposals_rejected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      runDetection: vi.fn(),
      applyCase: mockApplyCase,
      rejectCase: mockRejectCase,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingRecoveryPanel brandId="brand-001" />);
    
    expect(screen.getByText('Pendentes de Aprovação (1)')).toBeInTheDocument();
    expect(screen.getByText('user-001')).toBeInTheDocument();
    expect(screen.getByText('Resumo Guiado')).toBeInTheDocument();
  });
});
