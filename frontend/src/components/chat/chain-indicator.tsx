"use client";

import { Activity } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { CHAIN_CONFIGS } from "@/lib/constants";
import { cn } from "@/lib/utils";

const chainStyles: Record<string, string> = {
  ethereum: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300",
  polygon:
    "border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-900 dark:bg-purple-950 dark:text-purple-300",
  bsc: "border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-300",
  solana:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
  arbitrum:
    "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-300",
  base: "border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-300",
  optimism:
    "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300",
};

const labelForChain = (chain: string) => {
  const key = chain.toLowerCase().replace(/\s+/g, "-") as keyof typeof CHAIN_CONFIGS;
  const config = CHAIN_CONFIGS[key];
  return config?.symbol ?? chain.slice(0, 4).toUpperCase();
};

type ChainIndicatorProps = {
  chains: string[];
  isLoading?: boolean;
  compact?: boolean;
};

export function ChainIndicator({ chains, isLoading = false, compact = false }: ChainIndicatorProps) {
  const visibleChains = chains.slice(0, compact ? 4 : 8);

  if (!visibleChains.length && !isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Activity size={14} />
        No chain calls yet
      </div>
    );
  }

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      {isLoading && (
        <span className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <span className="h-2 w-2 rounded-full bg-primary motion-safe:animate-pulse" />
          Querying
        </span>
      )}
      {visibleChains.map((chain) => (
        <Badge
          key={chain}
          className={cn(
            "h-6 min-w-10 justify-center",
            isLoading && "motion-safe:animate-pulse",
            chainStyles[chain.toLowerCase()] ?? "bg-muted"
          )}
          title={CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS]?.name ?? chain}
        >
          {labelForChain(chain)}
        </Badge>
      ))}
      {chains.length > visibleChains.length && (
        <Badge className="h-6">+{chains.length - visibleChains.length}</Badge>
      )}
    </div>
  );
}
