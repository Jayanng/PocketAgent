"use client";

import { useState } from "react";
import { tokenStore } from "@/lib/token-store";

interface Props {
  open: boolean;
  onClose: () => void;
  onImported: (agentId: string, token: string) => void;
  onRequestChallenge: (
    agentId: string,
  ) => Promise<{ message: string; timestamp: number }>;
  onSignMessage: (
    message: string,
  ) => Promise<{ signature: string; publicKey: string }>;
  agentChains: string[];
  apiBase?: string;
}

export function TokenImportDialog({
  open,
  onClose,
  onImported,
  onRequestChallenge,
  onSignMessage,
  agentChains,
  apiBase = "",
}: Props) {
  const [tab, setTab] = useState<"paste" | "wallet">("paste");
  const [pasteAgentId, setPasteAgentId] = useState("");
  const [pasteToken, setPasteToken] = useState("");
  const [pasteError, setPasteError] = useState<string | null>(null);
  const [pasteBusy, setPasteBusy] = useState(false);

  const [walletAgentId, setWalletAgentId] = useState("");
  const [walletChain, setWalletChain] = useState(agentChains[0] ?? "ethereum");
  const [walletError, setWalletError] = useState<string | null>(null);
  const [walletBusy, setWalletBusy] = useState(false);

  if (!open) return null;

  async function handlePaste(): Promise<void> {
    setPasteError(null);
    setPasteBusy(true);
    try {
      const resp = await fetch(
        `${apiBase}/api/agents/${encodeURIComponent(pasteAgentId)}`,
        { headers: { "X-Agent-Access-Token": pasteToken } },
      );
      if (resp.status === 200) {
        tokenStore.set(pasteAgentId, pasteToken);
        onImported(pasteAgentId, pasteToken);
        onClose();
      } else if (resp.status === 401 || resp.status === 403) {
        setPasteError("Invalid token or wrong agent ID");
      } else {
        setPasteError(`Unexpected error (${resp.status})`);
      }
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : "Network error");
    } finally {
      setPasteBusy(false);
    }
  }

  async function handleWalletSign(): Promise<void> {
    setWalletError(null);
    setWalletBusy(true);
    try {
      const challenge = await onRequestChallenge(walletAgentId);
      const { signature, publicKey } = await onSignMessage(challenge.message);
      const resp = await fetch(
        `${apiBase}/api/agents/${encodeURIComponent(walletAgentId)}/reissue-token`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            proof: {
              type: "wallet_signature",
              chain: walletChain,
              message: challenge.message,
              signature,
              public_key: publicKey,
            },
          }),
        },
      );
      if (resp.ok) {
        const data = (await resp.json()) as { access_token: string };
        tokenStore.set(walletAgentId, data.access_token);
        onImported(walletAgentId, data.access_token);
        onClose();
      } else {
        const detail =
          ((await resp.json().catch(() => ({}))) as { detail?: string })
            ?.detail ?? `Error ${resp.status}`;
        setWalletError(detail);
      }
    } catch (e) {
      setWalletError(e instanceof Error ? e.message : "Failed");
    } finally {
      setWalletBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
    >
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Import access token</h2>
        <div className="mt-4 flex gap-2 border-b">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "paste"}
            onClick={() => setTab("paste")}
            className={`px-3 py-2 text-sm ${
              tab === "paste"
                ? "border-b-2 border-blue-600 font-medium"
                : "text-gray-600"
            }`}
          >
            Paste token
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "wallet"}
            onClick={() => setTab("wallet")}
            className={`px-3 py-2 text-sm ${
              tab === "wallet"
                ? "border-b-2 border-blue-600 font-medium"
                : "text-gray-600"
            }`}
          >
            Sign with wallet
          </button>
        </div>
        {tab === "paste" && (
          <div className="mt-4 space-y-3">
            <input
              placeholder="Agent ID"
              value={pasteAgentId}
              onChange={(e) => setPasteAgentId(e.target.value)}
              className="w-full rounded border px-3 py-2 text-sm"
            />
            <textarea
              placeholder="Access token"
              value={pasteToken}
              onChange={(e) => setPasteToken(e.target.value)}
              className="w-full rounded border px-3 py-2 font-mono text-xs"
              rows={3}
            />
            {pasteError && (
              <p className="text-sm text-red-600">{pasteError}</p>
            )}
          </div>
        )}
        {tab === "wallet" && (
          <div className="mt-4 space-y-3">
            <input
              placeholder="Agent ID"
              value={walletAgentId}
              onChange={(e) => setWalletAgentId(e.target.value)}
              className="w-full rounded border px-3 py-2 text-sm"
            />
            <select
              value={walletChain}
              onChange={(e) => setWalletChain(e.target.value)}
              className="w-full rounded border px-3 py-2 text-sm"
            >
              {agentChains.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-600">
              You&apos;ll be asked to sign a message with the wallet that owns
              this agent. The signature is verified server-side before issuing
              a new token.
            </p>
            {walletError && (
              <p className="text-sm text-red-600">{walletError}</p>
            )}
          </div>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
          >
            Cancel
          </button>
          {tab === "paste" ? (
            <button
              type="button"
              onClick={handlePaste}
              disabled={pasteBusy || !pasteAgentId || !pasteToken}
              className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
            >
              {pasteBusy ? "Validating..." : "Import"}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleWalletSign}
              disabled={walletBusy || !walletAgentId}
              className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
            >
              {walletBusy ? "Signing..." : "Sign and reissue"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
