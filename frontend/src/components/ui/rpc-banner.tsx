"use client";

import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";

type RpcBannerProps = {
  visible: boolean;
  onRetry?: () => void;
  onDismiss?: () => void;
};

export function RpcBanner({ visible, onRetry, onDismiss }: RpcBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (!visible || dismissed) return null;

  return (
    <div
      className={cn(
        "flex items-center gap-3 border-b border-yellow-200 bg-yellow-50 px-4 py-2.5 text-sm text-yellow-800 animate-slide-up",
      )}
    >
      <AlertTriangle size={16} className="shrink-0 text-yellow-600" />
      <span className="flex-1">
        Pocket RPC unavailable. Some features may not work.
      </span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 text-xs font-medium text-yellow-800 underline hover:text-yellow-900"
        >
          Retry
        </button>
      )}
      <button
        onClick={() => {
          setDismissed(true);
          onDismiss?.();
        }}
        className="shrink-0 text-yellow-600 hover:text-yellow-800"
        aria-label="Dismiss banner"
      >
        <X size={14} />
      </button>
    </div>
  );
}
