"use client";

import { useMemo, useState } from "react";
import { Activity, AlertCircle, ChevronDown, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api, groupByProtocol, type RelayStats, type Timeframe } from "@/lib/api";
import { Button } from "@/components/ui/button";

const TIMEFRAMES: { label: string; value: Timeframe }[] = [
  { label: "24h", value: "day" },
  { label: "7d", value: "week" },
  { label: "All", value: "all" },
];

const PREVIEW_COUNT = 5;

const maxRelays = (perChain: RelayStats["per_chain"]) =>
  perChain.reduce((m, c) => Math.max(m, c.relays), 1);

export function RelayStats({ agentId }: { agentId?: string | null }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["analytics", "relay-stats", agentId ?? null, timeframe],
    queryFn: () => api.analytics.relayStats(agentId ?? null, timeframe),
    staleTime: 30_000,
  });

  const successPct = data ? Math.round(data.success_rate * 100) : 0;
  const peak = data ? maxRelays(data.per_chain) : 1;

  const grouped = useMemo(
    () => groupByProtocol(data?.per_chain ?? []),
    [data]
  );

  const toggleSection = (protocol: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(protocol)) next.delete(protocol);
      else next.add(protocol);
      return next;
    });
  };

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-sm p-6 shadow-sm space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <Activity size={18} className="text-primary animate-pulse-soft" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground/80 font-mono">Relay Analytics</h2>
            <p className="text-[11px] text-muted-foreground">Pocket Network Gateway traffic</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="flex border border-border/60 rounded-md p-0.5 bg-muted/40">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.value}
                type="button"
                className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
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
            title="Refresh analytics"
            className="h-7 w-7 animate-fade-in"
          >
            <RefreshCw size={13} className={isFetching ? "animate-spin" : undefined} />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2.5 text-sm text-red-500 bg-red-500/5 border border-red-500/10 rounded-lg p-4 font-mono">
          <AlertCircle className="mt-0.5 shrink-0" size={15} />
          <span>{error instanceof Error ? error.message : "Failed to load relay stats"}</span>
        </div>
      ) : isLoading ? (
        <div className="space-y-4 py-8">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 skeleton" />
            ))}
          </div>
          <div className="h-20 skeleton" />
          <div className="h-32 skeleton" />
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Key Metrics Deck */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard label="Total Relays" value={data.total_relays.toLocaleString()} />
            <MetricCard label="Avg Latency" value={`${data.avg_latency_ms.toFixed(0)} ms`} />
            <MetricCard
              label="Success Rate"
              value={`${successPct}%`}
              tone={successPct >= 95 ? "good" : successPct >= 85 ? "warn" : "bad"}
            />
            <MetricCard label="POKT Estimate" value={`${data.total_pokt_cost.toFixed(4)}`} />
          </div>

          {/* SVG Trend Chart */}
          {data.daily_usage && data.daily_usage.length >= 2 && (
            <div className="rounded-lg border border-border/40 bg-muted/20 p-4 space-y-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground font-semibold">Daily Relay Volume</span>
              <RelayTrendChart points={data.daily_usage} />
            </div>
          )}

          {/* Relays per chain */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 font-mono border-b border-border/30 pb-1">
              Relays per Chain
            </h3>
            {data.per_chain.length === 0 ? (
              <p className="text-xs text-muted-foreground font-mono">No relay activity detected in this timeframe.</p>
            ) : (
              <div className="space-y-5">
                {grouped.map((section) => {
                  const isExpanded = expanded.has(section.protocol);
                  const visible = isExpanded ? section.items : section.items.slice(0, PREVIEW_COUNT);
                  const hiddenCount = section.items.length - visible.length;
                  return (
                    <div key={section.protocol} className="space-y-2.5">
                      <div className="flex items-center justify-between border-l-2 border-primary/40 pl-2">
                        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-foreground/80 font-mono">
                          {section.label}
                        </h4>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {section.items.length} active
                        </span>
                      </div>
                      <ul className="space-y-3 pl-2">
                        {visible.map((c) => (
                          <li key={c.chain} className="space-y-1 group">
                            <div className="flex items-baseline justify-between text-xs">
                              <span className="font-medium text-foreground/90 group-hover:text-primary transition-colors">
                                {c.chain}
                              </span>
                              <span className="font-mono text-muted-foreground text-[10px] space-x-1.5">
                                <span className="text-foreground/75 font-medium">{c.relays.toLocaleString()}</span>
                                <span>·</span>
                                <span>{c.avg_latency_ms.toFixed(0)} ms</span>
                              </span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-muted/60 overflow-hidden relative">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-primary/80 to-primary transition-all duration-500 ease-out"
                                style={{ width: `${(c.relays / peak) * 100}%` }}
                              />
                            </div>
                          </li>
                        ))}
                      </ul>
                      {hiddenCount > 0 && (
                        <button
                          type="button"
                          onClick={() => toggleSection(section.protocol)}
                          className="mt-1.5 ml-2 inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline font-mono"
                        >
                          <ChevronDown
                            size={11}
                            className={`transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                          />
                          {isExpanded ? "Show less" : `See ${hiddenCount} more`}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "warn" | "bad";
}) {
  const toneClass =
    tone === "good"
      ? "text-green-500"
      : tone === "warn"
        ? "text-amber-500"
        : tone === "bad"
          ? "text-red-500"
          : "text-foreground";
  return (
    <div className="rounded-lg border border-border/40 bg-muted/20 p-3 flex flex-col justify-between">
      <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`mt-1.5 text-base font-semibold font-mono ${toneClass}`}>{value}</p>
    </div>
  );
}

function RelayTrendChart({ points }: { points: RelayStats["daily_usage"] }) {
  const width = 500;
  const height = 90;
  const padX = 12;
  const padY = 8;

  const values = points.map((p) => p.relays);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  const stepX = (width - padX * 2) / (points.length - 1);
  const coords = points.map((p, i) => {
    const x = padX + i * stepX;
    const y = height - padY - ((p.relays - min) / range) * (height - padY * 2);
    return [x, y] as const;
  });

  const pathLine = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const pathFill = `${pathLine} L${coords[coords.length - 1][0].toFixed(1)},${(height - padY).toFixed(1)} L${coords[0][0].toFixed(1)},${(height - padY).toFixed(1)} Z`;

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[90px] w-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="relayGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Horizontal grid lines */}
        <line x1={padX} y1={padY} x2={width - padX} y2={padY} stroke="var(--border)" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.3" />
        <line x1={padX} y1={height / 2} x2={width - padX} y2={height / 2} stroke="var(--border)" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.3" />
        <line x1={padX} y1={height - padY} x2={width - padX} y2={height - padY} stroke="var(--border)" strokeWidth="0.5" opacity="0.3" />

        {/* Filled Area */}
        <path d={pathFill} fill="url(#relayGradient)" />

        {/* Line Path */}
        <path d={pathLine} fill="none" stroke="var(--primary)" strokeWidth="1.5" />

        {/* Data points */}
        {coords.map(([x, y], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="3"
            className="fill-card stroke-primary stroke-[1.5]"
          />
        ))}
      </svg>
    </div>
  );
}
