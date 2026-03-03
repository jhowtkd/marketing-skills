import { useEffect, useState, type ReactNode } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastProps extends Toast {
  onDismiss: (id: string) => void;
}

const TOAST_CONFIG: Record<
  ToastType,
  { icon: string; bgColor: string; borderColor: string; iconColor: string }
> = {
  success: {
    icon: "✓",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    iconColor: "text-green-600",
  },
  error: {
    icon: "✕",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    iconColor: "text-red-600",
  },
  warning: {
    icon: "⚠",
    bgColor: "bg-yellow-50",
    borderColor: "border-yellow-200",
    iconColor: "text-yellow-600",
  },
  info: {
    icon: "ℹ",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    iconColor: "text-blue-600",
  },
};

function ToastItem({
  id,
  type,
  title,
  message,
  duration = 5000,
  action,
  onDismiss,
}: ToastProps): JSX.Element {
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);
  const config = TOAST_CONFIG[type];

  useEffect(() => {
    if (duration <= 0) return;

    const startTime = Date.now();
    const endTime = startTime + duration;

    const updateProgress = () => {
      const now = Date.now();
      const remaining = Math.max(0, endTime - now);
      const newProgress = (remaining / duration) * 100;

      if (newProgress <= 0) {
        handleDismiss();
      } else {
        setProgress(newProgress);
        requestAnimationFrame(updateProgress);
      }
    };

    const animationFrame = requestAnimationFrame(updateProgress);

    return () => {
      cancelAnimationFrame(animationFrame);
    };
  }, [duration]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => {
      onDismiss(id);
    }, 300);
  };

  return (
    <div
      className={[
        "pointer-events-auto mb-3 w-full max-w-sm transform overflow-hidden rounded-lg border shadow-lg transition-all duration-300",
        config.bgColor,
        config.borderColor,
        isExiting ? "translate-x-full opacity-0" : "translate-x-0 opacity-100",
      ].join(" ")}
      role="alert"
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span
            className={[
              "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-sm font-bold",
              config.iconColor,
            ].join(" ")}
          >
            {config.icon}
          </span>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-slate-900">{title}</p>
            {message && (
              <p className="mt-1 text-sm text-slate-600">{message}</p>
            )}
            {action && (
              <button
                onClick={() => {
                  action.onClick();
                  handleDismiss();
                }}
                className="mt-2 text-sm font-medium text-slate-900 underline hover:no-underline"
              >
                {action.label}
              </button>
            )}
          </div>
          <button
            onClick={handleDismiss}
            className="shrink-0 text-slate-400 hover:text-slate-600"
            aria-label="Dismiss"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      {duration > 0 && (
        <div className="h-1 w-full bg-black/5">
          <div
            className={["h-full transition-all duration-100", config.iconColor.replace("text-", "bg-")].join(" ")}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
  position?: "top-right" | "top-left" | "bottom-right" | "bottom-left" | "top-center" | "bottom-center";
}

export function ToastContainer({
  toasts,
  onDismiss,
  position = "top-right",
}: ToastContainerProps): JSX.Element {
  const positionClasses = {
    "top-right": "top-4 right-4",
    "top-left": "top-4 left-4",
    "bottom-right": "bottom-4 right-4",
    "bottom-left": "bottom-4 left-4",
    "top-center": "top-4 left-1/2 -translate-x-1/2",
    "bottom-center": "bottom-4 left-1/2 -translate-x-1/2",
  };

  if (toasts.length === 0) {
    return <></>;
  }

  return (
    <div
      className={["fixed z-50 flex flex-col items-end", positionClasses[position]].join(" ")}
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} {...toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

export default ToastItem;
