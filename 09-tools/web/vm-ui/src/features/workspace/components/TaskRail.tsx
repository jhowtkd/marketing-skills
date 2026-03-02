import { useEffect, useRef, useCallback } from 'react';

export interface Task {
  id: string;
  label: string;
  icon: string;
  order: number;
}

export interface NavigationEvent {
  from: string;
  to: string;
  timestamp: number;
}

export interface TaskTimeUpdate {
  taskId: string;
  timeSpent: number;
}

interface TaskRailProps {
  tasks: Task[];
  activeTaskId: string;
  completedTaskIds: string[];
  nextRecommendedTaskId?: string;
  onTaskSelect: (taskId: string) => void;
  onTaskComplete?: (taskId: string) => void;
  onNavigate?: (event: NavigationEvent) => void;
  onTaskTimeUpdate?: (update: TaskTimeUpdate) => void;
}

export default function TaskRail({
  tasks,
  activeTaskId,
  completedTaskIds,
  nextRecommendedTaskId,
  onTaskSelect,
  onTaskComplete,
  onNavigate,
  onTaskTimeUpdate,
}: TaskRailProps) {
  const taskStartTimeRef = useRef<number>(Date.now());
  const previousTaskIdRef = useRef<string>(activeTaskId);

  // Sort tasks by order
  const sortedTasks = [...tasks].sort((a, b) => a.order - b.order);

  // Track time spent on tasks
  useEffect(() => {
    const now = Date.now();
    const previousTaskId = previousTaskIdRef.current;
    
    // If task changed, report time spent on previous task
    if (previousTaskId !== activeTaskId) {
      const timeSpent = now - taskStartTimeRef.current;
      
      if (onTaskTimeUpdate && previousTaskId) {
        onTaskTimeUpdate({
          taskId: previousTaskId,
          timeSpent,
        });
      }
      
      // Report navigation event
      if (onNavigate && previousTaskId) {
        onNavigate({
          from: previousTaskId,
          to: activeTaskId,
          timestamp: now,
        });
      }
      
      // Reset timer for new task
      taskStartTimeRef.current = now;
      previousTaskIdRef.current = activeTaskId;
    }
  }, [activeTaskId, onNavigate, onTaskTimeUpdate]);

  const handleTaskClick = useCallback((taskId: string) => {
    if (taskId !== activeTaskId) {
      onTaskSelect(taskId);
    }
  }, [activeTaskId, onTaskSelect]);

  const handleCompleteClick = useCallback((e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    if (onTaskComplete) {
      onTaskComplete(taskId);
    }
  }, [onTaskComplete]);

  // Calculate progress
  const totalTasks = sortedTasks.length;
  const completedCount = completedTaskIds.length;
  const progressPercentage = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;

  // Get icon for task
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'edit':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        );
      case 'inbox':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        );
      case 'clock':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'settings':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
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

  return (
    <nav 
      className="flex flex-col h-full bg-white border-r border-slate-200 w-64"
      aria-label="Task navigation"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-100">
        <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
          Workflow
        </h2>
      </div>

      {/* Progress Bar */}
      <div className="px-4 py-3 border-b border-slate-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-500">Progress</span>
          <span className="text-xs font-medium text-slate-700">{progressPercentage}%</span>
        </div>
        <div 
          role="progressbar"
          aria-valuenow={progressPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Workflow progress: ${progressPercentage}%`}
          className="h-2 bg-slate-100 rounded-full overflow-hidden"
        >
          <div 
            className="h-full bg-[var(--vm-primary)] transition-all duration-300 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto py-2">
        {sortedTasks.map((task, index) => {
          const isActive = task.id === activeTaskId;
          const isCompleted = completedTaskIds.includes(task.id);
          const isRecommended = task.id === nextRecommendedTaskId;
          const stepNumber = index + 1;

          return (
            <div
              key={task.id}
              role="button"
              onClick={() => handleTaskClick(task.id)}
              data-active={isActive}
              data-completed={isCompleted}
              data-recommended={isRecommended}
              aria-current={isActive ? 'step' : undefined}
              aria-label={`${task.label}${isActive ? ' (current step)' : ''}${isCompleted ? ' - completed' : ''}`}
              className={`
                relative flex items-center gap-3 px-4 py-3 mx-2 rounded-xl cursor-pointer
                transition-all duration-200 group
                ${isActive 
                  ? 'bg-[var(--vm-primary)] text-white shadow-md' 
                  : isCompleted
                    ? 'bg-emerald-50 text-emerald-900 hover:bg-emerald-100'
                    : 'hover:bg-slate-50 text-slate-700'
                }
              `}
            >
              {/* Step Number / Icon */}
              <div className={`
                flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0
                ${isActive 
                  ? 'bg-white/20' 
                  : isCompleted
                    ? 'bg-emerald-200 text-emerald-800'
                    : 'bg-slate-100 text-slate-500 group-hover:bg-slate-200'
                }
              `}>
                {isCompleted ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="text-sm font-semibold">{stepNumber}</span>
                )}
              </div>

              {/* Icon */}
              <div className={`flex-shrink-0 ${isActive ? 'text-white/90' : ''}`}>
                {getIcon(task.icon)}
              </div>

              {/* Label */}
              <span className={`flex-1 text-sm font-medium ${isActive ? 'text-white' : ''}`}>
                {task.label}
              </span>

              {/* Recommended Badge */}
              {isRecommended && !isActive && (
                <span className="absolute -top-1 -right-1">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-200">
                    Next
                  </span>
                </span>
              )}

              {/* Complete Button (for active task) */}
              {isActive && onTaskComplete && !isCompleted && (
                <button
                  onClick={(e) => handleCompleteClick(e, task.id)}
                  aria-label={`Mark ${task.label} as complete`}
                  className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 transition-colors"
                  title="Mark as complete"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </button>
              )}

              {/* Completed Indicator */}
              {isCompleted && !isActive && (
                <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer Stats */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{completedCount} of {totalTasks} completed</span>
          {completedCount === totalTasks && (
            <span className="text-emerald-600 font-medium">All done!</span>
          )}
        </div>
      </div>
    </nav>
  );
}
