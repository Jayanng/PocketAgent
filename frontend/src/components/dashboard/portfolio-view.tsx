"use client";

import { useState } from "react";
import { AlertCircle, PieChart, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const DISTRIBUTION_COLORS = [
  "var(--primary)",
  "oklch(62% 0.14 180)",
  "oklch(64% 0.16 140)",
  "oklch(66% 0.16 90)",
  "oklch(68% 0.16 50)",
  "oklch(70% 0.15 20)",
];

export function PortfolioView() {
  const [address, setAddress] = useState("");
  const [submitted, setSubmitted] = useState("");

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["analytics", "portfolio", submitted],
    queryFn: () => api.analytics.portfolio(submitted),
    enabled: submitted.trim().length > 0,
    staleTime: 30_000,
  });

  const holdings = data?.holdings ?? [];
  const valued = holdings.filter((h) => h.usd_value != null);

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6 shadow-sm space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <PieChart size={18} className="text-primary" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground/80 font-mono">Portfolio Analyzer</h2>
            <p className="text-[11px] text-muted-foreground">Multi-chain token balances</p>
          </div>
        </div>
        {data && (
          <Button variant="secondary" size="icon" onClick={() => void refetch()} title="Refresh balances" className="h-7 w-7">
            <RefreshCw size={13} className={isFetching ? "animate-spin" : undefined} />
          </Button>
        )}
      </div>

      <div className="space-y-4">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(address);
          }}
        >
          <Input
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="0x… wallet address"
            className="font-mono text-xs focus-visible:ring-primary/20"
          />
          <Button type="submit" disabled={!address.trim() || isLoading} className="h-10 text-xs px-4">
            {isLoading ? "Analyzing…" : "Analyze"}
          </Button>
        </form>

        {error ? (
          <div className="flex items-start gap-2.5 text-sm text-red-500 bg-red-500/5 border border-red-500/10 rounded-lg p-4 font-mono">
            <AlertCircle className="mt-0.5 shrink-0" size={15} />
            <span>{error instanceof Error ? error.message : "Failed to load portfolio"}</span>
          </div>
        ) : data ? (
          <div className="space-y-5">
            {/* Total balance card */}
            <div className="rounded-lg border border-border/40 bg-muted/20 p-4 space-y-1">
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Aggregate Valuation</p>
              <p className="text-xl font-bold font-mono text-foreground/90">
                ${data.total_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </p>
              <p className="text-[9px] font-mono text-muted-foreground/75">
                {data.chains_checked} chains scanned · {new Date(data.checked_at).toLocaleTimeString()}
              </p>
            </div>

            {/* Distribution segments */}
            {valued.length > 0 && (
              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-semibold">Distribution</span>
                <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted/40 border border-border/20">
                  {valued.map((h, i) => (
                    <div
                      key={h.chain}
                      style={{
                        width: `${h.share * 100}%`,
                        background: DISTRIBUTION_COLORS[i % DISTRIBUTION_COLORS.length],
                      }}
                      title={`${h.name}: ${Math.round(h.share * 100)}%`}
                      className="transition-all duration-300 first:rounded-l-full last:rounded-r-full"
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Balances table */}
            <div className="overflow-x-auto border border-border/30 rounded-lg bg-muted/10">
              <table className="w-full text-xs font-mono text-left border-collapse">
                <thead>
                  <tr className="border-b border-border/40 bg-muted/20 text-muted-foreground/80 uppercase text-[9px] tracking-wider">
                    <th className="py-2.5 px-3 font-semibold">Chain</th>
                    <th className="py-2.5 px-3 font-semibold">Balance</th>
                    <th className="py-2.5 px-3 text-right font-semibold">USD Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/20">
                  {holdings.map((h) => (
                    <tr key={h.chain} className="hover:bg-muted/10 transition-colors">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-foreground/90 font-sans text-xs">{h.name}</div>
                        <div className="text-[9px] text-muted-foreground font-mono uppercase mt-0.5">{h.protocol}</div>
                      </td>
                      <td className="py-2.5 px-3 text-foreground/80 font-mono text-xs">
                        {h.formatted ? `${parseFloat(h.formatted).toLocaleString(undefined, { maximumFractionDigits: 6 })} ${h.symbol}` : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right text-foreground/90 font-mono text-xs font-medium">
                        {h.usd_value != null
                          ? `$${h.usd_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : !isLoading ? (
          <p className="text-[11px] font-mono text-muted-foreground/75 py-2">
            Enter a public wallet address to query balance holdings across multichain node clusters.
          </p>
        ) : null}
      </div>
    </div>
  );
}
