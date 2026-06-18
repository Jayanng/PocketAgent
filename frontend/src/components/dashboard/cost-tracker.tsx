"use client";

import { useState } from "react";
import { AlertCircle, Coins, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api, type CostTracker, type Timeframe } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const TIMEFRAMES: { label: string; value: Timeframe }[] = [
  { label: "24h", value: "day" },
  { label: "7d", value: "week" },
  { label: "All", value: "all" },
];

export function CostTracker({ agentId }: { agentId?: string | null }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("all");

  // React Query owns fetch state; timeframe changes the query key → refetch.
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["analytics", "cost-tracker", agentId ?? null, timeframe],
    queryFn: () => api.analytics.costTracker(agentId ?? null, timeframe),
    staleTime: 30_000,
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Coins size={16} className="text-primary" />
          <h2 className="text-sm font-semibold">Relay Cost (POKT)</h2>
        </div>
        <div className="flex items-center gap-1">
          {TIMEFRAMES.map((tf) => (
            <Button
              key={tf.value}
              variant={timeframe === tf.value ? "primary" : "secondary"}
              size="sm"
              onClick={() => setTimeframe(tf.value)}
            >
              {tf.label}
            </Button>
          ))}
          <Button
            variant="secondary"
            size="icon"
            onClick={() => void refetch()}
            title="Refresh"
          >
            <RefreshCw size={14} className={isFetching ? "animate-spin" : undefined} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error ? (
          <div className="flex items-start gap-2 text-sm text-red-600">
            <AlertCircle className="mt-0.5 shrink-0" size={14} />
            <span>{error instanceof Error ? error.message : "Failed to load cost data"}</span>
          </div>
        ) : isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : data ? (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border border-border bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Total notional POKT</p>
                <p className="mt-1 text-lg font-semibold">{data.total_pokt_cost.toFixed(4)}</p>
              </div>
              <div className="rounded-md border border-border bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Relays billed</p>
                <p className="mt-1 text-lg font-semibold">{data.total_relays.toLocaleString()}</p>
              </div>
            </div>

            <TrendChart points={data.daily_trend} />

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Cost by chain
              </p>
              <ul className="space-y-1.5">
                {data.per_chain.length === 0 && (
                  <li className="text-sm text-muted-foreground">No cost data yet.</li>
                )}
                {data.per_chain.map((c) => (
                  <li key={c.chain} className="flex items-center justify-between text-sm">
                    <span className="font-medium">{c.chain}</span>
                    <span className="text-muted-foreground">
                      {c.pokt_cost.toFixed(4)} POKT · {Math.round(c.share * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <p className="text-xs text-muted-foreground">{data.note}</p>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

/** Minimal inline SVG line chart for the daily POKT trend. */
function TrendChart({ points }: { points: CostTracker["daily_trend"] }) {
  if (points.length < 2) {
    return (
      <p className="rounded-md border border-dashed border-border bg-muted/30 p-3 text-center text-xs text-muted-foreground">
        Not enough data for a trend yet.
      </p>
    );
  }
  const width = 280;
  const height = 70;
  const pad = 6;
  const values = points.map((p) => p.pokt_cost);
  const max = Math.max(...values, 0.0001);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const stepX = (width - pad * 2) / (points.length - 1);
  const coords = points.map((p, i) => {
    const x = pad + i * stepX;
    const y = height - pad - ((p.pokt_cost - min) / span) * (height - pad * 2);
    return [x, y] as const;
  });
  const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Daily POKT trend
      </p>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[70px] w-full" preserveAspectRatio="none">
        <path d={path} fill="none" stroke="var(--primary)" strokeWidth="1.5" />
        {coords.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="2" fill="var(--primary)" />
        ))}
      </svg>
    </div>
  );
}
