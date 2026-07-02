"use client";

import { useState } from "react";
import { tokenStore } from "@/lib/token-store";
import { api } from "@/lib/api";

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
      // Goes through the centralized API client so error mapping,
      // auth headers, and retry behaviour stay consistent with the rest
      // of the app. (Previously this dialog used raw fetch.)
      await api.agents.get(pasteAgentId, pasteToken);
      tokenStore.set(pasteAgentId, pasteToken);
      onImported(pasteAgentId, pasteToken);
      onClose();
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : "Invalid token or wrong agent ID");
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
      const data = await api.agents.reissue(walletAgentId, {
        proof: {
          type: "wallet_signature",
          chain: walletChain,
          message: challenge.message,
          signature,
          public_key: publicKey,
        },
      });
      tokenStore.set(walletAgentId, data.access_token);
      onImported(walletAgentId, data.access_token);
      onClose();
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
