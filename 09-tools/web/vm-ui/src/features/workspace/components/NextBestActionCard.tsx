import { useEffect, useRef } from 'react';

export interface Action {
  id: string;
  label: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  icon: string;
}

export interface ActionSelectionEvent {
  actionId: string;
  isRecommended: boolean;
  timestamp: number;
}

export interface ImpressionEvent {
  cardId: string;
  timeToImpression: number;
}

interface NextBestActionCardProps {
  actions: Action[];
  recommendedActionId?: string;
  title?: string;
  isLoading?: boolean;
  disabled?: boolean;
  onActionClick: (actionId: string) => void;
  onTrackSelect?: (event: ActionSelectionEvent) => void;
  onTrackImpression?: (event: ImpressionEvent) => void;
}

export default function NextBestActionCard({
  actions,
  recommendedActionId,
  title = 'Recommended Next Step',
  isLoading = false,
  disabled = false,
  onActionClick,
  onTrackSelect,
  onTrackImpression,
}: NextBestActionCardProps) {
  const mountTimeRef = useRef<number>(Date.now());
  const hasTrackedImpression = useRef<boolean>(false);

  // Track impression on mount
  useEffect(() => {
    if (!hasTrackedImpression.current && onTrackImpression) {
      const timeToImpression = Date.now() - mountTimeRef.current;
      onTrackImpression({
        cardId: 'next-best-action',
        timeToImpression,
      });
      hasTrackedImpression.current = true;
    }
  }, [onTrackImpression]);

  const handleActionClick = (action: Action) => {
    const isRecommended = action.id === recommendedActionId;
    
    if (onTrackSelect) {
      onTrackSelect({
        actionId: action.id,
        isRecommended,
        timestamp: Date.now(),
      });
    }
    
    onActionClick(action.id);
  };

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'plus':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        );
      case 'eye':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        );
      case 'send':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        );
      case 'edit':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        );
      case 'check':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" strokeWidth={2} />
          </svg>
        );
    }
  };

  const getPriorityStyles = (priority: string, isRecommended: boolean) => {
    if (isRecommended) {
      return {
        card: 'bg-gradient-to-r from-[var(--vm-primary)] to-[var(--vm-primary-strong)] text-white shadow-lg scale-[1.02]',
        icon: 'bg-white/20 text-white',
        badge: 'bg-white text-[var(--vm-primary)]',
      };
    }

    switch (priority) {
      case 'high':
        return {
          card: 'bg-red-50 border-red-200 hover:bg-red-100',
          icon: 'bg-red-100 text-red-600',
          badge: 'bg-red-100 text-red-700',
        };
      case 'medium':
        return {
          card: 'bg-amber-50 border-amber-200 hover:bg-amber-100',
          icon: 'bg-amber-100 text-amber-600',
          badge: 'bg-amber-100 text-amber-700',
        };
      case 'low':
        return {
          card: 'bg-slate-50 border-slate-200 hover:bg-slate-100',
          icon: 'bg-slate-100 text-slate-600',
          badge: 'bg-slate-100 text-slate-700',
        };
      default:
        return {
          card: 'bg-white border-slate-200 hover:bg-slate-50',
          icon: 'bg-slate-100 text-slate-600',
          badge: 'bg-slate-100 text-slate-700',
        };
    }
  };

  if (isLoading) {
    return (
      <div 
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        role="status"
        aria-label="Loading next best actions"
      >
        <div className="flex items-center justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-3 border-slate-200 border-t-[var(--vm-primary)]" />
        </div>
        <p className="text-center text-sm text-slate-500">Loading recommendations...</p>
      </div>
    );
  }

  if (actions.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-6">
        <p className="text-center text-sm text-slate-500">No actions available</p>
      </div>
    );
  }

  // Sort actions to show recommended first, then by priority
  const sortedActions = [...actions].sort((a, b) => {
    if (a.id === recommendedActionId) return -1;
    if (b.id === recommendedActionId) return 1;
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">
        {title}
      </h3>
      
      <div className="space-y-3">
        {sortedActions.map((action) => {
          const isRecommended = action.id === recommendedActionId;
          const styles = getPriorityStyles(action.priority, isRecommended);
          
          return (
            <button
              key={action.id}
              onClick={() => handleActionClick(action)}
              disabled={disabled}
              data-recommended={isRecommended}
              data-priority={action.priority}
              data-primary={isRecommended}
              aria-label={`${action.label}${isRecommended ? ' - recommended' : ''}`}
              className={`
                w-full flex items-center gap-4 p-4 rounded-xl border-2 
                transition-all duration-200 text-left
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:shadow-md'}
                ${styles.card}
              `}
            >
              {/* Icon */}
              <div className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${styles.icon}`}>
                {getIcon(action.icon)}
              </div>
              
              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${isRecommended ? 'text-white' : 'text-slate-900'}`}>
                    {action.label}
                  </span>
                  {isRecommended && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles.badge}`}>
                      Recommended
                    </span>
                  )}
                </div>
                <p className={`text-sm mt-0.5 ${isRecommended ? 'text-white/80' : 'text-slate-600'}`}>
                  {action.description}
                </p>
              </div>
              
              {/* Arrow */}
              <div className={`flex-shrink-0 ${isRecommended ? 'text-white' : 'text-slate-400'}`}>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          );
        })}
      </div>
      
      {/* Progress indicator */}
      <div className="mt-4 pt-4 border-t border-slate-100">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Choose your next step</span>
          <span>{actions.length} options available</span>
        </div>
      </div>
    </div>
  );
}
