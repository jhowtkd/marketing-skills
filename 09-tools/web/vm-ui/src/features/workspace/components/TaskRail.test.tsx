import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TaskRail from './TaskRail';

describe('TaskRail', () => {
  const mockTasks = [
    { id: 'studio', label: 'Studio', icon: 'edit', order: 1 },
    { id: 'inbox', label: 'Inbox', icon: 'inbox', order: 2 },
    { id: 'timeline', label: 'Timeline', icon: 'clock', order: 3 },
    { id: 'settings', label: 'Settings', icon: 'settings', order: 4 },
  ];

  const defaultProps = {
    tasks: mockTasks,
    activeTaskId: 'studio',
    completedTaskIds: [],
    onTaskSelect: vi.fn(),
    onTaskComplete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render all task items', () => {
      render(<TaskRail {...defaultProps} />);
      
      expect(screen.getByText('Studio')).toBeInTheDocument();
      expect(screen.getByText('Inbox')).toBeInTheDocument();
      expect(screen.getByText('Timeline')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('should render tasks in order', () => {
      render(<TaskRail {...defaultProps} />);
      
      // Get task items specifically (not complete buttons)
      const taskContainer = screen.getByLabelText('Task navigation');
      const taskItems = taskContainer.querySelectorAll('[role="button"]');
      
      expect(taskItems[0]).toHaveTextContent('Studio');
      expect(taskItems[1]).toHaveTextContent('Inbox');
      expect(taskItems[2]).toHaveTextContent('Timeline');
      expect(taskItems[3]).toHaveTextContent('Settings');
    });

    it('should mark active task visually', () => {
      render(<TaskRail {...defaultProps} activeTaskId="inbox" />);
      
      const inboxButton = screen.getByText('Inbox').closest('[role="button"]') || screen.getByText('Inbox').parentElement;
      expect(inboxButton).toHaveAttribute('data-active', 'true');
    });

    it('should mark completed tasks visually', () => {
      render(<TaskRail {...defaultProps} completedTaskIds={['studio', 'inbox']} />);
      
      const studioButton = screen.getByText('Studio').closest('[role="button"]') || screen.getByText('Studio').parentElement;
      expect(studioButton).toHaveAttribute('data-completed', 'true');
    });
  });

  describe('navigation', () => {
    it('should call onTaskSelect when task is clicked', () => {
      const onTaskSelect = vi.fn();
      render(<TaskRail {...defaultProps} onTaskSelect={onTaskSelect} />);
      
      fireEvent.click(screen.getByText('Inbox'));
      
      expect(onTaskSelect).toHaveBeenCalledWith('inbox');
      expect(onTaskSelect).toHaveBeenCalledTimes(1);
    });

    it('should allow navigation to any task (task-first approach)', () => {
      const onTaskSelect = vi.fn();
      render(
        <TaskRail 
          {...defaultProps} 
          onTaskSelect={onTaskSelect}
          activeTaskId="studio"
          completedTaskIds={[]}
        />
      );
      
      // Can click on Settings even if no previous tasks completed
      fireEvent.click(screen.getByText('Settings'));
      
      expect(onTaskSelect).toHaveBeenCalledWith('settings');
    });

    it('should not call onTaskSelect when clicking active task', () => {
      const onTaskSelect = vi.fn();
      render(<TaskRail {...defaultProps} onTaskSelect={onTaskSelect} />);
      
      fireEvent.click(screen.getByText('Studio'));
      
      expect(onTaskSelect).not.toHaveBeenCalled();
    });
  });

  describe('step progress', () => {
    it('should show progress indicator for each step', () => {
      render(<TaskRail {...defaultProps} />);
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
    });

    it('should calculate progress percentage correctly', () => {
      render(
        <TaskRail 
          {...defaultProps} 
          completedTaskIds={['studio', 'inbox']}
        />
      );
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');
    });

    it('should show 0% progress when no tasks completed', () => {
      render(<TaskRail {...defaultProps} completedTaskIds={[]} />);
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
    });

    it('should show 100% progress when all tasks completed', () => {
      render(
        <TaskRail 
          {...defaultProps} 
          completedTaskIds={['studio', 'inbox', 'timeline', 'settings']}
        />
      );
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '100');
    });

    it('should display step numbers', () => {
      render(<TaskRail {...defaultProps} />);
      
      // Each task should show its step number
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('4')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have proper ARIA labels for navigation', () => {
      render(<TaskRail {...defaultProps} />);
      
      expect(screen.getByLabelText('Task navigation')).toBeInTheDocument();
    });

    it('should indicate current step to screen readers', () => {
      render(<TaskRail {...defaultProps} activeTaskId="inbox" />);
      
      const inboxButton = screen.getByLabelText('Inbox (current step)');
      expect(inboxButton).toBeInTheDocument();
    });

    it('should indicate completed steps to screen readers', () => {
      render(<TaskRail {...defaultProps} completedTaskIds={['studio']} />);
      
      const studioButton = screen.getByLabelText(/Studio.*completed/);
      expect(studioButton).toBeInTheDocument();
    });
  });

  describe('guided flow integration', () => {
    it('should show next recommended task', () => {
      render(
        <TaskRail 
          {...defaultProps} 
          activeTaskId="studio"
          completedTaskIds={['studio']}
          nextRecommendedTaskId="inbox"
        />
      );
      
      expect(screen.getByText('Next')).toBeInTheDocument();
    });

    it('should highlight next recommended task', () => {
      render(
        <TaskRail 
          {...defaultProps} 
          activeTaskId="studio"
          completedTaskIds={['studio']}
          nextRecommendedTaskId="inbox"
        />
      );
      
      const inboxItem = screen.getByText('Inbox').closest('[data-recommended="true"]');
      expect(inboxItem).toBeInTheDocument();
    });

    it('should call onTaskComplete when task is marked complete', () => {
      const onTaskComplete = vi.fn();
      render(<TaskRail {...defaultProps} onTaskComplete={onTaskComplete} />);
      
      const completeButton = screen.getByLabelText('Mark Studio as complete');
      fireEvent.click(completeButton);
      
      expect(onTaskComplete).toHaveBeenCalledWith('studio');
    });
  });

  describe('v29 UX metrics tracking', () => {
    it('should track navigation events for UX telemetry', () => {
      const onTaskSelect = vi.fn();
      const onNavigate = vi.fn();
      
      const { rerender } = render(
        <TaskRail 
          {...defaultProps} 
          onTaskSelect={onTaskSelect}
          onNavigate={onNavigate}
        />
      );
      
      // Click triggers onTaskSelect
      fireEvent.click(screen.getByText('Inbox'));
      expect(onTaskSelect).toHaveBeenCalledWith('inbox');
      
      // Simulate parent updating activeTaskId (navigation happens in useEffect)
      rerender(
        <TaskRail 
          {...defaultProps} 
          activeTaskId="inbox"
          onTaskSelect={onTaskSelect}
          onNavigate={onNavigate}
        />
      );
      
      expect(onNavigate).toHaveBeenCalledWith({
        from: 'studio',
        to: 'inbox',
        timestamp: expect.any(Number),
      });
    });

    it('should track time spent on each task', () => {
      vi.useFakeTimers();
      const onTaskTimeUpdate = vi.fn();
      
      const { rerender } = render(
        <TaskRail 
          {...defaultProps} 
          onTaskTimeUpdate={onTaskTimeUpdate}
        />
      );
      
      // Simulate 5 seconds on studio
      vi.advanceTimersByTime(5000);
      
      // Navigate to inbox
      rerender(
        <TaskRail 
          {...defaultProps} 
          activeTaskId="inbox"
          onTaskTimeUpdate={onTaskTimeUpdate}
        />
      );
      
      expect(onTaskTimeUpdate).toHaveBeenCalledWith({
        taskId: 'studio',
        timeSpent: expect.any(Number),
      });
      
      vi.useRealTimers();
    });
  });
});
