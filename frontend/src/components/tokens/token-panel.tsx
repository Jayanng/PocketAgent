"use client";

import { useEffect, useState } from "react";
import { Copy, RotateCcw, X } from "lucide-react";
import { tokenStore } from "@/lib/token-store";

interface Props {
  agentId: string;
  agentName: string;
  onRotate: () => void;
  onImport: () => void;
  onSignToReissue: () => void;
}

export function TokenPanel({
  agentId,
  agentName,
  onRotate,
  onImport,
  onSignToReissue,
}: Props) {
  const [hasToken, setHasToken] = useState<boolean>(() => tokenStore.has(agentId));
  const [rotatedAt, setRotatedAt] = useState<Date | null>(null);

  useEffect(() => {
    // Track the "recently rotated" auto-clear timer so we can clear it on
    // unmount or when agentId changes. Without this, the timer fires
    // setRotatedAt on an unmounted component (React warns) and leaks on
    // every StrictMode mount/unmount cycle.
    let clearTimer: ReturnType<typeof setTimeout> | null = null;
    const unsubscribe = tokenStore.onChange((e) => {
      if (e.agentId !== agentId) return;
      setHasToken(e.type === "set");
      if (e.type === "set") {
        setRotatedAt(new Date());
        if (clearTimer) clearTimeout(clearTimer);
        // Auto-clear the "recently rotated" banner after 5 minutes (pure timer, not render-time).
        clearTimer = setTimeout(() => {
          setRotatedAt((current) =>
            current && Date.now() - current.getTime() >= 5 * 60 * 1000 - 1000 ? null : current,
          );
          clearTimer = null;
        }, 5 * 60 * 1000);
      }
    });
    return () => {
      unsubscribe();
      if (clearTimer) {
        clearTimeout(clearTimer);
        clearTimer = null;
      }
    };
  }, [agentId]);

  if (!hasToken) {
    return (
      <div
        className="rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900"
        data-testid="missing-banner"
      >
        <p className="text-sm font-semibold">Access token required</p>
        <p className="mt-1 text-sm">
          This agent&apos;s access token is not in this browser. To use it,
          you&apos;ll need to import or reissue.
        </p>
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={onImport}
            className="rounded border px-3 py-1 text-sm hover:bg-amber-100"
          >
            Import token
          </button>
          <button
            type="button"
            onClick={onSignToReissue}
            className="rounded border px-3 py-1 text-sm hover:bg-amber-100"
          >
            Sign with wallet to reissue
          </button>
        </div>
      </div>
    );
  }

  async function handleCopy(): Promise<void> {
    const tok = tokenStore.get(agentId);
    if (!tok) return;
    try {
      await navigator.clipboard.writeText(tok);
    } catch (e) {
      console.error("Clipboard write failed", e);
    }
  }

  return (
    <div className="rounded-md border p-3" data-testid="active-panel">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          Access token{agentName ? ` for ${agentName}` : ""}
        </span>
        <span className="font-mono text-sm text-gray-500">••••••••</span>
      </div>
      {rotatedAt && (
        <p className="mt-2 text-xs text-blue-700">
          Token rotated at {rotatedAt.toLocaleTimeString()}. Old token is now
          invalid.
        </p>
      )}
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded border px-3 py-1 text-sm hover:bg-gray-50"
        >
          <Copy className="h-3 w-3" /> Copy
        </button>
        <button
          type="button"
          onClick={onRotate}
          className="flex items-center gap-1 rounded border px-3 py-1 text-sm hover:bg-gray-50"
        >
          <RotateCcw className="h-3 w-3" /> Rotate
        </button>
        <button
          type="button"
          onClick={() => tokenStore.forget(agentId)}
          className="flex items-center gap-1 rounded px-3 py-1 text-sm text-gray-600 hover:bg-gray-50"
        >
          <X className="h-3 w-3" /> Remove from this device
        </button>
      </div>
    </div>
  );
}
