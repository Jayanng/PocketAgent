"use client";

import { WalletCards } from "lucide-react";
import { useAccount, useBalance } from "wagmi";

import { ChainIcon } from "@/components/chains/chain-icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CHAIN_CONFIGS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { useAgentStore } from "@/store/agent-store";

const summaryChains = ["ethereum", "polygon", "arbitrum", "optimism", "bsc", "avalanche", "base"] as const;

type BalanceDisplayProps = {
  className?: string;
  compact?: boolean;
};

function ConnectedChainBalance({ chainKey }: { chainKey: (typeof summaryChains)[number] }) {
  const { address, isConnected } = useAccount();
  const config = CHAIN_CONFIGS[chainKey];
  const chainId = typeof config.chainId === "number" ? config.chainId : undefined;
  const { data, isLoading, error } = useBalance({
    address,
    chainId,
    query: {
      enabled: Boolean(isConnected && address && chainId),
      staleTime: 30_000,
    },
  });

  return (
    <div className="flex items-center justify-between gap-2 rounded-md border border-border bg-background px-3 py-2">
      <div className="flex min-w-0 items-center gap-2">
        <ChainIcon chain={chainKey} />
        <span className="truncate text-xs font-medium">{config.name}</span>
      </div>
      <span className="shrink-0 text-xs font-semibold">
        {error ? "Error" : isLoading ? "..." : data ? `${Number(data.formatted).toFixed(4)} ${data.symbol}` : "0"}
      </span>
    </div>
  );
}

export function BalanceDisplay({ className, compact = false }: BalanceDisplayProps) {
  const { address, isConnected } = useAccount();
  const { selectedAgent, selectedAgentId, balances, isLoadingBalances, loadBalances } = useAgentStore();

  if (!isConnected || !address) {
    return (
      <div className={cn("rounded-md border border-border bg-background p-3", className)}>
        <div className="flex items-center gap-2 text-sm font-semibold">
          <WalletCards size={16} />
          Wallet Balances
        </div>
        <p className="mt-2 text-xs text-muted-foreground">Connect a wallet to query native balances through Pocket RPC.</p>
      </div>
    );
  }

  const agentChains = selectedAgent?.chains ?? [];

  return (
    <div className={cn("rounded-md border border-border bg-background p-3", className)}>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase text-muted-foreground">Connected Wallet</p>
          <p className="mt-1 truncate text-sm font-semibold">{address}</p>
        </div>
        <Badge>{summaryChains.length} EVM</Badge>
      </div>

      {!compact && (
        <div className="mt-3 grid gap-2">
          {summaryChains.map((chainKey) => (
            <ConnectedChainBalance key={chainKey} chainKey={chainKey} />
          ))}
        </div>
      )}

      {selectedAgent && (
        <div className="mt-3 border-t border-border pt-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Agent Wallet</p>
            <Button
              variant="secondary"
              size="sm"
              disabled={!selectedAgentId || isLoadingBalances}
              onClick={() => selectedAgentId && void loadBalances(selectedAgentId)}
            >
              {isLoadingBalances ? "Loading..." : "Refresh"}
            </Button>
          </div>
          <div className="mt-2 space-y-2">
            {agentChains.slice(0, compact ? 3 : agentChains.length).map((chain) => {
              const balance = balances[chain];
              return (
                <div key={chain} className="flex items-center justify-between gap-2 text-xs">
                  <span className="truncate text-muted-foreground">{CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS]?.name ?? chain}</span>
                  <span className="shrink-0 font-semibold">
                    {balance?.error ? "Error" : balance?.formatted ?? balance?.amount_decimal ?? balance?.amount ?? "Not loaded"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
