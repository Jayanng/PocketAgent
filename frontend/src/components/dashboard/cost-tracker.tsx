"use client";

import { useState } from "react";
import { AlertCircle, Coins, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api, type CostTracker as CostTrackerType, type Timeframe } from "@/lib/api";
import { Button } from "@/components/ui/button";

const TIMEFRAMES: { label: string; value: Timeframe }[] = [
  { label: "24h", value: "day" },
  { label: "7d", value: "week" },
  { label: "All", value: "all" },
];

export function CostTracker({ agentId }: { agentId?: string | null }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("all");

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["analytics", "cost-tracker", agentId ?? null, timeframe],
    queryFn: () => api.analytics.costTracker(agentId ?? null, timeframe),
    staleTime: 30_000,
  });

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6 shadow-sm space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <Coins size={18} className="text-primary" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground/80 font-mono">Cost Ledger</h2>
            <p className="text-[11px] text-muted-foreground">POKT token cost calculation</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="flex border border-border/60 rounded-md p-0.5 bg-muted/40">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.value}
                type="button"
                className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                  timeframe === tf.value
                    ? "bg-card text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setTimeframe(tf.value)}
              >
                {tf.label}
              </button>
            ))}
          </div>
          <Button
            variant="secondary"
            size="icon"
            onClick={() => void refetch()}
            title="Refresh cost metrics"
            className="h-7 w-7"
          >
            <RefreshCw size={13} className={isFetching ? "animate-spin" : undefined} />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2.5 text-sm text-red-500 bg-red-500/5 border border-red-500/10 rounded-lg p-4 font-mono">
          <AlertCircle className="mt-0.5 shrink-0" size={15} />
          <span>{error instanceof Error ? error.message : "Failed to load cost data"}</span>
        </div>
      ) : isLoading ? (
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="h-16 skeleton" />
            <div className="h-16 skeleton" />
          </div>
          <div className="h-20 skeleton" />
          <div className="h-28 skeleton" />
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Metrics summary */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border/40 bg-muted/20 p-3">
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Notional Cost (POKT)</p>
              <p className="mt-1.5 text-base font-semibold font-mono">{data.total_pokt_cost.toFixed(4)}</p>
            </div>
            <div className="rounded-lg border border-border/40 bg-muted/20 p-3">
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Relays Billed</p>
              <p className="mt-1.5 text-base font-semibold font-mono">{data.total_relays.toLocaleString()}</p>
            </div>
          </div>

          {/* SVG Daily Trend Chart */}
          <div className="rounded-lg border border-border/40 bg-muted/20 p-4 space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-semibold">Daily POKT Trend</span>
            <TrendChart points={data.daily_trend} />
          </div>

          {/* Cost by chain */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 font-mono border-b border-border/30 pb-1">
              Cost by Chain
            </h3>
            {data.per_chain.length === 0 ? (
              <p className="text-xs text-muted-foreground font-mono">No cost data available for this timeframe.</p>
            ) : (
              <ul className="space-y-3.5">
                {data.per_chain.map((c) => (
                  <li key={c.chain} className="space-y-1 group">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-foreground/90 group-hover:text-primary transition-colors">{c.chain}</span>
                      <span className="font-mono text-muted-foreground text-[10px] space-x-1.5">
                        <span className="text-foreground/75 font-medium">{c.pokt_cost.toFixed(4)} POKT</span>
                        <span>·</span>
                        <span>{Math.round(c.share * 100)}%</span>
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-muted/60 overflow-hidden relative">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary/80 to-primary transition-all duration-500 ease-out"
                        style={{ width: `${c.share * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {data.note && (
            <p className="text-[10px] font-mono text-muted-foreground/70 border-t border-border/30 pt-3">
              {data.note}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

function TrendChart({ points }: { points: CostTrackerType["daily_trend"] }) {
  if (points.length < 2) {
    return (
      <p className="text-[10px] font-mono text-muted-foreground/70 py-4 text-center">
        Insufficient data for trend chart.
      </p>
    );
  }
  const width = 280;
  const height = 75;
  const padX = 10;
  const padY = 6;
  const values = points.map((p) => p.pokt_cost);
  const max = Math.max(...values, 0.0001);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const stepX = (width - padX * 2) / (points.length - 1);
  const coords = points.map((p, i) => {
    const x = padX + i * stepX;
    const y = height - padY - ((p.pokt_cost - min) / span) * (height - padY * 2);
    return [x, y] as const;
  });
  const pathLine = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const pathFill = `${pathLine} L${coords[coords.length - 1][0].toFixed(1)},${(height - padY).toFixed(1)} L${coords[0][0].toFixed(1)},${(height - padY).toFixed(1)} Z`;

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[75px] w-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <line x1={padX} y1={padY} x2={width - padX} y2={padY} stroke="var(--border)" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.3" />
        <line x1={padX} y1={height - padY} x2={width - padX} y2={height - padY} stroke="var(--border)" strokeWidth="0.5" opacity="0.3" />

        <path d={pathFill} fill="url(#costGradient)" />
        <path d={pathLine} fill="none" stroke="var(--primary)" strokeWidth="1.5" />

        {coords.map(([x, y], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="2.5"
            className="fill-card stroke-primary stroke-[1.5]"
          />
        ))}
      </svg>
    </div>
  );
}
