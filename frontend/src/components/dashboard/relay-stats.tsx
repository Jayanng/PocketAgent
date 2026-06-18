"use client";

import { useMemo, useState } from "react";
import { Activity, AlertCircle, ChevronDown, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api, groupByProtocol, type RelayStats, type Timeframe } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const TIMEFRAMES: { label: string; value: Timeframe }[] = [
  { label: "24h", value: "day" },
  { label: "7d", value: "week" },
  { label: "All", value: "all" },
];

const PREVIEW_COUNT = 5; // chains shown per protocol section before "see more"

const maxRelays = (perChain: RelayStats["per_chain"]) =>
  perChain.reduce((m, c) => Math.max(m, c.relays), 1);

export function RelayStats({ agentId }: { agentId?: string | null }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // React Query owns the fetch state — no manual useState/useEffect, which
  // keeps this clear of the react-hooks/set-state-in-effect rule. Changing
  // the timeframe changes the query key, so the data refetches automatically.
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
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-primary" />
          <h2 className="text-sm font-semibold">Pocket Relays</h2>
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
            <span>{error instanceof Error ? error.message : "Failed to load relay stats"}</span>
          </div>
        ) : isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : data ? (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Metric label="Total relays" value={data.total_relays.toLocaleString()} />
              <Metric label="Avg latency" value={`${data.avg_latency_ms.toFixed(0)} ms`} />
              <Metric
                label="Success rate"
                value={`${successPct}%`}
                tone={successPct >= 90 ? "good" : successPct >= 50 ? "warn" : "bad"}
              />
              <Metric label="Notional POKT" value={data.total_pokt_cost.toFixed(4)} />
            </div>

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Relays per chain
              </p>
              {data.per_chain.length === 0 ? (
                <p className="text-sm text-muted-foreground">No relay activity yet.</p>
              ) : (
                <div className="space-y-4">
                  {grouped.map((section) => {
                    const isExpanded = expanded.has(section.protocol);
                    const visible = isExpanded ? section.items : section.items.slice(0, PREVIEW_COUNT);
                    const hiddenCount = section.items.length - visible.length;
                    return (
                      <div key={section.protocol}>
                        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          {section.label}
                          <span className="ml-2 font-normal text-muted-foreground/70">
                            {section.items.length} chains
                          </span>
                        </h3>
                        <ul className="space-y-2">
                          {visible.map((c) => (
                            <li key={c.chain} className="space-y-1">
                              <div className="flex items-center justify-between text-sm">
                                <span className="font-medium">{c.chain}</span>
                                <span className="text-muted-foreground">
                                  {c.relays} · {c.avg_latency_ms.toFixed(0)} ms
                                </span>
                              </div>
                              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                                <div
                                  className="h-full rounded-full bg-primary transition-all"
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
                            className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                          >
                            <ChevronDown
                              size={12}
                              className={isExpanded ? "rotate-180 transition-transform" : "transition-transform"}
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
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Metric({
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
      ? "text-green-600"
      : tone === "warn"
        ? "text-amber-600"
        : tone === "bad"
          ? "text-red-600"
          : "text-foreground";
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}
