"use client";

import { Activity } from "lucide-react";

import { CHAIN_CONFIGS, chainBadgeSymbol } from "@/lib/constants";
import { cn } from "@/lib/utils";

type ChainIndicatorProps = {
  chains: string[];
  isLoading?: boolean;
  compact?: boolean;
};

export function ChainIndicator({ chains, isLoading = false, compact = false }: ChainIndicatorProps) {
  const visibleChains = chains.slice(0, compact ? 4 : 8);

  if (!visibleChains.length && !isLoading) {
    return (
      <div className="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground/60">
        <Activity size={12} className="opacity-70" />
        No active calls
      </div>
    );
  }

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
      {isLoading && (
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-soft" />
          Querying RPC…
        </span>
      )}
      {visibleChains.map((chain) => (
        <span
          key={chain}
          className={cn(
            "inline-flex items-center justify-center rounded border border-border/50 bg-muted/20 px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground uppercase tracking-wider shadow-sm",
            isLoading && "animate-pulse-soft"
          )}
          title={CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS]?.name ?? chain}
        >
          {chainBadgeSymbol(chain)}
          <span className="ml-1 shrink-0 rounded bg-green-500/10 px-1 py-0 text-[7px] font-semibold tracking-widest text-green-500/80">
            MAINNET
          </span>
        </span>
      ))}
      {chains.length > visibleChains.length && (
        <span className="inline-flex items-center justify-center rounded border border-border/50 bg-muted/20 px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground/50">
          +{chains.length - visibleChains.length}
        </span>
      )}
    </div>
  );
}
