"use client";

import { useState } from "react";
import { AlertCircle, PieChart, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
  // `submitted` is the address actually being queried; it doubles as the
  // query key. Empty until the user submits the form (query stays disabled).
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
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <PieChart size={16} className="text-primary" />
          <h2 className="text-sm font-semibold">Multi-chain Portfolio</h2>
        </div>
        {data && (
          <Button variant="secondary" size="icon" onClick={() => void refetch()} title="Refresh">
            <RefreshCw size={14} className={isFetching ? "animate-spin" : undefined} />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
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
            className="font-mono text-sm"
          />
          <Button type="submit" disabled={!address.trim() || isLoading}>
            {isLoading ? "Loading…" : "Analyze"}
          </Button>
        </form>

        {error ? (
          <div className="flex items-start gap-2 text-sm text-red-600">
            <AlertCircle className="mt-0.5 shrink-0" size={14} />
            <span>{error instanceof Error ? error.message : "Failed to load portfolio"}</span>
          </div>
        ) : data ? (
          <>
            <div className="rounded-md border border-border bg-muted/40 p-3">
              <p className="text-xs text-muted-foreground">Total portfolio value</p>
              <p className="mt-1 text-2xl font-semibold">
                ${data.total_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Across {data.chains_checked} chains · checked {new Date(data.checked_at).toLocaleTimeString()}
              </p>
            </div>

            {valued.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Distribution
                </p>
                <div className="flex h-2 w-full overflow-hidden rounded-full">
                  {valued.map((h, i) => (
                    <div
                      key={h.chain}
                      style={{
                        width: `${h.share * 100}%`,
                        background: DISTRIBUTION_COLORS[i % DISTRIBUTION_COLORS.length],
                      }}
                      title={`${h.name}: ${Math.round(h.share * 100)}%`}
                    />
                  ))}
                </div>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Chain</th>
                    <th className="py-2 pr-3 font-medium">Balance</th>
                    <th className="py-2 pr-3 text-right font-medium">USD</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => (
                    <tr key={h.chain} className="border-b border-border/60">
                      <td className="py-2 pr-3">
                        <div className="font-medium">{h.name}</div>
                        <div className="text-xs text-muted-foreground">{h.protocol}</div>
                      </td>
                      <td className="py-2 pr-3 font-mono">
                        {h.formatted ? `${h.formatted} ${h.symbol}` : "—"}
                      </td>
                      <td className="py-2 pr-3 text-right">
                        {h.usd_value != null
                          ? `$${h.usd_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : !isLoading ? (
          <p className="text-sm text-muted-foreground">
            Enter a wallet address to fetch balances across chains via Pocket RPC.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
