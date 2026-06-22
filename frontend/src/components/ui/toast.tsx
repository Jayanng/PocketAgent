"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { AlertCircle, CheckCircle2, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info";

type Toast = {
  id: string;
  type: ToastType;
  message: string;
  action?: { label: string; onClick: () => void };
};

type ToastContextValue = {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, "id">) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    // Auto-dismiss after 5s
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Listen for API error events from api.ts
  useEffect(() => {
    function handler(e: CustomEvent<{ message: string; actionLabel?: string; actionOnClick?: () => void }>) {
      addToast({
        type: "error",
        message: e.detail.message,
        action:
          e.detail.actionLabel && e.detail.actionOnClick
            ? { label: e.detail.actionLabel, onClick: e.detail.actionOnClick }
            : undefined,
      });
    }
    window.addEventListener("toast:api-error", handler as EventListener);
    return () => window.removeEventListener("toast:api-error", handler as EventListener);
  }, [addToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              "flex items-start gap-3 rounded-lg border p-4 shadow-lg animate-slide-up",
              toast.type === "error" &&
                "border-red-200 bg-red-50 text-red-800",
              toast.type === "success" &&
                "border-green-200 bg-green-50 text-green-800",
              toast.type === "info" &&
                "border-border bg-card text-foreground",
            )}
          >
            {toast.type === "error" && (
              <AlertCircle size={18} className="mt-0.5 shrink-0 text-red-500" />
            )}
            {toast.type === "success" && (
              <CheckCircle2
                size={18}
                className="mt-0.5 shrink-0 text-green-500"
              />
            )}
            <div className="flex-1 text-sm">{toast.message}</div>
            {toast.action && (
              <button
                onClick={toast.action.onClick}
                className="shrink-0 text-xs font-medium underline"
              >
                {toast.action.label}
              </button>
            )}
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 text-muted-foreground hover:text-foreground"
              aria-label="Dismiss"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
