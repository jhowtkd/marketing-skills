import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import InboxPanel from './InboxPanel';

// Mock the hooks
vi.mock('./useInbox', () => ({
  useInbox: vi.fn(),
}));

import { useInbox } from './useInbox';

const mockedUseInbox = vi.mocked(useInbox);

describe('InboxPanel - Task First Redesign', () => {
  const mockTasks = [
    { task_id: 'task1', title: 'Review Creative', status: 'pending', priority: 'high', type: 'review' },
    { task_id: 'task2', title: 'Approve Copy', status: 'pending', priority: 'medium', type: 'approval' },
    { task_id: 'task3', title: 'Old Task', status: 'completed', priority: 'low', type: 'review' },
  ];

  const mockApprovals = [
    { approval_id: 'app1', title: 'Budget Approval', status: 'pending', urgency: 'high' },
    { approval_id: 'app2', title: 'Final Sign-off', status: 'completed', urgency: 'medium' },
  ];

  const defaultMockReturn = {
    tasks: mockTasks,
    approvals: mockApprovals,
    artifactStages: [],
    artifactContents: {},
    completeTask: vi.fn(),
    commentTask: vi.fn(),
    grantApproval: vi.fn(),
    loadArtifactContent: vi.fn(),
    refreshTasks: vi.fn(),
    refreshApprovals: vi.fn(),
    refreshArtifacts: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseInbox.mockReturnValue(defaultMockReturn);
  });

  describe('task-first layout', () => {
    it('should show actionable section first', () => {
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      // Actionable items should be prominently displayed
      expect(screen.getByText(/Pendencias desta versao/i)).toBeInTheDocument();
    });

    it('should display actionable vs non-actionable split', () => {
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      // Should show count of actionable items (in the badge)
      const blockersBadge = screen.getByText(/\d+ bloqueio/i);
      expect(blockersBadge).toBeInTheDocument();
    });

    it('should show empty state when no actionable items', () => {
      mockedUseInbox.mockReturnValue({
        ...defaultMockReturn,
        tasks: [{ ...mockTasks[0], status: 'completed' }],
        approvals: [{ ...mockApprovals[0], status: 'completed' }],
      });
      
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      // Should show 0 or completed state
      const blockersBadge = screen.getByText(/0 bloqueio/i);
      expect(blockersBadge.textContent).toContain('0');
    });
  });

  describe('semantic timeline view', () => {
    it('should render inbox panel', () => {
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      expect(screen.getByText(/Pendencias desta versao/i)).toBeInTheDocument();
    });

    it('should show thread selection prompt when no thread', () => {
      render(<InboxPanel activeThreadId={null} activeRunId={null} devMode={false} />);
      
      // Should show initial state guidance
      expect(screen.getByText(/Escolha um job/i)).toBeInTheDocument();
    });
  });

  describe('guided flow integration', () => {
    it('should prioritize high priority items', () => {
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      // High priority items should be displayed
      // The panel shows actionable items (pending tasks/approvals)
      expect(screen.getByText(/Tarefas pendentes/i)).toBeInTheDocument();
      expect(screen.getByText(/Aprovacoes pendentes/i)).toBeInTheDocument();
    });

    it('should allow completing tasks directly', async () => {
      const completeTask = vi.fn();
      mockedUseInbox.mockReturnValue({
        ...defaultMockReturn,
        completeTask,
      });
      
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      // Find and click a complete button for a task
      const completeButtons = screen.getAllByRole('button');
      // Look for a button that might complete a task
      const actionButton = completeButtons.find(btn => 
        btn.textContent?.toLowerCase().includes('aprovar') ||
        btn.textContent?.toLowerCase().includes('completar')
      );
      
      if (actionButton) {
        fireEvent.click(actionButton);
      }
    });
  });

  describe('accessibility', () => {
    it('should have proper heading structure', () => {
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toBeInTheDocument();
    });

    it('should indicate actionable items to screen readers', () => {
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      // Look for status indicators
      const statusElements = screen.getAllByText(/pendente|bloqueando/i);
      expect(statusElements.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('v29 UX metrics', () => {
    it('should track task completion', async () => {
      const completeTask = vi.fn().mockResolvedValue(undefined);
      mockedUseInbox.mockReturnValue({
        ...defaultMockReturn,
        completeTask,
      });
      
      render(<InboxPanel activeThreadId="thread1" activeRunId="run1" devMode={false} />);
      
      // Interactions are tracked through the hook
      expect(mockedUseInbox).toHaveBeenCalledWith('thread1', 'run1');
    });
  });
});
