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

export default useToast;
