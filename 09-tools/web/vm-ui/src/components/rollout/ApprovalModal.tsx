/**
 * ApprovalModal Component
 * Modal for confirming approve/reject/rollback actions with operator details
 */

import { useState, useEffect } from "react";

export type ApprovalAction = "approve" | "reject" | "rollback";

interface ApprovalModalProps {
  isOpen: boolean;
  action: ApprovalAction;
  experimentId: string;
  onClose: () => void;
  onSubmit: (data: { operatorId: string; reason: string }) => Promise<void>;
  isSubmitting: boolean;
}

const ACTION_CONFIG: Record<
  ApprovalAction,
  { 
    title: string; 
    confirmLabel: string; 
    confirmColor: string;
    description: string;
  }
> = {
  approve: {
    title: "Confirm Promotion Approval",
    confirmLabel: "Approve Promotion",
    confirmColor: "bg-green-600 hover:bg-green-700",
    description: "You are about to promote the experiment variant to production. This action cannot be undone.",
  },
  reject: {
    title: "Confirm Promotion Rejection",
    confirmLabel: "Reject Promotion",
    confirmColor: "bg-red-600 hover:bg-red-700",
    description: "You are about to reject the promotion and keep the current variant active.",
  },
  rollback: {
    title: "Confirm Manual Rollback",
    confirmLabel: "Force Rollback",
    confirmColor: "bg-red-600 hover:bg-red-700",
    description: "You are about to immediately rollback the experiment to the previous version.",
  },
};

const MIN_REASON_LENGTH = 10;

export function ApprovalModal({
  isOpen,
  action,
  experimentId,
  onClose,
  onSubmit,
  isSubmitting,
}: ApprovalModalProps) {
  const [operatorId, setOperatorId] = useState("");
  const [reason, setReason] = useState("");
  const [operatorTouched, setOperatorTouched] = useState(false);
  const [reasonTouched, setReasonTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setOperatorId("");
      setReason("");
      setOperatorTouched(false);
      setReasonTouched(false);
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const config = ACTION_CONFIG[action];
  const isReasonValid = reason.trim().length >= MIN_REASON_LENGTH;
  const isOperatorValid = operatorId.trim().length > 0;
  const isFormValid = isOperatorValid && isReasonValid;

  const showOperatorError = operatorTouched && !isOperatorValid;
  const showReasonValidation = reasonTouched;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOperatorTouched(true);
    setReasonTouched(true);
    setError(null);

    if (!isFormValid) return;

    try {
      await onSubmit({ operatorId: operatorId.trim(), reason: reason.trim() });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    }
  };

  const getValidationMessage = () => {
    if (!showReasonValidation) return null;
    if (reason.trim().length === 0) return "Minimum 10 characters required";
    if (reason.trim().length < MIN_REASON_LENGTH) return "Minimum 10 characters required";
    return "Reason meets requirements";
  };

  const validationMessage = getValidationMessage();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="approval-modal-title"
      aria-describedby="approval-modal-description"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-2xl">
        {/* Header */}
        <div className="border-b border-slate-100 px-6 py-4">
          <h2
            id="approval-modal-title"
            className="text-lg font-semibold text-slate-900"
          >
            {config.title}
          </h2>
          <p id="approval-modal-description" className="mt-2 text-sm text-slate-600">
            {config.description}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Experiment: <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{experimentId}</code>
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          <div className="space-y-4">
            {/* Operator ID */}
            <div>
              <label
                htmlFor="operator-id"
                className="block text-sm font-medium text-slate-700"
              >
                Operator ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="operator-id"
                value={operatorId}
                onChange={(e) => setOperatorId(e.target.value)}
                onBlur={() => setOperatorTouched(true)}
                placeholder="your.user.id"
                className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-[var(--vm-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--vm-primary)]"
                disabled={isSubmitting}
                aria-required="true"
                aria-invalid={showOperatorError}
              />
              {showOperatorError && (
                <p className="mt-1 text-xs text-red-600">Operator ID is required</p>
              )}
            </div>

            {/* Reason */}
            <div>
              <label
                htmlFor="reason"
                className="block text-sm font-medium text-slate-700"
              >
                Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                onBlur={() => setReasonTouched(true)}
                placeholder={`Explain why you are ${action === "approve" ? "approving" : action === "reject" ? "rejecting" : "rolling back"} this promotion...`}
                rows={3}
                className="mt-1 block w-full resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm focus:border-[var(--vm-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--vm-primary)]"
                disabled={isSubmitting}
                aria-required="true"
                minLength={MIN_REASON_LENGTH}
              />
              {showReasonValidation && (
                <div className="mt-1 flex items-center justify-between text-xs">
                  <span className={isReasonValid ? "text-green-600" : "text-slate-500"}>
                    {validationMessage}
                  </span>
                  <span className={reason.length < MIN_REASON_LENGTH ? "text-red-500" : "text-slate-400"}>
                    {reason.length}/{MIN_REASON_LENGTH}
                  </span>
                </div>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div 
                className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
                role="alert"
                aria-live="assertive"
              >
                {error}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isFormValid || isSubmitting}
              className={`flex-1 rounded-xl px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${config.confirmColor}`}
            >
              {isSubmitting ? "Processing..." : config.confirmLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ApprovalModal;
