/**
 * ApprovalActions Component
 * Action buttons for approve/reject/rollback based on policy state
 */

import type { RolloutStatus, RolloutMode } from "../../api/rolloutDashboard";

interface ApprovalActionsProps {
  mode: RolloutMode;
  status: RolloutStatus;
  canRollback: boolean;
  onApprove: () => void;
  onReject: () => void;
  onRollback: () => void;
  disabled?: boolean;
}

export function ApprovalActions({
  mode,
  status,
  canRollback,
  onApprove,
  onReject,
  onRollback,
  disabled = false,
}: ApprovalActionsProps) {
  // Show approve/reject for supervised mode with pending_review status
  const showApprovalActions = mode === "SUPERVISED" && status === "pending_review";
  
  // Show rollback for promoted status OR when canRollback is true
  const showRollback = status === "promoted" || canRollback;

  if (!showApprovalActions && !showRollback) {
    return (
      <span className="text-sm text-slate-400 italic">
        No actions available
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2" role="group" aria-label="Approval actions">
      {showApprovalActions && (
        <>
          <button
            onClick={onApprove}
            disabled={disabled}
            className="inline-flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1"
            aria-label="Approve promotion to production"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Approve Promotion
          </button>
          <button
            onClick={onReject}
            disabled={disabled}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-1"
            aria-label="Reject promotion"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Reject Promotion
          </button>
        </>
      )}
      
      {showRollback && (
        <button
          onClick={onRollback}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1"
          aria-label="Force rollback to previous version"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
          </svg>
          Force Rollback
        </button>
      )}
    </div>
  );
}

export default ApprovalActions;
