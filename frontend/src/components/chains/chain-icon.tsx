"use client";

import { CHAIN_CONFIGS, chainBadgeSymbol } from "@/lib/constants";
import { cn } from "@/lib/utils";

const protocolStyles: Record<string, string> = {
  evm: "border-blue-200 bg-blue-50 text-blue-700",
  solana: "border-emerald-200 bg-emerald-50 text-emerald-700",
  cosmos: "border-violet-200 bg-violet-50 text-violet-700",
  sui: "border-cyan-200 bg-cyan-50 text-cyan-700",
  near: "border-lime-200 bg-lime-50 text-lime-700",
  tron: "border-red-200 bg-red-50 text-red-700",
};

type ChainIconProps = {
  chain: string;
  className?: string;
};

export function ChainIcon({ chain, className }: ChainIconProps) {
  const config = CHAIN_CONFIGS[chain as keyof typeof CHAIN_CONFIGS];
  const label = chainBadgeSymbol(chain);
  const protocol = config?.protocol ?? "evm";

  return (
    <span
      className={cn(
        "inline-flex h-7 w-9 shrink-0 items-center justify-center rounded-md border text-[10px] font-bold",
        protocolStyles[protocol] ?? "border-border bg-muted text-muted-foreground",
        className
      )}
      title={config?.name ?? chain}
      aria-label={config?.name ?? chain}
    >
      {label.slice(0, 4)}
    </span>
  );
}
