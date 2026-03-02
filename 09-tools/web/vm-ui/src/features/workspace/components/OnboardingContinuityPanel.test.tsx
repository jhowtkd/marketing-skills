/**
 * OnboardingContinuityPanel Tests (v35)
 * 
 * Vitest tests for the Onboarding Continuity Panel component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock the hook
vi.mock('../hooks/useOnboardingContinuity', () => ({
  useOnboardingContinuity: vi.fn(),
}));

import { OnboardingContinuityPanel } from './OnboardingContinuityPanel';
import { useOnboardingContinuity } from '../hooks/useOnboardingContinuity';

const mockedUseOnboardingContinuity = vi.mocked(useOnboardingContinuity);

describe('OnboardingContinuityPanel', () => {
  const mockRefresh = vi.fn();
  const mockResumeHandoff = vi.fn();
  const mockFreeze = vi.fn();
  const mockRollback = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockedUseOnboardingContinuity.mockReturnValue({
      status: null,
      handoffs: [],
      metrics: null,
      loading: true,
      error: null,
      refresh: mockRefresh,
      createCheckpoint: vi.fn(),
      resumeHandoff: mockResumeHandoff,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingContinuityPanel brandId="brand-001" />);
    
    expect(screen.getByText('Atualizando...')).toBeInTheDocument();
  });

  it('renders metrics when loaded', () => {
    mockedUseOnboardingContinuity.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v35',
        frozen: false,
        metrics: {
          checkpoints_created: 128,
          checkpoints_committed: 112,
          checkpoints_rolled_back: 8,
          bundles_created: 64,
          bundles_pending: 5,
          bundles_completed: 52,
          bundles_failed: 4,
          resumes_auto_applied: 42,
          resumes_needing_approval: 8,
          context_loss_events: 7,
          conflicts_detected: 8,
        },
        recent_handoffs: [],
      },
      handoffs: [],
      metrics: {
        checkpoints_created: 128,
        checkpoints_committed: 112,
        checkpoints_rolled_back: 8,
        bundles_created: 64,
        bundles_pending: 5,
        bundles_completed: 52,
        bundles_failed: 4,
        resumes_auto_applied: 42,
        resumes_needing_approval: 8,
        context_loss_events: 7,
        conflicts_detected: 8,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      createCheckpoint: vi.fn(),
      resumeHandoff: mockResumeHandoff,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingContinuityPanel brandId="brand-001" />);
    
    expect(screen.getByText('Checkpoints Criados')).toBeInTheDocument();
    expect(screen.getByText('128')).toBeInTheDocument();
    expect(screen.getByText('Handoffs Completados')).toBeInTheDocument();
    expect(screen.getByText('52')).toBeInTheDocument();
  });

  it('renders handoffs list', () => {
    mockedUseOnboardingContinuity.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v35',
        frozen: false,
        metrics: {
          checkpoints_created: 10,
          checkpoints_committed: 8,
          checkpoints_rolled_back: 0,
          bundles_created: 3,
          bundles_pending: 1,
          bundles_completed: 2,
          bundles_failed: 0,
          resumes_auto_applied: 2,
          resumes_needing_approval: 0,
          context_loss_events: 0,
          conflicts_detected: 0,
        },
        recent_handoffs: [
          {
            bundle_id: 'bundle-001',
            user_id: 'user-001',
            brand_id: 'brand-001',
            source_session: 'session-abc',
            target_session: 'session-xyz',
            checkpoint_ids: ['cp-001'],
            context_payload: {
              current_step: 'step_3',
              current_step_number: 3,
              completed_steps: ['step_1', 'step_2'],
              form_data: { company: 'Acme' },
              version: 3,
            },
            source_priority: 'session',
            status: 'pending',
            created_at: '2026-03-01T10:00:00Z',
          },
          {
            bundle_id: 'bundle-002',
            user_id: 'user-002',
            brand_id: 'brand-001',
            source_session: 'session-def',
            target_session: 'session-uvw',
            checkpoint_ids: ['cp-002'],
            context_payload: {
              current_step: 'step_5',
              current_step_number: 5,
              completed_steps: ['step_1', 'step_2', 'step_3', 'step_4'],
              form_data: { company: 'TechCorp' },
              version: 5,
            },
            source_priority: 'recovery',
            status: 'completed',
            created_at: '2026-03-01T09:00:00Z',
            completed_at: '2026-03-01T09:05:00Z',
          },
        ],
      },
      handoffs: [
        {
          bundle_id: 'bundle-001',
          user_id: 'user-001',
          brand_id: 'brand-001',
          source_session: 'session-abc',
          target_session: 'session-xyz',
          checkpoint_ids: ['cp-001'],
          context_payload: {
            current_step: 'step_3',
            current_step_number: 3,
            completed_steps: ['step_1', 'step_2'],
            form_data: { company: 'Acme' },
            version: 3,
          },
          source_priority: 'session',
          status: 'pending',
          created_at: '2026-03-01T10:00:00Z',
        },
        {
          bundle_id: 'bundle-002',
          user_id: 'user-002',
          brand_id: 'brand-001',
          source_session: 'session-def',
          target_session: 'session-uvw',
          checkpoint_ids: ['cp-002'],
          context_payload: {
            current_step: 'step_5',
            current_step_number: 5,
            completed_steps: ['step_1', 'step_2', 'step_3', 'step_4'],
            form_data: { company: 'TechCorp' },
            version: 5,
          },
          source_priority: 'recovery',
          status: 'completed',
          created_at: '2026-03-01T09:00:00Z',
          completed_at: '2026-03-01T09:05:00Z',
        },
      ],
      metrics: {
        checkpoints_created: 10,
        checkpoints_committed: 8,
        checkpoints_rolled_back: 0,
        bundles_created: 3,
        bundles_pending: 1,
        bundles_completed: 2,
        bundles_failed: 0,
        resumes_auto_applied: 2,
        resumes_needing_approval: 0,
        context_loss_events: 0,
        conflicts_detected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      createCheckpoint: vi.fn(),
      resumeHandoff: mockResumeHandoff,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingContinuityPanel brandId="brand-001" />);
    
    expect(screen.getByText('user-001')).toBeInTheDocument();
    expect(screen.getByText('user-002')).toBeInTheDocument();
    expect(screen.getByText('PENDENTE')).toBeInTheDocument();
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    expect(screen.getByText('Retomar')).toBeInTheDocument();
  });

  it('calls resumeHandoff when resume button is clicked', async () => {
    mockedUseOnboardingContinuity.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v35',
        frozen: false,
        metrics: {
          checkpoints_created: 5,
          checkpoints_committed: 4,
          checkpoints_rolled_back: 0,
          bundles_created: 2,
          bundles_pending: 1,
          bundles_completed: 1,
          bundles_failed: 0,
          resumes_auto_applied: 1,
          resumes_needing_approval: 0,
          context_loss_events: 0,
          conflicts_detected: 0,
        },
        recent_handoffs: [
          {
            bundle_id: 'bundle-001',
            user_id: 'user-001',
            brand_id: 'brand-001',
            source_session: 'session-abc',
            target_session: 'session-xyz',
            checkpoint_ids: ['cp-001'],
            context_payload: { current_step: 'step_3' },
            source_priority: 'session',
            status: 'pending',
            created_at: '2026-03-01T10:00:00Z',
          },
        ],
      },
      handoffs: [
        {
          bundle_id: 'bundle-001',
          user_id: 'user-001',
          brand_id: 'brand-001',
          source_session: 'session-abc',
          target_session: 'session-xyz',
          checkpoint_ids: ['cp-001'],
          context_payload: { current_step: 'step_3' },
          source_priority: 'session',
          status: 'pending',
          created_at: '2026-03-01T10:00:00Z',
        },
      ],
      metrics: {
        checkpoints_created: 5,
        checkpoints_committed: 4,
        checkpoints_rolled_back: 0,
        bundles_created: 2,
        bundles_pending: 1,
        bundles_completed: 1,
        bundles_failed: 0,
        resumes_auto_applied: 1,
        resumes_needing_approval: 0,
        context_loss_events: 0,
        conflicts_detected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      createCheckpoint: vi.fn(),
      resumeHandoff: mockResumeHandoff,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingContinuityPanel brandId="brand-001" />);
    
    const resumeButton = screen.getByText('Retomar');
    fireEvent.click(resumeButton);
    
    await waitFor(() => {
      expect(mockResumeHandoff).toHaveBeenCalledWith('bundle-001', expect.any(String), 'current-user');
    });
  });

  it('calls freeze when freeze button is clicked', async () => {
    mockedUseOnboardingContinuity.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v35',
        frozen: false,
        metrics: {
          checkpoints_created: 0,
          checkpoints_committed: 0,
          checkpoints_rolled_back: 0,
          bundles_created: 0,
          bundles_pending: 0,
          bundles_completed: 0,
          bundles_failed: 0,
          resumes_auto_applied: 0,
          resumes_needing_approval: 0,
          context_loss_events: 0,
          conflicts_detected: 0,
        },
        recent_handoffs: [],
      },
      handoffs: [],
      metrics: {
        checkpoints_created: 0,
        checkpoints_committed: 0,
        checkpoints_rolled_back: 0,
        bundles_created: 0,
        bundles_pending: 0,
        bundles_completed: 0,
        bundles_failed: 0,
        resumes_auto_applied: 0,
        resumes_needing_approval: 0,
        context_loss_events: 0,
        conflicts_detected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      createCheckpoint: vi.fn(),
      resumeHandoff: mockResumeHandoff,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingContinuityPanel brandId="brand-001" />);
    
    const freezeButton = screen.getByText('Congelar');
    fireEvent.click(freezeButton);
    
    await waitFor(() => {
      expect(mockFreeze).toHaveBeenCalledWith('current-user', 'Emergency freeze from UI');
    });
  });

  it('displays frozen state correctly', () => {
    mockedUseOnboardingContinuity.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'frozen',
        version: 'v35',
        frozen: true,
        metrics: {
          checkpoints_created: 0,
          checkpoints_committed: 0,
          checkpoints_rolled_back: 0,
          bundles_created: 0,
          bundles_pending: 0,
          bundles_completed: 0,
          bundles_failed: 0,
          resumes_auto_applied: 0,
          resumes_needing_approval: 0,
          context_loss_events: 0,
          conflicts_detected: 0,
        },
        recent_handoffs: [],
      },
      handoffs: [],
      metrics: {
        checkpoints_created: 0,
        checkpoints_committed: 0,
        checkpoints_rolled_back: 0,
        bundles_created: 0,
        bundles_pending: 0,
        bundles_completed: 0,
        bundles_failed: 0,
        resumes_auto_applied: 0,
        resumes_needing_approval: 0,
        context_loss_events: 0,
        conflicts_detected: 0,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      createCheckpoint: vi.fn(),
      resumeHandoff: mockResumeHandoff,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingContinuityPanel brandId="brand-001" />);
    
    expect(screen.getByText('Congelado')).toBeInTheDocument();
  });

  it('shows conflict and context loss metrics', () => {
    mockedUseOnboardingContinuity.mockReturnValue({
      status: {
        brand_id: 'brand-001',
        state: 'active',
        version: 'v35',
        frozen: false,
        metrics: {
          checkpoints_created: 50,
          checkpoints_committed: 45,
          checkpoints_rolled_back: 2,
          bundles_created: 20,
          bundles_pending: 3,
          bundles_completed: 15,
          bundles_failed: 2,
          resumes_auto_applied: 12,
          resumes_needing_approval: 3,
          context_loss_events: 5,
          conflicts_detected: 8,
        },
        recent_handoffs: [],
      },
      handoffs: [],
      metrics: {
        checkpoints_created: 50,
        checkpoints_committed: 45,
        checkpoints_rolled_back: 2,
        bundles_created: 20,
        bundles_pending: 3,
        bundles_completed: 15,
        bundles_failed: 2,
        resumes_auto_applied: 12,
        resumes_needing_approval: 3,
        context_loss_events: 5,
        conflicts_detected: 8,
      },
      loading: false,
      error: null,
      refresh: mockRefresh,
      createCheckpoint: vi.fn(),
      resumeHandoff: mockResumeHandoff,
      freeze: mockFreeze,
      rollback: mockRollback,
    });

    render(<OnboardingContinuityPanel brandId="brand-001" />);
    
    expect(screen.getByText('Conflitos & Perdas')).toBeInTheDocument();
    expect(screen.getByText('Conflitos Detectados')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('Perdas de Contexto')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});
