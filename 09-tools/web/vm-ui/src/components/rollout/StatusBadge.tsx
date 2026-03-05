/**
 * StatusBadge Component
 * Displays rollout status with appropriate visual styling
 */

import type { RolloutStatus } from "../../api/rolloutDashboard";

interface StatusBadgeProps {
  status: RolloutStatus;
  className?: string;
}

const STATUS_CONFIG: Record<
  string,
  { 
    label: string; 
    bgColor: string; 
    textColor: string; 
    borderColor: string;
    ariaLabel: string;
    hasSpinner?: boolean;
  }
> = {
  promoted: {
    label: "Promoted",
    bgColor: "bg-green-100",
    textColor: "text-green-800",
    borderColor: "border-green-200",
    ariaLabel: "Status: Promoted to production",
  },
  blocked: {
    label: "Blocked",
    bgColor: "bg-red-100",
    textColor: "text-red-800",
    borderColor: "border-red-200",
    ariaLabel: "Status: Blocked due to policy violation",
  },
  rolled_back: {
    label: "Rolled Back",
    bgColor: "bg-orange-100",
    textColor: "text-orange-800",
    borderColor: "border-orange-200",
    ariaLabel: "Status: Rolled back to previous version",
  },
  pending_review: {
    label: "Pending Review",
    bgColor: "bg-yellow-100",
    textColor: "text-yellow-800",
    borderColor: "border-yellow-200",
    ariaLabel: "Status: Pending manual review",
  },
  evaluating: {
    label: "Evaluating",
    bgColor: "bg-blue-100",
    textColor: "text-blue-800",
    borderColor: "border-blue-200",
    ariaLabel: "Status: Currently evaluating",
    hasSpinner: true,
  },
};

const UNKNOWN_CONFIG = {
  label: "unknown",
  bgColor: "bg-gray-100",
  textColor: "text-gray-800",
  borderColor: "border-gray-200",
  ariaLabel: "Status: unknown",
};

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || {
    ...UNKNOWN_CONFIG,
    label: status,
    ariaLabel: `Status: ${status}`,
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${config.bgColor} ${config.textColor} ${config.borderColor} ${className}`}
      role="status"
      aria-label={config.ariaLabel}
    >
      {config.hasSpinner && (
        <svg
          className="h-3 w-3 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {config.label}
    </span>
  );
}

export default StatusBadge;
