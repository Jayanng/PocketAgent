"use client";

import { useMemo, useState } from "react";
import { AlertCircle, Check, Copy, ExternalLink, Wallet } from "lucide-react";
import { useAccount, useSendTransaction, useSwitchChain } from "wagmi";
import { parseEther } from "viem";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { CHAIN_CONFIGS, type ChainKey } from "@/lib/constants";
import type { Agent } from "@/lib/api";

type FundAgentDialogProps = {
  agent: Agent;
  open: boolean;
  onClose: () => void;
};

// Prefilled small amount — real mainnet funds on a cheap L2 (cents).
// User can edit. Clearly labeled in the UI.
const DEFAULT_AMOUNT = "0.001";

export function FundAgentDialog({ agent, open, onClose }: FundAgentDialogProps) {
  const agentChains = (agent.chains as ChainKey[]).filter((c) => CHAIN_CONFIGS[c]);
  const [selectedChain, setSelectedChain] = useState<ChainKey>(
    agentChains[0] ?? "ethereum"
  );
  const [amount, setAmount] = useState(DEFAULT_AMOUNT);
  const [copied, setCopied] = useState(false);

  const { address: connectedAddress, isConnected } = useAccount();
  const { switchChainAsync } = useSwitchChain();
  const {
    sendTransactionAsync,
    isPending: isSending,
    data: txHash,
    error: sendError,
  } = useSendTransaction();

  const chainConfig = CHAIN_CONFIGS[selectedChain];
  const isEvm = chainConfig?.protocol === "evm";
  const evmChainId = typeof chainConfig?.chainId === "number" ? chainConfig.chainId : null;
  const walletAddress =
    (chainConfig?.protocol ? agent.wallet_addresses?.[chainConfig.protocol] : null) ??
    (isEvm ? agent.wallet_address : null) ??
    "";

  const explorerUrl = useMemo(() => {
    if (!chainConfig || !txHash) return null;
    return `${chainConfig.blockExplorerUrl.replace(/\/$/, "")}/tx/${txHash}`;
  }, [chainConfig, txHash]);

  const copyAddress = async () => {
    if (!walletAddress) return;
    await navigator.clipboard.writeText(walletAddress);
    setCopied(true);
  };

  const sendFromConnected = async () => {
    if (!sendTransactionAsync || !walletAddress || !evmChainId) return;
    // If the connected wallet is on a different chain, switch first so the
    // send lands on the agent's intended chain.
    try {
      await switchChainAsync?.({ chainId: evmChainId });
    } catch {
      // User may decline the switch — let sendTransactionAsync surface the error.
    }
    await sendTransactionAsync({
      to: walletAddress as `0x${string}`,
      value: parseEther(amount || "0"),
      chainId: evmChainId,
    });
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? null : onClose())}>
      <DialogContent className="max-w-lg">
        <DialogHeader
          title={`Fund ${agent.name}`}
          description="Send native tokens to this agent's wallet so its write tools can transact."
          onClose={onClose}
        />

        <div className="space-y-4 p-4">
          {/* Agent wallet address — always visible, copyable */}
          <div className="rounded-md border border-border bg-background p-3">
            <p className="text-xs font-medium uppercase text-muted-foreground">
              Agent {chainConfig?.protocol?.toUpperCase() ?? ""} Wallet Address
            </p>
            <div className="mt-2 flex items-center gap-2">
              <code className="min-w-0 flex-1 break-all text-xs">
                {walletAddress || `No ${chainConfig?.protocol ?? "chain"} wallet address`}
              </code>
              <Button variant="secondary" size="sm" onClick={copyAddress} disabled={!walletAddress}>
                <Copy size={14} />
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>

          {/* Chain selector — agent's enabled chains */}
          <label className="block space-y-2">
            <span className="text-sm font-medium">Fund on chain</span>
            <select
              value={selectedChain}
              onChange={(e) => {
                setSelectedChain(e.target.value as ChainKey);
                setCopied(false);
              }}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            >
              {agentChains.length === 0 && <option value="">No chains enabled</option>}
              {agentChains.map((chain) => (
                <option key={chain} value={chain}>
                  {CHAIN_CONFIGS[chain]?.name ?? chain} ({CHAIN_CONFIGS[chain]?.symbol})
                </option>
              ))}
            </select>
          </label>

          {/* Amount — real mainnet funds, clearly labeled */}
          <label className="block space-y-2">
            <span className="text-sm font-medium">
              Amount ({chainConfig?.symbol ?? ""})
            </span>
            <Input
              type="number"
              min="0"
              step="0.0001"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <p className="text-xs text-amber-600">
              ⚠ Real mainnet funds. This sends actual {chainConfig?.symbol ?? "tokens"} on the
              {" "}{chainConfig?.name ?? "selected"} mainnet via your connected wallet.
            </p>
          </label>

          {/* Path 1: connected wallet (EVM only) */}
          <div className="space-y-2 rounded-md border border-border p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-sm font-medium">
                <Wallet size={15} />
                Send from connected wallet
              </span>
              {isConnected && connectedAddress && (
                <Badge className="max-w-[12rem] truncate">
                  {connectedAddress.slice(0, 6)}…{connectedAddress.slice(-4)}
                </Badge>
              )}
            </div>

            {!isConnected ? (
              <p className="text-xs text-muted-foreground">
                Connect an EVM wallet (MetaMask, WalletConnect, Coinbase, etc.) via the wallet button to use this path.
              </p>
            ) : !isEvm ? (
              <div className="flex items-start gap-2 text-xs text-red-600">
                <AlertCircle className="mt-0.5 shrink-0" size={14} />
                <span>
                  Connected EVM wallets can&apos;t send to {chainConfig?.name}. Use
                  &ldquo;Transfer manually&rdquo; below to fund the {chainConfig?.symbol} address
                  from a {chainConfig?.protocol} wallet.
                </span>
              </div>
            ) : (
              <>
                <Button
                  className="w-full"
                  onClick={() => void sendFromConnected()}
                  disabled={isSending || !amount || !walletAddress}
                >
                  {isSending ? "Confirm in wallet…" : `Send ${amount} ${chainConfig?.symbol} from connected wallet`}
                </Button>
                {txHash && (
                  <div className="flex items-center gap-2 rounded-md border border-green-200 bg-green-50 p-2 text-xs text-green-800">
                    <Check size={14} />
                    <span className="truncate font-mono">{txHash.slice(0, 10)}…{txHash.slice(-6)}</span>
                    {explorerUrl && (
                      <a href={explorerUrl} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex items-center gap-1 font-medium hover:underline">
                        View <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                )}
                {sendError && (
                  <div className="flex items-start gap-2 text-xs text-red-600">
                    <AlertCircle className="mt-0.5 shrink-0" size={14} />
                    <span className="break-words">{sendError.message}</span>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Path 2: transfer manually — always available, any wallet/chain */}
          <div className="space-y-2 rounded-md border border-border p-3">
            <span className="flex items-center gap-2 text-sm font-medium">
              <Copy size={15} />
              Transfer manually
            </span>
            <p className="text-xs text-muted-foreground">
              Copy the agent address above and send {amount || "0"} {chainConfig?.symbol ?? ""}
              {" "}to it from a wallet or exchange that supports {chainConfig?.name ?? "the selected chain"}.
              No connection needed.
            </p>
          </div>

          <div className="flex justify-end border-t border-border pt-4">
            <Button variant="secondary" onClick={onClose}>Done</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
