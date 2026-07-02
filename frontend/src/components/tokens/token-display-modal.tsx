"use client";

import { useEffect, useRef, useState } from "react";
import { Copy, Download, Eye, EyeOff } from "lucide-react";

interface Props {
  open: boolean;
  agentName: string;
  token: string;
  onAcknowledged: () => void;
}

export function TokenDisplayModal({
  open,
  agentName,
  token,
  onAcknowledged,
}: Props) {
  const [revealed, setRevealed] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");
  // Track pending copy-reset timer so we can clear it if the modal
  // unmounts before the 2-second "Copied ✓" indicator expires. Without
  // this, React warns about state updates on an unmounted component
  // (and in StrictMode the timer leaks on every mount/unmount cycle).
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (copyTimerRef.current) {
        clearTimeout(copyTimerRef.current);
        copyTimerRef.current = null;
      }
    };
  }, []);

  if (!open) return null;

  async function handleCopy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(token);
      setCopyState("copied");
      if (copyTimerRef.current) {
        clearTimeout(copyTimerRef.current);
      }
      copyTimerRef.current = setTimeout(() => {
        setCopyState("idle");
        copyTimerRef.current = null;
      }, 2000);
    } catch (e) {
      console.error("Clipboard write failed", e);
    }
  }

  function handleDownload(): void {
    const blob = new Blob(
      [
        `PocketAgent access token for "${agentName}"\n\n${token}\n\nKeep this secret. The server only stores a hash; lost tokens can only be recovered via wallet signature.\n`,
      ],
      { type: "text/plain" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pocketagent-${agentName.replace(/\s+/g, "-")}-token.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="token-modal"
    >
      <div
        className="max-w-md rounded-lg bg-white p-6 shadow-xl"
        role="dialog"
        aria-modal="true"
      >
        <h2 className="text-lg font-semibold">✓ Agent created</h2>
        <p className="mt-2 text-sm text-gray-600">Your access token</p>
        <div className="mt-4 flex items-center gap-2 rounded-md border bg-gray-50 p-3">
          <code
            className="flex-1 overflow-hidden font-mono text-sm"
            data-testid="token-display"
          >
            {revealed ? token : "•".repeat(40)}
          </code>
          <button
            type="button"
            onClick={() => setRevealed(!revealed)}
            aria-label={revealed ? "Hide token" : "Show token"}
            className="rounded p-1 hover:bg-gray-200"
          >
            {revealed ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        </div>
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 rounded border px-3 py-1 text-sm hover:bg-gray-50"
          >
            <Copy className="h-4 w-4" />
            {copyState === "copied" ? "Copied ✓" : "Copy"}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="flex items-center gap-1 rounded border px-3 py-1 text-sm hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            Download .txt
          </button>
        </div>
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          ⚠ Save this token now. It cannot be recovered later unless you have the
          agent&apos;s wallet. The server only stores a hash.
        </div>
        <div className="mt-4 flex items-center gap-2">
          <input
            id="ack"
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            aria-label="I have saved my token"
          />
          <label htmlFor="ack" className="text-sm">
            I have saved my token
          </label>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={onAcknowledged}
            disabled={!acknowledged}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
