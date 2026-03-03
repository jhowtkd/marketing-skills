import { useState, useCallback, useRef } from "react";
import type { Toast, ToastType } from "../components/ui/Toast";

interface ToastOptions {
  title: string;
  message?: string;
  type?: ToastType;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface UseToastReturn {
  toasts: Toast[];
  showToast: (options: ToastOptions) => string;
  dismissToast: (id: string) => void;
  dismissAll: () => void;
  // Convenience methods
  success: (title: string, message?: string, duration?: number) => string;
  error: (title: string, message?: string, duration?: number) => string;
  warning: (title: string, message?: string, duration?: number) => string;
  info: (title: string, message?: string, duration?: number) => string;
}

export function useToast(): UseToastReturn {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idCounter = useRef(0);

  const generateId = (): string => {
    idCounter.current += 1;
    return `toast-${Date.now()}-${idCounter.current}`;
  };

  const showToast = useCallback((options: ToastOptions): string => {
    const id = generateId();
    const newToast: Toast = {
      id,
      type: options.type || "info",
      title: options.title,
      message: options.message,
      duration: options.duration ?? 5000,
      action: options.action,
    };

    setToasts((prev) => [...prev, newToast]);
    return id;
  }, []);

  const dismissToast = useCallback((id: string): void => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const dismissAll = useCallback((): void => {
    setToasts([]);
  }, []);

  // Convenience methods
  const success = useCallback(
    (title: string, message?: string, duration?: number): string => {
      return showToast({ title, message, type: "success", duration });
    },
    [showToast]
  );

  const error = useCallback(
    (title: string, message?: string, duration?: number): string => {
      return showToast({ title, message, type: "error", duration });
    },
    [showToast]
  );

  const warning = useCallback(
    (title: string, message?: string, duration?: number): string => {
      return showToast({ title, message, type: "warning", duration });
    },
    [showToast]
  );

  const info = useCallback(
    (title: string, message?: string, duration?: number): string => {
      return showToast({ title, message, type: "info", duration });
    },
    [showToast]
  );

  return {
    toasts,
    showToast,
    dismissToast,
    dismissAll,
    success,
    error,
    warning,
    info,
  };
}

// Hook for API operations with toast notifications
interface UseToastApiOptions {
  onSuccess?: (message: string) => void;
  onError?: (message: string) => void;
}

export function useToastApi({ onSuccess, onError }: UseToastApiOptions = {}) {
  const { success, error } = useToast();

  const wrapApiCall = useCallback(
    async <T,>(
      promise: Promise<T>,
      options: {
        loading?: string;
        success?: string;
        error?: string;
      } = {}
    ): Promise<T | null> => {
      try {
        const result = await promise;
        if (options.success) {
          success(options.success);
          onSuccess?.(options.success);
        }
        return result;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : options.error || "Operation failed";
        error(options.error || "Error", message);
        onError?.(message);
        return null;
      }
    },
    [success, error, onSuccess, onError]
  );

  return { wrapApiCall };
}

// Provider pattern for global toast state
import { createContext, useContext, type ReactNode } from "react";

interface ToastContextValue extends UseToastReturn {
  ToastContainer: () => JSX.Element;
}

const ToastContext = createContext<ToastContextValue | null>(null);

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps): JSX.Element {
  const toast = useToast();
  const { toasts, dismissToast } = toast;

  // Import ToastContainer dynamically to avoid circular dependency
  const ToastContainerComponent = (): JSX.Element => {
    const { ToastContainer } = require("../components/ui/Toast");
    return ToastContainer({ toasts, onDismiss: dismissToast });
  };

  return (
    <ToastContext.Provider value={{ ...toast, ToastContainer: ToastContainerComponent }}>
      {children}
      <ToastContainerComponent />
    </ToastContext.Provider>
  );
}

export function useToastContext(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToastContext must be used within a ToastProvider");
  }
  return context;
}
