"use client";

import { useState } from "react";
import { tokenStore } from "@/lib/token-store";
import { api } from "@/lib/api";

interface Props {
  open: boolean;
  agentId: string;
  onClose: () => void;
  onRotated: (newToken: string) => void;
  apiBase?: string;
}

export function TokenRotateDialog({
  open,
  agentId,
  onClose,
  onRotated,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function handleRotate(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const currentToken = tokenStore.get(agentId);
      if (!currentToken) throw new Error("No current token in this browser");
      // Goes through the centralized API client so error mapping,
      // auth headers, and retry behaviour stay consistent with the rest
      // of the app. (Previously this dialog used raw fetch.)
      const data = await api.agents.reissue(agentId, {
        proof: { type: "current_token", token: currentToken },
      });
      tokenStore.set(agentId, data.access_token);
      onRotated(data.access_token);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rotation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
    >
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Rotate access token?</h2>
        <p className="mt-2 text-sm text-gray-600">
          This will invalidate the current token immediately. You&apos;ll need
          to save the new one.
        </p>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleRotate}
            disabled={busy}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
          >
            {busy ? "Rotating..." : "Rotate"}
          </button>
        </div>
      </div>
    </div>
  );
}
