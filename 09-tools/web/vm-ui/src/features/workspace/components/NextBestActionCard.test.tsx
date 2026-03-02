import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import NextBestActionCard from './NextBestActionCard';

describe('NextBestActionCard', () => {
  const mockActions = [
    {
      id: 'create_campaign',
      label: 'Create Campaign',
      description: 'Start a new marketing campaign',
      priority: 'high' as const,
      icon: 'plus',
    },
    {
      id: 'review_assets',
      label: 'Review Assets',
      description: 'Check pending creative assets',
      priority: 'medium' as const,
      icon: 'eye',
    },
    {
      id: 'publish_content',
      label: 'Publish Content',
      description: 'Schedule content for publication',
      priority: 'low' as const,
      icon: 'send',
    },
  ];

  const defaultProps = {
    actions: mockActions,
    recommendedActionId: 'create_campaign',
    onActionClick: vi.fn(),
    title: 'Recommended Next Step',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render the card with title', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      expect(screen.getByText('Recommended Next Step')).toBeInTheDocument();
    });

    it('should render all actions', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      expect(screen.getByText('Create Campaign')).toBeInTheDocument();
      expect(screen.getByText('Review Assets')).toBeInTheDocument();
      expect(screen.getByText('Publish Content')).toBeInTheDocument();
    });

    it('should render action descriptions', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      expect(screen.getByText('Start a new marketing campaign')).toBeInTheDocument();
      expect(screen.getByText('Check pending creative assets')).toBeInTheDocument();
    });

    it('should highlight recommended action', () => {
      render(<NextBestActionCard {...defaultProps} recommendedActionId="create_campaign" />);
      
      const recommendedButton = screen.getByText('Create Campaign').closest('[data-recommended="true"]');
      expect(recommendedButton).toBeInTheDocument();
    });

    it('should show recommended badge on primary action', () => {
      render(<NextBestActionCard {...defaultProps} recommendedActionId="create_campaign" />);
      
      expect(screen.getByText('Recommended')).toBeInTheDocument();
    });
  });

  describe('interaction', () => {
    it('should call onActionClick when action is clicked', () => {
      const onActionClick = vi.fn();
      render(<NextBestActionCard {...defaultProps} onActionClick={onActionClick} />);
      
      fireEvent.click(screen.getByText('Create Campaign'));
      
      expect(onActionClick).toHaveBeenCalledWith('create_campaign');
    });

    it('should call onActionClick with correct action id', () => {
      const onActionClick = vi.fn();
      render(<NextBestActionCard {...defaultProps} onActionClick={onActionClick} />);
      
      fireEvent.click(screen.getByText('Review Assets'));
      
      expect(onActionClick).toHaveBeenCalledWith('review_assets');
    });

    it('should render primary CTA for recommended action', () => {
      render(<NextBestActionCard {...defaultProps} recommendedActionId="create_campaign" />);
      
      const primaryButton = screen.getByRole('button', { name: /create campaign/i });
      expect(primaryButton).toHaveAttribute('data-primary', 'true');
    });
  });

  describe('states', () => {
    it('should show loading state', () => {
      render(<NextBestActionCard {...defaultProps} isLoading />);
      
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('should show empty state when no actions', () => {
      render(<NextBestActionCard {...defaultProps} actions={[]} />);
      
      expect(screen.getByText('No actions available')).toBeInTheDocument();
    });

    it('should disable actions when disabled prop is true', () => {
      render(<NextBestActionCard {...defaultProps} disabled />);
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe('priority styling', () => {
    it('should apply high priority styling', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      const highPriorityAction = screen.getByText('Create Campaign').closest('[data-priority="high"]');
      expect(highPriorityAction).toBeInTheDocument();
    });

    it('should apply medium priority styling', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      const mediumPriorityAction = screen.getByText('Review Assets').closest('[data-priority="medium"]');
      expect(mediumPriorityAction).toBeInTheDocument();
    });

    it('should apply low priority styling', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      const lowPriorityAction = screen.getByText('Publish Content').closest('[data-priority="low"]');
      expect(lowPriorityAction).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have proper heading structure', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      const heading = screen.getByRole('heading', { level: 3 });
      expect(heading).toHaveTextContent('Recommended Next Step');
    });

    it('should indicate recommended action to screen readers', () => {
      render(<NextBestActionCard {...defaultProps} recommendedActionId="create_campaign" />);
      
      const recommendedButton = screen.getByLabelText(/create campaign.*recommended/i);
      expect(recommendedButton).toBeInTheDocument();
    });

    it('should have accessible buttons', () => {
      render(<NextBestActionCard {...defaultProps} />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
      buttons.forEach(button => {
        expect(button).toHaveAttribute('aria-label');
      });
    });
  });

  describe('v29 UX integration', () => {
    it('should track action selection for telemetry', () => {
      const onActionClick = vi.fn();
      const onTrackSelect = vi.fn();
      
      render(
        <NextBestActionCard 
          {...defaultProps} 
          onActionClick={onActionClick}
          onTrackSelect={onTrackSelect}
        />
      );
      
      fireEvent.click(screen.getByText('Create Campaign'));
      
      expect(onTrackSelect).toHaveBeenCalledWith({
        actionId: 'create_campaign',
        isRecommended: true,
        timestamp: expect.any(Number),
      });
    });

    it('should track time to first action impression', () => {
      vi.useFakeTimers();
      const onTrackImpression = vi.fn();
      
      render(
        <NextBestActionCard 
          {...defaultProps} 
          onTrackImpression={onTrackImpression}
        />
      );
      
      vi.advanceTimersByTime(100);
      
      expect(onTrackImpression).toHaveBeenCalledWith({
        cardId: 'next-best-action',
        timeToImpression: expect.any(Number),
      });
      
      vi.useRealTimers();
    });
  });
});
